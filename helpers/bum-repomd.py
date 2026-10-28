#!/usr/bin/env python3
"""Load checksum-verified RPM-MD and create an install plan (prototype)."""
import argparse
import fcntl
import gzip
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ElementTree
import zlib

try:
    import librepo
    import solv
except ImportError as exc:
    print(json.dumps({"protocol": 1,
                      "error": f"missing Python dependency: {exc.name}"}),
          file=sys.stderr)
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

    package_metadata = {}
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

        checksum = package.find(f"{COMMON_NS}checksum")
        location = package.find(f"{COMMON_NS}location")
        size = package.find(f"{COMMON_NS}size")
        package_metadata_entry = {
            "checksum_type": checksum.get("type", "") if checksum is not None else "",
            "checksum": (
                checksum.text.strip()
                if checksum is not None and checksum.text else ""
            ),
            "location": location.get("href", "") if location is not None else "",
            "size": int(size.get("package", "0")) if size is not None else 0,
        }
        solvable = repo.add_solvable()
        solvable.name = name
        package_metadata[solvable.id] = package_metadata_entry
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
    return package_metadata


def _validate_source(source):
    invalid_chars = (
        any(ch.isspace() or unicodedata.category(ch) == "Cc" for ch in source)
        if isinstance(source, str) else True
    )
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
    raise ValueError("repository source must be a local directory or HTTP(S) URL")


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
        raise ValueError(f"cache directory is not owned by current user: {path}")
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
        package_metadata = _parse_primary(pool, repo, primary_path)
        repo.internalize()
        pool.createwhatprovides()
        return pool, repo, package_metadata


def _download_packages_unlocked(source, cache_dir, packages):
    source = _validate_source(source)
    cache_dir = _secure_cache_dir(cache_dir)
    is_remote = source.startswith(("http://", "https://"))
    package_cache = os.path.join(cache_dir, "packages")
    os.makedirs(package_cache, mode=0o700, exist_ok=True)
    package_cache = _secure_cache_dir(package_cache)
    staged = []
    published = []
    try:
        for package in packages:
            href = package.get("location", "")
            checksum_type = package.get("checksum_type", "").lower()
            checksum = package.get("checksum", "")
            size = package.get("size", 0)
            parsed_href = urllib.parse.urlsplit(href)
            decoded_path = urllib.parse.unquote(parsed_href.path)
            if (not href or parsed_href.scheme or parsed_href.netloc
                    or parsed_href.query or parsed_href.fragment
                    or re.search(r"%(?![0-9A-Fa-f]{2})", href)
                    or "%" in decoded_path
                    or decoded_path.startswith("/") or "\\" in decoded_path
                    or any(part in ("", ".", "..")
                           for part in decoded_path.split("/"))):
                raise ValueError("unsafe or missing package location")
            if (not isinstance(size, int) or isinstance(size, bool) or size <= 0
                    or not checksum_type or not checksum):
                raise ValueError("package metadata lacks checksum or size")
            try:
                digest = hashlib.new(checksum_type.replace("-", "").lower())
            except ValueError as exc:
                raise ValueError(
                    f"unsupported package checksum: {checksum_type}"
                ) from exc
            if (len(checksum) != digest.digest_size * 2
                    or any(ch not in "0123456789abcdefABCDEF"
                           for ch in checksum)):
                raise ValueError("invalid package checksum format")
            filename = hashlib.sha256(
                (href + "\0" + checksum.lower()).encode("utf-8")
            ).hexdigest()
            suffix = os.path.splitext(os.path.basename(decoded_path))[1]
            final_path = os.path.join(package_cache, filename + suffix)
            try:
                os.lstat(final_path)
                cache_entry_exists = True
            except FileNotFoundError:
                cache_entry_exists = False
            if cache_entry_exists:
                if not stat.S_ISREG(os.lstat(final_path).st_mode):
                    raise ValueError("unsafe package cache entry")
                with open(final_path, "rb") as cached:
                    cached_digest = hashlib.new(digest.name)
                    cached_size = 0
                    for block in iter(lambda: cached.read(1024 * 1024), b""):
                        cached_size += len(block)
                        cached_digest.update(block)
                if (cached_size == size
                        and cached_digest.hexdigest().lower() == checksum.lower()):
                    staged.append((None, final_path))
                    continue
            fd, stage_path = tempfile.mkstemp(
                prefix=".bum-download-", dir=package_cache
            )
            os.close(fd)
            handle = librepo.Handle()
            handle.setopt(librepo.LRO_REPOTYPE, librepo.LR_YUMREPO)
            handle.setopt(librepo.LRO_URLS, [source])
            handle.setopt(librepo.LRO_LOCAL, not is_remote)
            handle.setopt(librepo.LRO_CHECKSUM, True)
            handle.download_package(
                href, stage_path, librepo.checksum_str_to_type(checksum_type),
                checksum, size, None, False
            )
            actual_size = 0
            actual_digest = hashlib.new(digest.name)
            with open(stage_path, "rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    actual_size += len(block)
                    actual_digest.update(block)
            if (actual_size != size
                    or actual_digest.hexdigest().lower() != checksum.lower()):
                raise ValueError(f"download checksum/size mismatch: {href}")
            staged.append((stage_path, final_path))

        backups = []
        try:
            for stage_path, final_path in staged:
                if stage_path is None:
                    published.append(final_path)
                    continue
                if os.path.lexists(final_path):
                    backup_fd, backup_path = tempfile.mkstemp(
                        prefix=".bum-backup-", dir=package_cache
                    )
                    os.close(backup_fd)
                    os.replace(final_path, backup_path)
                    backups.append((backup_path, final_path))
                published.append(final_path)
                os.replace(stage_path, final_path)
        except Exception:
            for final_path in published:
                try:
                    os.unlink(final_path)
                except FileNotFoundError:
                    pass
            for backup_path, final_path in backups:
                os.replace(backup_path, final_path)
            raise
        for backup_path, _ in backups:
            try:
                os.unlink(backup_path)
            except FileNotFoundError:
                pass
        return published
    except Exception:
        for stage_path, _ in staged:
            if stage_path is not None:
                try:
                    os.unlink(stage_path)
                except FileNotFoundError:
                    pass
        raise


def _download_packages(source, cache_dir, packages):
    """Serialize package cache downloads/publication within one cache."""
    cache_dir = _secure_cache_dir(cache_dir)
    lock_path = os.path.join(cache_dir, ".bum-download.lock")
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    lock_fd = os.open(lock_path, flags, 0o600)
    try:
        info = os.fstat(lock_fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077):
            raise ValueError("unsafe package download lock")
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        return _download_packages_unlocked(source, cache_dir, packages)
    finally:
        os.close(lock_fd)


def _plan(source, package_name, cache_dir, download_dir=None):
    if (not package_name or package_name.startswith("-")
            or any(ch.isspace() or unicodedata.category(ch) == "Cc"
                   for ch in package_name)):
        raise ValueError("invalid package name")
    pool, repo, package_metadata = _load_repo(source, cache_dir)
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
    plan_items = [
        {"name": item.name, "evr": item.evr, "arch": item.arch,
         **package_metadata.get(item.id, {})}
        for item in solver.transaction().steps()
    ]
    if download_dir is not None:
        files = _download_packages(source, download_dir, plan_items)
        for item, path in zip(plan_items, files):
            item["downloaded"] = path
    return {"protocol": PROTOCOL_VERSION, "plan": plan_items}


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
    parser.add_argument(
        "--download", metavar="DIR",
        help="download transaction RPMs into a private cache",
    )
    args = parser.parse_args()
    try:
        result = _plan(args.repo, args.package, args.cache_dir, args.download)
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