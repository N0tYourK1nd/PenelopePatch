import penelope

# Required: must subclass penelope.Module
class pspy(penelope.Module):

    # Module category shown in `run` listing
    category = "Privilege Escalation"

    # Set False to disable without deleting the file
    enabled = True

    # Set True to auto-run when a session is first established
    on_session_start = False

    # Set True to auto-run on first interactive attach
    on_first_attach = False

    # Set True to auto-run when session ends
    on_session_end = False

    def run(session, args=None):
        """
        Runs pspy64 on the target in a new window, similar to how peass-ng works.
        """

        # Guard: hook calls pass args=None — parse only when user-invoked
        if args is None:
            return

        # Guard on OS if module is platform-specific
        if session.OS != 'Unix':
            penelope.logger.error("Unix only")
            return

        if not session.agent:
            penelope.logger.error("pspy requires agent mode (run upgrade first)")
            return

        import os as _os
        _here = _os.path.dirname(_os.path.abspath(__file__))
        output = session.script(_os.path.join(_here, "scripts", "pspy64.sh"))