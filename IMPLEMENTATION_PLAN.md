# bum Implementation Plan

**Status:** Draft — pending project-owner review  
**Last updated:** 2026-10-27  
**Purpose:** A progress-tracking plan usable by the project owner or a delegated
coding agent. Update status, evidence, and decisions as work proceeds.

## Project direction

bum is to become a standalone RPM package manager implemented primarily in
Bash, not a frontend that delegates package operations to DNF or microdnf.
The initial user-facing operations are `install`, `upgrade`, and `remove`.
Eventual microdnf parity is aspirational, not an initial-release criterion.

bum owns repository parsing, metadata and package downloads, cache management,
package selection, dependency solving, and transaction planning. **RPM itself
performs system package transactions.** bum will not reimplement the RPM
database or transaction behavior and will not delegate package operations to
DNF/microdnf. The architecture phase decides how bum invokes RPM and handles
locking, errors, and recovery, not whether to reinvent RPM transactions.

## How to track progress

Use one of these values for each phase and task:

- `[ ]` Not started
- `[-]` In progress
- `[x]` Complete, with verification evidence recorded
- `[!]` Blocked; explain the blocker
- `[~]` Deferred or descoped; record why

A phase is complete only when its exit criteria are met and evidence is
recorded. A code change or agent report alone is not evidence. Record commands,
relevant results, test environment, and commit/PR where applicable. Keep scope
changes in the decision log.

### Progress summary

| Phase | Status | Owner | Evidence / notes |
|---|---|---|---|
| 0. Requirements and support contract | [ ] | | |
| 1. Architecture and feasibility spike | [ ] | | |
| 2. Container test infrastructure and CI | [ ] | | |
| 3. CLI, configuration, and test foundation | [ ] | | |
| 4. Repository parsing and metadata/cache | [ ] | | |
| 5. Package model, solver, and transaction plan | [ ] | | |
| 6. Download and trust verification | [ ] | | |
| 7. RPM transaction integration | [ ] | | |
| 8. Initial release hardening | [ ] | | |
| 9. Compatibility expansion toward microdnf | [ ] | | |

## Scope and non-goals

### Initial scope

- Support explicitly selected releases and architectures of Fedora, RHEL,
  CentOS, and AlmaLinux. Phase 0 will specify the matrix.
- Provide `install`, `upgrade`, and `remove` operations.
- Own repository parsing, metadata acquisition, cache, downloads, verification,
  package selection, and dependency planning.
- Use RPM itself for system package transactions through a supported interface.
- Provide a plan-only or equivalent review mode before system mutation.
- Run tests that inspect or mutate package state in disposable containers:
  locally with Podman and in GitHub Actions CI. Do not mutate the developer
  host.

### Not an initial-release promise

- Full microdnf, DNF, or yum compatibility.
- Every repository option, metadata version, compression format, architecture,
  modularity feature, or dependency policy used by every target release.
- Reimplementing the RPM database or transaction engine.

Record scope changes in the decision log and update the compatibility matrix
and tests.

## Global engineering and safety requirements

These apply to every implementation phase:

- Run package-state and system-changing tests only in disposable containers.
  The local supported runner is Podman; GitHub Actions provides CI coverage.
  Never mount the host RPM database or package directories into test containers.
- Keep local and CI verification commands aligned through a shared runner
  where practical. Record image references/digests, commands, results, and logs.
- Follow `STYLEGUIDE.md`: `fn_` function names, four-space indentation,
  maximum 80-character lines, and the `__return__` convention. Resolve the
  tabs-versus-spaces ambiguity and enforce one convention.
- bum may use lower-level RPM ecosystem components, but must not hand package
  operations to DNF/microdnf or reimplement RPM transaction behavior.
- Do not use `eval`; quote values and pass commands through Bash arrays.
- Validate user input and repo configuration; reject unsupported or ambiguous
  constructs rather than silently misinterpreting them.
- Check external command failures and preserve meaningful exit statuses.
- Treat repository metadata and packages as untrusted. Verify integrity and
  signatures according to an explicit policy; never silently disable checks.
- Use safe temporary files, atomic cache publication, locks, and cleanup on
  interruption where applicable.

## Phases

### Phase 0 — Requirements and supported-platform contract

**Status:** [ ] Not started

**Tasks**

- [ ] Specify supported OS releases, architectures, and RPM versions for the
  first milestone and initial release.
- [ ] Define which lower-level RPM libraries/tools bum may use, while retaining
  ownership of repository parsing, metadata lifecycle, downloads, cache, and
  package-manager behavior.
- [ ] Define the RPM invocation interface as a research question for Phase 1;
  RPM itself performs system transactions.
- [ ] Define initial repository syntax and metadata/compression formats,
  including variable expansion and unsupported options.
- [ ] Set dependency policy: architecture selection, weak dependencies,
  obsoletes, conflicts, and downgrade behavior.
- [ ] Define privilege expectations, confirmation, noninteractive mode, exit
  statuses, and behavior when another package manager is active.
- [ ] Define compatibility expectations for systems already managed by DNF
  and how RPM database state is treated.
- [ ] Agree on initial release criteria and postponed features.

**Exit criteria**

- A reviewed support matrix and behavioral contract exist.
- Each item is decided or explicitly deferred with rationale and an owner.

**Evidence:** specification/review link and unresolved questions.

### Phase 1 — Architecture and feasibility spike

**Status:** [ ] Not started

**Objective:** Prove bum can load repository metadata and produce a correct
dependency-resolved plan using a viable architecture, without modifying the
host.

**Tasks**

- [ ] Compare lower-level RPM ecosystem options for metadata parsing, version
  comparison, dependency solving, and RPM invocation. Assess stability,
  bindings, availability across targets, licensing, and upgrade compatibility.
- [ ] Research metadata formats actually emitted by selected distributions.
- [ ] Choose Bash/helper component boundaries and interfaces. bum retains
  repository configuration, metadata lifecycle, downloads, cache, and command
  behavior; RPM performs system package transactions.
- [ ] Prototype loading metadata from a representative test repository and
  producing a deterministic plan without running a transaction.
- [ ] Prototype version and capability matching against package fixtures.
- [ ] Record transaction invocation, lock strategy, trust/key model, cache
  ownership, error model, and fallback options in an Architecture Decision
  Record (ADR).

**Exit criteria**

- An ADR is reviewed and answers the architecture questions above.
- A repeatable prototype resolves a dependency chain and reports missing or
  conflicting dependencies without running a transaction.
- Dependencies and limitations are documented for each target platform.

**Evidence:** prototype command, fixture/repository identity, expected/actual
plan, and results. One repository does not establish broad compatibility.

### Phase 2 — Container test infrastructure and CI

**Status:** [ ] Not started

**Objective:** Make verification reproducible and isolate all integration and
system-changing tests from the developer host.

**Tasks**

- [ ] Define image requirements from the Phase 0 support matrix. Select distro,
  release, and architecture images; pin versions/digests where feasible and
  document the update policy.
- [ ] Add a Podman local runner to build/pull images and run tests in disposable
  containers. Proposed shared entry point: `tests/container/run.sh`.
- [ ] Mount only the checkout and controlled fixtures/cache. Do not mount host
  RPM databases, package directories, or credentials. Minimize and document
  required privileges.
- [ ] Separate fast checks (syntax, unit, fixture tests) from container
  integration tests (metadata, downloads, RPM transactions).
- [ ] Capture output and image identity, propagate exit status, and provide
  useful failure diagnostics.
- [ ] Add GitHub Actions workflows using the shared test interface where
  practical, with matrix coverage for supported images/architectures available
  on GitHub-hosted runners.
- [ ] Configure pull-request required checks. Define coverage for matrix
  entries unavailable on hosted runners (alternate runner or documented
  manual/periodic test); do not mark uncovered entries as passing.
- [ ] Document Podman prerequisites, local commands, CI behavior, and failure
  reproduction steps.

**Exit criteria**

- The Podman runner uses disposable containers, preserves failures, and does
  not mutate host package state.
- GitHub Actions runs the same test commands where practical and exposes
  actionable logs per supported CI matrix entry.
- Unavailable entries have a defined coverage path and are not reported as
  passing without execution.
- Pull requests are gated by agreed required checks.

**Container matrix tracking template**

| Distro/release | Architecture | Image tag/digest | Podman | GitHub Actions | Suites / notes |
|---|---|---|---|---|---|
| TBD | TBD | TBD | Pending | Pending | From Phase 0 support matrix |

**Evidence:** Podman command/output, workflow run links, image identifiers,
matrix results, and exclusions or alternate coverage.

### Phase 3 — CLI, configuration, and test foundation

**Status:** [ ] Not started

**Tasks**

- [ ] Add executable `bum` and source libraries relative to its location,
  independent of caller working directory.
- [ ] Implement dispatch for `install`, `upgrade`, and `remove`, plus help and
  version output. Unimplemented commands must fail clearly.
- [ ] Define configuration precedence, validation, defaults, and errors. Keep
  sourced libraries free of unintended execution.
- [ ] Establish exit-status and diagnostic conventions.
- [ ] Add test scaffolding and fixtures. Ensure tests run through the container
  infrastructure in Phase 2 where required.
- [ ] Enforce the chosen tabs-versus-spaces style interpretation.

**Exit criteria**

- Help/version and invalid command/argument behavior are tested.
- Every Bash source passes `bash -n`.
- Tests run without root unless a disposable container explicitly requires it;
  no test mutates the host.

**Verification (adapt as harness is implemented):**

```bash
bash -n bum libbum/*.bash
./bum --help
./bum --version
```

Record the final automated test command when available.

### Phase 4 — Repository parsing, metadata, and cache

**Status:** [ ] Not started

**Tasks**

- [ ] Specify and implement `.repo` syntax: sections, comments, blank lines,
  duplicate keys, empty values, quoting, defaults, and invalid input behavior.
- [ ] Support multiple repositories without flattening their settings into one
  global map.
- [ ] Implement only the variable expansion rules specified in Phase 0.
- [ ] Validate URLs, local paths, and supported options. Reject malformed or
  unsupported required configuration with actionable errors.
- [ ] Implement metadata retrieval and supported format/compression handling.
- [ ] Implement cache layout, expiration, refresh, atomic publication, locking,
  and cleanup of incomplete data.
- [ ] Add fixture tests from actual repo files and metadata for supported
  distribution/release families.

**Exit criteria**

- Parser tests cover sections, comments, malformed input, duplicate values,
  spaces, empty values, and variable expansion.
- Metadata tests cover formats, stale/missing cache, failed/interrupted
  retrieval, and invalid content.
- Invalid or partial metadata is never exposed as a valid cache entry.

### Phase 5 — Package model, dependency solving, and transaction plan

**Status:** [ ] Not started

**Tasks**

- [ ] Define package identity, EVR/version comparison, architecture, provides,
  requires, conflicts, obsoletes, and repository priority semantics.
- [ ] Implement candidate selection and dependency closure using the Phase 1
  architecture.
- [ ] Implement `install`, `upgrade`, and `remove` plan generation.
- [ ] Detect unsatisfied dependencies, conflicts, unsupported metadata, and
  ambiguous candidates; report them without making changes.
- [ ] Add plan-only output suitable for review and automated tests.
- [ ] Test dependency chains/cycles, missing dependencies, version constraints,
  architecture/multilib selection, conflicts, obsoletes, upgrades, and
  downgrades according to Phase 0 policy.

**Exit criteria**

- Plans are deterministic for fixed inputs and identify package source and
  selection reason.
- Failure cases are actionable and make no system changes.
- Tests establish expected behavior for every in-scope dependency policy.

### Phase 6 — Downloads and trust verification

**Status:** [ ] Not started

**Tasks**

- [ ] Download selected packages into bum-managed cache using safe temporary
  files and atomic publication.
- [ ] Verify package checksums against trusted metadata before use.
- [ ] Implement metadata and package signature handling according to Phase 0
  trust policy.
- [ ] Define trusted-key enrollment, rotation, expiry/revocation, and user
  confirmation. Never trust a key solely because downloaded metadata names it.
- [ ] Handle retries, interruptions, cache reuse, corruption, disk-full errors,
  and cleanup.
- [ ] Test tampering, invalid/missing signatures, and repository unavailability.

**Exit criteria**

- Corrupt or unverifiable content cannot enter usable cache or transactions.
- Tests demonstrate integrity and signature failures fail closed.
- Trust policy and key behavior are documented.

### Phase 7 — RPM transaction integration

**Status:** [ ] Not started

**Tasks**

- [ ] Implement install, upgrade, and remove through RPM itself, using the
  solver plan and verified cached packages. Do not reimplement RPM transaction
  or database behavior.
- [ ] Acquire appropriate locks and detect concurrent package-manager activity.
- [ ] Revalidate system state as needed between planning and transaction.
- [ ] Report transaction progress and preserve failure status/diagnostics.
- [ ] Define interruption, recovery, and partial-transaction behavior according
  to guarantees provided by RPM.
- [ ] Test in disposable containers for every runnable support-matrix entry:
  install, upgrade, remove, dependency/signature failure, interruption, and
  lock contention. Use alternate isolated runners for entries unsupported by
  local Podman or GitHub-hosted runners.

**Exit criteria**

- End-to-end operations work in the declared initial support matrix.
- Container tests confirm bum does not delegate operations to DNF/microdnf.
- Failures preserve system/package database consistency within documented RPM
  guarantees.
- Recorded container matrix results identify passed, failed, and uncovered
  entries; no entry is counted as passing without test evidence.

### Phase 8 — Initial release hardening

**Status:** [ ] Not started

**Tasks**

- [ ] Audit privileged paths, input handling, quoting, temporary files,
  external calls, locks, and trust decisions.
- [ ] Add useful interactive/noninteractive diagnostics without exposing secrets.
- [ ] Document installation, prerequisites, platforms, configuration, commands,
  examples, cache management, trust setup, and limitations.
- [ ] Run the full container test suite across the supported matrix. Treat
  untested entries as explicit release gaps, not implied coverage.
- [ ] Verify README claims and update Bash/external-tool requirements.
- [ ] Publish a release checklist and known limitations.

**Exit criteria**

- Release-blocking local Podman and GitHub Actions checks pass in recorded
  clean environments; all matrix gaps are reviewed and dispositioned.
- Security and compatibility limitations are documented.
- No microdnf parity claim is made without a documented compatibility suite.

### Phase 9 — Compatibility expansion toward microdnf

**Status:** [ ] Not started; long-term

**Tasks**

- [ ] Build a command/behavior matrix against a named microdnf version and
  target distributions.
- [ ] Prioritize features by user value and architectural dependencies.
- [ ] Implement each feature with tests against documented behavior.
- [ ] Track unsupported options, output differences, and platform-specific
  behavior.

**Exit criteria**

- Parity claims name the upstream version, test suite, and supported platform
  matrix. Until then, describe compatibility as partial/aspirational.

## Initial test strategy

- **Unit tests:** repository parsing, configuration, version comparison,
  metadata interpretation, candidate selection, planning, and error formatting.
- **Fixture tests:** sanitized repo files and metadata from supported releases;
  no network or root required for ordinary unit runs.
- **Download tests:** controlled local server/fixtures for success, failure,
  corruption, interruption, and cache reuse.
- **Container integration tests:** disposable images matching the declared
  distro/release/architecture matrix. Run locally through Podman and in GitHub
  Actions. Cover metadata, downloads, RPM transactions, failure modes, and
  locks. Never mutate the developer host.
- **Static checks:** Bash syntax and selected style/lint checks aligned with
  `STYLEGUIDE.md`.
- **Security tests:** invalid configuration, malicious path/URL inputs,
  checksum/signature failures, lock contention, and interruption.

The shared runner should expose separate fast and integration suites and return
accurate status. Each test report records image identity, architecture, command,
result, and useful logs. Add exact commands to this plan as the harness evolves.

## Research references

Validate these against versions selected in Phase 0; interfaces and support
status can evolve.

- [DNF5 commands](https://dnf5.readthedocs.io/en/latest/commands/index.html)
  illustrates the breadth of the eventual command surface.
- [DNF command reference](https://dnf.readthedocs.io/en/latest/command_ref.html)
  is a separate compatibility reference; DNF and DNF5 must not be assumed
  interchangeable without testing.
- [libdnf documentation](https://libdnf.readthedocs.io/en/dnf-5-devel/index.html)
  describes a high-level package-management library. Assess stability and
  suitability for each target during Phase 1.
- [libdnf project](https://github.com/rpm-software-management/libdnf)
  provides upstream context; confirm licensing, version support, and platform
  availability before selection.

## Decision log

Add dated entries with context, options, decision, consequences, owner, and
research/review links.

| Date | Decision | Status | Reference / rationale |
|---|---|---|---|
| 2026-10-27 | Standalone manager; initial install/upgrade/remove; microdnf parity aspirational. | Confirmed | Project owner |
| 2026-10-27 | bum owns repo parsing, metadata/download/cache, and package-manager behavior. | Confirmed | Project owner |
| 2026-10-27 | RPM itself performs system package transactions; do not reimplement RPM transaction/database behavior. | Confirmed | Project owner direction |
| 2026-10-27 | Container-contained testing; local Podman and GitHub Actions CI. | Confirmed | Project owner direction |
| TBD | Initial OS release/architecture matrix. | Open | Phase 0 |
| TBD | Metadata/solver components and helper-language boundary. | Open | Phase 1 ADR |
| TBD | RPM invocation and concurrency/locking design. | Open | Phase 1 ADR |
| TBD | Repository, package signature, and key trust policy. | Open | Phase 0 / Phase 1 ADR |
| TBD | Container image matrix and CI coverage for unsupported hosted targets. | Open | Phase 2 |

## Change log

| Date | Change |
|---|---|
| 2026-10-27 | Initial progress-tracking plan created from owner direction and repository review. |
| 2026-10-27 | Clarified RPM transaction boundary; added Podman/GitHub Actions container matrix. |
