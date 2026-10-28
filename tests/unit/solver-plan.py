#!/usr/bin/env python3
"""Small libsolv plan tests without RPM or network."""
import solv


def _make_package(repo, name, evr="1.0-1", arch="x86_64"):
    package = repo.add_solvable()
    package.name = name
    package.evr = evr
    package.arch = arch
    package.add_provides(package.nameid)
    return package


def _make_solver(packages):
    pool = solv.Pool()
    pool.setarch("x86_64")
    repo = pool.add_repo("fixture")
    solvables = {}
    for definition in packages:
        package = _make_package(
            repo,
            definition["name"],
            definition.get("evr", "1.0-1"),
            definition.get("arch", "x86_64"),
        )
        for requirement in definition.get("requires", []):
            package.add_requires(pool.Dep(requirement))
        for conflict in definition.get("conflicts", []):
            package.add_conflicts(pool.Dep(conflict))
        solvables[definition["name"]] = package
    repo.internalize()
    pool.createwhatprovides()
    return pool, solvables


pool, packages = _make_solver(
    [
        {"name": "demo-app", "requires": ["demo-lib"]},
        {"name": "demo-lib"},
    ]
)
solver = pool.Solver()
job = pool.Job(
    solv.Job.SOLVER_INSTALL | solv.Job.SOLVER_SOLVABLE,
    packages["demo-app"].id,
)
problems = solver.solve([job])
assert not problems, [str(problem) for problem in problems]
plan = {
    (item.name, item.evr, item.arch)
    for item in solver.transaction().steps()
}
assert plan == {
    ("demo-app", "1.0-1", "x86_64"),
    ("demo-lib", "1.0-1", "x86_64"),
}, plan

pool, packages = _make_solver(
    [{"name": "missing-app", "requires": ["not-present"]}]
)
solver = pool.Solver()
job = pool.Job(
    solv.Job.SOLVER_INSTALL | solv.Job.SOLVER_SOLVABLE,
    packages["missing-app"].id,
)
assert solver.solve([job]), "missing dependency unexpectedly resolved"

pool, packages = _make_solver(
    [
        {"name": "app-one", "conflicts": ["app-two"]},
        {"name": "app-two"},
    ]
)
solver = pool.Solver()
jobs = [
    pool.Job(
        solv.Job.SOLVER_INSTALL | solv.Job.SOLVER_SOLVABLE,
        packages[name].id,
    )
    for name in ("app-one", "app-two")
]
assert solver.solve(jobs), "conflicting packages unexpectedly resolved"

# Exercise the protocol adapter's installed-state jobs when available.
import json
import os
import subprocess
import sys

helper = os.path.join(
    os.path.dirname(__file__), "..", "..", "helpers", "bum-solver.py"
)

def run_request(request):
    return subprocess.run(
        [sys.executable, helper],
        input=json.dumps({"protocol": 1, **request}),
        text=True, capture_output=True, check=False,
    )

base = {
    "arch": "x86_64",
    "packages": [
        {"name": "demo", "evr": "2.0-1"},
        {"name": "demo", "evr": "3.0-1"},
    ],
    "installed": [{"name": "demo", "evr": "1.0-1"}],
}
result = run_request({**base, "operation": "upgrade", "package": "demo"})
assert result.returncode == 0, result.stderr + result.stdout
upgrade = json.loads(result.stdout)
assert upgrade["operation"] == "upgrade"
assert any(item["name"] == "demo" and item["evr"] == "3.0-1"
           and item["action"] == "install" for item in upgrade["plan"]), upgrade
assert any(item["name"] == "demo" and item["action"] == "remove"
           for item in upgrade["plan"]), upgrade

order_fixture = os.path.join(
    os.path.dirname(__file__), "..", "fixtures", "solver",
    "upgrade-order.json",
)
with open(order_fixture, encoding="utf-8") as fixture_file:
    order_request = json.load(fixture_file)
order_result = run_request(order_request)
assert order_result.returncode == 0, order_result.stderr + order_result.stdout
ordered_plan = json.loads(order_result.stdout)["plan"]
installed_order = [item["name"] for item in ordered_plan
                   if item["action"] == "install"]
assert len(installed_order) == 2 and set(installed_order) == {
    "zulu-lib", "alpha-app"
}, ordered_plan

legacy = {
    "protocol": 1,
    "operation": "install",
    "package": "demo-app",
    "arch": "x86_64",
    "packages": [{"name": "demo-app", "evr": "1.0-1"}],
}
legacy_plan = json.loads(run_request(legacy).stdout)["plan"]
empty_installed_plan = json.loads(
    run_request({**legacy, "installed": []}).stdout
)["plan"]
assert legacy_plan == empty_installed_plan, (legacy_plan, empty_installed_plan)
assert set(legacy_plan[0]) == {"name", "evr", "arch"}, legacy_plan

result = run_request({**base, "operation": "remove", "package": "demo"})
assert result.returncode == 0, result.stderr + result.stdout
removal = json.loads(result.stdout)
assert removal["plan"] == [{"action": "remove", "name": "demo",
                           "evr": "1.0-1", "arch": "x86_64"}], removal

# An upgrade with no newer candidate must not report a misleading no-op.
old_only = {
    "operation": "upgrade",
    "package": "demo",
    "arch": "x86_64",
    "installed": [{"name": "demo", "evr": "2.0-1"}],
    "packages": [{"name": "demo", "evr": "1.0-1"}],
}
old_result = run_request(old_only)
assert old_result.returncode == 1, old_result.stdout
assert "error" in json.loads(old_result.stdout), old_result.stdout

# Removing a package required by another installed package must not
# silently erase the dependent package as a side effect.
required_state = {
    "operation": "remove",
    "package": "demo-lib",
    "arch": "x86_64",
    "installed": [
        {"name": "demo-app", "evr": "1.0-1", "requires": ["demo-lib"]},
        {"name": "demo-lib", "evr": "1.0-1"},
    ],
    "packages": [],
}
remove_result = run_request(required_state)
if remove_result.returncode == 0:
    actions = json.loads(remove_result.stdout)["plan"]
    assert {item["name"] for item in actions} == {"demo-lib"}, actions

print("[PASS] libsolv dependency-plan tests")
