#!/usr/bin/env python3
"""Verify package download cache publication serializes concurrent writers."""
import hashlib
import importlib.util
import multiprocessing
import pathlib
import tempfile
import time

helper_path = pathlib.Path(__file__).resolve().parents[2] / "helpers" / "bum-repomd.py"
spec = importlib.util.spec_from_file_location("bum_repomd_lock", helper_path)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def worker(root, ready, release, results):
    cache = pathlib.Path(root) / "cache"
    cache.mkdir(mode=0o700, exist_ok=True)
    (cache / "packages").mkdir(mode=0o700, exist_ok=True)
    href = "demo-app-1.0-1.noarch.rpm"
    data = b"concurrent-rpm-payload"
    checksum = hashlib.sha256(data).hexdigest()

    class FakeHandle:
        def setopt(self, *_args):
            pass

        def download_package(self, _href, target_path, *_args):
            ready.put(True)
            if not release.wait(10):
                raise TimeoutError("test release timed out")
            pathlib.Path(target_path).write_bytes(data)

    old_handle = helper.librepo.Handle
    old_unlocked = helper._download_packages_unlocked
    try:
        helper.librepo.Handle = FakeHandle
        def blocked_unlocked(source, cache_dir, packages):
            ready.put(True)
            if not release.wait(10):
                raise TimeoutError("test release timed out")
            return old_unlocked(source, cache_dir, packages)
        helper._download_packages_unlocked = blocked_unlocked
        result = helper._download_packages(str(root), str(cache), [{
            "location": href,
            "checksum_type": "sha256",
            "checksum": checksum,
            "size": len(data),
        }])
        results.put(("ok", result[0]))
    except Exception as exc:  # communicate child errors to parent
        results.put(("error", repr(exc)))
    finally:
        helper._download_packages_unlocked = old_unlocked
        helper.librepo.Handle = old_handle


with tempfile.TemporaryDirectory(prefix="bum-lock-") as tmp:
    context = multiprocessing.get_context("fork")
    ready = context.Queue()
    release = context.Event()
    results = context.Queue()
    workers = [context.Process(
        target=worker, args=(tmp, ready, release, results)
    ) for _ in range(2)]
    for process in workers:
        process.start()
    first_ready = ready.get(timeout=10)
    assert first_ready
    time.sleep(0.25)
    assert ready.empty(), "second writer entered download while lock held"
    release.set()
    assert ready.get(timeout=10)
    outcomes = [results.get(timeout=10) for _ in workers]
    for process in workers:
        process.join(timeout=10)
        assert process.exitcode == 0, process.exitcode
    assert all(item[0] == "ok" for item in outcomes), outcomes
    target = pathlib.Path(outcomes[0][1])
    data = target.read_bytes()
    assert data == b"concurrent-rpm-payload"
    assert hashlib.sha256(data).hexdigest() == hashlib.sha256(
        b"concurrent-rpm-payload"
    ).hexdigest()
    assert not list(target.parent.glob(".bum-download-*"))
    assert not list(target.parent.glob(".bum-backup-*"))

print("[PASS] concurrent RPM cache publication is serialized")
