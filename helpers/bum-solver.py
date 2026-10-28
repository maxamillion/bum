#!/usr/bin/env python3
"""Thin libsolv adapter for package-plan experiments; never runs RPM."""
import json
import sys

import solv

PROTOCOL_VERSION = 1


def _error(message):
    print(json.dumps({"protocol": PROTOCOL_VERSION, "error": message}))
    return 2


def _strings(value, field, package_name):
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError(f"{field} for {package_name} must be strings")
    return value


def _solve(request):
    pool = solv.Pool()
    architecture = request.get("arch", "x86_64")
    if not isinstance(architecture, str) or not architecture:
        raise ValueError("arch must be a non-empty string")
    pool.setarch(architecture)
    repo = pool.add_repo("bum-input")
    by_name = {}

    packages = request.get("packages", [])
    if not isinstance(packages, list):
        raise ValueError("packages must be a JSON array")

    for package in packages:
        if not isinstance(package, dict):
            raise ValueError("each package must be a JSON object")
        name = package.get("name")
        evr = package.get("evr")
        if not isinstance(name, str) or not name:
            raise ValueError("package name must be a non-empty string")
        if not isinstance(evr, str) or not evr:
            raise ValueError(f"package {name} requires a non-empty evr")
        if name in by_name:
            raise ValueError(f"duplicate package name in fixture: {name}")

        package_arch = package.get("arch", architecture)
        if not isinstance(package_arch, str) or not package_arch:
            raise ValueError(f"package {name} has invalid architecture")

        solvable = repo.add_solvable()
        solvable.name = name
        solvable.evr = evr
        solvable.arch = package_arch
        solvable.add_provides(solvable.nameid)
        for capability in _strings(package.get("provides", []), "provides", name):
            solvable.add_provides(pool.Dep(capability))
        for requirement in _strings(package.get("requires", []), "requires", name):
            solvable.add_requires(pool.Dep(requirement))
        for conflict in _strings(package.get("conflicts", []), "conflicts", name):
            solvable.add_conflicts(pool.Dep(conflict))
        by_name[name] = solvable

    repo.internalize()
    pool.createwhatprovides()

    operation = request.get("operation", "install")
    package_name = request.get("package")
    if operation not in {"install", "upgrade", "remove"}:
        raise ValueError(f"unsupported operation: {operation}")
    if not isinstance(package_name, str) or package_name not in by_name:
        raise ValueError(f"unknown package: {package_name}")
    if operation != "install":
        raise ValueError(
            f"{operation} planning requires installed-state support"
        )

    job = pool.Job(
        solv.Job.SOLVER_INSTALL | solv.Job.SOLVER_SOLVABLE,
        by_name[package_name].id,
    )
    solver = pool.Solver()
    problems = solver.solve([job])
    if problems:
        return {
            "protocol": PROTOCOL_VERSION,
            "error": "dependency resolution failed",
            "problems": [str(problem) for problem in problems],
        }

    transaction = solver.transaction()
    return {
        "protocol": PROTOCOL_VERSION,
        "operation": operation,
        "plan": [
            {"name": item.name, "evr": item.evr, "arch": item.arch}
            for item in transaction.steps()
        ],
    }


def main():
    try:
        request = json.load(sys.stdin)
        if not isinstance(request, dict):
            return _error("request must be a JSON object")
        if request.get("protocol") != PROTOCOL_VERSION:
            return _error("unsupported protocol version")
        response = _solve(request)
        print(json.dumps(response, sort_keys=True))
        return 0 if "error" not in response else 1
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return _error(str(exc))


if __name__ == "__main__":
    sys.exit(main())
