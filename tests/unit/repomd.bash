#!/usr/bin/env bash
# RPM-MD fixture integrity and solver integration checks.
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
repo_fixture="$repo_root/tests/fixtures/rpmmd"

if ! command -v python3 >/dev/null 2>&1 || \
    ! python3 -c 'import librepo, solv' >/dev/null 2>&1; then
    printf '[SKIP] librepo/libsolv bindings unavailable\n'
    exit 0
fi

output=$(python3 "$repo_root/helpers/bum-repomd.py" \
    "$repo_fixture" demo-app)
python3 -c '
import json, sys
response = json.loads(sys.argv[1])
assert response["protocol"] == 1
assert {(p["name"], p["evr"], p["arch"]) for p in response["plan"]} == {
    ("demo-app", "1.0-1", "noarch"),
    ("demo-lib", "1.0-1", "noarch"),
}
' "$output"

printf '[PASS] RPM-MD metadata and dependency plan\n'
