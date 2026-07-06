---
name: domain-review
description: |
  Independent qualitative review of a complete spec set. Runs after
  audit is green; surfaces inconsistencies, coverage gaps, and
  semantic contradictions the suite's mechanical checks can't catch.
  Read-only — produces a structured findings report; never edits spec
  files. The user reads the report and decides what to fix via the
  normal update-mode flow.
prerequisites:
  - Phase 7 (audit) has signed off. If audit is failing, fix
    mechanical issues first — there's no point doing a qualitative
    review on a spec set with failing structural checks.
trigger_phrases:
  - "review my spec set"
  - "independent review"
  - "qualitative review"
  - "domain review"
  - "run the review"
  - "review the spec"
  - "sanity check the spec"
---

# Domain Review

A spec set passes audit (17/17 mechanical checks green) and the
generator runs clean. That's necessary but not sufficient. Mechanical
checks catch shape, structure, sha256 drift, missing fields. They
**don't** catch:

- Two docs saying contradictory things about the same concept
- An OpenAPI operation with no user story behind it
- A domain event with no operation that emits it
- An NFR threshold that contradicts another NFR's budget
- A Decision Log entry whose stated intent isn't reflected in the
  actual spec
- A required attribute with no scenario testing its missing-field case

This skill is the qualitative pass that catches that class of issue.

## What this skill does

1. **Verify audit is green.** If `task audit --repo <target>` exits
   non-zero, refuse the review and tell the user to fix mechanical
   issues first.
2. **Read every spec file** under `docs/specifications/` and
   `docs/specifications/contracts/`, plus every
   `.spec-suite/phases/phase-N-passed.yaml` sidecar (for Decision Log entries).
3. **Walk the five review categories** (below). For each, produce a
   list of findings or an explicit "checked and OK" note.
4. **Write a structured report** to
   `.spec-suite/reviews/<ISO-timestamp>.md` AND echo to
   stdout. The report is append-only — each run produces a new
   timestamped file; older reviews are kept for historical reference.
5. **Suggest next steps.** For each finding, the report includes a
   one-sentence fix recommendation. The user decides which to action;
   re-engaging affected phases happens through the normal update-mode
   flow (edit the file, re-sign the phase, decisions land in the
   sidecar).

The review **does not** edit any spec file. It does **not** sign
anything off. It does **not** invoke any gate. It's read-only.

## When to run

- **Before a major release** of a spec set (the human equivalent of a
  "design review" milestone)
- **After a large update-mode change** (e.g. a new entity, a new
  flow) to catch ripple-effect inconsistencies
- **Periodically** — quarterly or per-sprint — as a hygiene check on
  long-lived spec sets
- **On demand** when the user feels something is off but doesn't know
  what

Not run automatically as part of any gate. The review is a human-
prompted action, not a CI blocker.

## The five review categories

### 1. Cross-document type / shape inconsistencies

Same concept, different shape in different files. Check:

- An attribute typed `integer` in `domain-model.md` but `string` in
  `contracts/openapi.yaml`
- A field marked required in one place, optional in another
- An enum's value set drifting across files (e.g. domain-model lists
  `[active, archived]` but openapi schema has `[active, archived,
  deleted]`)
- Constraint drift across files (e.g. minimum/maximum on `priceCents`
  inconsistent between `RateCardEntry` and `InvoiceLineItem`)
- Cardinality / multiplicity mismatches (domain-model says "has-many"
  but openapi exposes a single FK or vice versa)

### 2. Coverage gaps between docs

Things that exist in one doc and not the corresponding one. Check:

- User stories in `prd.md` whose endpoint isn't in
  `contracts/openapi.yaml`
- Operations in `contracts/openapi.yaml` not justified by any user
  story
- Acceptance scenarios in `acceptance-scenarios.md` referencing
  endpoints, fields, error codes, or events that don't exist in
  the contracts
- Error codes referenced in acceptance scenarios but not in any user
  story's acceptance criteria (or vice versa)
- Entities declared in `domain-model.md` with no API surface in
  openapi at all (sometimes intentional — flag for confirmation)
- Domain events declared in `domain-model.md`'s Domain Events table
  but not in any AsyncAPI channel

### 3. Logical / semantic contradictions

Things that internally contradict. Check:

- A persona described as doing things the auth matrix forbids
- An operation marked Forbidden for a role that the role description
  says they can do
- Lifecycle transitions in `domain-model.md` that no operation in
  `contracts/openapi.yaml` can trigger (orphan state)
- A domain event whose payload requires a field that the originating
  entity doesn't have
- NFR thresholds that contradict each other (e.g. read latency p95
  tighter than auth latency budget when reads require auth)
- NFR delivery semantics vs asyncapi's promises (e.g. NFR says event
  publication is best-effort and non-blocking while asyncapi claims
  consumers can reconstruct everything from the stream alone —
  best-effort delivery cannot support a completeness guarantee)
- Entity creation timing told differently by different docs (e.g.
  openapi returns the entity's id at invite time, domain-model says
  it's created at acceptance, glossary says at invite — especially
  when a required field like `userId` can't exist yet under one of
  the tellings)
- A Decision Log entry whose stated rationale contradicts the
  implementation (e.g. "snapshot at scheduled" decision but openapi
  or scenarios imply snapshot at completion)

### 4. Missing-case gaps

Required behaviour that isn't tested or specified. Check:

- Required attribute X but no acceptance scenario for the missing-X
  validation case
- Status enum value Y declared but no operation can produce it
- An auth-matrix cell marked "Allowed-if-owner" but no scenario tests
  the cross-owner FORBIDDEN case
- Error code declared in `error-catalogue.md` but no scenario tests
  the conditions that trigger it
- Lifecycle terminal state (e.g. `cancelled`) declared but no
  scenario covers reaching it
- Dead contract surface: components/schemas referenced by no
  operation (especially ones carrying `[secret]` fields — dead
  schemas with secrets are drift waiting to leak), and response
  fields no consumer can ever use (e.g. a refresh token issued with
  no refresh endpoint)
- Unobservable Then clauses: scenario assertions with no contract
  surface to observe them through (no response field, header, event,
  or follow-up call could verify the claim)

### 5. Decision Log drift

For each `decisions:` entry across `.spec-suite/phases/phase-N-passed.yaml` sidecars,
verify the implementation still matches the stated intent:

- Does the decision still apply to the current spec, or has subsequent
  editing made it stale?
- Are the `affects:` files still showing the documented choice, or
  has one of them drifted?
- Are any decisions outdated by later decisions (later ones override
  earlier ones with no record of the supersession)?

## How to run

The user invokes via:

```bash
mise exec -- task review -- --repo <target-dir>
```

or directly (from anywhere):

```bash
python <suite-root>/scripts/domain_review.py --repo <target-dir>
```

The `scripts/domain_review.py` runner:

1. Resolves the target repo
2. Verifies audit is green (calls `shared.run_phase.run_phase('audit',
   target)`)
3. Loads all relevant spec files into a context buffer
4. Prints the file list and category checklist
5. Hands off to the agent (this skill) to do the qualitative pass
6. Receives the structured report from the agent and writes it to
   `.spec-suite/reviews/<timestamp>.md`

The agent's job is **between steps 5 and 6**: read everything, apply
the five categories, write the report content. The runner does the
mechanical wrapping.

## Report format

The report is markdown, structured for both human scan and machine
parse. Example:

```markdown
# Spec set review — <domain-name>

**Reviewed:** 2026-05-31T15:22:00Z
**Audit state at review:** 17/17 PASS (commit abc123)
**Reviewer:** Claude Code (domain-review skill)
**Suite version:** 1.0.0

## Critical findings

### CRIT-001: <one-sentence problem>
**File + location:** `docs/specifications/contracts/openapi.yaml` line 954
**Problem:** <one-sentence explanation>
**Recommended fix:** <one-sentence fix>

## Important findings

### IMP-001: <one-sentence problem>
...

## Minor findings

- <file>: <one-line note>
- <file>: <one-line note>

## Things checked and OK

- Cross-document enum alignment: 4 lifecycles (Walk, Invoice, Invite,
  PasswordResetToken) consistent across domain-model, openapi, asyncapi.
- Error code coverage: every code in auth-matrix appears in error-catalogue.
- ...

## Decision Log review

<entries that look stale or contradictory, or "all decisions still
match the implementation">

## Summary

<2-3 sentences>: overall health, top thing to fix, any patterns
across findings.
```

The user reads the report, picks findings to fix, edits the spec
files, re-signs the affected phases through the normal update-mode
flow, and (optionally) re-runs the review later to confirm
resolution.

## What this skill never does

- Never edits a spec file.
- Never signs anything off.
- Never invokes a gate.
- Never declares a spec set "ready" or "broken" — that's the user's
  call after reading the findings.
- Never overwrites a previous review report (each run is a new
  timestamped file).
- Never refuses to run on a "good" spec set — if everything's clean,
  the report shows zero findings and lots of "checked and OK"
  entries.

## Files this skill reads

All of:

- `docs/specifications/prd.md`
- `docs/specifications/domain-model.md`
- `docs/specifications/glossary.md`
- `docs/specifications/auth-matrix.md`
- `docs/specifications/error-catalogue.md`
- `docs/specifications/sequence-diagrams.md`
- `docs/specifications/nfr.md`
- `docs/specifications/acceptance-scenarios.md`
- `docs/specifications/contracts/openapi.yaml`
- `docs/specifications/contracts/asyncapi.yaml`
- `docs/specifications/contracts/datacontract.yaml`
- Every `.spec-suite/phases/phase-N-passed.yaml` sidecar (for
  Decision Log entries)
- `.spec-suite/ambiguities.md` (for context on deferrals)

## Files this skill writes

- `.spec-suite/reviews/<ISO-timestamp>.md` — the report.
  Each run produces a new file; old reviews stay for historical
  reference.
