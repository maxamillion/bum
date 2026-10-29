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


def _package(repo, pool, definition, architecture, field):
    if not isinstance(definition, dict):
        raise ValueError(f"each {field} package must be a JSON object")
    name, evr = definition.get("name"), definition.get("evr")
    if not isinstance(name, str) or not name:
        raise ValueError(f"{field} package name must be a non-empty string")
    if not isinstance(evr, str) or not evr:
        raise ValueError(f"package {name} requires a non-empty evr")
    package_arch = definition.get("arch", architecture)
    if not isinstance(package_arch, str) or not package_arch:
        raise ValueError(f"package {name} has invalid architecture")

    solvable = repo.add_solvable()
    solvable.name, solvable.evr, solvable.arch = name, evr, package_arch
    solvable.add_provides(solvable.nameid)
    capabilities = _strings(definition.get("provides", []), "provides", name)
    for capability in capabilities:
        solvable.add_provides(pool.Dep(capability))
    requirements = _strings(definition.get("requires", []), "requires", name)
    for requirement in requirements:
        solvable.add_requires(pool.Dep(requirement))
    conflicts = _strings(definition.get("conflicts", []), "conflicts", name)
    for conflict in conflicts:
        solvable.add_conflicts(pool.Dep(conflict))
    return solvable


def _solve(request):
    pool = solv.Pool()
    architecture = request.get("arch", "x86_64")
    if not isinstance(architecture, str) or not architecture:
        raise ValueError("arch must be a non-empty string")
    pool.setarch(architecture)

    packages = request.get("packages", [])
    installed = request.get("installed", [])
    if not isinstance(packages, list):
        raise ValueError("packages must be a JSON array")
    if not isinstance(installed, list):
        raise ValueError("installed must be a JSON array")
    available_repo = pool.add_repo("bum-input")
    candidates = {}
    for definition in packages:
        solvable = _package(
            available_repo, pool, definition, architecture, "available"
        )
        candidates.setdefault(solvable.name, []).append(solvable)
    system_repo = pool.add_repo("@System")
    installed_by_name = {}
    for definition in installed:
        solvable = _package(
            system_repo, pool, definition, architecture, "installed"
        )
        identity = (solvable.name, solvable.arch)
        if identity in installed_by_name:
            raise ValueError(
                f"duplicate installed package identity: "
                f"{solvable.name}.{solvable.arch}"
            )
        installed_by_name[identity] = solvable
    pool.installed = system_repo
    available_repo.internalize()
    system_repo.internalize()
    pool.createwhatprovides()

    operation = request.get("operation", "install")
    name = request.get("package")
    requested_arch = request.get("arch", architecture)
    if not isinstance(requested_arch, str) or not requested_arch:
        raise ValueError("arch must be a non-empty string")
    if operation not in {"install", "upgrade", "remove"}:
        raise ValueError(f"unsupported operation: {operation}")
    if not isinstance(name, str) or not name:
        raise ValueError("package must be a non-empty string")
    if operation == "install":
        if name not in candidates:
            raise ValueError(f"unknown package: {name}")
        # Name-based install lets libsolv select the best candidate/version.
        job = pool.Job(
            solv.Job.SOLVER_INSTALL | solv.Job.SOLVER_SOLVABLE_NAME,
            pool.str2id(name, 1),
        )
    else:
        installed_matches = [
            solvable for (installed_name, installed_arch), solvable
            in installed_by_name.items()
            if installed_name == name and installed_arch == requested_arch
        ]
        if not installed_matches:
            raise ValueError(
                f"unknown installed package: {name}.{requested_arch}"
            )
        if len(installed_matches) > 1:
            raise ValueError(
                f"ambiguous installed package: {name}.{requested_arch}"
            )
        old = installed_matches[0]
        flag = (
            solv.Job.SOLVER_UPDATE
            if operation == "upgrade"
            else solv.Job.SOLVER_ERASE
        )
        job = pool.Job(flag | solv.Job.SOLVER_SOLVABLE, old.id)

    solver = pool.Solver()
    problems = solver.solve([job])
    if problems:
        return {
            "protocol": PROTOCOL_VERSION,
            "error": "dependency resolution failed",
            "problems": [str(problem) for problem in problems],
        }

    transaction = solver.transaction()
    plan = []
    if operation == "upgrade" and not any(
        item.repo == available_repo and item.name == name
        for item in transaction.steps()
    ):
        return {
            "protocol": PROTOCOL_VERSION,
            "error": f"no upgrade candidate available for: {name}",
        }
    for item in transaction.steps():
        # Installed steps are removals; available steps are additions.
        action = "remove" if item.repo == system_repo else "install"
        plan.append({
            "action": action,
            "name": item.name,
            "evr": item.evr,
            "arch": item.arch,
        })
    # Preserve libsolv's transaction order: dependency and erase ordering can
    # be significant when this plan is eventually executed.
    # Keep protocol-v1 install response shape independent of installed state.
    if operation == "install":
        plan = [
            {key: item[key] for key in ("name", "evr", "arch")}
            for item in plan
        ]
    return {"protocol": PROTOCOL_VERSION, "operation": operation, "plan": plan}


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
