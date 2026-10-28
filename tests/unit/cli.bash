#!/usr/bin/env bash
# CLI behavior smoke tests.
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
bum_cmd="$repo_root/bum"

output=$("$bum_cmd" --help)
[[ "$output" == *'install PACKAGE'* ]]
test "$("$bum_cmd" --version)" = 'bum 0.1-alpha'

if "$bum_cmd" unknown >/dev/null 2>&1; then
    printf 'expected unknown command to fail\n' >&2
    exit 1
else
    test "$?" -eq 2
fi

if "$bum_cmd" install >/dev/null 2>&1; then
    printf 'expected missing package argument to fail\n' >&2
    exit 1
else
    test "$?" -eq 2
fi

if "$bum_cmd" install package >/dev/null 2>&1; then
    printf 'expected unimplemented command to fail\n' >&2
    exit 1
else
    test "$?" -eq 3
fi

printf '[PASS] CLI tests\n'
