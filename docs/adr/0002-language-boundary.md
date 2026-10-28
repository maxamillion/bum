# ADR 0002: Language boundary for package metadata and solving

- **Status:** Proposed
- **Date:** 2026-10-28
- **Decision owner:** Project owner

## Context

bum's CLI and orchestration are Bash-led. Candidate lower-level components
librepo and libsolv provide Python bindings in Fedora 44 and AlmaLinux 9
container probes after installing their Python subpackages. Bash cannot call
these APIs natively; invoking Python helpers or writing a compiled helper adds
an interface and packaging boundary. Reimplementing the libraries' complex
metadata/solver behavior in Bash is not the preferred direction.

## Proposed decision

Keep the executable, CLI policy, repo-file parser, cache policy, command
orchestration, and transaction request generation in Bash. Use a small Python
helper for librepo/libsolv operations if Phase 1 prototypes establish that the
bindings and required methods work across every target. Give it a versioned,
validated JSON-lines or JSON request/response protocol, explicit errors, and no
authority to execute package transactions. RPM remains the transaction engine.

Do not commit to implementation until testing the oldest supported platform,
metadata loading, solving behavior, trust verification, and per-platform
version/packaging support. If Python bindings are absent on a target, choose
between a maintained helper build, RPM-native supported lower-level interface,
or narrowing the support matrix; do not silently fall back to DNF.

## Evidence so far

- Fedora 44 container: `python3-solv` and `python3-librepo` are available and
  importable after installing distro packages; libsolv 0.7.40 and librepo
  1.21.2 were observed.
- AlmaLinux 9 container: the same Python modules are available/importable after
  installing distro packages; libsolv 0.7.24 and librepo 1.19.0 were observed.
- A hand-built libsolv fixture on Fedora 44 and AlmaLinux 9 selected an
  application plus its dependency and rejected an unresolved dependency. This
  demonstrates binding functionality for a narrow solver case, not RPM-MD
  ingestion, installed-state solving, or full API equivalence.
- This confirms availability on two candidate releases only. It does not prove
  support across the complete target matrix.

## Consequences

- Bash remains the user-facing and policy/orchestration language, while
  mature bindings handle intricate metadata and SAT solving.
- JSON boundaries need schema validation, resource limits, stable errors, and
  version negotiation.
- Python runtime and bindings become runtime/build requirements on supported
  systems unless the helper is packaged or otherwise delivered.
- Helper must be tested as an untrusted-input boundary and must never invoke
  DNF/microdnf or perform transactions.

## Required validation

- [ ] Verify supported versions and package availability across every target.
- [ ] Prototype librepo metadata fetch and checksum validation.
- [ ] Prototype libsolv repository input and install/upgrade/remove solving.
- [ ] Test protocol malformed input, large metadata, and helper failures.
- [ ] Agree on Python helper boundary and runtime support before adoption.

## References

- [librepo Python examples](https://rpm-software-management.github.io/librepo/examples.html)
- [libsolv bindings documentation](https://github.com/openSUSE/libsolv/blob/master/doc/libsolv-bindings.txt)
- [libsolv project](https://github.com/openSUSE/libsolv)
