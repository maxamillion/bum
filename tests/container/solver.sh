#!/usr/bin/env bash
# Run RPM-MD and solver prototypes in a disposable Podman container.
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "$script_dir/../.." && pwd)
image=${1:-quay.io/almalinuxorg/almalinux:9}
podman_bin=${PODMAN:-podman}

if ! command -v "$podman_bin" >/dev/null 2>&1; then
    printf 'error: Podman executable not found: %s\n' "$podman_bin" >&2
    exit 127
fi
if ! "$podman_bin" image exists "$image"; then
    "$podman_bin" pull "$image"
fi

test_root=$(mktemp -d "${TMPDIR:-/tmp}/bum-solver-test.XXXXXX")
cleanup() {
    rm -rf -- "$test_root"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

tar --exclude=.git -C "$repo_root" -cf - . | tar -C "$test_root" -xf -

printf 'Running metadata/solver tests in %s\n' "$image"
# Network only enables binding installation in the disposable container.
# shellcheck disable=SC2016
"$podman_bin" run --rm --network=pasta \
    --volume "$test_root:/workspace:ro,Z" \
    --workdir /workspace \
    --entrypoint /bin/bash \
    "$image" -c '
        set -euo pipefail
        if command -v dnf >/dev/null 2>&1; then
            dnf -y -q install python3-solv python3-librepo
        elif command -v microdnf >/dev/null 2>&1; then
            microdnf -y install python3-solv python3-librepo
        else
            printf "No package installer for RPM-MD test dependencies\\n" >&2
            exit 77
        fi
        python3 tests/unit/solver-plan.py
        python3 helpers/bum-solver.py < tests/fixtures/solver/install.json
        bash tests/unit/repomd.bash
        python3 tests/unit/repomd-remote.py
    '
