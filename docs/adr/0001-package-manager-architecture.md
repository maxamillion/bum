# ADR 0001: Standalone package manager architecture

- **Status:** Proposed
- **Date:** 2026-10-27
- **Decision owner:** Project owner

## Context

bum is a Bash-led standalone RPM package manager targeting selected Fedora,
RHEL, CentOS, and AlmaLinux releases. Its initial operations are install,
upgrade, and remove; eventual microdnf parity is aspirational.

bum owns repository configuration parsing, metadata acquisition, cache,
package downloads, selection, dependency planning, and orchestration. RPM
itself performs system package transactions. bum must neither delegate package
operations to DNF/microdnf nor reimplement RPM's database/transaction engine.

Implementing RPM-MD parsing, transfer/mirror behavior, dependency solving, and
RPM semantics from scratch in Bash would create a large correctness and
security burden. Lower-level RPM ecosystem components may be reused so bum can
own package-manager behavior without reimplementing stable specialist formats
and APIs.

## Proposed component boundary

1. **Repository configuration:** Bash bum parser validates supported `.repo`
   syntax/options and creates the repository configuration used by bum.
2. **RPM-MD and transfers:** evaluate librepo for metadata and package transfer
   support. bum owns repository selection, cache policy/lifecycle, and user
   behavior. Validate whether to call its Python bindings or use a helper.
3. **Dependency solving:** evaluate libsolv fed by metadata selected/managed by
   bum. bum owns command semantics, candidate policy, transaction intent, and
   reviewable plan. A solver result is not an RPM transaction.
4. **Installed state/transactions:** use RPM itself for installed database
   queries as needed and for install/upgrade/remove transactions. Do not build
   a parallel package database or transaction engine.
5. **Language boundary:** Bash remains CLI and orchestration. ADR 0002 proposes
   a narrow Python helper for bindings; adoption requires compatibility and
   protocol tests across the selected support matrix.

This is proposed, not a claim that dependencies are available or supported on
every target. Verify versions and APIs against the approved matrix.

## Consequences

- Reuse mature metadata, transfer, solver, and transaction components while
  retaining bum's package-manager policy and orchestration.
- Binding and library versions may differ across Fedora and enterprise
  releases; a stable helper protocol or maintained build may be needed.
- RPM is the only system transaction executor. Do not let a helper call DNF or
  microdnf, and do not treat a solver plan as execution authorization.
- Repo parsing by bum does not require reimplementing every metadata encoding
  or HTTP behavior.
- Compatibility claims are limited to tested version/platform combinations.

## Required feasibility work

- [ ] Select releases/architectures; record RPM, librepo, libsolv and binding
  versions in each container.
- [ ] Fetch RPM-MD metadata and validate checksums without DNF/microdnf.
- [ ] Generate deterministic install/upgrade/remove plans for fixtures.
- [ ] Demonstrate bum uses RPM itself for final system transactions.
- [ ] Establish signature/checksum trust and key enrollment behavior.
- [ ] Validate helper/API and packaging across the oldest target.
- [ ] Run probes only in disposable Podman containers and record image digests,
  commands, outputs, and limitations.

## Alternatives

- **Reimplement parsing/solver/transaction in Bash:** rejected as initial
  direction due to duplicated semantics and broad correctness/security burden.
- **Use DNF/microdnf as operation engine:** rejected because it violates the
  standalone requirement and bum's ownership of package workflow.
- **Use lower-level RPM ecosystem components with bum orchestration:** proposed
  for validation; reuses specialist components without delegating the workflow.

## References

- [librepo project](https://github.com/rpm-software-management/librepo)
- [librepo documentation](https://rpm-software-management.github.io/librepo/)
- [libsolv project](https://github.com/openSUSE/libsolv)
- [libsolv bindings](https://github.com/openSUSE/libsolv/blob/master/doc/libsolv-bindings.txt)
- [RPM transaction-set API](https://rpm.org/docs/latest/api/group__rpmts.html)
- [RPM documentation](https://rpm.org/docs/)

## Review / implementation evidence

| Date | Reviewer / agent | Result and evidence |
|---|---|---|
| TBD | | |
