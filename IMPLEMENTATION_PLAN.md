# bum Implementation Plan

**Status:** Draft — pending project-owner review  
**Last updated:** 2026-10-27  
**Purpose:** A progress-tracking plan usable by the project owner or a delegated
coding agent. Update the status, evidence, and decision records as work proceeds.

## Project direction

bum is to become a standalone RPM package manager implemented primarily in
Bash, not a frontend that delegates package operations to DNF or microdnf.
The initial user-facing operations are `install`, `upgrade`, and `remove`.
The eventual compatibility goal is microdnf parity; parity is aspirational and
is not an initial-release acceptance criterion.

bum is responsible for parsing repository configuration, obtaining and
validating repository metadata, managing downloads and cache, selecting
packages and resolving dependencies, and planning operations. This plan
recommends keeping the RPM transaction engine as the boundary for changing the
installed system, rather than reimplementing RPM's database and transaction
semantics. That recommendation must be confirmed in the architecture phase.
bum must not invoke DNF/microdnf to perform the requested package operation.

## How to track progress

Use one of these values for each phase and task:

- `[ ]` Not started
- `[-]` In progress
- `[x]` Complete, with verification evidence recorded
- `[!]` Blocked; explain the blocker
- `[~]` Deferred or explicitly descoped; record why

A phase is complete only when its exit criteria are met and the evidence is
recorded below. A code change or agent report alone is not evidence. Record
commands run, relevant output/results, test environment, and commit/PR if
applicable. Keep decisions and scope changes in the decision log; do not
silently rewrite the project contract.

### Progress summary

| Phase | Status | Owner | Evidence / notes |
|---|---|---|---|
| 0. Requirements and support contract | [ ] | | |
| 1. Architecture and feasibility spike | [ ] | | |
| 2. CLI, configuration, and test foundation | [ ] | | |
| 3. Repository parsing and metadata/cache | [ ] | | |
| 4. Package model, solver, and transaction plan | [ ] | | |
| 5. Download and trust verification | [ ] | | |
| 6. RPM transaction integration | [ ] | | |
| 7. Initial release hardening | [ ] | | |
| 8. Compatibility expansion toward microdnf | [ ] | | |

## Scope and non-goals

### Initial scope

- Support explicitly selected releases and architectures of Fedora, RHEL,
  CentOS, and AlmaLinux. The exact matrix is an open decision in Phase 0.
- Provide `install`, `upgrade`, and `remove` operations.
- Own repository parsing, metadata acquisition, cache management, package
  downloads, verification, package selection, and dependency planning.
- Use RPM for the system package transaction, subject to the architecture
  decision and supported RPM interfaces.
- Provide a plan-only or equivalent review mode before system mutation.

### Not an initial-release promise

- Full microdnf, DNF, or yum compatibility.
- Every repository option, metadata version, compression format, architecture,
  modularity feature, or dependency policy used by every target release.
- Reimplementing the RPM database or package transaction engine.

Any narrowing or expansion of this scope should be recorded in the decision
log and reflected in the compatibility matrix and tests.

## Global engineering and safety requirements

These apply to every implementation phase:

- Follow `STYLEGUIDE.md`: `fn_` function names, four-space indentation,
  maximum 80-character lines, and the project's `__return__` convention.
  Resolve the guide's tabs-versus-spaces wording and enforce the chosen rule.
- Preserve the standalone boundary: bum may use lower-level RPM ecosystem
  components, but must not hand package operations to DNF/microdnf.
- Do not use `eval`; quote values and pass commands through Bash arrays.
- Validate user input and repository configuration. Reject unsupported or
  ambiguous constructs rather than silently misinterpreting them.
- Check and report external command failures and preserve meaningful exit
  statuses.
- Treat repository metadata and packages as untrusted input. Verify integrity
  and signatures according to an explicit policy; never silently disable
  verification to make an operation succeed.
- Use safe temporary files, atomic cache publication, locking, and cleanup on
  interruption where applicable.
- Never test system-changing operations on a developer's host. Use disposable
  virtual machines or containers and record the environment.

## Phases

### Phase 0 — Requirements and supported-platform contract

**Status:** [ ] Not started

**Tasks**

- [ ] Specify supported OS releases, architectures, and RPM versions for the
  first milestone and initial release.
- [ ] Define the meaning of standalone: which components bum owns and which
  lower-level RPM libraries/tools it may call.
- [ ] Decide whether the RPM transaction API is invoked through a library,
  bindings, or an RPM command interface; document why.
- [ ] Define initial repository configuration syntax and metadata/compression
  formats, including variable expansion and unsupported options.
- [ ] Set initial dependency policy: architecture selection, weak dependencies,
  obsoletes, conflicts, and downgrade behavior.
- [ ] Define root/privilege expectations, interactive confirmation, noninteractive
  mode, exit statuses, and behavior when another package manager is active.
- [ ] Define whether compatibility with systems already managed by DNF is
  required, and how RPM database ownership/state is treated.
- [ ] Agree on initial release criteria and what is explicitly postponed.

**Exit criteria**

- A reviewed support matrix and written behavioral contract exist.
- Each requirement above is either decided or explicitly marked deferred with
  rationale and an owner.

**Evidence to record:** link to specification/review and unresolved questions.

### Phase 1 — Architecture and feasibility spike

**Status:** [ ] Not started

**Objective:** Prove that bum can load real repository metadata and construct a
correct dependency-resolved plan using a viable architecture before building
system-changing commands.

**Tasks**

- [ ] Compare lower-level RPM ecosystem options for metadata parsing, version
  comparison, dependency solving, and RPM transactions. Assess stability,
  language bindings, availability on every target release, licensing, and
  upgrade compatibility.
- [ ] Research repository metadata formats and the formats actually emitted by
  the selected supported distributions.
- [ ] Choose which components are Bash, which may be helper/library code, and
  the interface between them. Keep bum in control of repository configuration,
  metadata lifecycle, downloads, cache, and command behavior.
- [ ] Prototype loading metadata from a representative test repository and
  producing a deterministic plan without modifying the host.
- [ ] Prototype version and capability matching against fixture packages.
- [ ] Record transaction boundary, lock strategy, trust/key model, cache
  ownership, error model, and fallback options in an Architecture Decision
  Record (ADR).

**Exit criteria**

- An ADR is reviewed and answers the architecture questions above.
- A repeatable prototype resolves at least one dependency chain and reports
  missing/conflicting dependencies without running a transaction.
- Dependencies and limitations are documented for every target platform.

**Verification evidence:** prototype invocation, fixture/repository identity,
expected versus actual plan, and test results. A demo against one repository
alone does not establish broad compatibility.

### Phase 2 — CLI, configuration, and test foundation

**Status:** [ ] Not started

**Tasks**

- [ ] Add the executable `bum` entry point and stable library sourcing based on
  the executable's location, independent of the caller's working directory.
- [ ] Implement command dispatch for `install`, `upgrade`, and `remove`, plus
  help and version output. Commands may initially return a clear
  not-implemented status.
- [ ] Define and implement configuration precedence, validation, defaults, and
  error reporting. Keep sourced library files free of unintended execution.
- [ ] Establish consistent exit-status and diagnostic conventions.
- [ ] Add automated test scaffolding, fixture conventions, and a CI syntax/test
  job.
- [ ] Choose and enforce the style guide's tabs-versus-spaces interpretation.

**Exit criteria**

- CLI help/version and invalid-command/argument behavior are tested.
- Every Bash source file passes `bash -n`.
- Tests can run without root and do not modify the host.

**Verification commands (adapt paths as the test harness is added):**

```bash
bash -n bum libbum/*.bash
./bum --help
./bum --version
```

Record exact output and add the final automated test command when the harness
exists.

### Phase 3 — Repository parsing, metadata, and cache

**Status:** [ ] Not started

**Tasks**

- [ ] Specify and implement supported `.repo` syntax: sections, comments,
  blank lines, duplicate keys, empty values, quoting, defaults, and invalid
  input behavior.
- [ ] Support multiple repositories and preserve repository identity and
  per-repository settings; do not flatten all settings into one global map.
- [ ] Implement only the variable expansion rules specified in Phase 0.
- [ ] Validate repository URLs, local paths, and supported options. Reject
  malformed or unsupported required configuration with actionable errors.
- [ ] Implement metadata retrieval and supported format/compression handling.
- [ ] Implement cache directory layout, freshness/expiration policy, refresh,
  atomic publication, locking, and cleanup of incomplete data.
- [ ] Add fixture tests based on actual repo files and metadata from each
  supported distribution/release family.

**Exit criteria**

- Parser tests cover multiple sections, comments, blank lines, malformed
  values, duplicate values, spaces, empty values, and variable behavior.
- Metadata tests cover supported formats, stale/missing cache, failed or
  interrupted retrieval, and invalid content.
- No partial or invalid metadata is exposed as a valid cache entry.

### Phase 4 — Package model, dependency solving, and transaction plan

**Status:** [ ] Not started

**Tasks**

- [ ] Define package identity, EVR/version comparison, architecture, provides,
  requires, conflicts, obsoletes, and repository priority semantics.
- [ ] Implement candidate selection and dependency closure using the Phase 1
  architecture.
- [ ] Implement `install`, `upgrade`, and `remove` plan generation.
- [ ] Detect unsatisfied dependencies, conflicts, unsupported package metadata,
  and ambiguous candidates; report them without making changes.
- [ ] Add plan-only output suitable for review and automated testing.
- [ ] Test dependency chains, cycles, unavailable dependencies, version
  constraints, architecture/multilib selection, conflicts, obsoletes, and
  upgrades/downgrades according to the Phase 0 policy.

**Exit criteria**

- Plans are deterministic for fixed inputs and identify repository/source and
  reason for each selected package.
- Failure cases produce actionable diagnostics and no system changes.
- Tests establish expected behavior for every in-scope dependency policy.

### Phase 5 — Downloads and trust verification

**Status:** [ ] Not started

**Tasks**

- [ ] Download selected packages into bum-managed cache using safe temporary
  files and atomic publication.
- [ ] Verify package checksums against trusted metadata before use.
- [ ] Implement repository metadata signature and package signature handling
  according to the Phase 0 trust policy.
- [ ] Define trusted-key enrollment, key rotation, revocation/expiry behavior,
  and user confirmation. Never trust a key merely because it appeared in
  downloaded metadata.
- [ ] Handle retries, interrupted transfers, existing cache entries, corrupt
  files, disk-full errors, and cleanup.
- [ ] Test tampered metadata/packages, invalid or missing signatures, and
  unavailable repositories.

**Exit criteria**

- Corrupt or unverifiable content cannot enter the usable cache or transaction.
- Tests demonstrate integrity and signature failures fail closed.
- Trust configuration and user-facing key behavior are documented.

### Phase 6 — RPM transaction integration

**Status:** [ ] Not started

**Tasks**

- [ ] Implement the chosen RPM transaction boundary for install, upgrade, and
  remove, using the solver plan and verified cached packages.
- [ ] Acquire appropriate locks and detect concurrent package-manager activity.
- [ ] Revalidate system state as needed between planning and transaction.
- [ ] Report transaction progress and preserve failure status/diagnostics.
- [ ] Define interruption, rollback/recovery, and partially completed
  transaction behavior based on what RPM can guarantee.
- [ ] Add integration tests in disposable supported OS environments. Include
  install, upgrade, remove, dependency failure, signature failure, interrupted
  operation, and lock contention scenarios.

**Exit criteria**

- End-to-end operations work in the declared initial support matrix.
- Tests confirm bum does not delegate package operations to DNF/microdnf.
- Failed operations leave package database/system state consistent with the
  documented RPM transaction guarantees.

### Phase 7 — Initial release hardening

**Status:** [ ] Not started

**Tasks**

- [ ] Audit all privileged paths, input handling, quoting, temporary files,
  external command calls, locks, and trust decisions.
- [ ] Add diagnostics/logging appropriate for interactive and noninteractive
  use, without exposing secrets.
- [ ] Document installation, prerequisites, supported platforms, configuration,
  commands, examples, cache management, trust setup, and limitations.
- [ ] Run the full test suite across the supported matrix or document any
  matrix gaps as release blockers/known limitations.
- [ ] Verify the README's claims against implemented behavior and update
  requirements (including Bash and external tools).
- [ ] Publish a release checklist and known limitations.

**Exit criteria**

- All release-blocking tests pass in recorded clean environments.
- Security and compatibility limitations are documented.
- No claim of microdnf parity is made unless independently demonstrated by a
  documented compatibility suite.

### Phase 8 — Compatibility expansion toward microdnf

**Status:** [ ] Not started; long-term

**Tasks**

- [ ] Build a command and behavior compatibility matrix from the selected
  microdnf reference/version and target distributions.
- [ ] Prioritize features based on user value and architectural dependencies.
- [ ] Implement each feature behind tests that compare documented bum behavior
  with the chosen compatibility target.
- [ ] Track unsupported options, output differences, and platform-specific
  behavior explicitly.

**Exit criteria**

- Parity claims are tied to a named upstream version, test suite, and supported
  platform matrix. Until then, describe compatibility as partial/aspirational.

## Initial test strategy

- **Unit tests:** repository parsing, configuration, version comparison,
  metadata interpretation, candidate selection, dependency planning, and error
  formatting.
- **Fixture tests:** sanitized repo files and metadata from supported releases;
  no network or root required for normal unit-test runs.
- **Download tests:** local HTTP test server or controlled fixtures for success,
  failure, corruption, interruption, and cache reuse.
- **Integration tests:** disposable VMs/containers matching the declared support
  matrix. Never run package mutation tests against a developer workstation.
- **Static checks:** Bash syntax checking and a selected linter/style check,
  configured to match the project guide.
- **Security tests:** invalid configuration, malicious path/URL inputs,
  checksum/signature failures, lock contention, and interrupted operations.

Every phase should add its exact verification command(s) to this document as
those commands become available. Record environment details and results in the
phase's evidence field or a linked test report.

## Research references

These references informed the initial plan; validate details against the
versions selected in Phase 0, since interfaces and support status evolve.

- [DNF5 commands](https://dnf5.readthedocs.io/en/latest/commands/index.html)
  illustrates the breadth of the eventual command surface.
- [DNF command reference](https://dnf.readthedocs.io/en/latest/command_ref.html)
  is a separate compatibility reference; DNF and DNF5 behavior should not be
  treated as interchangeable without testing.
- [libdnf documentation](https://libdnf.readthedocs.io/en/dnf-5-devel/index.html)
  describes a high-level package-management library. Its stability and
  suitability for each supported target must be evaluated during Phase 1.
- [libdnf project](https://github.com/rpm-software-management/libdnf)
  provides upstream project context; confirm licensing, version support, and
  platform availability before selecting it.

## Decision log

Add dated entries. Include context, options considered, decision, consequences,
owner, and links to relevant research or review.

| Date | Decision | Status | Reference / rationale |
|---|---|---|---|
| 2026-10-27 | Standalone package manager; initial operations are install, upgrade, remove; eventual microdnf parity is aspirational. | Confirmed by project owner | User direction |
| 2026-10-27 | bum owns repo parsing, metadata/download/cache management and package-manager behavior. | Confirmed by project owner | User direction |
| TBD | Initial OS release/architecture matrix. | Open | Phase 0 |
| TBD | Metadata/solver components and helper-language boundary. | Open | Phase 1 ADR |
| TBD | RPM transaction interface and concurrency/locking design. | Open | Phase 1 ADR |
| TBD | Repository, package signature, and key trust policy. | Open | Phase 0 / Phase 1 ADR |

## Change log

| Date | Change |
|---|---|
| 2026-10-27 | Initial progress-tracking plan created from project-owner direction and repository review. |
