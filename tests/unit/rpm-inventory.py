#!/usr/bin/env python3
"""Test RPM header inventory extraction without a system RPM database."""
import importlib.util
import pathlib

helper_path = pathlib.Path(__file__).resolve().parents[2] / "helpers" / "bum-rpm-inventory.py"
spec = importlib.util.spec_from_file_location("bum_rpm_inventory", helper_path)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class Header(dict):
    pass


class TransactionSet:
    def __init__(self, headers):
        self.headers = headers
        self.queries = 0

    def dbMatch(self):
        self.queries += 1
        return iter(self.headers)


class FakeRPM:
    RPMTAG_NAME = 1000
    RPMTAG_EPOCH = 1001
    RPMTAG_VERSION = 1002
    RPMTAG_RELEASE = 1003
    RPMTAG_ARCH = 1004
    RPMTAG_PROVIDENAME = 1010
    RPMTAG_PROVIDEVERSION = 1011
    RPMTAG_PROVIDEFLAGS = 1012
    RPMTAG_REQUIRENAME = 1020
    RPMTAG_REQUIREVERSION = 1021
    RPMTAG_REQUIREFLAGS = 1022

    def __init__(self, headers):
        self.ts = TransactionSet(headers)

    def TransactionSet(self):
        return self.ts


def make_header(name, epoch, version, release, arch, provides=(), requires=()):
    return Header({
        FakeRPM.RPMTAG_NAME: name,
        FakeRPM.RPMTAG_EPOCH: epoch,
        FakeRPM.RPMTAG_VERSION: version,
        FakeRPM.RPMTAG_RELEASE: release,
        FakeRPM.RPMTAG_ARCH: arch,
        FakeRPM.RPMTAG_PROVIDENAME: [d[0] for d in provides],
        FakeRPM.RPMTAG_PROVIDEVERSION: [d[1] for d in provides],
        FakeRPM.RPMTAG_PROVIDEFLAGS: [d[2] for d in provides],
        FakeRPM.RPMTAG_REQUIRENAME: [d[0] for d in requires],
        FakeRPM.RPMTAG_REQUIREVERSION: [d[1] for d in requires],
        FakeRPM.RPMTAG_REQUIREFLAGS: [d[2] for d in requires],
    })


headers = [
    make_header(
        "zlib", 0, "1.2", "3.el9", "x86_64",
        provides=[("zlib", "", 0), ("libz.so.1()(64bit)", "1.2", 8)],
        requires=[("glibc", "2.34", 12)],
    ),
    make_header("bash", None, "5.1", "2.el9", "x86_64"),
]
fake = FakeRPM(headers)
packages = helper.inventory(fake)
assert fake.ts.queries == 1
assert [item["name"] for item in packages] == ["bash", "zlib"]
assert packages[0]["evr"] == "5.1-2.el9"
assert packages[1]["provides"] == [
    {"name": "zlib", "flags": 0, "evr": None},
    {"name": "libz.so.1()(64bit)", "flags": 8, "evr": "1.2"},
]
assert packages[1]["requires"] == [
    {"name": "glibc", "flags": 12, "evr": "2.34"},
]

bad = FakeRPM([make_header(
    "bad", 0, "1", "1", "x86_64",
    provides=[("cap", "1", 0)],
)])
bad.ts.headers[0][FakeRPM.RPMTAG_PROVIDEVERSION] = []
try:
    helper.inventory(bad)
    raise AssertionError("inconsistent dependency arrays accepted")
except ValueError as exc:
    assert "inconsistent provide arrays" in str(exc)

print("[PASS] RPM header inventory extraction")
