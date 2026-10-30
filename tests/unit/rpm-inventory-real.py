#!/usr/bin/env python3
"""Check live RPM query output in a disposable integration container."""
import json
import pathlib
import subprocess
import sys

helper = pathlib.Path(__file__).resolve().parents[2] / "helpers" / "bum-rpm-inventory.py"
result = subprocess.run(
    [sys.executable, str(helper)], capture_output=True, text=True, check=False
)
assert result.returncode == 0, result.stderr or result.stdout
response = json.loads(result.stdout)
assert response["protocol"] == 1
assert response["packages"]
assert all(set(item) == {"name", "evr", "arch"}
           for item in response["packages"])
print("[PASS] live RPM inventory query")
