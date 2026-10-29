#!/usr/bin/env python3
"""Verify remove planner fails closed and forwards real inventory."""
import importlib.util
import contextlib
import io
import json
import pathlib
import subprocess
import sys

helper_path = pathlib.Path(__file__).resolve().parents[2] / "helpers" / "bum-plan-remove.py"
spec = importlib.util.spec_from_file_location("bum_plan_remove", helper_path)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)

old_argv, old_stdin = sys.argv, sys.stdin
old_run = helper.subprocess.run
try:
    sys.argv = [str(helper_path), "--inventory", "inventory", "--solver", "solver"]
    sys.stdin = io.StringIO(json.dumps({
        "protocol": 1, "package": "demo", "arch": "x86_64",
    }))
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        if "inventory" in args:
            return subprocess.CompletedProcess(args, 0, json.dumps({
                "protocol": 1,
                "packages": [{"name": "demo", "evr": "1.0-1", "arch": "x86_64"}],
            }), "")
        request = json.loads(kwargs["input"])
        assert request["installed"][0]["name"] == "demo"
        assert request["operation"] == "remove"
        return subprocess.CompletedProcess(args, 0, '{"protocol":1,"plan":[]}\n', "")

    helper.subprocess.run = fake_run
    with contextlib.redirect_stdout(io.StringIO()) as output:
        assert helper.main() == 0
    assert json.loads(output.getvalue())["plan"] == []
    assert len(calls) == 2

    sys.stdin = io.StringIO(json.dumps({
        "protocol": 1, "package": "demo", "arch": "x86_64",
    }))
    helper.subprocess.run = lambda *_args, **_kwargs: subprocess.CompletedProcess(
        ["rpm"], 1, '{"protocol":1,"error":"rpmdb unavailable"}', ""
    )
    with contextlib.redirect_stdout(io.StringIO()) as output:
        assert helper.main() == 2
    assert json.loads(output.getvalue())["error"].startswith(
        "RPM inventory failed:"
    )
finally:
    helper.subprocess.run = old_run
    sys.stdin, sys.argv = old_stdin, old_argv

print("[PASS] remove plan inventory integration and fail-closed behavior")
