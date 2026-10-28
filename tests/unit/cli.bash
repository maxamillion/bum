#!/usr/bin/env bash
# CLI behavior smoke tests.
set -euo pipefail
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
bum_cmd="$repo_root/bum"
output=$("$bum_cmd" --help)
[[ "$output" == *'install PACKAGE'* ]]
[[ "$output" == *'plan install PACKAGE'* ]]
test "$("$bum_cmd" --version)" = 'bum 0.1-alpha'
expect_status() {
    local expected=$1; shift
    if "$@" >/dev/null 2>&1; then
        printf 'expected status %s: %s\n' "$expected" "$*" >&2
        exit 1
    else
        test "$?" -eq "$expected"
    fi
}
expect_status 2 "$bum_cmd" unknown
expect_status 2 "$bum_cmd" install
expect_status 3 "$bum_cmd" install package
expect_status 2 "$bum_cmd" plan install package
expect_status 2 "$bum_cmd" plan install package --repo
expect_status 2 "$bum_cmd" plan install '' --repo on
expect_status 2 "$bum_cmd" plan install --bad --repo on
expect_status 2 "$bum_cmd" plan install $'bad\tname' --repo on

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir "$tmp/repos"
cat > "$tmp/repos/example.repo" <<'EOF'
[off]
baseurl=https://example.invalid/repo
enabled=0
[on]
baseurl=https://example.invalid/repo
EOF
cat > "$tmp/python" <<'EOF'
#!/usr/bin/env bash
if [[ $1 == -c ]]; then exit 0; fi
printf called > "$BUM_MARKER"
printf '{"protocol":1,"plan":[]}\n'
EOF
chmod +x "$tmp/python"
export BUM_REPODIR="$tmp/repos" BUM_CACHEDIR="$tmp/cache"
export BUM_PYTHON="$tmp/python" BUM_MARKER="$tmp/marker"
expect_status 2 "$bum_cmd" plan install pkg --repo missing
[[ ! -e "$tmp/cache" ]]
[[ ! -e "$tmp/marker" ]]
expect_status 2 "$bum_cmd" plan install pkg --repo off
[[ ! -e "$tmp/cache" ]]
[[ ! -e "$tmp/marker" ]]
# Existing cache directories must be private and owned by the caller.
mkdir "$tmp/unsafe-cache"
chmod 0755 "$tmp/unsafe-cache"
expect_status 2 env BUM_CACHEDIR="$tmp/unsafe-cache" "$bum_cmd" plan install pkg --repo on
[[ ! -e "$tmp/marker" ]]
output=$("$bum_cmd" plan install pkg --repo on)
[[ "$output" == *'"plan":[]'* ]]
[[ -e "$tmp/marker" ]]
printf '[PASS] CLI tests\n'
