#!/usr/bin/env python3
"""Read installed RPM inventory as JSON; never modifies RPM state."""
import json
import subprocess
import sys

PROTOCOL_VERSION = 1


def inventory(rpm="rpm"):
    result = subprocess.run(
        [rpm, "-qa", "--qf", "%{NAME}\\t%{EPOCHNUM}\\t%{VERSION}\\t%{RELEASE}\\t%{ARCH}\\n"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    )
    if result.returncode:
        message = result.stderr.strip() or "rpm query failed"
        raise RuntimeError(message)
    packages = []
    seen = set()
    for line_number, line in enumerate(result.stdout.splitlines(), 1):
        fields = line.split("\t")
        if len(fields) != 5 or any(not field for field in fields):
            raise ValueError(f"malformed rpm query record at line {line_number}")
        name, epoch, version, release, arch = fields
        identity = (name, arch)
        if identity in seen:
            raise ValueError(
                f"duplicate installed package identity: {name}.{arch}"
            )
        seen.add(identity)
        epoch = "0" if epoch == "(none)" else epoch
        evr = f"{epoch}:{version}-{release}" if epoch != "0" else f"{version}-{release}"
        packages.append({"name": name, "evr": evr, "arch": arch})
    packages.sort(key=lambda item: (item["name"], item["arch"], item["evr"]))
    return packages


def main():
    rpm = sys.argv[1] if len(sys.argv) == 2 else "rpm"
    if len(sys.argv) > 2:
        print(json.dumps({"protocol": PROTOCOL_VERSION,
                          "error": "usage: bum-rpm-inventory.py [RPM]"}))
        return 2
    try:
        packages = inventory(rpm)
    except (OSError, UnicodeError, RuntimeError, ValueError) as exc:
        print(json.dumps({"protocol": PROTOCOL_VERSION, "error": str(exc)}))
        return 1
    print(json.dumps({"protocol": PROTOCOL_VERSION, "packages": packages},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
