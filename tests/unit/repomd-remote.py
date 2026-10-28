#!/usr/bin/env python3
"""Exercise remote RPM-MD retrieval and cache reuse over loopback HTTP."""
import functools
import gzip
import hashlib
import http.server
import json
import os
import pathlib
import re
import shutil
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
        first = subprocess.run(
            command, capture_output=True, text=True
        )
        if first.returncode != 0 and "No module named" in first.stderr:
            error = json.loads(first.stderr)
            assert error["protocol"] == 1 and "error" in error, first.stderr
            print("[SKIP] Python librepo/solv dependencies unavailable")
            sys.exit(0)
        assert first.returncode == 0, first.stderr
        second = subprocess.run(
            command, check=True, capture_output=True, text=True
        )
        for output in (first.stdout, second.stdout):
            plan = json.loads(output)["plan"]
            assert {item["name"] for item in plan} == {"demo-app", "demo-lib"}
        cache_path = pathlib.Path(cache)
        assert cache_path.stat().st_mode & 0o777 == 0o700

        for invalid in ("", "-option", "bad name", "bad\tname"):
            invalid_name = "invalid-" + str(len(invalid))
            invalid_cache = pathlib.Path(cache) / invalid_name
            rejected = subprocess.run(
                [sys.executable, str(repo_root / "helpers" / "bum-repomd.py"),
                 url, invalid, "--cache-dir", str(invalid_cache)],
                capture_output=True, text=True,
            )
            assert rejected.returncode == 2, rejected.stderr
            assert not invalid_cache.exists()

        invalid_url = subprocess.run(
            [sys.executable, str(repo_root / "helpers" / "bum-repomd.py"),
             "http://[invalid", "demo-app", "--cache-dir",
             str(pathlib.Path(cache) / "invalid-url-cache")],
            capture_output=True, text=True,
        )
        assert invalid_url.returncode == 2, invalid_url.stdout
        error = json.loads(invalid_url.stderr)
        assert error["protocol"] == 1 and "error" in error

        unsafe_cache = pathlib.Path(cache) / "unsafe"
        unsafe_cache.mkdir(mode=0o755)
        unsafe_cache.chmod(0o755)
        rejected = subprocess.run(
            [sys.executable, str(repo_root / "helpers" / "bum-repomd.py"),
             url, "demo-app", "--cache-dir", str(unsafe_cache)],
            capture_output=True, text=True,
        )
        assert rejected.returncode == 2, rejected.stderr

        corrupt_repo = pathlib.Path(cache) / "corrupt-repo"
        shutil.copytree(fixture, corrupt_repo)
        corrupt_primary = b"<metadata><package>broken</metadata>"
        compressed = gzip.compress(corrupt_primary)
        digest = hashlib.sha256(compressed).hexdigest()
        corrupt_name = f"{digest}-primary.xml.gz"
        (corrupt_repo / "repodata" / corrupt_name).write_bytes(compressed)
        repomd_path = corrupt_repo / "repodata" / "repomd.xml"
        repomd = repomd_path.read_text(encoding="utf-8")
        repomd = re.sub(
            r"(<data type=\"primary\">.*?<checksum type=\"sha256\">)"
            r".*?(</checksum>)",
            rf"\g<1>{digest}\g<2>", repomd, count=1, flags=re.DOTALL,
        )
        repomd = re.sub(
            r"(<data type=\"primary\">.*?<location href=\")([^\"]+)(\")",
            rf"\g<1>repodata/{corrupt_name}\g<3>", repomd,
            count=1, flags=re.DOTALL,
        )
        repomd_path.write_text(repomd, encoding="utf-8")
        corrupt_handler = functools.partial(
            http.server.SimpleHTTPRequestHandler, directory=str(corrupt_repo)
        )
        corrupt_server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), corrupt_handler
        )
        corrupt_thread = threading.Thread(
            target=corrupt_server.serve_forever, daemon=True
        )
        corrupt_thread.start()
        try:
            corrupt_result = subprocess.run(
                [sys.executable, str(repo_root / "helpers" / "bum-repomd.py"),
                 f"http://127.0.0.1:{corrupt_server.server_port}/", "demo-app",
                 "--cache-dir", str(pathlib.Path(cache) / "corrupt-cache")],
                capture_output=True, text=True,
            )
            assert corrupt_result.returncode == 2, corrupt_result.stdout
            error = json.loads(corrupt_result.stderr)
            assert error["protocol"] == 1 and "error" in error, \
                corrupt_result.stderr
        finally:
            corrupt_server.shutdown()
            corrupt_server.server_close()
            corrupt_thread.join(timeout=5)
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)

# Exercise the public plan-only CLI against a local fixture repository.
with tempfile.TemporaryDirectory(prefix="bum-cli-test-") as test_root:
    repo_dir = pathlib.Path(test_root) / "repos"
    repo_dir.mkdir()
    (repo_dir / "fixture.repo").write_text(
        f"[fixture]\nbaseurl={fixture.as_uri()}\n", encoding="utf-8"
    )
    env = os.environ.copy()
    env.update({
        "BUM_REPODIR": str(repo_dir),
        "BUM_CACHEDIR": str(pathlib.Path(test_root) / "cache"),
        "BUM_PYTHON": sys.executable,
    })
    result = subprocess.run(
        [
            str(repo_root / "bum"), "plan", "install", "demo-app",
            "--repo", "fixture",
        ],
        env=env, check=False, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"public CLI failed ({result.returncode}): "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
    cli_plan = json.loads(result.stdout)["plan"]
    assert {item["name"] for item in cli_plan} == {"demo-app", "demo-lib"}

print("[PASS] remote RPM-MD, cache reuse, and public plan CLI")
