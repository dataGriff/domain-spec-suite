---
name: domain-conformance-audit
description: |
  Phase 7. Read-only audit that re-runs every cross-reference check
  defined across phases 1-6 plus a set of audit-only checks (template
  placeholders, sign-off integrity, force-advance acceptance, ambiguity
  resolution, generator cleanliness). Invoked by the orchestrator at
  the end of the suite walk, or directly via `task audit` against an
  existing spec set. The audit is the gate that gives the soft middle
  gates teeth — a spec set isn't "complete" until it passes.
prerequisites:
  - Target directory has been bootstrapped (Phase 0 sidecar exists).
  - All phases 1-6 expected to have signed off (otherwise the cross-
    reference checks will report missing inputs).
trigger_phrases:
  - "run the audit"
  - "audit this spec set"
  - "phase 7"
  - "is the spec set complete?"
---

# Phase 7 — Conformance Audit

This skill is **purely mechanical**. It runs a Python check runner
against a target repo and reports the results. There are **no rubric
checks** at this phase — every preceding phase has already had its
rubric findings recorded; the audit re-verifies the mechanical
guarantees.

## What this skill does

1. Resolves the target repo (current working directory by default).
2. Verifies Phase 0 (`.spec-suite/bootstrap.yaml`) is present — if not, refuses
   and tells the user to run the `domain-bootstrap` skill first.
3. Invokes `shared/run_phase.py audit --repo <target>`.
4. Renders the structured report the runner produces (pass/fail per
   check, with interview-style failure messages per §7 Hard Rule 10).
5. If exit code is 0: announces *"Audit passed. Spec set is complete
   under suite version X / gate version Y."*
6. If exit code is non-zero: reports the failing check ids and their
   messages verbatim. **Does not attempt to auto-fix anything** —
   every failure is a deliberate user decision about which phase to
   re-run or which content to amend.

## How to run

From any directory:

```bash
python <suite-root>/shared/run_phase.py audit --repo <target-dir>
```

Or via the suite's Taskfile (works from inside the suite repo):

```bash
task audit -- --repo <target-dir>
```

`<target-dir>` defaults to the current working directory if omitted.

## What this skill never does

- Never edits any file in the target repo.
- Never relaxes a failing check. Every check failure is surfaced
  verbatim; the user decides what to do about it.
- Never bypasses a check. The only escape hatch for a stuck check is
  `task suite:force-advance <phase> --reason '<text>'`, which writes
  an entry to `.spec-suite/progress.yaml` that the audit then surfaces as a
  finding until accepted via `task suite:accept-force`.

## Checks the audit runs

Listed in `gate.yaml`. Categories:

- **Audit-only** — checks that exist only at audit time:
  - `NO-TEMPLATE-PLACEHOLDERS`
  - `SIGNOFF-SHA256-MATCHES`
  - `FORCE-ADVANCES-ALL-ACCEPTED`
  - `AMBIGUITIES-NO-AUDIT-REQUIRED`
  - `GENERATOR-CLEAN-OUTPUT`
- **Cross-phase re-runs** — same modules that earlier phases ran;
  re-run here at error severity:
  - `ENTITY-IN-GLOSSARY`
  - `ENTITY-IN-OPENAPI-SCHEMA`
  - `FIELD-MATCH-DOMAIN-OPENAPI`
  - `WRITE-OP-HAS-ASYNCAPI-CHANNEL`
  - `EVENT-IN-DATACONTRACT`
  - `AUTH-MATRIX-OPENAPI-MATCH`
  - `ERROR-CODE-IN-CATALOGUE`
  - `PRD-STORY-PERSONA-LINK`
  - `LIFECYCLE-IN-FLOWS`

Each check lives in `shared/checks/<id>.py` and exposes a `metadata`
dict + `run(repo_root)` function per SUITE-DESIGN §5.5.

## Reporting style

The runner prints, for each check:

- `PASS  <CHECK-ID>` on success
- `SKIP  <CHECK-ID> — <reason>` if prerequisites aren't met
- `FAIL  <CHECK-ID>` followed by the interview-style message and any
  supporting details

End with a summary: `N passed, M failed, K skipped`.

Pass this output to the user verbatim — don't paraphrase. The wording
is deliberate and pre-tested against the §7 prompting rules.
