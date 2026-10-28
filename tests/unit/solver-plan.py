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

print("[PASS] libsolv dependency-plan tests")
