#!/usr/bin/env python3
"""Test shared RPM dependency conversion relations and errors."""
import pathlib
import sys

helpers = pathlib.Path(__file__).resolve().parents[2] / "helpers"
sys.path.insert(0, str(helpers))
import bum_solver_common

try:
    import solv
except ImportError:
    print("[SKIP] python-solv unavailable")
    raise SystemExit(0)

pool = solv.Pool()
relation_cases = (
    (2, "<"),
    (4, ">"),
    (8, "="),
    (10, "<="),
    (12, ">="),
)
for flags, expected in relation_cases:
    dep_id = bum_solver_common.rpm_dependency(pool, "virtual", flags, "2")
    assert expected in pool.dep2str(dep_id), (flags, pool.dep2str(dep_id))

for flags, evr in ((2 | 4, "2"), (2, None), (0, None)):
    if flags == 0:
        assert pool.dep2str(bum_solver_common.rpm_dependency(
            pool, "unversioned", flags, evr
        )) == "unversioned"
        continue
    try:
        bum_solver_common.rpm_dependency(pool, "bad", flags, evr)
        raise AssertionError("invalid relation accepted")
    except ValueError:
        pass

print("[PASS] shared RPM relation conversion")
