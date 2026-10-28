#!/usr/bin/env python3
"""Exercise remote RPM-MD retrieval and cache reuse over loopback HTTP."""
import functools
import http.server
import json
import pathlib
import subprocess
import sys
import tempfile
import threading

repo_root = pathlib.Path(__file__).resolve().parents[2]
fixture = repo_root / "tests" / "fixtures" / "rpmmd"
handler = functools.partial(
    http.server.SimpleHTTPRequestHandler, directory=str(fixture)
)
server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    url = f"http://127.0.0.1:{server.server_port}/"
    with tempfile.TemporaryDirectory(prefix="bum-cache-test-") as cache:
        command = [
            sys.executable,
            str(repo_root / "helpers" / "bum-repomd.py"),
            url,
            "demo-app",
            "--cache-dir",
            cache,
        ]
        first = subprocess.run(command, check=True, capture_output=True, text=True)
        second = subprocess.run(command, check=True, capture_output=True, text=True)
        for output in (first.stdout, second.stdout):
            plan = json.loads(output)["plan"]
            assert {item["name"] for item in plan} == {"demo-app", "demo-lib"}
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)

print("[PASS] remote RPM-MD retrieval and cache reuse")
