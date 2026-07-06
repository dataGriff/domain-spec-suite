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
5.5. [Execution Model](#55-execution-model)
6. [Update Mode](#6-update-mode)
7. [The Prompting Style](#7-the-prompting-style)
7.5. [Question-Bank Format](#75-question-bank-format)
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
- `.spec-suite/ambiguities.md` — Resolved and deferred open questions
- `.spec-suite/progress.yaml` — Phase state (suite-managed, not user-edited)
- `.spec-suite/phases/phase-N-passed.yaml` × 8 (phases 0–7) — Phase
  sign-off sidecars
- Repository shell: `Taskfile.yml`, linting configs, `mkdocs.yml`, generator
  scripts, hooks, CI workflows, instruction files

When the audit phase passes, this spec set is declared complete and ready to
drive implementations.

### The target repo

The suite operates on **empty** repositories. There is no pre-existing template
the user must apply. Phase 0 (Bootstrap) copies a canonical shell from
`skills/domain-bootstrap/templates/` into the target directory, then runs its
gate. This shell is the **single source of truth** for what a domain repo
should look like, eliminating drift between a separate template and the
skills that operate on it.

The legacy standalone `domain-api-template` repo is being absorbed into the
suite during the v1.0.0 build: its contents become the seed for
`skills/domain-bootstrap/templates/`, and the standalone repo will be
archived once v1.0.0 ships. From then on, any change to the canonical shell
happens inside the suite (and bumps the suite or gate version
accordingly — see §10).

Bootstrap refuses to run in a non-empty directory by default. The `--force`
flag honours `skills/domain-bootstrap/template_manifest.yaml` and only
overwrites files listed there; user-authored specs in
`docs/specifications/*.md` and the `.spec-suite/` state directory are never touched.
This makes shell upgrades safe (see also `task suite:upgrade-shell` in §9).

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

**Target directory naming.** Bootstrap refuses if the target directory
name doesn't start with `spec-` (the convention for domain spec repos
— `spec-items`, `spec-dog-walking`, `spec-orders`). The prefix makes
spec repos easy to identify in a list of sibling repos. Pass
`--allow-non-prefix` to bypass for legacy targets.

If the target directory already contains files, bootstrap refuses by default
and exits with a message pointing to `--force` (manifest-aware re-bootstrap
for shell upgrades) or `task suite:upgrade-shell` (the same operation
wrapped behind a clearer name). Neither path overwrites spec content; both
consult `template_manifest.yaml`.

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
- `.github/workflows/audit.yml` (Section 9, PR-time conformance audit)
- `.github/workflows/docs.yml` (Section 9, GitHub Pages deploy on push to main)
- `.github/CODEOWNERS`
- Consumption guidance: `docs/implementation-guide.md` (canonical),
  `AGENTS.md`, and `.github/instructions/api-implementation.instructions.md`
  (pointers — see below)
- Empty `.spec-suite/progress.yaml` with Phase 0 marked complete and Phase 1 ready
- `.spec-suite/bootstrap.yaml` recording the suite and gate versions that produced
  the shell
- `.spec-suite/template-manifest.yaml` listing every file bootstrap owns (used by
  `--force` re-bootstrap and `task suite:upgrade-shell` to know what may
  be overwritten)

Bootstrap **deliberately ships no spec-authoring agent guidance** — no
`CLAUDE.md`, and nothing that instructs an agent how to write or edit
the specs. The suite's orchestrator and phase skills are the only
sanctioned interface for spec-set changes. A bootstrapped domain repo
is intentionally a slate that the skills drive; authoring guidance
lives in the suite's `skills/*/SKILL.md` files, not in the target
repo. (The shipped `AGENTS.md` is not authoring guidance — see below —
its first job is telling agents *not* to edit the specs directly.)

What bootstrap *does* ship is **consumption guidance** — aimed at the
opposite direction of travel: engineers and AI coding agents building
an implementation *from* the finished spec set. It is agent-agnostic
by design (v1.0.19): the content lives once, and each agent ecosystem
finds it through its native discovery mechanism.

- `docs/implementation-guide.md` — the **canonical** playbook
  (reading order, authority map, build workflow, verification loop),
  published on the docs site so humans and agents read the same page.
- `AGENTS.md` (repo root) — the cross-agent instructions standard;
  a thin pointer: repo is spec-authoritative, changes only via the
  orchestrator, implementers follow the guide.
- `.github/instructions/api-implementation.instructions.md` — the
  GitHub Copilot discovery pointer at the same guide.
- `skills/domain-implement` (suite-side, not bootstrap-installed) —
  the interactive walk-through of the guide for Claude-family agents.

None of these authorise spec edits; all route spec changes back
through the orchestrator. (History: gate 1.4 / v1.0.18 first allowed
the `.github/instructions` guide after earlier revisions banned all
instruction files while the docs index referenced one; v1.0.19
restructured to canonical-guide + pointers.)

After Bootstrap, the orchestrator immediately prompts to start Phase 1.

---

## 3. The Orchestrator

The orchestrator is a skill in its own right (`domain-orchestrator`). It is
the entry point for all user interaction with the suite.

### Responsibilities

**On invocation, read state.** Load `.spec-suite/progress.yaml` if present. Identify
current phase status: not-started, in-progress, passed (with version and
timestamp), or stale (file modified after sign-off — see Section 6).

**Decide what to do.**

- No `.spec-suite/progress.yaml`: this is a new domain. Confirm with the user, explain
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

`.spec-suite/progress.yaml` is the authoritative state for the suite. The orchestrator
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

# Force-advance entries — written by `task suite:force-advance`.
# Audit fails on any unaccepted entry; clear with `task suite:accept-force`.
force_advances: []
# Example entry:
# force_advances:
#   - phase: contracts
#     reason: "Spectral install blocked on upstream bug X"
#     forced_at: "2026-05-26T10:00:00Z"
#     operator: "griff182uk"
#     accepted: false
#     accepted_reason: null
#     accepted_at: null

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

`.spec-suite/phases/phase-N-passed.yaml` records the per-phase audit trail:

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

# Soft-gate warnings that were explicitly responded to. Silent dismissal
# is impossible — every warning surfaced by the gate must appear here with
# a response.
warnings_responded:
  - id: MOD-LIFECYCLE-DEFINED
    response: deferred            # resolved | deferred | n-a
    reason: "lifecycle TBD pending UX review"
    required_by: audit            # only set when response == deferred
    ts: "2026-05-25T14:40:00Z"

# Findings produced by the agent's rubric evaluation per §5.5 and §7.
# Same engagement model as warnings: every finding needs a response.
rubric_findings:
  - id: RUBRIC-PROBLEM-USER-PAIN
    verdict: warn                 # pass | warn
    detail: "problem statement still reads solution-first"
    response: resolved
    reason: "rewrote to lead with user pain (see commit abc)"
    ts: "2026-05-25T14:42:00Z"

# Decision Log: agent-emitted record of semantic choices the agent
# made that AREN'T surfaced by any check or rubric. These are the
# choices between defensible alternatives (entity split-vs-collapse,
# FK-vs-copy denormalization, snapshot timing, retention windows,
# ownership-rule semantics, etc.). Sign_off requires id + summary +
# rationale on every entry. The Decision Log gives the user something
# to revise against post-sign-off: read it, disagree, edit the file,
# re-sign. See §6 (update mode) for the revision flow.
decisions:
  - id: PRD-PERSONA-COUNT-TWO
    summary: "Captured two personas (Stockroom Lead, Operations Analyst)
      rather than collapsing into one."
    rationale: "The read/write split is the core of the problem statement;
      collapsing personas would hide the access-control motivation."
    affects:
      - docs/specifications/prd.md
    ts: "2026-05-25T14:43:00Z"

files_signed:
  - path: docs/specifications/prd.md
    sha256: "abc123..."
    mtime: "2026-05-25T14:44:30Z"   # human readability only — not consulted
```

The sha256 on file sign-off is authoritative: if the file is hand-edited
later, the hash mismatch is how staleness is detected (see §6). `mtime` is
recorded for human readers but is never used in the staleness check —
it would produce false positives on `git checkout`, IDE saves, or fresh
clones.

### The ambiguities file

`.spec-suite/ambiguities.md` tracks deferrals in markdown so it's human-readable:

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

## 4.5. Events Carry Full Domain State

Every domain event publishes the full state of its affected entity
at the moment of the event. The data contract records that state.
Together they form the audit-grade historic record — every
downstream consumer (analytics, audit log, time-travel
reconstruction, event-sourced reader) can recover what happened
from the event stream alone, without re-querying the live API.

Thin events are an anti-pattern. An event payload that carries
only identifiers (`{dogId, ownerId}` without `name, breed, ageYears,
…`) forces every consumer back to the API, couples downstream
availability to API availability, and reduces the data contract
to a record of *that an event happened* rather than *what it
carried*. The contract loses its audit value.

The `EVENT-PAYLOAD-COVERS-ENTITY-STATE` check (§5.5) enforces this
at Phase 6 + audit. For every event in the model's `## Domain
Events` table, every required entity attribute must appear in the
matching AsyncAPI message payload and the matching datacontract
record. The asyncapi payload and datacontract record must also
agree with each other.

**Sensitive fields** are excluded via the `[secret]` marker in the
attribute's Description column:

```markdown
| `passwordHash` | string | Yes | [secret] bcrypt hash, never published to events |
```

The parser strips `[secret]`-tagged attributes from the
must-appear set. Visible to reviewers in the model itself; no
separate exclusion file.

**Removal events** (channel action ∈ `removed` / `deleted` /
`expired`) are exempt: the entity is gone, so a minimal payload
(id + timestamp) is the right shape.

**Aggregate roots with contained collections** (Invoice + line
items, RateCard + entries) MUST carry their declared child
collections in the same event. Aggregates are declared in the
model's `## Aggregates` section:

```markdown
## Aggregates

| Root | Child | Collection |
|------|-------|------------|
| `Invoice` | `InvoiceLineItem` | `lineItems` |
| `RateCard` | `RateCardEntry` | `entries` |
```

For each declared root → child → collection, the check verifies:

- the asyncapi payload's `data.<collection>` is an array of
  objects whose item properties cover the child's published
  attributes;
- the datacontract record's `<collection>` is an ODCS
  `logicalType: array` whose `items.properties` cover the same
  set;
- the two sides agree on the item property set.

The `## Aggregates` section is opt-in — domains with no
aggregates simply omit it.

---

## 4.6. Idempotent Mutating Ops

Networks lose responses. Clients retry. Without a per-intent
identifier, the server can't tell a retried call from a fresh
one. The result on a `POST` is a duplicate entity: two walks
booked, two invoices paid, two of the same dog.

The convention (Stripe / IETF
`draft-ietf-httpapi-idempotency-key-header`):

- Client generates a UUID **per intent** (not per attempt).
- Client sends it in `Idempotency-Key: <uuid>`.
- Server stores `{key → response}` for ~24h. On retry, the
  stored response is replayed verbatim (same status, same body,
  same `Location` header on creates).

In the OpenAPI contract this is expressed as a reusable
parameter declared under `components.parameters.IdempotencyKey`
and `$ref`-ed from every POST operation. The error catalogue
gains `IDEMPOTENCY_KEY_CONFLICT` (409) for the "same key, different
body" case. `IDEMPOTENCY-KEY-ON-POST-OPS` enforces presence.

**Scope: required on POST, not enforced on PUT/PATCH/DELETE.**
POST is the only verb that creates new state from scratch — the
dangerous one. PUT/PATCH/DELETE are verb-idempotent (same input
→ same final state), so the header is optional there; declaring
it adds *response* determinism but isn't load-bearing.

The server-side replay-store implementation (Redis, Postgres TTL
table, etc.) is a runtime concern outside the contract.

---

## 4.7. Data Contract SLAs and Derived Data Products

The data contract claims to serve "reporting, analytics, downstream
sync" — so it must carry the SLAs a consumer plans against. Three
`slaProperties` are mandatory (`DATACONTRACT-SLA-COMPLETE`, gate 1.4):

- **availability** — delivery guarantee (from the NFRs);
- **retention** — replay horizon (from the NFRs);
- **latency** — freshness: how long after a domain transition
  commits is its event readable. This is the property operational
  dashboards and near-real-time consumers actually size against.

Record-level `quality:` expectations (PK uniqueness, required-field
completeness, legal enum members) are stated as ODCS `type: text`
entries — documentation-grade until a real quality runner exists.

**Derived data products** are the designed-but-not-yet-mechanised
second layer: summarised/read-model perspectives (per-entity
histories, per-period aggregates) computed *from* the event stream,
each authored as its own ODCS contract under
`contracts/data-products/<name>.yaml` with explicit source-event
lineage and its own (usually staler) SLAs. The convention is
specified in `skills/domain-datacontract/SKILL.md`; gate checks for
it arrive with the first real product (see BUILD-PLAN Post-v1
Backlog). The event contract alone remains a complete Phase 6
output — products are opt-in, consumer-driven artifacts.

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

### Parent + sub-skill phases

Some phases produce multiple output files with different
authoring conventions. To keep `SKILL.md` files scannable, a
phase MAY be implemented as a **parent skill plus authoring
sub-skills**:

- The parent owns the phase: `PHASE_TO_SKILL` maps to it, its
  `gate.yaml` lists every check, `sign_off.py` signs the
  combined output. The parent's `SKILL.md` orchestrates and
  carries the cross-reference rules.
- Each sub-skill owns the authoring conventions for one part of
  the phase's surface. Sub-skills have a `SKILL.md` only — no
  `gate.yaml`, no checks, no templates of their own. They're
  loaded by reference from the parent.

**Phase 6 is the canonical example.** `domain-contracts` is the
parent and runs the gate; `domain-openapi`,
`domain-asyncapi`, and `domain-datacontract` are authoring
sub-skills that the parent's `SKILL.md` routes to depending on
which contract the user is editing.

This pattern is opt-in. Most phases produce one document and
don't need it; the splitting cost is only worth paying when
authoring conventions diverge enough that mixing them in one
file becomes a readability problem.

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
5. If no failures and no warnings → write sign-off, update .spec-suite/progress.yaml,
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

## 5.5. Execution Model

Phase skills are markdown — they instruct the agent — but **gate enforcement
is mechanical**. The agent does not get to decide whether a check passed.
This section pins down how that works.

### Tooling

- Python 3.x, pinned in the domain repo's `.mise.toml`.
- Taskfile is the single entry point for every check operation. Skills,
  hooks, and CI all invoke the same `task gate:<phase>` and `task audit`
  targets, so versions and behaviour stay consistent across contexts.

### Where checks live

- **`shared/checks/<id>.py`** — checks consumed by more than one phase
  (cross-reference checks, audit-time integrity checks).
- **`skills/<phase>/checks/<id>.py`** — checks unique to a single phase.

Both types follow the same module shape:

```python
# shared/checks/auth_matrix_openapi_match.py

metadata = {
    "id": "AUTH-OPENAPI-MATCH",
    "category": "cross-reference",        # structural | cross-reference
    "phases": ["access-control", "contracts", "audit"],
    "severity_by_phase": {
        "access-control": "warning",      # soft-gate phase
        "contracts": "error",             # hard-gate phase
        "audit": "error",
    },
    "prerequisites": [
        {"file_exists": "docs/specifications/contracts/openapi.yaml"},
    ],
}

def run(repo_root: Path) -> CheckResult:
    ...
```

A check whose `prerequisites` are not met is **skipped** (not failed). This
is what lets Phase 3 list `AUTH-OPENAPI-MATCH` — it's a no-op there until
the OpenAPI file appears in Phase 6, at which point the same module runs
with `error` severity.

### Rubric checks

Rubric checks (e.g. *"problem statement describes user pain rather than
solution"*) are the exception: they cannot be evaluated in Python. They
live as prose in the phase skill's `SKILL.md` under a clearly marked
`## Rubric checks` section. When the phase runs:

1. The agent reads the prose rubric and the spec file.
2. For each rubric rule it emits a finding with verdict `pass` or `warn`.
3. Findings are written into the phase's `.spec-suite/phases/phase-N-passed.yaml` under
   `rubric_findings:` (schema in §4).
4. Each `warn` finding feeds the soft-gate engagement loop — the user must
   resolve, defer, or mark non-applicable with reason before sign-off.

This keeps rubric checks honest (the user must see and respond to every
finding) while not pretending the agent's verdict is mechanically
reproducible. Mechanical checks remain the load-bearing ones; rubric checks
are a quality nudge with a paper trail.

### Decision Log

Mechanical checks catch consistency violations. Rubric checks nudge on
quality. Neither surfaces the **semantic choices the agent makes between
defensible alternatives** — choices like "snapshot the price at the
walk's `scheduled` transition rather than `completed`", or "split
`User` from `Walker`/`Client` profiles rather than collapse", or "the
ownership rule traverses `Client.invitedByWalkerId` rather than
embedding `walkerId` on every owned resource". These ship as part of
the spec — they shape the contract — but checks pass either way.

Each phase sidecar therefore carries a `decisions:` block (schema in
§4). Each entry is `{ id, summary, rationale, affects, ts }`. The
agent emits one whenever it picks between defensible alternatives and
nothing else (no check, no rubric) records the choice. Each soft-
middle and contracts SKILL.md carries a `## Decision Log` section
listing the decision-prone areas for that phase, so the agent has a
prompt for what to surface.

The Decision Log is **for the human reader**. Sign-off doesn't gate on
it — empty `decisions:` is valid YAML. But the user reading the spec
set later (or revisiting it months on) uses the Log to discover what
the agent decided silently. If they disagree, they edit the relevant
file and re-sign the phase (§6 update mode).

This is the discoverability mechanism for "the spec was generated;
what did the agent decide for me?".

### The runner

`shared/run_phase.py` is the single check runner:

```
task gate:<phase>
  → loads skills/<phase>/gate.yaml (the manifest of check ids)
  → loads each check module, evaluates prerequisites
  → runs applicable checks, collects results
  → exits 0 only if every applicable check passes
    at the phase-appropriate severity
```

### Sign-off

`shared/sign_off.py` is the **only** way `.spec-suite/phases/phase-N-passed.yaml` is written.
It does this:

1. Runs `task gate:<phase>`.
2. If exit code is non-zero: refuse, print failing check ids, exit non-zero.
3. If exit code is zero: prompt the agent to attach `warnings_responded:`,
   `rubric_findings:`, and `decisions:` blocks. Refuse to proceed until
   every surfaced warning and `warn` finding has a response. The
   `decisions:` block is optional but expected on soft-middle and
   contracts phases — see Decision Log above.
4. Compute sha256 for every file the phase signed.
5. Write `.spec-suite/phases/phase-N-passed.yaml`, update `.spec-suite/progress.yaml`.

The only way to bypass step 2 is `task suite:force-advance` (Decision 5 /
§9), which writes an entry to `.spec-suite/progress.yaml`'s `force_advances:` array
that the audit will surface as a finding until cleared by
`task suite:accept-force`.

### Implications

- Tests for the suite (in its own repo) are Python tests that import the
  check modules directly. No need to stand up a real domain repo for unit
  testing.
- Hooks (§9) invoke the same `task gate:<phase>` and `task audit` targets
  the skill uses. There is no separate "hook-only" check path.
- A new check is added by writing one Python module, adding its id to the
  relevant phase `gate.yaml` files, and writing a question for it in
  `questions.md` (§7.5).

---

## 6. Update Mode

After a spec set has passed audit, users will edit it. The suite supports
this through targeted update mode.

### Detection

On every orchestrator invocation, compute each spec file's current sha256 and
compare against the value recorded in the corresponding
`.spec-suite/phases/phase-N-passed.yaml`. Any mismatch marks that phase as `stale`.

`mtime` is **not** consulted. It's recorded in the sign-off file for human
readability only. mtime resets on `git checkout`, IDE saves, fresh clones,
`rsync`, and anything that re-materialises the working tree, all of which
produce false-positive staleness. sha256 is the only signal that survives
those operations and only changes when the content actually changes.

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

### Qualitative review layer (`domain-review` skill)

Mechanical checks catch shape, structure, and sha256 drift. They
**don't** catch semantic inconsistencies: two docs saying contradictory
things about the same concept, an OpenAPI operation with no user
story behind it, an NFR threshold that contradicts another NFR's
budget, a Decision Log entry whose intent isn't reflected in the
actual spec.

The `domain-review` skill (`skills/domain-review/SKILL.md`) is the
qualitative pass. It runs after audit is green and walks five
review categories:

1. Cross-document type / shape inconsistencies
2. Coverage gaps between docs
3. Logical / semantic contradictions
4. Missing-case gaps
5. Decision Log drift

Output is a structured markdown report at
`.spec-suite/reviews/<ISO-timestamp>.md`. The report is
read-only: the user reads findings and decides what to action via
the normal update-mode flow (no automatic fixes).

The skill is **not** part of the phase progression and **not** a
gate. It's a human-prompted action: invoke before a major release,
after a large update-mode change, or periodically as hygiene. Each
run produces a new timestamped report; older reports stay for
historical reference.

The runner (`scripts/domain_review.py`) verifies audit is green,
enumerates the files the agent will read, prints the category
checklist, and provides a `--write-report` mode for persisting the
agent's report body. The qualitative work — actually reading the
files and producing findings — is the agent's job, codified in
`SKILL.md`.

### Audit respects prior-phase engagement

The audit re-runs cross-reference checks at error severity. When a check
was legitimately n-a'd or deferred at its owning phase (recorded in that
phase's `warnings_responded`), re-firing it at audit-error would lose
the engagement.

`shared/prior_engagement.py` reads every prior phase's
`.spec-suite/phases/phase-N-passed.yaml`, builds a map of `check_id →
{response, reason, phase}` for any entry whose response is `n-a` or
`deferred`, and downgrades matching audit error outcomes to warning.
The downgrade attaches a carry-forward note in the audit output
("n-a/deferred at phase 'flows' — reason: …") and synthesises a
`warnings_responded` entry so the audit's sign-off doesn't refuse on
un-engaged warnings.

`resolved` responses do NOT carry forward — if the fix decayed and the
check fires again, that's a new finding worth surfacing at audit error.

The mechanism preserves audit's discoverability (the carry-forward is
visible) without blocking sign-off on a decision the user already made.
Staleness (sha256 drift) still fails the audit normally; only the
specific check-id-matched downgrades apply.

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

## 7.5. Question-Bank Format

Every phase skill carries a `questions.md` file. It is the elicitation
script the skill uses when a gate check surfaces a failure or warning —
the §7 rules say *what* the prompting should feel like; this section says
how each individual question is structured so any agent running the skill
behaves the same way.

### Schema

Each entry binds one question to one gate-check id. The order of fields is
fixed.

```yaml
- id: PRD-PERSONA-FRUSTRATION
  binds_to_check: PRD-PERSONA-FRUSTRATION

  # The opening question. One sentence, business language, names the
  # specific subject. Use {{placeholders}} for values the runner
  # interpolates from the file under inspection.
  lead_in: |
    What specifically frustrates {{persona_name}} about how they work today?

  # Vagueness-pushback. Listed in priority order; the agent picks the
  # first probe whose trigger matches the user's previous answer. Probes
  # never batch — one probe per turn, per §7 Hard Rule 1.
  probes:
    - trigger: "answer describes a desired feature rather than current pain"
      ask: |
        That sounds like a feature wish. What's the current pain that
        creates the wish?
    - trigger: "answer is qualitative ('it's slow', 'annoying')"
      ask: |
        Slow at what task, and by how much? Give me a number if you can.
    - trigger: "answer is hypothetical"
      ask: |
        Has this happened? How often, in the last month?

  # One concrete answer that would pass the check. Used as a worked
  # example when the user gets stuck — never spoken back to them verbatim
  # unless they ask.
  good_example: |
    "Contributors spend ~20 minutes a day re-typing item IDs across the
     spreadsheet, the ticket system, and the warehouse app."

  # One concrete answer that would fail the check, paired with the
  # rebuttal the agent should give. Trains the agent to recognise the
  # failure mode in unfamiliar phrasings.
  bad_example:
    answer: "It's slow."
    rebuttal: |
      "Slow" doesn't help me write a frustration into the PRD. Slow at
      what task, and by how much?

  # The reflect-before-writing template (§7 Hard Rule 3). The agent
  # interpolates the user's resolved answer and asks for confirmation
  # before committing anything to the file.
  reflect_template: |
    So {{persona_name}} is frustrated by {{summary}}. I'll capture that
    as the frustration. Sound right?
```

### Authoring rules

1. **One entry per gate check.** Coverage is enforced: the build task fails
   if any check id in a phase's `gate.yaml` lacks a `questions.md` entry.
2. **`lead_in` reads as an interview question, never a lint diagnostic**
   (§7 Hard Rule 10). The check id never appears in user-facing text.
3. **At least two probes**, ordered most-likely first. Don't pad — a probe
   that never triggers is dead weight.
4. **Examples come from the domain.** When authoring a question, pull the
   `good_example` and `bad_example` from real conversations or from the
   Items fixture. Invented examples drift.
5. **`reflect_template` always closes with a confirmation request.** Never
   write to file silently after a free-text answer.

### Runtime contract

The phase skill loads `questions.md` once at start, indexes by
`binds_to_check`, and uses entries as follows during the §5 loop:

1. Run gate checks → collect failures/warnings.
2. For each finding, look up its question by `binds_to_check`.
3. Ask `lead_in`. If the answer is vague, ask the matching probe. Repeat
   probes up to twice; if still vague, defer or mark non-applicable per
   the soft-gate engagement loop.
4. Run `reflect_template` against the user's resolved answer.
5. On confirmation, write the edit. Re-run affected checks.

This pattern is identical across phases. Anything skill-specific (the
templates, the gate manifest, the rubric prose) lives elsewhere in the
skill directory; `questions.md` is the elicitation contract.

---

## 8. Per-Phase Specifications

This section captures the gate criteria summary per phase. The full question
banks for each phase live in their respective skill directories
(`skills/<phase>/questions.md`) and are produced during build.

### Phase 0: Bootstrap — Hard gate (trivial)

Structural checks:
- All expected files exist at expected paths
- All files have valid syntax (YAML files parse, markdown is well-formed)
- `.spec-suite/progress.yaml` initialized with Phase 0 status passed
- `.spec-suite/bootstrap.yaml` records suite and gate version

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
  *(deferred in v1 — no reliable heuristic for extracting entity mentions
  from story prose without false positives; documented as a known
  limitation in the modeling SKILL.md and BUILD-PLAN 5.1)*
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

Runs all phases 1-6 cross-reference checks simultaneously, and re-runs
the Phase 6 tool lints (Spectral on OpenAPI/AsyncAPI, datacontract-cli;
each skips where its CLI isn't installed). Additionally:
- Verifies no unreplaced template placeholders (no `[Resource1]`, `[Domain]`,
  or `{{` strings remain in any spec file or rendered output)
- Verifies `.spec-suite/ambiguities.md` has no items marked `required-by: audit` that
  remain unresolved
- Verifies all `.spec-suite/phases/phase-N-passed.yaml` sidecars are present and not stale
  (sha256 comparison per §6)
- Verifies `.spec-suite/progress.yaml`'s `force_advances:` array contains no entries
  with `accepted: false`. Any unaccepted force-advance fails the audit and
  surfaces a finding instructing the user to either resolve the underlying
  check failures or run `task suite:accept-force <phase> --reason '<text>'`
  to record an explicit acceptance.
- Runs `task domain:check` and confirms it passes
- Runs the generator script and verifies the output is **clean**, defined
  as:
  - exit code 0
  - no `[Resource1]`, `[Domain]`, or `{{` placeholder strings in the
    rendered `domain-overview.html`
  - every entity named in `domain-model.md` appears in the rendered
    overview (cross-reference)
  - no Python tracebacks or warnings on stderr

On pass: writes `.spec-suite/phases/phase-7-passed.yaml` with the full
check manifest, timestamp, and gate-version. Declares spec set complete.

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

- Every `.spec-suite/phases/phase-N-passed.yaml` records the `gate_version` it was signed off
  against.
- `.spec-suite/progress.yaml` records the `gate_version` of the suite when the domain
  was started.
- `.spec-suite/bootstrap.yaml` records the `gate_version` of the shell that was
  initially copied into the repo.
- The orchestrator, on detecting that the suite's current gate-version is
  newer than the spec set's, says: "This spec set was audited under
  gate-version 1.0. The current suite is at gate-version 1.1, which added
  [N] new checks. Want to re-audit?"
- If yes, only the audit phase needs to re-run; that's the gate that
  enforces everything.
- If no, the spec set remains valid at its original gate version.

After a re-audit, per-phase sign-off files may carry a different
`gate_version` from `.spec-suite/bootstrap.yaml` and from each other (e.g. discovery
re-signed under 1.1 while modeling is still at 1.0). This is **expected
and correct** — it reflects the actual audit history of the spec set.
The orchestrator never rewrites historical `gate_version` values; it only
appends.

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
user at a time editing a given spec set. `.spec-suite/progress.yaml` and the phase
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

1. **What if a phase skill itself has a bug and produces broken output?**
   The audit will catch it. But during the build, we need a way to manually
   reset a phase: `task suite:reset-phase modeling` or similar, in the
   suite's own Taskfile. *(Resolved in v1.0.14: `scripts/reset_phase.py`
   deletes the sidecar + signed outputs and marks the phase not-started;
   dry-run by default, `--yes` to apply.)*

(Previous items 1, 3, and 4 — standalone phase invocation, manual override
of hard gates, and bootstrap re-run on a non-empty directory — have all
been resolved and folded into §5, §5.5, §1, and §9.)

---

*End of SUITE-DESIGN.md*
