---
name: domain-discovery
description: |
  Phase 1. Drives Product Requirements Document (`prd.md`) authoring
  by interviewing the user against a structured question bank
  (`questions.md`). Hard gate: 8 structural checks + 2 rubric checks
  must all be resolved before sign-off. The PRD is the foundational
  spec — every later phase derives from it.
prerequisites:
  - Phase 0 (bootstrap) has signed off — `.spec-suite/phases/phase-0-passed.yaml` exists
    and lists `docs/specifications/prd.md` (the template) among its
    expected files.
trigger_phrases:
  - "phase 1"
  - "start discovery"
  - "draft the prd"
  - "sign off discovery"
  - "begin domain"
---

# Phase 1 — Discovery

This skill has two halves: **author** (walk the user through writing
the PRD via the question bank) and **validate + sign-off** (mechanical
gate against the result). Discovery is the only phase that starts from
zero — there are no upstream specs to derive from, so authoring is
purely conversational.

## What this skill does

1. Resolves the target repo (current working directory by default).
2. Verifies Phase 0 (bootstrap) has signed off — refuses if not.
3. **Author half.** If `docs/specifications/prd.md` doesn't exist,
   runs `task init:discovery -- --repo <target>` to copy the blank
   `.spec-suite/templates/prd.md` skeleton into place. Never overwrites existing
   files. Then walks the user through populating each section using
   `questions.md` as the elicitation script (see "Authoring" below).
4. **Validate half.** Invokes the runner
   (`shared/run_phase.py discovery --repo <target>`) which runs every
   structural check listed in `gate.yaml`.
5. **Rubric pass.** Reads the prose rubric below against the current
   `prd.md` and emits findings (`pass` or `warn`) with the rubric ids
   listed below. Findings are surfaced to the user; each `warn` must
   be resolved, deferred (with reason and required-by phase), or
   marked non-applicable (with reason) before sign-off proceeds.
6. If every structural check passes AND every rubric `warn` has a
   response: invokes `shared/sign_off.py discovery` which computes
   sha256 for `prd.md` and writes `.spec-suite/phases/phase-1-passed.yaml`.
7. If any structural check fails: looks up the question by
   `binds_to_check` in `questions.md`, runs the §5 interview loop,
   re-runs affected checks, repeats until clean.

## Authoring

Discovery is interview-driven. The agent reads `questions.md` once at
start and indexes by `binds_to_check`. When a check fails (or, on a
blank PRD, every check fails), the agent picks the highest-priority
failure and walks the question entry:

1. Ask `lead_in` — the opening business-language interview question.
2. Receive the user's answer.
3. If the answer is vague, walk the `probes` in order — one probe per
   turn (§7 Hard Rule 1). After two probes, route to defer or mark
   non-applicable.
4. When the answer is concrete, render `reflect_template` against it
   and ask for confirmation (§7 Hard Rule 3) — never write to file
   silently after a free-text answer.
5. On confirmation, write the edit into `prd.md`. Re-run the affected
   check.
6. Loop until the gate is green.

Section-by-section ordering is the natural one:

| Order | Section | Driver checks |
| --- | --- | --- |
| 1 | Problem Statement | PRD-PROBLEM-USER-PAIN + rubric |
| 2 | Target Users / Personas | PRD-PERSONA-EXISTS, -GOAL, -FRUSTRATION |
| 3 | Goals + Non-Goals | PRD-NON-GOAL |
| 4 | User Stories | PRD-STORY-ACCEPTANCE, PRD-STORY-PERSONA-LINK |
| 5 | Constraints | (no gate check — capture for downstream) |
| 6 | Success Metrics | PRD-METRICS-MEASURABLE + rubric |

For a brand-new domain expect 30–60 minutes of focused interview —
roughly one session. Resumption is supported (see Section 6 of
SUITE-DESIGN); the orchestrator detects an in-progress phase from
`.spec-suite/progress.yaml` and re-enters this skill where it left off.

## Rubric checks

Two rubric judgements live here as prose (per SUITE-DESIGN §5.5).
Read the prose against the current `prd.md` and emit a finding for
each rubric id below with `verdict: pass` or `verdict: warn` plus a
short detail. Findings go into `.spec-suite/phases/phase-1-passed.yaml` under
`rubric_findings:` via the sign-off engagement loop — each `warn`
needs an explicit response (resolved, deferred-with-required-by, or
n-a-with-reason) before sign-off completes.

### RUBRIC-PROBLEM-USER-PAIN

> The Problem Statement should describe **user pain**, not the
> solution shape.

**Pass when:** The statement opens with what specifically goes wrong
for the user today — the moment in their day where current tools fail
them, in concrete language a colleague would recognise. The solution
(your domain) may appear later in the section, but the *opening*
frames the pain.

**Warn when:** The statement leads with what's being built ("we are
building an X that..."), or with a market-category description ("the
team productivity space lacks..."), or with generic feelings ("users
want efficiency"). In each case the user pain is implicit or absent
and the statement reads as a pitch rather than a problem.

When emitting a `warn`, name the specific phrasing that misses (the
opening sentence quoted) and what concrete user moment is missing.

### RUBRIC-METRICS-MEASURABLE

> Success metrics should be **measurable and realistic**, not
> aspirational.

**Pass when:** Each metric pairs a concrete signal (a number, a
validated check, a count) with the conditions under which it would be
measured. The reader can imagine, six months in, asking "did we hit
this?" and getting a yes/no answer.

**Warn when:** A metric reduces to a feeling ("users love it") or a
direction without a target ("adoption grows") or a number with no
unit/window ("hit 10"). The `PRD-METRICS-MEASURABLE` structural check
catches the most obvious cases (no digit, no measurable verb) — this
rubric is the second pass for metrics that look measurable but
aren't actually checkable.

When emitting a `warn`, quote the metric verbatim and ask the user
what specific number or check would prove it was met.

## How to run

From any directory:

```bash
# Lay down the blank PRD template if it doesn't exist yet
mise exec -- task init:discovery -- --repo <target-dir>

# Validate (no side-effects beyond the runner's exit code)
mise exec -- task gate:discovery -- --repo <target-dir>

# Sign off (refuses if the gate fails)
mise exec -- task sign-off:discovery -- --repo <target-dir>
```

Or directly:

```bash
python <suite-root>/scripts/init_phase.py discovery --repo <target-dir>
python <suite-root>/shared/run_phase.py discovery --repo <target-dir>
python <suite-root>/shared/sign_off.py discovery --repo <target-dir>
```

## Checks in this gate

Listed in `gate.yaml`. All structural (one cross-reference). No tool
checks — Discovery touches only `prd.md`.

- `PRD-PROBLEM-USER-PAIN` — Problem Statement is non-empty and
  substantive (not a placeholder TODO)
- `PRD-PERSONA-EXISTS` — at least one real persona declared
- `PRD-PERSONA-GOAL` — every persona has a non-trivial Goal
- `PRD-PERSONA-FRUSTRATION` — every persona has a non-trivial Frustration
- `PRD-NON-GOAL` — at least one explicit non-goal
- `PRD-STORY-ACCEPTANCE` — every `US-N` story has real acceptance
  criteria (not all `- [ ] TODO`)
- `PRD-STORY-PERSONA-LINK` — every story's `**As a** <actor>,` names
  a declared persona, a known role, or a recognised pre-onboarding
  actor (cross-reference)
- `PRD-METRICS-MEASURABLE` — every success metric contains a number
  or measurable verb

## What this skill never does

- Never edits `prd.md` without confirmation (per §7 Hard Rule 3).
- Never relaxes a check or rubric. The only escape is
  `task suite:force-advance discovery --reason '<text>'`, which the
  audit surfaces until accepted.
- Never writes the sign-off file directly. That's
  `shared/sign_off.py`'s sole prerogative — and it refuses unless
  `task gate:discovery` exits 0 (or `--force-advance` is given).
- Never speaks check ids to the user (per §7 Hard Rule 10). Failures
  are interview questions; check ids are an internal-engineering
  concept.

## Files this phase signs

Listed in `gate.yaml` under `signs_files:`:

- `docs/specifications/prd.md`

`shared/sign_off.py` computes sha256 and records it in
`.spec-suite/phases/phase-1-passed.yaml`. The audit's `SIGNOFF-SHA256-MATCHES` check
verifies it later; any post-sign-off edit to the PRD marks discovery
stale until it's re-signed.
