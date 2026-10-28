#!/usr/bin/env python3
"""Load checksum-verified RPM-MD and create an install plan (prototype)."""
import argparse
import gzip
import json
import os
import sys
import tempfile
import xml.etree.ElementTree as ElementTree

import librepo
import solv

PROTOCOL_VERSION = 1
COMMON_NS = "{http://linux.duke.edu/metadata/common}"
RPM_NS = "{http://linux.duke.edu/metadata/rpm}"


def _text(element, path):
    child = element.find(path)
    return child.text if child is not None and child.text else ""


def _dependency(pool, entry):
    name = entry.get("name")
    if not name:
        return None
    flags = entry.get("flags")
    version = entry.get("ver")
    release = entry.get("rel")
    if flags and version:
        evr = f"{version}-{release}" if release else version
        name = f"{name} {flags} {evr}"
    return pool.Dep(name)


def _parse_primary(pool, repo, primary_path):
    with gzip.open(primary_path, "rb") as metadata_file:
        root = ElementTree.parse(metadata_file).getroot()

    for package in root.findall(f"{COMMON_NS}package"):
        name = _text(package, f"{COMMON_NS}name")
        version = package.find(f"{COMMON_NS}version")
        arch = _text(package, f"{COMMON_NS}arch")
        if not name or version is None or not arch:
            raise ValueError("primary metadata package missing identity fields")

        epoch = version.get("epoch", "0") or "0"
        ver = version.get("ver", "")
        release = version.get("rel", "")
        if not ver or not release:
            raise ValueError(f"invalid EVR for package {name}")
        evr = f"{epoch}:{ver}-{release}" if epoch != "0" else f"{ver}-{release}"

        solvable = repo.add_solvable()
        solvable.name = name
        solvable.evr = evr
        solvable.arch = arch
        solvable.add_provides(solvable.nameid)

        format_node = package.find(f"{COMMON_NS}format")
        if format_node is None:
            continue
        for tag, method in (("provides", solvable.add_provides),
                            ("requires", solvable.add_requires),
                            ("conflicts", solvable.add_conflicts)):
            parent = format_node.find(f"{RPM_NS}{tag}")
            if parent is None:
                continue
            for entry in parent.findall(f"{RPM_NS}entry"):
                dependency = _dependency(pool, entry)
                if dependency is not None:
                    method(dependency)


def _load_repo(source, cache_dir):
    os.makedirs(cache_dir, mode=0o755, exist_ok=True)
    cache_dir = os.path.realpath(cache_dir)
    source = os.path.realpath(source) if os.path.isdir(source) else source
    with tempfile.TemporaryDirectory(prefix="bum-repomd-") as work_dir:
        handle = librepo.Handle()
        result = librepo.Result()
        handle.setopt(librepo.LRO_REPOTYPE, librepo.LR_YUMREPO)
        handle.setopt(librepo.LRO_URLS, [source])
        handle.setopt(librepo.LRO_LOCAL, not source.startswith(("http://", "https://")))
        handle.setopt(librepo.LRO_CACHEDIR, cache_dir)
        handle.setopt(librepo.LRO_DESTDIR, work_dir)
        handle.setopt(librepo.LRO_CHECKSUM, True)
        handle.setopt(librepo.LRO_IGNOREMISSING, True)
        handle.setopt(librepo.LRO_RPMMDDLIST, ["primary"])
        handle.setopt(librepo.LRO_YUMDLIST, ["primary"])
        handle.perform(result)

        paths = result.getinfo(librepo.LRR_YUM_REPO)
        primary_path = paths.get("primary")
        if not primary_path:
            raise ValueError("RPM-MD repository has no primary metadata")

        pool = solv.Pool()
        pool.setarch("x86_64")
        repo = pool.add_repo("bum-repomd")
        _parse_primary(pool, repo, primary_path)
        repo.internalize()
        pool.createwhatprovides()
        return pool, repo


def _plan(source, package_name, cache_dir):
    pool, repo = _load_repo(source, cache_dir)
    matches = [item for item in repo.solvables_iter() if item.name == package_name]
    if not matches:
        raise ValueError(f"package not found: {package_name}")
    solver = pool.Solver()
    job = pool.Job(
        solv.Job.SOLVER_INSTALL | solv.Job.SOLVER_SOLVABLE,
        matches[0].id,
    )
    problems = solver.solve([job])
    if problems:
        return {
            "protocol": PROTOCOL_VERSION,
            "error": "dependency resolution failed",
            "problems": [str(problem) for problem in problems],
        }
    return {
        "protocol": PROTOCOL_VERSION,
        "plan": [
            {"name": item.name, "evr": item.evr, "arch": item.arch}
            for item in solver.transaction().steps()
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", help="local RPM-MD repository directory or URL")
    parser.add_argument("package")
    parser.add_argument(
        "--cache-dir",
        default=os.path.join(tempfile.gettempdir(), "bum-cache"),
        help="directory for librepo's metadata cache",
    )
    args = parser.parse_args()
    try:
        result = _plan(args.repo, args.package, args.cache_dir)
        print(json.dumps(result, sort_keys=True))
        return 0 if "error" not in result else 1
    except (librepo.LibrepoException, OSError, ValueError) as exc:
        print(
            json.dumps({"protocol": PROTOCOL_VERSION, "error": str(exc)}),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
