#!/usr/bin/env bash
# Solver-helper protocol and dependency-plan tests.
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
helper="$repo_root/helpers/bum-solver.py"
fixture_dir="$repo_root/tests/fixtures/solver"

if ! command -v python3 >/dev/null 2>&1; then
    printf '[SKIP] python3 is unavailable\n'
    exit 0
fi
if ! python3 -c 'import solv' >/dev/null 2>&1; then
    printf '[SKIP] python3-solv is unavailable\n'
    exit 0
fi

output=$(python3 "$helper" < "$fixture_dir/install.json")
python3 -c '
import json, sys
result = json.loads(sys.argv[1])
assert result["protocol"] == 1
assert result["operation"] == "install"
assert result["plan"] == [
    {"name": "demo-app", "evr": "1.0-1", "arch": "x86_64"},
    {"name": "demo-lib", "evr": "1.0-1", "arch": "x86_64"},
]
' "$output"

if python3 "$helper" < "$fixture_dir/unresolved.json" >/dev/null; then
    printf 'expected unresolved dependency to fail\n' >&2
    exit 1
else
    test "$?" -eq 1
fi

printf '[PASS] solver-helper tests\n'
