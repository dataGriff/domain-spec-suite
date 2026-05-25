# SUITE-DESIGN.md

> Design document for the **domain-spec-suite** — a suite of Claude skills that
> takes a user from "I have an idea for a domain" to "I have a complete,
> internally-consistent, implementation-agnostic spec set that can drive
> multiple implementations forever."
>
> This document captures the *why*: phase model, gate philosophy, prompting
> style, update mode, hook tiers, gate versioning policy. It is reference
> material.
>
> For the operational checklist of *what to build next*, see `BUILD-PLAN.md`.

---

## Table of Contents

1. [Purpose and Scope](#1-purpose-and-scope)
2. [The Phase Model](#2-the-phase-model)
3. [The Orchestrator](#3-the-orchestrator)
4. [The Progress Schema](#4-the-progress-schema)
5. [The Phase Skill Pattern](#5-the-phase-skill-pattern)
6. [Update Mode](#6-update-mode)
7. [The Prompting Style](#7-the-prompting-style)
8. [Per-Phase Specifications](#8-per-phase-specifications)
9. [Hooks and CI Integration](#9-hooks-and-ci-integration)
10. [Versioning Policy](#10-versioning-policy)
11. [Open Questions and Known Limitations](#11-open-questions-and-known-limitations)

---

## 1. Purpose and Scope

### What this suite is

A suite of Claude skills that drives a user through producing a complete,
internally-consistent spec set for a business domain. The suite owns the
design process. Implementations consume its output.

### What this suite is not

- Not an implementation generator
- Not a framework or language chooser
- Not opinionated about runtime, database, or hosting
- Not a CRUD scaffold

The output is design documents and contracts. What is built from those
documents is downstream and out of scope.

### The artifact produced

A populated repository containing:

- `prd.md` — Product requirements
- `domain-model.md` — Entities, relationships, lifecycles
- `glossary.md` — Ubiquitous language
- `auth-matrix.md` — Roles and permissions
- `error-catalogue.md` — Canonical error codes
- `sequence-diagrams.md` — Interaction flows
- `nfr.md` — Non-functional requirements
- `acceptance-scenarios.md` — Given/When/Then scenarios at contract level
- `contracts/openapi.yaml` — REST contract
- `contracts/asyncapi.yaml` — Event contract
- `contracts/datacontract.yaml` — Data contract
- `_ambiguities.md` — Resolved and deferred open questions
- `_progress.yaml` — Phase state (suite-managed, not user-edited)
- `_phase-N-passed.yaml` × 7 — Phase sign-off sidecars
- Repository shell: `Taskfile.yml`, linting configs, `mkdocs.yml`, generator
  scripts, hooks, CI workflows, instruction files

When the audit phase passes, this spec set is declared complete and ready to
drive implementations.

### The target repo

The suite operates on **empty** repositories. There is no pre-existing template
the user must apply. Phase 0 (Bootstrap) of the suite produces the entire
repository shell. This is a deliberate design choice: the suite is the single
source of truth for what a domain repo should look like, eliminating drift
between a separate template and the skills that operate on it.

---

## 2. The Phase Model

The suite walks every user through eight phases in fixed order. Phases cannot
be skipped. The orchestrator (Section 3) is responsible for prompting and
sequencing.

| # | Phase | Gate Type | Produces |
|---|-------|-----------|----------|
| 0 | Bootstrap | Hard (trivial) | Repository shell |
| 1 | Discovery | Hard | `prd.md` |
| 2 | Modeling | Soft+engagement | `domain-model.md`, `glossary.md` |
| 3 | Access Control | Soft+engagement | `auth-matrix.md`, `error-catalogue.md` |
| 4 | Flows | Soft+engagement | `sequence-diagrams.md` |
| 5 | NFRs | Soft+engagement | `nfr.md`, `acceptance-scenarios.md` |
| 6 | Contracts | Hard | `contracts/openapi.yaml`, `contracts/asyncapi.yaml`, `contracts/datacontract.yaml` |
| 7 | Audit | Hard | Audit report; clears spec set as complete |

### Gate types

**Hard gate.** Phase cannot complete unless all gate criteria pass. No
deferrals accepted. Used at the bookends (Discovery, Contracts, Audit) and
trivially at Bootstrap (files exist or they don't).

**Soft gate with mandatory engagement.** Phase requires the user to respond to
every gate warning, but the user may resolve, defer (with required-by phase,
typically audit), or mark non-applicable (with reason). Phase advances once
every warning has an explicit response. Silent dismissal is not possible.

**Hard audit gate.** Phase 7 enforces resolution of every deferred item from
phases 2-5 and runs all cross-file consistency checks. This is what gives soft
gates teeth.

Phases must be invoked in order on a fresh domain. The orchestrator refuses
out-of-order invocation. Update mode (Section 6) is the only path to
re-running phases non-sequentially, and it has its own rules.

### Phase 0: Bootstrap specifics

Bootstrap is mechanical, not interactive. The only user interaction is a
confirmation at the start: "I'm about to set up this directory as a domain
spec repo. This will create [N files]. Proceed?"

Bootstrap produces:

- Repository structure (`docs/`, `docs/specifications/`,
  `docs/specifications/contracts/`, `scripts/`, `.githooks/`)
- `Taskfile.yml` with linting and docs tasks
- Linting configuration (`.spectral-openapi.yaml`, `.spectral-asyncapi.yaml`)
- `.mise.toml` for tool version pinning
- `README.md` (skeletal, gets filled in during Phase 1)
- `mkdocs.yml`
- `docs/index.md` (skeletal)
- Generator script (`scripts/generate_domain_overview.py`)
- `.gitignore`
- `.githooks/pre-commit` and `.githooks/pre-push` (Section 9)
- `.github/workflows/audit.yml` (Section 9)
- `AGENTS.md` and `.github/instructions/*.md` (instruction files for
  agents working on the domain repo after the suite has produced it)
- Empty `_progress.yaml` with Phase 0 marked complete and Phase 1 ready
- `_bootstrap.yaml` recording the suite and gate versions that produced
  the shell

After Bootstrap, the orchestrator immediately prompts to start Phase 1.

---

## 3. The Orchestrator

The orchestrator is a skill in its own right (`domain-orchestrator`). It is
the entry point for all user interaction with the suite.

### Responsibilities

**On invocation, read state.** Load `_progress.yaml` if present. Identify
current phase status: not-started, in-progress, passed (with version and
timestamp), or stale (file modified after sign-off — see Section 6).

**Decide what to do.**

- No `_progress.yaml`: this is a new domain. Confirm with the user, explain
  the process (Section 7), initialize progress, prompt for Phase 0 Bootstrap.
- In-progress phase exists: resume it.
- All phases through N passed, N+1 not started: prompt to start N+1.
- All phases passed including audit: spec set is complete. Offer update mode
  (Section 6).
- Any phase stale: enter update mode for the affected phase chain.

**Prompt the user to start each phase.** Use the prompting style in Section 7.
The prompt includes: phase name, what it produces, what later phases depend on
it, roughly how long. End with explicit confirmation request — never
auto-advance into a phase.

**Hand off to the phase skill.** Each phase is a separate skill. The
orchestrator invokes it after the user confirms. The phase skill runs its
loop (Section 5), updates files, and on completion writes its sign-off
sidecar.

**On phase completion, prompt for the next phase.** Same pattern. Don't chain
phases without user acknowledgment — each phase deserves a deliberate start.

**On audit pass, declare complete.** Explicit closure: "Spec set complete.
Audited against gate-version X.Y at timestamp. Ready to drive implementations."

### What the orchestrator does not do

- Does not run gate checks itself (phase skills own their checks)
- Does not edit spec files directly (phase skills own their files)
- Does not auto-advance between phases (always confirms with user)

The orchestrator only reads sign-offs and progress state and routes the user.

---

## 4. The Progress Schema

`_progress.yaml` is the authoritative state for the suite. The orchestrator
reads it on every invocation. Phase skills update it when they complete.

```yaml
suite_version: "1.0.0"
gate_version: "1.0.0"
domain_name: "items"           # populated after Phase 1
started_at: "2026-05-25T14:00:00Z"
last_updated: "2026-05-25T15:30:00Z"

phases:
  bootstrap:
    status: passed             # not-started | in-progress | passed | stale
    signed_off_at: "2026-05-25T14:05:00Z"
    gate_version: "1.0.0"
  discovery:
    status: passed
    signed_off_at: "2026-05-25T14:45:00Z"
    gate_version: "1.0.0"
    deferred_items: 0
  modeling:
    status: in-progress
    started_at: "2026-05-25T15:00:00Z"
    deferred_items: 2
  access-control:
    status: not-started
  flows:
    status: not-started
  nfrs:
    status: not-started
  contracts:
    status: not-started
  audit:
    status: not-started

session_log:
  - timestamp: "2026-05-25T14:00:00Z"
    event: suite-initialized
  - timestamp: "2026-05-25T14:05:00Z"
    event: phase-passed
    phase: bootstrap
  - timestamp: "2026-05-25T14:45:00Z"
    event: phase-passed
    phase: discovery
  - timestamp: "2026-05-25T15:00:00Z"
    event: phase-started
    phase: modeling
```

### Per-phase sign-off sidecars

`_phase-N-passed.yaml` records the per-phase audit trail:

```yaml
phase: discovery
signed_off_at: "2026-05-25T14:45:00Z"
gate_version: "1.0.0"
checks_passed:
  - PRD-PROBLEM-USER-PAIN
  - PRD-PERSONA-EXISTS
  - PRD-PERSONA-GOAL
  - PRD-PERSONA-FRUSTRATION
  - PRD-NON-GOAL
  - PRD-STORY-ACCEPTANCE
  - PRD-STORY-PERSONA-LINK
  - PRD-METRICS-MEASURABLE
files_signed:
  - path: docs/specifications/prd.md
    mtime: "2026-05-25T14:44:30Z"
    sha256: "abc123..."
deferred_items: []
```

The sha256 on file signoff matters: if the file is hand-edited later, the
hash mismatch is how staleness is detected.

### The ambiguities file

`_ambiguities.md` tracks deferrals in markdown so it's human-readable:

```markdown
# Open Ambiguities

## Deferred to: audit

### ITEM-001: NFR latency target undefined
- Recorded in phase: nfrs
- Reason: Unknown until performance testing
- Resolution required before: audit phase

## Resolved

### ITEM-000: Should Contributor be its own entity?
- Resolved in phase: modeling
- Decision: No — contributor is a role on User, not a separate entity
- Resolved at: 2026-05-25T15:15:00Z
```

---

## 5. The Phase Skill Pattern

Every phase skill follows the same structure. This is what makes the suite
predictable and the orchestrator's job possible.

### Each phase skill has

1. A `SKILL.md` with description, prerequisites, and instructions
2. A `gate.yaml` defining its check list
3. A `templates/` directory with skeletal output files
4. A `checks/` directory with check implementations (scripts or check
   definitions)
5. A `questions.md` or equivalent — the question bank the skill uses to elicit
   information

### Prerequisites declaration

At the top of each phase's `gate.yaml`:

```yaml
phase: modeling
prerequisites:
  - phase: discovery
    must_be: passed
inputs:
  - docs/specifications/prd.md
outputs:
  - docs/specifications/domain-model.md
  - docs/specifications/glossary.md
```

The skill refuses to run if prerequisites aren't met, even if invoked
directly outside the orchestrator. Defense in depth.

### Phase skill loop

```
1. Verify prerequisites — if not met, refuse and explain.
2. Load existing output files (if resuming) or copy from templates.
3. Load relevant upstream files (PRD for modeling, etc.).
4. Run gate checks → collect failures.
5. If no failures and no warnings → write sign-off, update _progress.yaml,
   return to orchestrator.
6. If failures (hard gate) or warnings (soft gate):
   a. Pick highest-priority finding.
   b. Ask the user the targeted question.
   c. Receive answer.
   d. Show diff before writing.
   e. Apply edit.
   f. Re-run affected checks.
   g. Go to step 5.
```

### Hard vs soft difference is at step 5-6

- **Hard gate**: failures must become passes. Cannot advance otherwise.
- **Soft gate**: warnings can become passes, deferrals, or
  non-applicable-with-reason. Cannot advance until every warning has an
  explicit response.

### Check categories

Used in every phase, in descending order of trustworthiness:

- **Structural** — parse the file, check shape. Most reliable. No LLM.
- **Cross-reference** — verify consistency with other spec files. Mechanical.
  No LLM.
- **Rubric** — LLM-judged with a narrow yes/no rubric. Use sparingly, only
  when nothing else works.

Every check has: id, description, category, verifier (the actual check
logic), severity (error/warning), and an `on_fail` message that's an
interview question, not a lint diagnostic.

### Standalone phase invocation is refused

If a user invokes a phase skill directly without going through the
orchestrator (e.g., by name), the phase skill detects no orchestrator state
or out-of-sequence invocation, refuses, and points the user back to the
orchestrator. This prevents the "I just want to update one thing" path from
bypassing dependency checks.

---

## 6. Update Mode

After a spec set has passed audit, users will edit it. The suite supports
this through targeted update mode.

### Detection

On every orchestrator invocation, compare each spec file's mtime and sha256
against the corresponding `_phase-N-passed.yaml` record. Any mismatch marks
that phase as `stale`.

### On detection of staleness

The orchestrator identifies all phases that depend on the changed file (the
dependency chain is fixed and known — see below) and reports:

> "I've detected changes to `prd.md` since Phase 1 was last signed off.
> This affects: modeling, access-control, flows, nfrs, contracts, audit.
>
> Options:
> 1. **Targeted update (recommended)**: Re-run only the phases affected by
>    the changes. I'll load each affected phase, identify which gate checks
>    are now failing, and walk through only those.
> 2. **Full re-run**: Walk through all affected phases from scratch as if
>    they hadn't been done before.
> 3. **Audit-only**: Skip directly to audit and surface inconsistencies.
>    You'll need to address findings manually.
>
> Which would you like?"

### Targeted update mechanics

For each affected phase in dependency order:

1. Load the existing output file as the starting point (not the blank
   template).
2. Run gate checks against the current state.
3. Surface only the checks that are now failing because of upstream changes.
4. Walk the user through resolving them (same loop as normal phase
   execution).
5. Re-sign the phase when checks pass.

### Phase dependency chain (fixed)

- bootstrap → everything (rarely changes after initial run)
- discovery → modeling, access-control, flows, nfrs, contracts, audit
- modeling → access-control, flows, nfrs, contracts, audit
- access-control → flows, contracts, audit
- flows → contracts, audit
- nfrs → contracts, audit
- contracts → audit

If discovery's `prd.md` changes, every downstream phase becomes stale. If
only `nfr.md` is hand-edited, only contracts and audit go stale.

### Hard rule

A phase cannot be signed-off while any upstream phase is stale. The
orchestrator enforces this on phase entry: "Cannot run contracts phase —
modeling phase is stale due to changes in prd.md. Re-run modeling first."

This is what prevents partial-update inconsistency states.

### Audit-only mode caveat

Option 3 (audit-only) is permitted but discouraged. The audit will catch
cross-file inconsistencies but won't walk the user through fixing them.
Useful as an escape hatch when the user knows exactly what they're doing.
Always offered last in the option list.

---

## 7. The Prompting Style

This section is referenced by every phase skill's `SKILL.md`. Single source
of truth for tone.

### The voice

A senior business analyst conducting an interview. Patient, focused, takes
notes, will not let a vague answer through.

### Hard rules

1. **One question per turn. Always.** No batched questions, no "and also,
   while we're here." Each turn is a focused exchange.
2. **Lead with what's needed and why.** "I need to define the first persona —
   what's their primary goal in using this system?"
3. **Reflect before writing.** Show the user how you understood their answer
   before committing it to a file. Catch misinterpretations early.
4. **Push back on vagueness.** "Fast" is not an answer; "p95 under 200ms" is.
   Ask for the number.
5. **Business language by default.** Technical language only when precision
   requires it (contracts phase, mostly).
6. **No filler.** No "great question," no "excellent," no "let's dive in."
7. **Show progress at phase boundaries.** "Phase 2 of 7 complete. 4 entities
   defined, 2 deferrals logged. Next: Access Control."
8. **Acknowledge mistakes plainly.** "I had that wrong — let me fix it." Not
   apologies.
9. **Don't editorialize.** If the user defers an item or skips an optional
   field, record it and move on. Don't argue.
10. **Failures are interview questions.** Never "PRD-PERSONA-FRUSTRATION
    failed for persona 2." Always "Persona 'Viewer' has no frustration
    listed. What specifically frustrates a Viewer about how they work today?"

### Expectation-setting on first run

> "This process walks through 8 phases (one quick setup phase, then 7 design
> phases) to produce a complete spec set for your domain. For a domain of
> moderate complexity, expect 2-4 sessions. You can pause at any time and
> resume later. The output is meant to persist — time invested here saves
> implementation time across every codebase that uses these specs.
>
> Ready to start Phase 0: Bootstrap?"

This is the only place where the suite "sells" itself. Everywhere else, it
just works.

---

## 8. Per-Phase Specifications

This section captures the gate criteria summary per phase. The full question
banks for each phase live in their respective skill directories
(`skills/<phase>/questions.md`) and are produced during build.

### Phase 0: Bootstrap — Hard gate (trivial)

Structural checks:
- All expected files exist at expected paths
- All files have valid syntax (YAML files parse, markdown is well-formed)
- `_progress.yaml` initialized with Phase 0 status passed
- `_bootstrap.yaml` records suite and gate version

### Phase 1: Discovery — Hard gate

Structural checks:
- PRD has problem statement (non-empty)
- At least one persona
- At least one non-goal
- At least one user story
- At least one success metric
- Every persona has goal and frustration (both non-empty, both ≥ 10 chars)
- Every user story has at least one acceptance criterion
- Every story names an existing persona (cross-reference within the file)
- Every metric contains a number or measurable verb (regex check)

Rubric checks (LLM-judged, narrow):
- Problem statement describes user pain rather than solution
- Success metrics are measurable rather than aspirational

### Phase 2: Modeling — Soft+engagement

Structural checks:
- Every entity has id, createdAt, updatedAt
- Every entity has at least one business rule
- Every entity with a status field has a defined lifecycle
- Every relationship is bidirectional (if A has many B, B belongs to A is
  recorded)
- Every entity name is unique
- Glossary contains every entity name and every attribute name

Cross-reference checks:
- Every entity mentioned in PRD user stories appears in the domain model
- Every entity name appears in glossary

### Phase 3: Access Control — Soft+engagement

Structural checks:
- Every role has a description
- Every operation in auth matrix has every role's permission specified
- Every error in the catalogue has code, HTTP status, meaning, and trigger
  condition

Cross-reference checks:
- Every role traces to a PRD persona (or is justified as a system role)
- Every ownership rule references a real field on the referenced entity
- Auth matrix operations align with eventual OpenAPI operations (deferred
  to contracts phase if OpenAPI not yet written)

### Phase 4: Flows — Soft+engagement

Structural checks:
- Every diagram has a title and participants
- Every participant is either a defined role or named external system

Cross-reference checks:
- Every PRD user story has at least one sequence diagram
- Every state transition in domain model lifecycles appears in a flow

### Phase 5: NFRs — Soft+engagement

Structural checks:
- Every NFR has a measurable threshold (number, percentage, or time)
- Every acceptance scenario follows Given/When/Then structure

Rubric checks:
- NFR thresholds are realistic and concrete rather than aspirational

### Phase 6: Contracts — Hard gate

Tool checks (must pass):
- `task lint:openapi` passes
- `task lint:asyncapi` passes
- `task lint:datacontract` passes

Cross-reference checks:
- Every domain-model entity has an OpenAPI schema
- Every entity field name matches between domain-model and OpenAPI
- Every write OpenAPI operation has an AsyncAPI channel
- Every AsyncAPI event has a datacontract entry
- Every event payload field matches datacontract schema
- Every auth matrix operation has a corresponding OpenAPI operation
- Every error code in OpenAPI responses appears in error-catalogue.md

### Phase 7: Audit — Hard gate

Runs all phases 1-6 cross-reference checks simultaneously. Additionally:
- Verifies no unreplaced template placeholders
- Verifies `_ambiguities.md` has no items marked `required-by: audit` that
  remain unresolved
- Verifies all `_phase-N-passed.yaml` sidecars are present and not stale
- Runs `task domain:check` and confirms it passes
- Verifies generator script produces clean `domain-overview.html`

On pass: writes `_audit-passed.yaml` with the full check manifest, timestamp,
and gate-version. Declares spec set complete.

---

## 9. Hooks and CI Integration

The suite installs a tiered audit approach during Phase 0 Bootstrap. This
provides defense in depth without imposing latency that would drive
developers to bypass hooks.

### Tier 1 — Pre-commit hook (fast, always runs)

Target: <2 seconds.

What it does:
- If any file in `docs/specifications/` changed: run structural and
  cross-reference checks on just the affected files
- Detect staleness (file modified after sign-off): warn loudly
- Detect unreplaced template placeholders in changed files
- Reject the commit if hard checks fail

What it does **not** do:
- Run Spectral or datacontract-cli
- Run the full audit
- Run the generator script

Installed at `.githooks/pre-commit`. Activated by `task hooks:install`.

### Tier 2 — Pre-push hook (medium, runs less often)

Target: <15 seconds.

What it does:
- Run Spectral on contract YAMLs
- Run datacontract-cli
- Run cross-file consistency checks across all spec files
- Reject the push if any hard gate check fails

Installed at `.githooks/pre-push`.

### Tier 3 — CI on PR (full audit)

What it does:
- Runs the entire conformance audit (Phase 7)
- Regenerates the domain overview and confirms it produces clean output
- Blocks merge if audit fails

Installed at `.github/workflows/audit.yml`.

### Tier 4 — Manual `task audit` at any time

A developer working on specs can always run `task audit` themselves to get
the full check. This is for confidence-building during work, not enforcement.

### Staleness escape hatch

When the pre-commit hook detects a commit introducing staleness (changes to
a signed-off file without re-running the affected phase), it warns:

> "You're committing changes to `docs/specifications/prd.md`, but Phase 1
> (Discovery) was signed off and downstream phases depend on it. To prevent
> inconsistency, re-run the orchestrator before committing.
>
> If you're certain this change doesn't affect downstream phases, override
> with `git commit --no-verify` — this will be flagged in the audit on push."

The `--no-verify` escape is permitted (sometimes you genuinely just need to
fix a typo) but the escape gets recorded in commit history and the next
full audit will catch any resulting inconsistency.

---

## 10. Versioning Policy

Gate criteria will evolve as the suite is used. The versioning policy is
**frozen with opt-in re-audit** (Option B from design discussion).

### Two independent version numbers

- **Suite version** (e.g., 1.0.0 → 1.0.1): bug fixes, prompting improvements,
  template tweaks. Does not affect existing spec sets.
- **Gate version** (e.g., 1.0 → 1.1): new check, removed check, or changed
  check semantics. Affects whether existing spec sets are considered
  "current."

You version these independently. Most suite releases are suite-version-only
bumps; gate-version bumps are rarer and more deliberate.

### What happens to existing spec sets

- Every `_phase-N-passed.yaml` records the `gate_version` it was signed off
  against.
- `_progress.yaml` records the `gate_version` of the suite when the domain
  was started.
- The orchestrator, on detecting that the suite's current gate-version is
  newer than the spec set's, says: "This spec set was audited under
  gate-version 1.0. The current suite is at gate-version 1.1, which added
  [N] new checks. Want to re-audit?"
- If yes, only the audit phase needs to re-run; that's the gate that
  enforces everything.
- If no, the spec set remains valid at its original gate version.

### How gate versions are bumped

In the suite repo:

- A `gate-version.yaml` at the root of the suite (separate from suite
  version).
- Bumping requires a manual edit and a corresponding entry in
  `gate-changelog.md` describing what changed.
- A CI test in the suite repo runs the suite end-to-end against the Items
  example. If gates were tightened, the Items example might now fail; the
  changelog must explain why this is the right outcome.
- The suite repo refuses to release a new gate version without the
  changelog entry.

---

## 11. Open Questions and Known Limitations

### Known limitations (deferred to v2+)

**Multi-user collaboration is out of scope for v1.** The suite assumes one
user at a time editing a given spec set. `_progress.yaml` and the phase
sign-off files are not designed for concurrent access. If two users edit
simultaneously, last-write-wins, and the orchestrator may report
inconsistent state on the next run. Recommended workflow: spec set work
happens on a feature branch with one driver; reviews happen via pull
request like any other change. Real concurrent-edit support (locking, merge
resolution) deferred to a future version.

**ADR (Architectural Decision Records) support.** Not in v1. ADRs are a
valuable companion artifact but the suite's scope is the spec set itself.
A future version may add an ADR phase or fold ADRs into existing phases.

**Targeted update mode tooling for individual fields.** v1 supports
targeted update at the phase level. Finer-grained "I only changed one field
in one entity" updates still trigger full phase re-runs. Acceptable for v1.

### Open questions to resolve during build

1. **What happens if the user invokes a phase skill directly outside the
   orchestrator?** Decision: phase skill detects no orchestrator state,
   refuses, and points the user to the orchestrator. Don't allow standalone
   phase invocation.

2. **What if a phase skill itself has a bug and produces broken output?**
   The audit will catch it. But during the build, we need a way to manually
   reset a phase: `task suite:reset-phase modeling` or similar, in the
   suite's own Taskfile. Worth building early for our own testing.

3. **Manual override of hard gates.** A `--force-advance` mechanism that
   bypasses one gate, logs the bypass with reason in `_progress.yaml`, and
   surfaces it loudly in the conformance audit later. This isn't a weakness
   — it's an honesty mechanism. Users will bypass things one way or another;
   better to capture it than pretend it doesn't happen. Implementation
   detail to confirm during build.

4. **Bootstrap re-run on a non-empty directory.** What does the bootstrap
   skill do if it finds files already exist? Recommend: detect the
   situation, refuse to overwrite by default, offer `--force` flag that's
   explicit and loud.

---

*End of SUITE-DESIGN.md*
