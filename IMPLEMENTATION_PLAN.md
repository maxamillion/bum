# bum Implementation Plan

**Status:** In progress — staged delivery; not a complete package manager yet
**Last updated:** 2026-10-28
**Purpose:** A progress-tracking plan usable by the project owner or a delegated
coding agent. Update status, evidence, and decisions as work proceeds.

## Project direction

bum is a standalone RPM package manager implemented primarily in Bash, not a
frontend that delegates package operations to DNF or microdnf. The initial
user-facing operations are `install`, `upgrade`, and `remove`. Eventual
microdnf parity is aspirational, not an initial-release criterion.

bum owns repository parsing, metadata and package downloads, cache management,
package selection, dependency solving, and transaction planning. **RPM itself
performs system package transactions.** bum will not reimplement the RPM
database or transaction behavior and will not delegate package operations to
DNF/microdnf.

## How to track progress

Use one of these values for each phase and task:

- `[ ]` Not started
- `[-]` In progress
- `[x]` Complete, with verification evidence recorded
- `[!]` Blocked; explain the blocker
- `[~]` Deferred or descoped; record why

A phase is complete only when its exit criteria are met and evidence is
recorded. Record commands, results, test environment, and commit/PR as
applicable. Update the progress table and decision log when work changes scope.

### Progress summary

| Phase | Status | Owner | Evidence / notes |
|---|---|---|---|
| 0. Requirements and support contract | [-] | | Proposed matrix and policy; owner approval needed |
| 1. Architecture and feasibility spike | [-] | | librepo checksum-localization + RPM-MD/libsolv fixture plan pass Fedora 44/AlmaLinux 9; installed-state prototype remains |
| 2. Container test infrastructure and CI | [-] | | Rootless smoke matrix plus metadata/solver probes pass locally; hosted CI not run |
| 3. CLI, configuration, and test foundation | [-] | | Basic non-mutating plan-install CLI connected to repo parser and RPM-MD/libsolv helper; config/solver policy and installed state remain incomplete |
| 4. Repository parsing and metadata/cache | [-] | | Local repo discovery/validation; strict subset URL checks; librepo RPM-MD/cache prototype tested over loopback; freshness/locking remains |
| 5. Package model, solver, and transaction plan | [ ] | | |
| 6. Download and trust verification | [-] | | Helper package-download prototype stages/verifies and caches RPMs; signature policy remains open |
| 7. RPM transaction integration | [ ] | | |
| 8. Initial release hardening | [ ] | | |
| 9. Compatibility expansion toward microdnf | [ ] | | |

## Scope and non-goals

### Initial scope

- Validate support on selected Fedora, RHEL, CentOS, and AlmaLinux releases.
  Phase 0 proposes exact versions; owner approval is pending.
- Provide `install`, `upgrade`, and `remove` operations.
- Own repo parsing, metadata/cache lifecycle, downloads, package selection,
  verification, dependency solving, and planning.
- Use RPM itself for system package transactions through a supported interface.
- Provide a plan-only or equivalent review mode before system mutation.
- Run system-changing tests only in disposable containers: local Podman and
  GitHub Actions CI. Do not mutate the developer host.

### Not an initial-release promise

- Full microdnf, DNF, or yum compatibility.
- Every repo option, metadata format, compression, architecture, modularity
  feature, or dependency policy on every target release.
- Reimplementing the RPM database or transaction engine.

## Global engineering and safety requirements

- Package-state/system-changing tests run only in disposable containers. Never
  mount the host RPM database/package directories into test containers.
- Keep local and CI commands aligned; record image digest, command, results,
  and logs. Do not claim CI coverage before a workflow run.
- Follow `STYLEGUIDE.md`: `fn_` function names, four-space indentation,
  maximum 80-character lines, and `__return__`; clarify tabs-versus-spaces.
- No `eval`; quote inputs and use arrays for constructed commands.
- Validate repo configuration and user input; reject unsupported syntax clearly.
- Check subprocess statuses and preserve meaningful failure codes.
- Treat metadata/packages as untrusted; fail closed on checksum/signature
  errors. Use safe temporary files, atomic cache publication, locks, cleanup.

## Proposed support and behavior contract (owner review pending)

Working proposal: validate Fedora 44, RHEL UBI 9, CentOS Stream 9/10, and
AlmaLinux 9/10 on x86_64. This is a test matrix proposal, not a final promise
to support every release. Older enterprise releases and other architectures
remain unselected until API availability and CI coverage are established.

Initial repository scope should use RPM-MD `repomd.xml` and primary package
metadata. Compression formats, signature policy, key enrollment, and whether
additional metadata is required must be decided by Phase 0/1. bum parses repo
sections and key/value pairs; proposed first options are `baseurl`, `enabled`,
`gpgcheck`, and `gpgkey`. Mirrorlist/metalink and distro variable expansion are
out of initial scope until specified. Initial solving should reject downgrades,
select architecture-compatible packages, and report unsatisfied dependencies
or conflicts. Root is required for mutation; plan-only mode is available and
interactive mutations require confirmation. No setuid execution. RPM controls
the final transaction.

**Open owner decisions:** supported releases/architectures; exact metadata and
compression formats; trust/key policy; downgrade/weak-dependency policy;
noninteractive confirmation behavior; whether repo files support more than the
listed keys; and helper-language/runtime packaging.

## Phases

### Phase 0 — Requirements and supported-platform contract

**Status:** [-] In progress

- [ ] Confirm or revise the proposed OS/release/architecture matrix.
- [ ] Define lower-level components bum may use while owning package workflow.
- [ ] Define repo syntax/options, metadata/compression formats, and expansion.
- [ ] Set architecture, weak-dependency, obsoletes, conflict, and downgrade
  policy.
- [ ] Define root/privilege, confirmation, noninteractive, and exit behavior.
- [ ] Define behavior with existing DNF-managed state and concurrent managers.
- [ ] Agree on initial-release criteria and deferred features.

**Exit criteria:** reviewed matrix and written contract; every item decided or
deferred with rationale and owner.

### Phase 1 — Architecture and feasibility spike

**Status:** [-] In progress

**Tasks**

- [ ] Assess lower-level RPM ecosystem options and API/package availability on
  every target. Evaluate librepo (RPM-MD/download), libsolv (solver), and RPM
  transaction invocation as candidates.
- [ ] Prototype metadata loading, cache/checksum validation, and deterministic
  install/upgrade/remove plans without a system transaction.
- [ ] Decide Bash/helper boundary, protocol, runtime dependencies, and behavior
  where bindings are unavailable. DNF/microdnf cannot execute operations.
- [ ] Record transaction/locking, trust/key, cache, error, and recovery design
  in reviewed ADRs.

**Evidence to date:** `docs/adr/0001-package-manager-architecture.md` and
`docs/adr/0002-language-boundary.md` remain proposals. `tests/container/solver.sh`
installs librepo/libsolv bindings in disposable containers on Fedora 44 and
AlmaLinux 9. `tests/fixtures/rpmmd` contains a locally generated two-RPM
RPM-MD repository. With checksum checking enabled in librepo, the helper
localizes primary metadata; the prototype parses RPM-MD primary package records
and libsolv plans `demo-app` with `demo-lib`. Fixture solver tests also reject
unresolved dependencies and conflicts. This validates one fixture workflow,
not remote metadata transfer, production-grade cache policy, signatures,
installed-state planning, RPM transactions, or equivalence across the matrix.
Observed versions: librepo 1.21.2 / libsolv 0.7.40 (Fedora 44), librepo 1.19.0 /
libsolv 0.7.24 (AlmaLinux 9). Upstream:
[librepo](https://github.com/rpm-software-management/librepo),
[libsolv](https://github.com/openSUSE/libsolv),
[RPM transaction API](https://rpm.org/docs/latest/api/group__rpmts.html).

**Exit criteria:** ADR accepted; repeatable metadata/solver prototype passes
fixture tests on every selected target, with exact commands and results logged.

### Phase 2 — Container test infrastructure and CI

**Status:** [-] In progress

- [x] Add `tests/container/run.sh` using Podman and disposable containers.
- [x] Add GitHub Actions matrix with pinned image digests.
- [ ] Separate fast/unit and integration suites as their scale grows.
- [ ] Run hosted Actions and configure branch protection/required checks.
- [ ] Add more architectures only with a viable local/CI runner strategy.

The runner copies the repository to a temporary directory before SELinux
relabeling, uses a read-only mount and disabled network, and runs syntax/unit/CLI
checks. It does not mount host package state.

**Container matrix / local evidence** (Podman 5.8.9, Fedora 44 host, x86_64):

| Target image (digest reference recorded in workflow) | Detected release | Local Podman | GitHub Actions |
|---|---|---|---|
| Fedora 44 | 44; RPM 6.0.2 | Syntax/unit/CLI pass | Pending |
| RHEL UBI 9 | 9.8; RPM 4.16.1.3 | Syntax/unit/CLI pass | Pending |
| CentOS Stream 9 | 9; RPM 4.16.1.3 | Syntax/unit/CLI pass | Pending |
| CentOS Stream 10 | 10; RPM 4.19.1.1 | Syntax/unit/CLI pass | Pending |
| AlmaLinux 9 | 9.8; RPM 4.16.1.3 | Syntax/unit/CLI pass | Pending |
| AlmaLinux 10 | 10.2; RPM 4.19.1.1 | Syntax/unit/CLI pass | Pending |

Workflow: `.github/workflows/ci.yml`. Local results do not substitute for a
GitHub Actions run. Image digests and exact references are recorded in that
workflow and should be deliberately refreshed.

### Phase 3 — CLI, configuration, and test foundation

**Status:** [-] In progress

- [x] Add a non-mutating `plan install PACKAGE --repo REPO_ID` CLI path that
  validates repository selection and invokes the RPM-MD planner. This is a
  prototype vertical slice; it does not read installed RPM state or mutate the
  RPM database/package state.
- [x] Reject duplicate repository keys/sections, unsupported URL schemes,
  malformed supported URL authorities, and unsafe cache directory ownership or
  permissions before planning.

- [x] Add executable `bum`, help/version, basic command dispatch and status
  conventions for unimplemented operations.
- [ ] Define/validate configuration precedence, defaults, and error behavior.
- [x] Add initial parser and CLI fixture/smoke tests.
- [ ] Expand option parsing, diagnostics, and automated test harness.
- [ ] Enforce a resolved style convention and lint policy.

**Evidence:** `./bum --help`, `./bum --version`; CLI/parser tests execute from
`tests/container/run.sh`. Package operations still return not-implemented;
configuration resolution and package execution are incomplete.

### Phase 4 — Repository parsing, metadata, and cache

**Status:** [-] In progress

- [x] Implement deterministic local `*.repo` discovery and validate the first
  supported options (`name`, `baseurl`, `enabled`, `gpgcheck`, `gpgkey`), with
  boolean defaults and rejection of unknown options.
- [-] Specify parser handling for duplicate keys, comments, quoting, malformed
  values, multiple repo files, and all supported fields. Added a regression for
  retaining a valid final key/value line without a trailing newline; inline
  comment and quoting semantics remain open.
- [ ] Complete robust `.repo` parsing and fixtures from target distributions.
- [x] Prototype selected RPM-MD primary retrieval/parsing using librepo with
  checksum verification and reusable cache; a loopback HTTP fixture test checks
  remote retrieval and repeated use.
- [-] Productionize metadata cache freshness/expiration, locking, atomic
  publication, and interrupted cleanup. Package download/cache publication now
  has a per-cache process lock; metadata freshness and locking remain open.
- [ ] Test invalid, stale, missing, and corrupt metadata and transfer failures.

**Exit criteria:** parser and metadata tests pass; partial/invalid metadata is
never exposed as valid cache state.

### Phase 5 — Package model, dependency solving, and transaction plan

**Status:** [-] In progress

- [x] Extend the JSON/libsolv fixture adapter to model installed state and
  generate install, upgrade, and remove plans; test no-downgrade upgrade behavior
  and reject removal that would break an installed dependent. This remains a
  fixture planner, not production RPM database integration or complete policy
  coverage.
- [x] Add a read-only RPM CLI inventory adapter with normalized epoch-version-
  release/architecture records, deterministic ordering, and malformed/duplicate/
  RPM-query failure tests.
- [-] Add `plan remove PACKAGE [--arch ARCH]`: connect read-only RPM inventory
  to libsolv, select multilib identity explicitly, and reject removal that breaks
  installed dependents. The wrapper validates inventory and solver response
  schemas; RPM query/solver failures fail closed. Container tests compare RPM
  inventory before/after planning. This remains plan-only; install/upgrade
  planning and production solver policy are not complete.

- [ ] Define EVR, architecture, provides/requires, conflicts/obsoletes, and
  repository priority semantics.
- [ ] Implement candidate selection and dependency closure with selected solver.
- [ ] Implement install/upgrade/remove plan generation and plan-only output.
- [ ] Test dependency chains/cycles, unavailable dependencies, constraints,
  architecture/multilib, conflicts, obsoletes, and upgrade policy.

**Exit criteria:** deterministic plans identify selected source/reason; failure
cases are actionable and make no system changes.

### Phase 6 — Downloads and trust verification

**Status:** [-] In progress

- [x] Roll back failed RPM cache publication and test restoration of a prior
  cache entry with injected failure; confirm temporary files are cleaned.
- [x] Add an explicit helper `--download DIR` prototype: package hrefs from
  primary metadata are downloaded via librepo to staging files, size/checksum
  verified, and published in a private cache. Loopback tests verify downloads
  and reject payload tampering. The public plan-only CLI exposes this via
  `--download-dir DIR`; signature verification remains absent.
- [ ] Verify package checksums against metadata and signatures per explicit
  repository/key trust policy.
- [ ] Define trusted-key enrollment, rotation, expiry/revocation, confirmation.
- [ ] Test interrupted/corrupt downloads, cache reuse, tampering, and bad/missing
  signatures; all trust failures fail closed.

### Phase 7 — RPM transaction integration

**Status:** [ ] Not started

- [ ] Use RPM itself for install/upgrade/remove from solver plans and verified
  packages; do not implement RPM database/transaction behavior.
- [ ] Coordinate locks and concurrent managers; revalidate state before commit.
- [ ] Preserve RPM status, diagnostics, progress, and documented recovery limits.
- [ ] Test transactions only in disposable containers for every selected target.

**Exit criteria:** end-to-end behavior passes the support matrix; bum does not
hand operations to DNF/microdnf; failures respect RPM guarantees.

### Phase 8 — Initial release hardening

**Status:** [ ] Not started

- [ ] Audit privileged paths, input handling, temporary files, locks, and trust.
- [ ] Document supported platforms, dependencies, operations, config, trust,
  cache, and limitations; verify README claims.
- [ ] Run full Podman/Actions matrix, document test gaps, and publish known
  limitations and release checklist.

### Phase 9 — Compatibility expansion toward microdnf

**Status:** [ ] Long-term

- [ ] Select named microdnf reference version and create command/behavior matrix.
- [ ] Prioritize and implement compatibility with tests per feature/platform.
- [ ] Track output, option, and platform differences.

**Exit criteria:** parity claims identify upstream version, suite, and supported
platform matrix. Until then, compatibility remains aspirational/partial.

## Test strategy

- Unit/fixture tests for parser, config, versioning, metadata, solver, plans.
- Controlled local transfer tests for success, corruption, failure, interruption,
  and cache reuse.
- Disposable container integration tests for downloads and RPM operations.
- Syntax/style checks and security cases for paths, URLs, trust, locks, and
  interruption.
- Local Podman and GitHub Actions use the same test entry point where possible.

## Decision log

| Date | Decision | Status | Notes |
|---|---|---|---|
| 2026-10-27 | Standalone; initial install/upgrade/remove; microdnf parity aspirational. | Confirmed | Project owner |
| 2026-10-27 | bum owns repo parsing, metadata/download/cache, and package workflow. | Confirmed | Project owner |
| 2026-10-27 | RPM itself performs transactions; do not reimplement RPM database/transaction behavior. | Confirmed | Project owner |
| 2026-10-27 | Container-contained testing; local Podman and GitHub Actions. | Confirmed | Project owner |
| 2026-10-28 | Fedora 44, UBI 9, CentOS Stream 9/10, AlmaLinux 9/10 x86_64 initial test candidates. | Proposed | Owner approval pending |
| 2026-10-28 | Evaluate librepo/libsolv/RPM with Bash orchestration and possible Python helper. | Proposed | ADRs 0001/0002; feasibility incomplete |
| TBD | Repo format, trust/key policy, dependency defaults, privilege and locking policy. | Open | Phase 0 |

## Change log

| Date | Change |
|---|---|
| 2026-10-27 | Initial progress-tracking plan created; RPM boundary and container matrix documented. |
| 2026-10-28 | Began execution: architecture/language ADRs, Podman/Actions matrix, CLI and parser test foundation. |
