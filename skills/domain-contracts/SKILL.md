---
name: domain-contracts
description: |
  Phase 6. Conformance gate over the three contract files
  (`contracts/openapi.yaml`, `contracts/asyncapi.yaml`,
  `contracts/datacontract.yaml`). Lints each, then
  cross-references them against every upstream spec (domain
  model, glossary, auth matrix, error catalogue) and against
  each other. Hard gate: no warnings, no rubric judgements —
  every check is mechanical and every check must pass for
  sign-off. The only escape is
  `task suite:force-advance contracts --reason '<text>'`, which
  the audit then surfaces until accepted.

  Per-contract authoring conventions live in three sibling
  sub-skills:

  - [`domain-openapi`](../domain-openapi/SKILL.md) — OpenAPI
    3.0.3 conventions, including the Idempotency-Key on POST
    convention.
  - [`domain-asyncapi`](../domain-asyncapi/SKILL.md) — AsyncAPI
    2.6 + CloudEvents conventions, full-state-in-events, and
    aggregate-child collections.
  - [`domain-datacontract`](../domain-datacontract/SKILL.md) —
    ODCS 3.1 conventions, nested aggregate fields, and HTML
    rendering.

  This skill owns the gate; the sub-skills own the authoring
  guidance.
prerequisites:
  - Phases 1-5 have signed off (the contracts gate
    cross-references every prior phase's outputs).
  - Target repo has `spectral` and `datacontract` on PATH
    (pinned via the target's `.mise.toml`; the bootstrap
    installs them for you).
trigger_phrases:
  - "phase 6"
  - "run the contracts gate"
  - "sign off contracts"
  - "validate the contracts"
---

# Phase 6 — Contracts

This skill has two halves: **author** (produce three contract
YAML files from upstream specs) and **validate + sign-off**
(mechanical gate against the result). The validate half is
purely mechanical — contracts are right or they aren't, no
rubric checks. The author half is interactive: the skill reads
upstream specs and walks the user through filling in the
templates.

For the per-contract authoring conventions, route the user to
the appropriate sub-skill:

- OpenAPI section → `domain-openapi`
- AsyncAPI section → `domain-asyncapi`
- datacontract section → `domain-datacontract`

This SKILL.md keeps the **gate**, **sign-off**, **cross-reference
rules**, and **decision log** scope.

## What this skill does

1. Resolves the target repo (current working directory by
   default).
2. Verifies all earlier phases (1-5) have signed off — refuses
   if not.
3. **Author half.** If any of `contracts/openapi.yaml`,
   `contracts/asyncapi.yaml`, `contracts/datacontract.yaml` is
   missing, runs `task init:contracts -- --repo <target>` to
   copy the blank `.spec-suite/templates/contracts/*.yaml`
   skeletons into place. Never overwrites existing files (the
   user's authored work is safe). Then routes the user to the
   relevant sub-skill for that contract's conventions and walks
   them through populating each section using the upstream
   specs as the source of truth.
4. **Validate half.** Invokes the runner
   (`shared/run_phase.py contracts --repo <target>`), which
   runs every check listed in `gate.yaml`.
5. If every check passes: invokes `shared/sign_off.py contracts`
   which computes sha256s for the three contract files and
   writes `.spec-suite/phases/phase-6-passed.yaml`.
6. If any check fails: reports the failing check ids verbatim.
   Does not write the sign-off file. Tells the user to either
   fix the underlying issues or, in genuine emergencies, run
   `task suite:force-advance contracts --reason '<text>'`
   (which writes a `force_advances` entry to
   `.spec-suite/progress.yaml` that the audit surfaces until
   cleared via `task suite:accept-force`).

## Authoring routing

The three contracts are largely *derivable* from upstream specs
— the job is mechanical synthesis, not creative writing. The
sub-skills above carry the conventions for each contract
individually; this skill orchestrates the sequence:

1. Start with `domain-openapi` — the REST surface is the most
   visible to consumers and the easiest to validate against the
   auth matrix.
2. Then `domain-asyncapi` — every write op needs at least one
   channel; the event payload schemas reuse openapi schemas
   where possible.
3. Then `domain-datacontract` — the historic record mirrors the
   asyncapi payloads, so it's effectively the last step.

After every contract section, run `task gate:contracts -- --repo
<target>` to surface lint and cross-reference errors early.
Iterate until clean, then sign off.

## How to run

From any directory:

```bash
# Lay down blank templates if contracts/ doesn't exist yet
mise exec -- task init:contracts -- --repo <target-dir>

# Validate (no side-effects beyond the runner's exit code)
mise exec -- task gate:contracts -- --repo <target-dir>

# Sign off (refuses if the gate fails)
mise exec -- task sign-off:contracts -- --repo <target-dir>
```

Or directly:

```bash
python <suite-root>/scripts/init_phase.py contracts --repo <target-dir>
python <suite-root>/shared/run_phase.py contracts --repo <target-dir>
python <suite-root>/shared/sign_off.py contracts --repo <target-dir>
```

## Checks in this gate

Listed in `gate.yaml`. Two categories:

- **Tool checks** (subprocess linters; skipped if the tool isn't
  on PATH):
  - `SPECTRAL-OPENAPI` — `spectral lint contracts/openapi.yaml`
  - `SPECTRAL-ASYNCAPI` — `spectral lint contracts/asyncapi.yaml`
  - `DATACONTRACT-LINT` — `datacontract lint contracts/datacontract.yaml`
- **Cross-phase consistency** (shared modules; the audit re-runs
  the same modules at error severity):
  - `ENTITY-IN-OPENAPI-SCHEMA` — domain entity ↔ OpenAPI schema
  - `FIELD-MATCH-DOMAIN-OPENAPI` — attribute names align
  - `ENUM-VALUES-CONSISTENT` — named enums in `## Enumerations`
    have matching values in openapi.yaml + asyncapi.yaml +
    datacontract.yaml
  - `WRITE-OP-HAS-ASYNCAPI-CHANNEL` — every write op has an event
  - `EVENT-IN-DATACONTRACT` — every event has a datacontract
    record
  - `EVENT-PAYLOAD-COVERS-ENTITY-STATE` — every event payload +
    datacontract record carries the full entity state per
    SUITE-DESIGN §4.5
  - `AUTH-MATRIX-OPENAPI-MATCH` — auth-matrix operations ↔
    openapi
  - `ERROR-CODE-IN-CATALOGUE` — error codes traced back to
    catalogue
  - `IDEMPOTENCY-KEY-ON-POST-OPS` — every POST declares a
    required `Idempotency-Key` header so retries are safe
    (SUITE-DESIGN §4.6)

## Decision Log

Per SUITE-DESIGN §5.5 Decision Log. Contract drafting is mostly
mechanical synthesis from upstream specs, but several semantic
choices have no check that catches them. Emit `decisions:` for
any non-trivial choice:

```yaml
decisions:
  - id: OPENAPI-PAGINATION-CAP-50
    summary: "List endpoints cap pageSize at 50 (enforced via
      PageSize.maximum)."
    rationale: "Single-walker workload doesn't justify larger
      pages; lower cap protects mobile bandwidth for owners."
    affects: [docs/specifications/contracts/openapi.yaml,
      docs/specifications/nfr.md]
```

Decision-prone areas specific to each contract are documented in
the corresponding sub-skill.

## What this skill never does

- Never edits a contract file. Contracts are user-authored.
- Never relaxes a check. Every failure is surfaced; the user
  fixes the contract or force-advances.
- Never writes the sign-off file directly. That's
  `shared/sign_off.py`'s sole prerogative — and it refuses
  unless `task gate:contracts` exits 0 (or `--force-advance` is
  given).

## Files this phase signs

Listed in `gate.yaml` under `signs_files:`:

- `docs/specifications/contracts/openapi.yaml`
- `docs/specifications/contracts/asyncapi.yaml`
- `docs/specifications/contracts/datacontract.yaml`

`shared/sign_off.py` computes sha256 for each and records it in
`.spec-suite/phases/phase-6-passed.yaml`. The audit's
`SIGNOFF-SHA256-MATCHES` check verifies these later.
