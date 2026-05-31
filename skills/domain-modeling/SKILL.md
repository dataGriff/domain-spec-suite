---
name: domain-modeling
description: |
  Phase 2. Drives `domain-model.md` and `glossary.md` authoring.
  Soft + engagement gate: hard errors (duplicate entity name, glossary
  drift) refuse sign-off; warnings (missing timestamps, missing
  business rules, undefined lifecycles, one-way relationships) must
  each have an explicit response in `warnings_responded` (resolved /
  deferred / n-a) before sign-off completes.
prerequisites:
  - Phase 1 (discovery) has signed off — `_phase-1-passed.yaml` exists
    and prd.md carries the personas + user stories the model will
    cross-reference.
trigger_phrases:
  - "phase 2"
  - "start modeling"
  - "draft the domain model"
  - "sign off modeling"
---

# Phase 2 — Modeling

This skill has two halves: **author** (produce `domain-model.md` and
`glossary.md` from the PRD) and **validate + sign-off** (mechanical
gate plus the soft-gate engagement loop).

## What this skill does

1. Resolves the target repo (current working directory by default).
2. Verifies Phase 1 (discovery) has signed off — refuses if not.
3. **Author half.** If either output file is missing, runs
   `task init:modeling -- --repo <target>` to copy the blank templates
   from `_template/`. Never overwrites existing files. Then walks the
   user through populating the entities, relationships, lifecycles,
   and glossary entries via `questions.md`.
4. **Validate half.** Invokes the runner. Hard checks (duplicate
   name, glossary drift) refuse sign-off if they fail. Soft checks
   surface as warnings; each one needs a response.
5. **Soft-gate engagement.** For every warning the gate surfaced, ask
   the user (via the matching `questions.md` entry): is this a real
   issue to fix, or n-a (with reason), or to defer to a later phase
   (with `required_by`)? Capture each response in a list to pass to
   sign_off.
6. **Sign off.** Write a YAML file with `warnings_responded:` (and
   any rubric findings — none for modeling), then invoke
   `task sign-off:modeling -- --repo <target> --findings <yaml>`.
   The script verifies every warning has a response, then writes
   `_phase-2-passed.yaml` with sha256s for both files.

## Authoring

The PRD's user stories name entities implicitly ("add an item",
"register as a contributor", "request a walk"). Mining those for
candidate entities is the agent's job — propose a starter list, then
walk each through:

1. Heading + one-paragraph purpose
2. Attribute table (Attribute / Type / Required / Description)
3. Business rules (at least one if applicable)
4. Lifecycle table (if the entity has a `status` attribute)

Glossary entries are mechanical: every entity gets a `### <Entity>`
heading under `## Entities`, every attribute gets a `### <attribute>`
heading under `## <Entity> attributes`. Don't type them by hand —
run `task glossary:skeleton` (bootstrap-installed) to generate the
skeleton from `domain-model.md` with TODO placeholders, then walk
the entries and fill in real prose. On a domain with 10+ entities
this saves a meaningful amount of typing tedium and avoids missed
attributes.

After every entity, run `task gate:modeling -- --repo <target>` to
surface failures and warnings early. Iterate until the gate is clean
of errors and every warning has a response, then sign off.

## Soft-gate engagement loop

When the gate emits a warning:

1. Look up the question by `binds_to_check` in `questions.md`.
2. Ask `lead_in` with the warning's subject (entity name, attribute
   name, relationship pair).
3. On vague answers, walk the probes (one per turn, §7 Hard Rule 1).
4. Resolve to one of:
   - **resolved** — the user fixed the underlying issue; re-run the
     gate; the warning should clear
   - **deferred** — the warning is real but the fix lives in a later
     phase; capture `required_by: <phase>` so the audit surfaces it
     if it's not cleared by then
   - **n-a** — the warning is structural noise for this case (e.g.
     value object without `updatedAt`); capture the reason
5. Record the response. Move on.

When every warning has a response, write the findings YAML and call
sign_off.

## How to run

```bash
mise exec -- task init:modeling -- --repo <target-dir>
mise exec -- task gate:modeling -- --repo <target-dir>
mise exec -- task sign-off:modeling -- --repo <target-dir> --findings <yaml>
```

Or directly:

```bash
python <suite-root>/scripts/init_phase.py modeling --repo <target-dir>
python <suite-root>/shared/run_phase.py modeling --repo <target-dir>
python <suite-root>/shared/sign_off.py modeling --repo <target-dir> --findings <yaml>
```

The findings YAML:

```yaml
warnings_responded:
  - id: MODEL-ENTITY-HAS-ID-TIMESTAMPS
    response: n-a         # resolved | deferred | n-a
    reason: "User has no updateable fields in v1 (one-shot registration)"
    # required_by: audit  # only when response == deferred
rubric_findings: []       # modeling has no rubric checks
```

## Checks in this gate

Listed in `gate.yaml`.

### Hard errors (must pass)

- `MODEL-ENTITY-NAME-UNIQUE` — no duplicate entity names
- `ENTITY-IN-GLOSSARY` — every entity in the model is in the glossary
- `GLOSSARY-COVERS-ATTRIBUTES` — every attribute is glossed too

### Warnings (must each have a response)

- `MODEL-ENTITY-HAS-ID-TIMESTAMPS` — entities should have `id`,
  `createdAt`, `updatedAt`
- `MODEL-ENTITY-BUSINESS-RULE` — entities should have ≥1 business
  rule
- `MODEL-LIFECYCLE-DEFINED` — entities with a `status` attribute
  should have a documented lifecycle table
- `MODEL-RELATIONSHIP-BIDIRECTIONAL` — relationships should be stated
  in both directions

## Decision Log

Most modeling choices are driven by the gate or by clear upstream
references. Some aren't — those are the choices the agent should emit
as `decisions:` entries (per SUITE-DESIGN §5.5 Decision Log). The
findings YAML for sign-off carries them:

```yaml
decisions:
  - id: USER-WALKER-CLIENT-SPLIT
    summary: "Split authentication User from role profiles Walker / Client (1:1 each)."
    rationale: "Keeps the auth tables slim and lets each role carry
      role-specific fields without nullable noise."
    affects: [docs/specifications/domain-model.md]
```

### Decision-prone areas in this phase

The agent should emit a decision (or surface a question) whenever
choosing between defensible alternatives in any of these areas:

- **Entity split vs collapse.** When a role/persona could be modelled
  as a separate entity OR as a `role` flag on a shared one. Record
  which and why.
- **FK + denormalized copy.** When a child entity references a parent
  by FK AND also copies fields from it for snapshot purposes
  (e.g. `InvoiceLineItem.walkId` plus copied `walkType` /
  `durationMinutes`). Record what's snapshotted and why.
- **Snapshot timing.** When a derived value (price, status,
  configuration) is captured. Which upstream event triggers the
  snapshot — `scheduled`, `completed`, `issued`?
- **Immutability rules** that aren't enforced by a check. Why is
  `ownerId` immutable? Why isn't `email`?
- **Cardinality choices** that aren't obvious. Why exactly one of X
  per Y rather than many?
- **Status field with no lifecycle** that's marked n-a. Why is it a
  flag rather than a state machine?

Emit at least one decision when any non-obvious choice is made.
Empty `decisions:` is valid YAML, but on a phase this size that
usually signals the agent under-engaged.

## What this skill never does

- Never edits `domain-model.md` or `glossary.md` without confirmation
  (per §7 Hard Rule 3).
- Never silently dismisses a warning. The sign-off script refuses
  unless every warning has an explicit response.
- Never writes the sign-off file directly. That's `sign_off.py`'s
  sole prerogative.
- Never invents PRD entities — the agent only proposes entities that
  trace back to a user story or persona action.

## Files this phase signs

- `docs/specifications/domain-model.md`
- `docs/specifications/glossary.md`

The audit's `SIGNOFF-SHA256-MATCHES` check verifies these later.

## Known v1 limitations

- **No PRD-ENTITY-IN-MODEL cross-reference.** A PRD that names an
  entity the model doesn't have (e.g. "viewer comments" without a
  Comment entity) will not be flagged here. The heuristic is hard
  (capitalised words in stories ≠ entity references reliably) and
  the false-positive cost is too high for v1. Audit catches the
  reverse direction via `ENTITY-IN-GLOSSARY`.
