#!/usr/bin/env bash
# Run repository checks in a disposable Podman container.
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "$script_dir/../.." && pwd)
image=${1:-quay.io/fedora/fedora:44}
podman_bin=${PODMAN:-podman}

if ! command -v "$podman_bin" >/dev/null 2>&1; then
    printf 'error: Podman executable not found: %s\n' "$podman_bin" >&2
    exit 127
fi

if ! "$podman_bin" image exists "$image"; then
    printf 'Pulling test image: %s\n' "$image"
    "$podman_bin" pull "$image"
fi

test_root=$(mktemp -d "${TMPDIR:-/tmp}/bum-container-test.XXXXXX")
cleanup() {
    rm -rf -- "$test_root"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

if ! tar --exclude=.git -C "$repo_root" -cf - . | \
    tar -C "$test_root" -xf -; then
    printf 'error: failed to stage repository for container tests\n' >&2
    exit 1
fi

printf 'Running checks in %s\n' "$image"
# shellcheck disable=SC2016
"$podman_bin" run --rm --network=none \
    --userns=keep-id \
    --user "$(id -u):$(id -g)" \
    --volume "$test_root:/workspace:ro,Z" \
    --workdir /workspace \
    --entrypoint /bin/bash \
    "$image" -c '
        set -euo pipefail
        printf "image: "
        grep -E "^(ID|VERSION_ID)=" /etc/os-release
        printf "rpm: "
        rpm --version
        while IFS= read -r -d "" file; do
            printf "bash -n %s\n" "$file"
            bash -n "$file"
        done < <(find . -type f \
            \( -name "*.bash" -o -name "bum" -o -name "*.sh" \) \
            -print0)
        bash -n < bum.conf
        bash tests/unit/parser.bash
        bash tests/unit/cli.bash
    '
