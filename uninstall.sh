#!/usr/bin/env bash
set -euo pipefail

PIPX_LOCAL_VENVS="${PIPX_HOME:-$HOME/.local/share/pipx}/venvs"
for _pkg in penelope-shell-handler penelope; do
    _candidate="$PIPX_LOCAL_VENVS/$_pkg/bin/python3"
    if [ -x "$_candidate" ]; then
        PIPX_PYTHON="$_candidate"
        break
    fi
done
if [ -z "${PIPX_PYTHON:-}" ]; then
    echo "[!] Could not find penelope pipx venv" >&2
    exit 1
fi

PY="$PIPX_PYTHON"
PENELOPE_BIN="$(dirname "$PIPX_PYTHON")"

if [ -f "$PENELOPE_BIN/penelope.py" ]; then
    PENELOPE_PY="$PENELOPE_BIN/penelope.py"
else
    PENELOPE_PY="$("$PY" -c "import importlib.util; print(importlib.util.find_spec('penelope').origin)")"
fi

PENELOPE_BAK="${PENELOPE_PY}.bak"
MODULE_LINK="$(dirname "$PENELOPE_PY")/penelopeplus_modules"

if [ ! -f "$PENELOPE_PY" ]; then
    echo "[!] penelope.py not found" >&2
    exit 1
fi

# --- remove symlink ---
if [ -L "$MODULE_LINK" ]; then
    echo "[*] Removing symlink: $MODULE_LINK"
    rm "$MODULE_LINK"
else
    echo "[*] No symlink at $MODULE_LINK"
fi

# --- restore original penelope.py from backup ---
if [ -f "$PENELOPE_BAK" ]; then
    cp "$PENELOPE_BAK" "$PENELOPE_PY"
    rm "$PENELOPE_BAK"
    echo "[+] penelope.py restored from backup, backup removed"
else
    echo "[!] No backup found at $PENELOPE_BAK — penelope.py left as-is" >&2
fi

echo "[+] Uninstall complete."
