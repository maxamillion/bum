#!/usr/bin/env python3
"""Test installed RPM inventory parsing with a mocked rpm executable."""
import importlib.util
import pathlib

helper_path = pathlib.Path(__file__).resolve().parents[2] / "helpers" / "bum-rpm-inventory.py"
spec = importlib.util.spec_from_file_location("bum_rpm_inventory", helper_path)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class Result:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


original_run = helper.subprocess.run
try:
    helper.subprocess.run = lambda *_args, **_kwargs: Result(
        "zlib\t(none)\t1.2\t3.el9\tx86_64\n"
        "bash\t0\t5.1\t2.el9\tx86_64\n"
        "bash\t0\t5.1\t2.el9\ti686\n"
    )
    packages = helper.inventory()
    assert [item["name"] for item in packages] == ["bash", "bash", "zlib"]
    assert packages[0]["arch"] == "i686"
    assert packages[1]["arch"] == "x86_64"
    assert packages[2]["evr"] == "1.2-3.el9"

    helper.subprocess.run = lambda *_args, **_kwargs: Result(
        "bash\t0\t5.1\t2.el9\tx86_64\n"
        "bash\t0\t5.2\t1.el9\tx86_64\n"
    )
    try:
        helper.inventory()
        raise AssertionError("duplicate name/architecture accepted")
    except ValueError as exc:
        assert "duplicate installed package identity" in str(exc)

    helper.subprocess.run = lambda *_args, **_kwargs: Result("malformed\n")
    try:
        helper.inventory()
        raise AssertionError("malformed RPM record accepted")
    except ValueError as exc:
        assert "malformed rpm query record" in str(exc)

    helper.subprocess.run = lambda *_args, **_kwargs: Result(
        stderr="rpmdb unavailable", returncode=1
    )
    try:
        helper.inventory()
        raise AssertionError("RPM query failure accepted")
    except RuntimeError as exc:
        assert "rpmdb unavailable" in str(exc)
finally:
    helper.subprocess.run = original_run

print("[PASS] RPM inventory parser and error handling")
