# bum — Bash Update Madness

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
