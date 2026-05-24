# PenelopePlus

An extension kit for [penelope-shell-handler](https://github.com/brightio/penelope) (tested against v0.19.1).

PenelopePlus injects a module loader into penelope at install time. Modules are Python files dropped into the `modules/` directory and picked up automatically on each session. It also patches several upstream behaviours around Windows shell handling.

## Requirements

- [penelope-shell-handler](https://github.com/brightio/penelope) v0.19.1 installed via pipx
- Python 3.10+

## Install

```bash
bash install.sh
```

The installer patches penelope in place and creates a symlink from the penelope package directory into `modules/`. A backup of the original `penelope.py` is kept at `penelope.py.bak`.

To undo all changes:

```bash
bash uninstall.sh
```

## Writing Modules

Copy `modules/template.py`, rename it, and implement the `run(session, args)` method. The class name becomes the module name in penelope.

See [docs/module-api.md](docs/module-api.md) for the full API reference.

## Upstream Patches Applied

- Windows spawn: adds PowerShell reverse shell (`spawn` command now works on Windows sessions)
- Windows upload: PSH sessions use `Invoke-WebRequest` + `Expand-Archive` instead of the mshta bat-file path
- Windows tmp: PSH sessions use `$env:TEMP` instead of `%TEMP%` via cmd
- write_access: fixes a missing f-string prefix in the upstream Windows temp file check
- Prompt: `(Penelope)` renamed to `(Penelope+)` in yellow
