#!/usr/bin/env bash
set -euo pipefail

PIPX_PYTHON="/root/.local/share/pipx/venvs/penelope/bin/python3"
if [ -x "$PIPX_PYTHON" ]; then
    PY="$PIPX_PYTHON"
else
    PY="python3"
fi

PENELOPE_BIN="$(dirname "$PIPX_PYTHON")"
PENELOPE_PY="$PENELOPE_BIN/penelope.py"
MODULE_LINK="$PENELOPE_BIN/penelopeplus_modules"
LOADER_MARKER="# PenelopePlus loader"

if [ ! -f "$PENELOPE_PY" ]; then
    echo "[!] penelope.py not found at $PENELOPE_PY" >&2
    exit 1
fi

# --- remove symlink ---
if [ -L "$MODULE_LINK" ]; then
    echo "[*] Removing symlink: $MODULE_LINK"
    rm "$MODULE_LINK"
else
    echo "[*] No symlink at $MODULE_LINK"
fi

# --- strip loader block ---
if grep -qF "$LOADER_MARKER" "$PENELOPE_PY"; then
    echo "[*] Removing loader block..."
    "$PY" - "$PENELOPE_PY" "$LOADER_MARKER" <<'PYEOF'
import sys, pathlib

target = pathlib.Path(sys.argv[1])
marker = sys.argv[2]
end_marker = f"{marker} end"

lines = target.read_text().splitlines(keepends=True)
start = None
end = None
for i, line in enumerate(lines):
    if line.strip().startswith(marker) and start is None:
        start = i
    if start is not None and end_marker in line and i > start:
        end = i + 1
        break

if start is None:
    print("[*] Marker not found")
    sys.exit(0)

strip_from = start
while strip_from > 0 and lines[strip_from - 1].strip() == '':
    strip_from -= 1

del lines[strip_from:end]
target.write_text(''.join(lines))
print("[+] Loader block removed")
PYEOF
else
    echo "[*] No loader block found"
fi

# --- revert prompt patch ---
if grep -qF "paint('Penelope+').yellow" "$PENELOPE_PY"; then
    echo "[*] Reverting prompt patch..."
    "$PY" - "$PENELOPE_PY" <<'PYEOF'
import sys, pathlib
target = pathlib.Path(sys.argv[1])
text = target.read_text()
target.write_text(text.replace("paint('Penelope+').yellow", "paint('Penelope').magenta", 1))
print("[+] Prompt reverted")
PYEOF
else
    echo "[*] No prompt patch found"
fi

echo "[+] Uninstall complete."
