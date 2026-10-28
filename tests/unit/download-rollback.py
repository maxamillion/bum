#!/usr/bin/env python3
"""Verify failed RPM cache publication restores prior cache contents."""
import hashlib
import importlib.util
import pathlib
import tempfile

helper_path = pathlib.Path(__file__).resolve().parents[2] / "helpers" / "bum-repomd.py"
spec = importlib.util.spec_from_file_location("bum_repomd", helper_path)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)

with tempfile.TemporaryDirectory(prefix="bum-rollback-") as tmp:
    root = pathlib.Path(tmp)
    cache = root / "cache"
    cache.mkdir(mode=0o700)
    (cache / "packages").mkdir(mode=0o700)
    package_cache = cache / "packages"
    href = "demo-app-1.0-1.noarch.rpm"
    new_data = b"new-rpm-payload"
    old_data = b"previous-good-rpm"
    checksum = hashlib.sha256(new_data).hexdigest()
    filename = hashlib.sha256(
        (href + "\0" + checksum).encode("utf-8")
    ).hexdigest() + ".rpm"
    target = package_cache / filename
    target.write_bytes(old_data)
    target.chmod(0o600)

    original_replace = helper.os.replace

    def fail_stage_publish(src, dst):
        if pathlib.Path(dst) == target and pathlib.Path(src).name.startswith(
            ".bum-download-"
        ):
            raise OSError("injected publication failure")
        original_replace(src, dst)

    class FakeHandle:
        def setopt(self, *_args):
            pass

        def download_package(self, _href, target_path, *_args):
            pathlib.Path(target_path).write_bytes(new_data)

    original_replace = helper.os.replace
    original_handle = helper.librepo.Handle
    try:
        helper.os.replace = fail_stage_publish
        helper.librepo.Handle = FakeHandle
        try:
            helper._download_packages(
                str(root), str(cache), [{
                    "location": href,
                    "checksum_type": "sha256",
                    "checksum": checksum,
                    "size": len(new_data),
                }]
            )
            raise AssertionError("injected publish failure was ignored")
        except OSError as exc:
            assert "injected" in str(exc)
    finally:
        helper.os.replace = original_replace
        helper.librepo.Handle = original_handle

    assert target.read_bytes() == old_data
    assert not list(package_cache.glob(".bum-download-*"))
    assert not list(package_cache.glob(".bum-backup-*"))

print("[PASS] RPM cache publication rollback")
