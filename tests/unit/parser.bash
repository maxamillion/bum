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
if fn_parse_repofile "$repo_file"; then
    printf 'expected duplicate key to fail\n' >&2
    exit 1
fi
[[ "${__return__[error]}" == *'duplicate key'* ]]

cat > "$repo_file" <<'EOF'
[alpha]
name=first
[alpha]
baseurl=https://example.invalid
EOF
if fn_parse_repofile "$repo_file"; then
    printf 'expected duplicate section to fail\n' >&2
    exit 1
fi
[[ "${__return__[error]}" == *'duplicate section'* ]]

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

# Repository directory loader applies defaults and validates required fields.
repo_dir=$(mktemp -d)
trap 'rm -rf -- "$tmp_dir" "$repo_dir"' EXIT
fail() {
    printf '%s\n' "$1" >&2
    exit 1
}
cat > "$repo_dir/10-enabled.repo" <<'REPO'
[enabled]
name = Enabled repository
baseurl = https://example.invalid/repo?arch=x86_64
REPO
cat > "$repo_dir/20-disabled.repo" <<'REPO'
[disabled]
enabled = no
baseurl = file:///unused
REPO
cat > "$repo_dir/25-standard-port.repo" <<'REPO'
[standard-port]
baseurl = https://example.invalid:443/repo
REPO
if ! fn_load_repositories "$repo_dir"; then
    fail "valid repo directory rejected: ${__return__[error]}"
fi
[[ ${__return__[enabled|enabled]} == 1 && \
    ${__return__[enabled|gpgcheck]} == 1 && \
    ${__return__[disabled|enabled]} == 0 ]] || fail 'repo defaults incorrect'
cat > "$repo_dir/30-invalid.repo" <<'REPO'
[invalid]
enabled = perhaps
REPO
if fn_load_repositories "$repo_dir"; then
    fail 'invalid enabled value accepted'
fi
[[ ${__return__[error]} == *'invalid enabled value'* ]] || \
    fail 'invalid enabled diagnostic missing'
rm -f "$repo_dir/30-invalid.repo"

for bad_url in \
    'ftp://example.invalid/repo' \
    'https:///repo' \
    'https://bad host/repo' \
    'https://one.invalid/repo https://two.invalid/repo' \
    'file://relative/path' \
    'https://[abc]/repo' \
    'https://[::1]:bogus/repo' \
    'https://[::1]/repo' \
    'https://example.invalid:abc/repo' \
    'https://example.invalid:0/repo' \
    'https://example.invalid:65536/repo' \
    'https://user:pass@example.invalid/repo' \
    'https://example.invalid:/repo' \
    'https://example.invalid/repo#fragment'; do
    cat > "$repo_dir/40-invalid-url.repo" <<REPO
[bad]
baseurl = $bad_url
REPO
    if fn_load_repositories "$repo_dir"; then
        fail "invalid baseurl accepted: $bad_url"
    fi
    [[ ${__return__[error]} == *'baseurl'* || \
        ${__return__[error]} == *'unsupported baseurl scheme'* ]] || \
        fail "invalid baseurl diagnostic missing: $bad_url"
    rm -f "$repo_dir/40-invalid-url.repo"
done

cat > "$repo_dir/50-localhost-url.repo" <<'REPO'
[localhost]
baseurl = file://localhost/srv/repo
REPO
fn_load_repositories "$repo_dir" || fail "localhost file URL rejected"
printf '[PASS] repository directory loading tests\n'
