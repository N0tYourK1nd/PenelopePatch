"""
PenelopePlus module template.

Drop this file (renamed) into modules/ and run install.sh.
The class name becomes the module name shown in penelope's `run` command.

Session attributes available in run():
    session.OS          - 'Unix' | 'Windows'
    session.ip          - remote IP string
    session.port        - remote port int
    session.hostname    - remote hostname string
    session.user        - current user on remote
    session.arch        - architecture string (e.g. 'x86_64')
    session.system      - OS version string
    session.cwd         - current working directory (Path)
    session.tmp         - writable temp dir on remote (Path)
    session.id          - session ID int

Session methods available in run():
    session.exec(cmd, value=True)   - run command, return output as str (use this in modules)
    session.upload(src, remote_path=None, randomize_fname=False)
    session.download(remote_items)
    session.write_access(path)      - bool, check if path is writable
"""

import penelope

# Required: must subclass penelope.Module
class template_module(penelope.Module):

    # Module category shown in `run` listing
    category = "Misc"

    # Set True to auto-run when a session is first established
    on_session_start = False

    # Set True to auto-run on first interactive attach
    on_first_attach = False

    # Set True to auto-run when session ends
    on_session_end = False

    def run(session, args):
        """
        One-line description shown in `run` listing.

        Extended help shown when user runs: run template_module --help
        args is a string of everything the user typed after the module name,
        or None when triggered by a hook (on_session_start etc).
        """

        # Guard on OS if module is platform-specific
        if session.OS == 'Windows':
            penelope.logger.error("This module runs on Unix only")
            return

        # Run command and print output
        output = session.exec("id", value=True)
        if output:
            print(output)

        # Upload a local file
        # session.upload("/path/to/local/file", remote_path=session.tmp)

        # Parse args (args is a str or None when hook-triggered)
        # if args and "--verbose" in args:
        #     ...
