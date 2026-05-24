import penelope
import re

# Required: must subclass penelope.Module
class autofwd(penelope.Module):

    # Module category shown in `run` listing
    category = "Pivoting"
    os_filter = "Unix"  # handles both Unix and Windows

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