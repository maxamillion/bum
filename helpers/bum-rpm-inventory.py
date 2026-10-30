#!/usr/bin/env python3
"""Read installed RPM inventory and dependencies; never mutates RPM state."""
import json
import sys

try:
    import rpm
except ImportError as exc:
    print(json.dumps({"protocol": 1,
                      "error": f"missing Python dependency: {exc.name}"}))
    sys.exit(2)

PROTOCOL_VERSION = 1


def _values(header, tag):
    value = header[tag]
    return list(value) if value is not None else []


def _dependencies(header, rpm_module, stem):
    names = _values(header, getattr(rpm_module, f"RPMTAG_{stem}NAME"))
    versions = _values(header, getattr(rpm_module, f"RPMTAG_{stem}VERSION"))
    flags = _values(header, getattr(rpm_module, f"RPMTAG_{stem}FLAGS"))
    if not (len(names) == len(versions) == len(flags)):
        raise ValueError(f"inconsistent {stem.lower()} arrays in RPM header")
    dependencies = []
    for name, version, sense in zip(names, versions, flags):
        if not isinstance(name, str) or not name:
            raise ValueError(f"invalid {stem.lower()} name in RPM header")
        if version is not None and not isinstance(version, str):
            raise ValueError(f"invalid {stem.lower()} version in RPM header")
        if not isinstance(sense, int):
            raise ValueError(f"invalid {stem.lower()} flags in RPM header")
        dependencies.append({
            "name": name,
            "flags": sense,
            "evr": version or None,
        })
    return dependencies


def inventory(rpm_module=None):
    module = rpm if rpm_module is None else rpm_module
    transaction = module.TransactionSet()
    packages = []
    seen = set()
    tags = {
        "name": module.RPMTAG_NAME,
        "epoch": module.RPMTAG_EPOCH,
        "version": module.RPMTAG_VERSION,
        "release": module.RPMTAG_RELEASE,
        "arch": module.RPMTAG_ARCH,
    }
    for header in transaction.dbMatch():
        name = header[tags["name"]]
        epoch = header[tags["epoch"]]
        version = header[tags["version"]]
        release = header[tags["release"]]
        arch = header[tags["arch"]]
        if arch in (None, ""):
            arch = "noarch"
        if not all(isinstance(item, str) and item for item in
                   (name, version, release, arch)):
            raise ValueError("invalid package identity in RPM header")
        identity = (name, arch)
        if identity in seen:
            raise ValueError(
                f"duplicate installed package identity: {name}.{arch}"
            )
        seen.add(identity)
        epoch = str(epoch) if epoch not in (None, 0, "0", "") else "0"
        evr = f"{epoch}:{version}-{release}" if epoch != "0" \
            else f"{version}-{release}"
        packages.append({
            "name": name,
            "evr": evr,
            "arch": arch,
            "provides": _dependencies(header, module, "PROVIDE"),
            "requires": _dependencies(header, module, "REQUIRE"),
        })
    packages.sort(key=lambda item: (item["name"], item["arch"], item["evr"]))
    return packages


def main():
    try:
        packages = inventory()
    except (OSError, ValueError, RuntimeError, TypeError, KeyError) as exc:
        print(json.dumps({"protocol": PROTOCOL_VERSION, "error": str(exc)}))
        return 1
    print(json.dumps({"protocol": PROTOCOL_VERSION, "packages": packages},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
