import penelope

class scanner(penelope.Module):

    category = "Enumeration"
    os_filter = 'Unix'
    enabled = True
    on_session_start = False
    on_first_attach = False
    on_session_end = False

    COMMON_PORTS = [
        21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445,
        993, 995, 1723, 3000, 3306, 3389, 5432, 5900, 8080, 8443, 8888
    ]

    def run(session, args):
        """
        Ping sweep and TCP port scan from the target host.

        Usage:
          run scanner <subnet>          - ping sweep only, e.g. 192.168.1.0/24
          run scanner <subnet> <ports>  - sweep + port scan, e.g. 192.168.1.0/24 22,80,443
          run scanner <ip> <ports>      - port scan single host (skips sweep)
        Ports default to common list if omitted with a subnet.
        """

        if session.OS != 'Unix':
            penelope.logger.error("Unix only")
            return

        parts = args.split() if args else []
        if not parts:
            penelope.logger.error("Usage: scanner <subnet|ip> [port,port,...]")
            return

        target = parts[0]
        is_subnet = '/' in target

        # Parse custom ports
        if len(parts) >= 2:
            try:
                ports = [int(p) for p in parts[1].split(',')]
            except ValueError:
                penelope.logger.error("Ports must be comma-separated integers: 22,80,443")
                return
        else:
            ports = scanner.COMMON_PORTS if is_subnet else []

        if is_subnet:
            # Strip CIDR suffix and last octet to get base: 192.168.1.0/24 → 192.168.1
            base = target.split('/')[0].rsplit('.', 1)[0]

            penelope.logger.info(f"Ping sweep: {base}.1-254 ...")
            sweep_cmd = (
                f"for i in $(seq 1 254); do "
                f"(ping -c 1 -W 1 {base}.$i 2>/dev/null | grep -q 'bytes from' "
                f"&& echo {base}.$i) & "
                f"done; wait"
            )
            sweep_out = session.exec(sweep_cmd, value=True, timeout=60)

            if not sweep_out:
                penelope.logger.warning("No hosts responded to ping")
                return

            live_hosts = sweep_out.strip().splitlines()
            penelope.logger.info(f"Live hosts ({len(live_hosts)}):")
            for host in live_hosts:
                print(f"  {host}")
            print()

        else:
            live_hosts = [target]

        if not ports:
            return

        # TCP port scan via bash /dev/tcp - parallel per host
        port_list = ' '.join(str(p) for p in ports)
        penelope.logger.info(f"Port scanning {len(live_hosts)} host(s) ({len(ports)} ports)...")

        for host in live_hosts:
            scan_cmd = (
                f"for port in {port_list}; do "
                f"(timeout 1 bash -c \"echo >/dev/tcp/{host}/$port\" 2>/dev/null "
                f"&& echo {host}:$port) & "
                f"done; wait"
            )
            scan_out = session.exec(scan_cmd, value=True, timeout=30)
            if scan_out:
                penelope.logger.info(f"Open ports on {host}:")
                for line in sorted(scan_out.strip().splitlines(),key=lambda x: int(x.split(':')[-1])):
                    print(f"  {line}")
                print()
