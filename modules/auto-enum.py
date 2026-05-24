import penelope

class autoenum(penelope.Module):

    category = "Enumeration"
    os_filter = 'Unix'
    enabled = True
    on_session_start = False
    on_first_attach = False
    on_session_end = False

    # Common default SUID/SGID binaries to filter out - uncommon ones are the interesting finds
    DEFAULT_SETID = (
        '/usr/sbin/uuidd', '/usr/sbin/pppd', '/usr/bin/arping', '/usr/bin/expiry',
        '/usr/bin/chfn', '/usr/bin/sudo', '/usr/bin/chage', '/usr/bin/gpasswd',
        '/usr/bin/dotlockfile', '/usr/bin/newgrp', '/usr/bin/mlocate',
        '/usr/bin/mail-unlock', '/usr/bin/chsh', '/usr/bin/bsd-write',
        '/usr/bin/mail-touchlock', '/usr/bin/crontab', '/usr/bin/passwd',
        '/usr/bin/traceroute6.iputils', '/usr/bin/mail-lock', '/usr/bin/wall',
        '/usr/bin/mtr', '/usr/bin/sudoedit', '/usr/bin/lppasswd', '/usr/bin/X',
        '/usr/bin/pkexec', '/usr/bin/at', '/usr/bin/ssh-agent', '/usr/lib/pt_chown',
        '/usr/bin/su', '/usr/bin/mount', '/usr/bin/umount', '/usr/bin/fusermount',
        '/usr/lib/eject/dmcrypt-get-device',
        '/usr/lib/policykit-1/polkit-agent-helper-1',
        '/usr/lib/openssh/ssh-keysign',
        '/usr/lib/dbus-1.0/dbus-daemon-launch-helper',
    )

    def run(session, args):
        """
        Run common Linux enumeration checks and print results.
        """

        if session.OS == 'Windows':
            penelope.logger.error("Unix only")
            return

        default_filter = '|'.join(autoenum.DEFAULT_SETID).replace('/', r'\/')

        enum_commands = [
            # ── System ────────────────────────────────────────────────────────
            ('Kernel Version',
             'uname -a'),

            ('OS Version',
             'lsb_release -a 2>/dev/null || cat /etc/os-release 2>/dev/null'),

            # ── Users ─────────────────────────────────────────────────────────
            ('Current User',
             'id'),

            ('Users with Login Shells',
             "getent passwd | awk -F: 'BEGIN{while(getline s<\"/etc/shells\") shells[s]=1} ($7 in shells){print $1 \":\" $7}'"),

            ('Passwd File',
             'cat /etc/passwd'),

            ('Bash History',
             'cat ~/.bash_history 2>/dev/null'),

            ('Home Directory',
             'ls -la ~'),

            # ── Privileges ────────────────────────────────────────────────────
            ('Sudo Privileges',
             'sudo -l 2>&1 | grep -v "Sorry|not allowed"'),

            ('Sudo Version',
             'sudo -V 2>/dev/null | head -1'),

            # ── Processes & Environment ───────────────────────────────────────
            ('Running Processes',
             'ps -ef'),

            ('Environment Variables',
             'env'),

            # ── Network ───────────────────────────────────────────────────────
            ('Listening Ports',
             'netstat -tlnp 2>/dev/null || ss -tlnp 2>/dev/null'),

            ('ARP Cache',
             'arp -a 2>/dev/null'),

            ('Routes',
             'ip r 2>/dev/null || route -n 2>/dev/null'),

            # ── SUID / SGID ───────────────────────────────────────────────────
            ('SUID Binaries (non-default)',
             f'find / -path /proc -prune -o -perm /4000 -type f -print 2>/dev/null'
             f' | grep -Ev \'^({default_filter})$\''),

            ('SGID Binaries (non-default)',
             f'find / -path /proc -prune -o -perm /2000 -type f -print 2>/dev/null'
             f' | grep -Ev \'^({default_filter})$\''),

            # ── Interesting files ─────────────────────────────────────────────
            ('SSH Private Keys',
             'find / -path /proc -prune -o -name "id_rsa*" -o -name "id_ed25519*" -type f -print 2>/dev/null'),

            ('World-Writable Files',
             'find / -path /proc -prune -o -path /sys -prune -o -type f -perm -o+w -print 2>/dev/null'),

            ('Group-Readable (not world-readable)',
             'find / -perm -g=r -not -perm -o=r 2>/dev/null | grep -v /proc | grep -v /sys | grep -v /dev'),

            ('Files with ACLs',
             "getfacl --recursive --skip-base / 2>/dev/null | grep 'file:' | cut -d' ' -f3 | awk '{print \"/\"$1}'"),

            # ── Cron ──────────────────────────────────────────────────────────
            ('Cron Jobs',
             'grep -v "^#" /etc/crontab 2>/dev/null'),
        ]

        for name, cmd in enum_commands:
            output = session.exec(cmd, value=True, timeout=30)
            if not output:
                continue

            penelope.logger.info(f"--- {name} ---")

            if 'SUID' in name or 'SGID' in name:
                ls_output = session.exec(f"ls -la {output.replace(chr(10), ' ')}", value=True)
                print((ls_output or output) + "\n")
            else:
                print(output + "\n")
