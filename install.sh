#!/usr/bin/env bash
set -euo pipefail

if command -v pipx &>/dev/null; then
    _pipx_venvs="$(pipx environment 2>/dev/null | sed -n 's/^PIPX_LOCAL_VENVS=//p')"
fi
PIPX_LOCAL_VENVS="${_pipx_venvs:-${PIPX_HOME:-$HOME/.local/share/pipx}/venvs}"
PIPX_PYTHON="$PIPX_LOCAL_VENVS/penelope/bin/python3"
if [ -x "$PIPX_PYTHON" ]; then
    PY="$PIPX_PYTHON"
else
    PY="python3"
fi

# The actual running file — bin/penelope.py takes precedence over site-packages
# because Python adds the entrypoint script's directory to sys.path[0]
PENELOPE_BIN="$(dirname "$PIPX_PYTHON")"
PENELOPE_PY="$PENELOPE_BIN/penelope.py"

if [ ! -f "$PENELOPE_PY" ]; then
    echo "[!] penelope.py not found at $PENELOPE_PY" >&2
    exit 1
fi

MODULE_LINK="$PENELOPE_BIN/penelopeplus_modules"
MODULES_SRC="$(cd "$(dirname "$0")/modules" && pwd)"

echo "[*] penelope.py: $PENELOPE_PY"
echo "[*] modules src:  $MODULES_SRC"

# --- symlink modules dir ---
if [ -L "$MODULE_LINK" ]; then
    echo "[*] Updating symlink: $MODULE_LINK -> $MODULES_SRC"
    ln -sfn "$MODULES_SRC" "$MODULE_LINK"
elif [ -e "$MODULE_LINK" ]; then
    echo "[!] $MODULE_LINK exists and is not a symlink. Remove it manually." >&2
    exit 1
else
    echo "[*] Creating symlink: $MODULE_LINK -> $MODULES_SRC"
    ln -s "$MODULES_SRC" "$MODULE_LINK"
fi

# --- inject loader block ---
LOADER_MARKER="# PenelopePlus loader"
LOADER_VERSION="v2"
echo "[*] Patching penelope.py (loader)..."
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
        end = start + 1  # fallback: remove just the one line
    del lines[strip_from:end]
    print(f"[*] Replaced existing loader block")

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
print(f"[+] Loader injected at line {insert_at + 1}")
PYEOF

# --- patch prompt: (Penelope) magenta -> (Penelope+) yellow ---
if grep -qF "paint('Penelope+').yellow" "$PENELOPE_PY"; then
    echo "[*] Prompt patch already present — skipping"
else
    echo "[*] Patching penelope.py (prompt)..."
    "$PY" - "$PENELOPE_PY" <<'PYEOF'
import sys, pathlib

target = pathlib.Path(sys.argv[1])
OLD = "paint('Penelope').magenta"
NEW = "paint('Penelope+').yellow"

text = target.read_text()
if NEW in text:
    print("[*] Already patched")
    sys.exit(0)
if OLD not in text:
    print("[!] Could not find prompt string", file=sys.stderr)
    sys.exit(1)
target.write_text(text.replace(OLD, NEW, 1))
print("[+] Prompt patched: (Penelope) magenta -> (Penelope+) yellow")
PYEOF
fi

echo "[+] Done. Add modules to: $MODULES_SRC"
