"""
PenelopePlus module template.

Drop this file (renamed) into modules/ and run install.sh.
The class name becomes the module name shown in penelope's `run` command.

━━━ SESSION ATTRIBUTES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Identity
    session.id          - session ID int
    session.name        - display name string (hostname+ip+system)
    session.user        - current user on remote (e.g. 'www-data(33)')
    session.shell_pid   - remote shell PID int
    session.tty         - remote TTY string (e.g. '/dev/pts/0')

  Network
    session.ip          - remote IP string
    session.port        - remote port int (initial connection)
    session._host       - penelope listener IP (local/attacker side)
    session._port       - penelope listener port (local/attacker side)
    session.source      - 'reverse' | 'bind'
    session.listener    - TCPListener object, or None for bind shells
    session.latency     - connection latency

  System info
    session.OS          - 'Unix' | 'Windows' | None
    session.hostname    - remote hostname string
    session.arch        - architecture string (e.g. 'x86_64')
    session.system      - OS version string
    session.cwd         - current working directory string (lazy, queried once)
    session.tmp         - writable temp dir on remote string (lazy, e.g. '/tmp')

  Shell state
    session.type        - 'Raw' | 'PTY'
    session.subtype     - None | 'cmd' | 'psh' (Windows only)
    session.interactive - bool, shell has a prompt
    session.echoing     - bool, shell echoes input
    session.agent       - bool, session is agent-based (full-duplex)
    session.new         - bool, session not yet upgraded
    session.is_attached - bool (property), currently attached to this session

  Available binaries (Unix)
    session.bin         - dict of binary name → remote path (empty str if absent)
    Keys: 'sh', 'bash', 'python', 'python3', 'uname', 'script', 'socat',
          'tty', 'echo', 'base64', 'wget', 'curl', 'tar', 'rm', 'stty',
          'setsid', 'find', 'nc'
    Usage: if session.bin['bash']: ...

━━━ SESSION METHODS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  session.exec(cmd, value=False, timeout=False, raw=False)
      Run command on remote. Pass value=True to return output as str.
      value=False fires and forgets (non-blocking).

  session.upload(local_items, remote_path=None, randomize_fname=False)
      Upload local file(s) to remote. Returns list of remote Paths.
      local_items can be a path string, URL, or list of either.

  session.download(remote_items)
      Download file(s) from remote. Returns set of local Paths.

  session.spawn(port=None, host=None)
      Spawn a new session back to penelope's listener.
      No args = uses current listener host/port (_host/_port).
      spawn(4444) = reverse shell on port 4444.
      spawn(3333, '10.10.10.1') = reverse shell to specific host:port.

  session.write_access(path)
      Returns bool — True if path is writable on remote.

  session.upgrade()
      Attempt to upgrade Raw shell to PTY or agent.

  session.script(local_script)
      Run a local script file (or URL) on remote, save output locally.

  session.portfwd(_type, lhost, lport, rhost, rport)
      Set up port forwarding. _type: 'L' (local) or 'R' (remote).

  session.need_binary(name, url)
      Interactive prompt to upload/locate a binary on remote.
      Returns remote path string if found, False otherwise.

  session.kill()
      Kill/close this session.

  session.attach()  /  session.detach()
      Attach/detach interactive terminal to this session.

━━━ PENELOPE GLOBALS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  penelope.logger.info(msg)  / .warning(msg) / .error(msg)
  penelope.ask(prompt)       - interactive prompt, returns str
  penelope.core.sessions     - dict of {id: session}
  penelope.core.hosts        - dict of {name: [sessions]}
  penelope.core.listeners    - dict of {id: TCPListener}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import penelope
import re

# Required: must subclass penelope.Module
class autofwd(penelope.Module):

    # Module category shown in `run` listing
    category = "Pivoting"

    # Set True to auto-run when a session is first established
    on_session_start = False

    # Set True to auto-run on first interactive attach
    on_first_attach = False

    # Set True to auto-run when session ends
    on_session_end = False

    def run(session, args):
        """
        Use "netstat -tunl" to find open ports on remote and set up local port forwarding for each.
        """

        # Guard on OS if module is platform-specific
        if session.OS == 'Windows':
            penelope.logger.error("This module runs on Unix only")
            return

        # Forwarding Blacklist
        BLACKLIST = [
            22, # SSH
            53, # DNS
            68  # ?
        ]

        # Run command and return output
        output = session.exec("netstat -tunl", value=True)
        ports = [p for p in dict.fromkeys(re.findall(r':(\d+)\s', output)) if int(p) not in BLACKLIST]

        for port in ports:
            session.portfwd('L', '127.0.0.1', port, '127.0.0.1', port)