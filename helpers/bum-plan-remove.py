#!/usr/bin/env python3
"""Read-only package removal planner using installed RPM and libsolv."""
import argparse
import json
import subprocess
import sys

PROTOCOL_VERSION = 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--solver", required=True)
    args = parser.parse_args()
    try:
        request = json.load(sys.stdin)
        if not isinstance(request, dict) or request.get("protocol") != 1:
            raise ValueError("unsupported or malformed request protocol")
        package = request.get("package")
        arch = request.get("arch", "x86_64")
        if (not isinstance(package, str) or not package
                or not isinstance(arch, str) or not arch):
            raise ValueError("package and arch must be non-empty strings")
        inventory_result = subprocess.run(
            [sys.executable, args.inventory],
            capture_output=True, text=True, check=False,
        )
        if inventory_result.returncode:
            raise RuntimeError(
                "RPM inventory failed: " + inventory_result.stdout.strip()
            )
        inventory = json.loads(inventory_result.stdout)
        if (not isinstance(inventory, dict)
                or inventory.get("protocol") != 1
                or not isinstance(inventory.get("packages"), list)):
            raise ValueError("RPM inventory returned an invalid response")
        for item in inventory["packages"]:
            if (not isinstance(item, dict)
                    or not all(isinstance(item.get(key), str) and item[key]
                               for key in ("name", "evr", "arch"))):
                raise ValueError("RPM inventory contains an invalid package")
        solver_request = {
            "protocol": 1,
            "operation": "remove",
            "package": package,
            "arch": arch,
            "installed": inventory["packages"],
            "packages": [],
        }
        solved = subprocess.run(
            [sys.executable, args.solver],
            input=json.dumps(solver_request), text=True,
            capture_output=True, check=False,
        )
        if solved.returncode not in (0, 1):
            raise RuntimeError("solver failed: " + solved.stderr.strip())
        response = json.loads(solved.stdout)
        if (not isinstance(response, dict)
                or response.get("protocol") != 1
                or response.get("operation") != "remove"
                or not isinstance(response.get("plan"), list)
                or (solved.returncode == 1 and not response.get("error"))
                or (solved.returncode == 0 and response.get("error"))):
            raise ValueError("solver returned an invalid response")
        sys.stdout.write(json.dumps(response, sort_keys=True) + "\n")
        return solved.returncode
    except (KeyError, TypeError, ValueError, RuntimeError, OSError,
            json.JSONDecodeError) as exc:
        print(json.dumps({"protocol": PROTOCOL_VERSION, "error": str(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
