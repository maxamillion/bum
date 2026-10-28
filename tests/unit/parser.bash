#!/usr/bin/env bash
# Unit tests for the repo configuration parser.
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
# shellcheck source=libbum/parser.bash
# shellcheck disable=SC1091
source "$repo_root/libbum/parser.bash"

tmp_dir=$(mktemp -d)
trap 'rm -rf -- "$tmp_dir"' EXIT
repo_file=$tmp_dir/test.repo

cat > "$repo_file" <<'EOF'
# leading comment
[alpha]
name = Alpha Repository
baseurl = https://example.invalid/repo?x=a=b
enabled=1
; semicolon comment
[beta]
baseurl=file:///srv/repo
EOF

fn_parse_repofile "$repo_file"
# shellcheck disable=SC2154
 test "${__return__[alpha|name]}" = 'Alpha Repository'
test "${__return__[alpha|baseurl]}" = 'https://example.invalid/repo?x=a=b'
test "${__return__[beta|baseurl]}" = 'file:///srv/repo'
test "${__return__[alpha|enabled]}" = 1
test "${__return__[beta|__section__]}" = beta

cat > "$repo_file" <<'EOF'
[alpha]
name=first
name=second
EOF
fn_parse_repofile "$repo_file"
test "${__return__[alpha|name]}" = second

cat > "$repo_file" <<'EOF'
name=outside-section
EOF
if fn_parse_repofile "$repo_file"; then
    printf 'expected key outside section to fail\n' >&2
    exit 1
fi
[[ "${__return__[error]}" == *':1: expected section'* ]]

cat > "$repo_file" <<'EOF'
[]
EOF
if fn_parse_repofile "$repo_file"; then
    printf 'expected empty section to fail\n' >&2
    exit 1
fi
[[ "${__return__[error]}" == *':1: invalid section' ]]

if fn_parse_repofile "$tmp_dir/missing.repo"; then
    printf 'expected unreadable file to fail\n' >&2
    exit 1
fi
[[ "${__return__[error]}" == *'not a readable regular file'* ]]

if fn_parse_repofile; then
    printf 'expected missing argument to fail\n' >&2
    exit 1
fi
test "${__return__[error]}" = 'repository file path is required'

printf '[PASS] repository parser tests\n'
