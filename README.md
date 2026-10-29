# bum — Bash Update Madness

## Current plan-only prototypes

Experimental, non-mutating install and remove planning commands are available:

```bash
./bum plan install PACKAGE --repo REPO_ID [--repo-dir DIR] [--cache-dir DIR] [--download-dir DIR]
./bum plan remove PACKAGE [--arch ARCH]
```

`plan install` reads the selected repository from `.repo` files, fetches
RPM-MD primary metadata through librepo, and produces an install dependency
plan through libsolv. It writes metadata/cache files under the selected cache
directory; its planning path does not use installed RPM state. The optional
`--download-dir` exercises the package payload download/cache prototype.

`plan remove` queries installed package inventory with `rpm -qa` and asks
libsolv to plan removal for the requested package and architecture. It does not
load repository candidates or propose replacements. Both commands are planning
only: neither invokes an RPM transaction nor changes installed package state.
Package signature verification and trusted-key policy are not implemented.
The install prototype is limited to x86_64; the planning helpers require
compatible Python `libsolv` bindings, and install planning also requires
`librepo`. These are not supported package mutation workflows.

bum is an experimental, standalone RPM package manager written primarily in
Bash. The project is at an early stage; package operations are not implemented
yet.

The initial target operations are `install`, `upgrade`, and `remove` on
selected Fedora, RHEL, CentOS, and AlmaLinux releases. bum is intended to own
repository parsing, metadata and package downloads, caching, dependency
planning, and orchestration. RPM itself will execute system package
transactions; bum will not reimplement RPM transaction/database behavior or
use DNF/microdnf as its operation engine. Eventual microdnf parity is an
aspirational goal, not a current compatibility claim.

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for the staged plan,
open decisions, support-matrix tracking, and verification status.

## Requirements

The implementation target is Bash 5.1 or newer. Additional runtime dependencies
and supported platform releases will be documented as architecture decisions
are made.

## Development checks

The local container test runner uses Podman and runs syntax and CLI/parser
smoke tests without modifying host package state:

```bash
./tests/container/run.sh
```

An optional first argument selects a Podman image. GitHub Actions runs the
initial container syntax matrix for pull requests and pushes to `main`/`master`.
