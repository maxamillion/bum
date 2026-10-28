#!/usr/bin/env python3
"""Load checksum-verified RPM-MD and create an install plan (prototype)."""
import argparse
import gzip
import json
import os
import stat
import sys
import tempfile
import unicodedata
import zlib
import urllib.parse
import xml.etree.ElementTree as ElementTree

try:
    import librepo
    import solv
except ImportError as exc:
    # Keep dependency failures machine-readable for callers and diagnostics.
    message = f"missing Python dependency: {exc.name}"
    print(json.dumps({"protocol": 1, "error": message}), file=sys.stderr)
    sys.exit(2)

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


def _validate_source(source):
    invalid_chars = any(
        ch.isspace() or unicodedata.category(ch) == "Cc" for ch in source
    ) if isinstance(source, str) else True
    if not isinstance(source, str) or not source or invalid_chars:
        raise ValueError("invalid repository source")
    try:
        parsed = urllib.parse.urlsplit(source)
    except ValueError as exc:
        raise ValueError("invalid repository URL") from exc
    if parsed.scheme in ("http", "https"):
        if (not parsed.hostname or parsed.username or parsed.password
                or parsed.fragment):
            raise ValueError("invalid repository URL authority")
        try:
            port = parsed.port
        except ValueError as exc:
            raise ValueError("invalid repository URL port") from exc
        if port is not None and not 1 <= port <= 65535:
            raise ValueError("invalid repository URL port")
        return source
    if parsed.scheme == "file":
        if (parsed.netloc not in ("", "localhost") or parsed.query
                or parsed.fragment):
            raise ValueError("file repository URL must use a local path")
        path = urllib.parse.unquote(parsed.path)
        if not os.path.isabs(path):
            raise ValueError("file repository URL path must be absolute")
        return path
    if parsed.scheme:
        raise ValueError("unsupported repository URL scheme")
    if os.path.isdir(source):
        return os.path.realpath(source)
    raise ValueError(
        "repository source must be a local directory or HTTP(S) URL"
    )


def _secure_cache_dir(cache_dir):
    """Create/validate a private cache directory without following symlinks."""
    path = os.path.abspath(cache_dir)
    parent = os.path.dirname(path)
    if not os.path.exists(parent):
        try:
            os.makedirs(parent, mode=0o700, exist_ok=True)
        except OSError as exc:
            raise ValueError(f"cannot create cache parent: {parent}") from exc
    try:
        resolved_parent = os.path.realpath(parent, strict=True)
        parent_info = os.stat(resolved_parent, follow_symlinks=False)
    except OSError as exc:
        raise ValueError(f"unsafe cache parent: {parent}") from exc
    if resolved_parent != parent or not stat.S_ISDIR(parent_info.st_mode):
        raise ValueError(f"unsafe cache parent: {parent}")
    # Validate every ancestor: sticky shared ancestors such as /tmp are safe,
    # but writable non-sticky directories controlled by others are not.
    ancestor = resolved_parent
    while True:
        info = os.stat(ancestor, follow_symlinks=False)
        if info.st_uid not in (os.getuid(), 0):
            raise ValueError(f"unsafe cache parent: {ancestor}")
        if info.st_mode & 0o002 and not info.st_mode & stat.S_ISVTX:
            raise ValueError(f"unsafe cache parent: {ancestor}")
        next_ancestor = os.path.dirname(ancestor)
        if next_ancestor == ancestor:
            break
        ancestor = next_ancestor
    try:
        os.mkdir(path, 0o700)
    except FileExistsError:
        pass
    info = os.lstat(path)
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"cache path must be a directory: {path}")
    if info.st_uid != os.getuid():
        raise ValueError(
            f"cache directory is not owned by current user: {path}"
        )
    if info.st_mode & 0o077:
        raise ValueError(f"cache directory permissions are unsafe: {path}")
    return path


def _load_repo(source, cache_dir):
    source = _validate_source(source)
    cache_dir = _secure_cache_dir(cache_dir)
    with tempfile.TemporaryDirectory(prefix="bum-repomd-") as work_dir:
        handle = librepo.Handle()
        result = librepo.Result()
        handle.setopt(librepo.LRO_REPOTYPE, librepo.LR_YUMREPO)
        handle.setopt(librepo.LRO_URLS, [source])
        is_remote = source.startswith(("http://", "https://"))
        handle.setopt(librepo.LRO_LOCAL, not is_remote)
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
    if (not package_name or package_name.startswith("-")
            or any(ch.isspace() or unicodedata.category(ch) == "Cc"
                   for ch in package_name)):
        raise ValueError("invalid package name")
    pool, repo = _load_repo(source, cache_dir)
    matches = [
        item for item in repo.solvables_iter() if item.name == package_name
    ]
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
    cache_home = os.environ.get("XDG_CACHE_HOME")
    if not cache_home:
        cache_home = os.path.join(os.path.expanduser("~"), ".cache")
    parser.add_argument(
        "--cache-dir",
        default=os.path.join(cache_home, "bum"),
        help="directory for librepo's metadata cache",
    )
    args = parser.parse_args()
    try:
        result = _plan(args.repo, args.package, args.cache_dir)
        print(json.dumps(result, sort_keys=True))
        return 0 if "error" not in result else 1
    except (
        librepo.LibrepoException,
        ElementTree.ParseError,
        EOFError,
        UnicodeError,
        zlib.error,
        OSError,
        ValueError,
        RuntimeError,
        TypeError,
        AttributeError,
        KeyError,
        IndexError,
    ) as exc:
        print(
            json.dumps({"protocol": PROTOCOL_VERSION, "error": str(exc)}),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
