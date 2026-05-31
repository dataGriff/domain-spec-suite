---
name: domain-nfrs
description: |
  Phase 5. Drives `nfr.md` and `acceptance-scenarios.md` authoring.
  Soft + engagement gate. One warning (NFR threshold not numeric) and
  one hard check (acceptance scenarios use When/Then) plus one rubric
  (RUBRIC-NFR-REALISTIC) evaluated against the prose. Push-back on
  vague thresholds is the heart of this phase — most spec sets ship
  with aspirational NFRs unless someone actively forces numbers.
prerequisites:
  - Phase 1 (discovery) signed off — for the user stories that
    acceptance scenarios cover.
trigger_phrases:
  - "phase 5"
  - "start nfrs"
  - "draft the nfrs"
  - "draft acceptance scenarios"
  - "sign off nfrs"
---

# Phase 5 — Non-Functional Requirements

Produces two files:

- `nfr.md` — Quantified thresholds (latency, uptime, throughput,
  security defaults, observability hooks, compatibility policy).
- `acceptance-scenarios.md` — Given/When/Then scenarios at the
  contract level, one or more per user story.

## What this skill does

1. Verifies discovery has signed off.
2. **Author half.** If either file is missing, runs
   `task init:nfrs -- --repo <target>`. Then walks the user through:
   - NFRs grouped by category (Performance, Availability,
     Throughput, Security, Observability, Data, Compatibility)
   - One scenario per user story (or more for stories with multiple
     outcomes — success, validation error, permission error)
3. **Validate half.** Hard error: every scenario has When + Then.
   Warning: every NFR has a measurable threshold (numbers,
   percentages, time units, pXX percentiles).
4. **Rubric pass.** Evaluate the prose rubric (below) against the
   current `nfr.md` and emit findings (`pass` or `warn` per NFR or
   per category, the agent's call). The soft-gate engagement loop
   carries them through to sign-off.
5. **Sign off.** Same shape as the other soft-gate phases.

## Authoring

This is the phase with the highest push-back rate. Most users come in
with NFRs like "the API should be fast" or "the system should be
scalable", and the skill's job is to extract numbers.

Suggested order:

| Order | Group | Typical NFRs |
|---|---|---|
| 1 | Performance | p95 read latency, p95 write latency, p99 worst case |
| 2 | Availability | uptime %, event-delivery % |
| 3 | Throughput | steady-state rps, peak burst rps |
| 4 | Security | token lifetime, password-hash cost (in time) |
| 5 | Observability | log levels, what each event records, latency metrics |
| 6 | Data | retention, durability, PII-handling policy |
| 7 | Compatibility | backwards-compat policy for the OpenAPI contract |

Acceptance scenarios should be one per user-story-outcome pair:

- US-001 success → Scenario US-001-A
- US-001 validation error → Scenario US-001-B
- US-001 duplicate-email rejection → Scenario US-001-C
- ... etc.

Use `Given` for required preconditions; omit it for stateless
scenarios (the check accepts When + Then alone).

## Rubric checks

### RUBRIC-NFR-REALISTIC

> NFR thresholds should be **realistic and concrete**, not
> aspirational.

**Pass when:** Each numeric NFR's threshold is justified — either by
prior production data, by a stated load profile, or by an explicit
trade-off note ("p95 200ms allows a 50ms head-of-line buffer on top
of the 150ms ceiling"). The reader can plausibly imagine an
implementation hitting these numbers, and reviewers in six months
won't be left wondering where the targets came from.

**Warn when:** Numbers appear but feel pulled from thin air ("p95
50ms" with no load profile, "99.999%" uptime with no SLA-justifying
context, "10 000 rps" without any sizing rationale). Or numbers are
absent and the NFR is genuinely aspirational ("the system shall be
fast") — though the structural check catches the worst of those.

When emitting `warn`, name the specific NFR id and the missing
context (the load profile, the rationale, the source) and ask the
user to either tighten the numbers or add the context.

## Soft-gate engagement loop

Same shape as the other M5 phases. Each warning needs `response`
(resolved / deferred / n-a) plus a `reason`. The NFR threshold
warning is common; typical responses:

- **resolved** — added numeric threshold per the question's probe
- **n-a** — the NFR is a behavioural guarantee, not threshold-bearing
  (e.g. "no field is removed within a major version")
- **deferred** — the threshold can't be set yet; move the entry to
  `.spec-suite/ambiguities.md` with `required_by: <phase>` and mark this
  warning n-a with reason "moved to ambiguities"

## How to run

```bash
mise exec -- task init:nfrs -- --repo <target-dir>
mise exec -- task gate:nfrs -- --repo <target-dir>
mise exec -- task sign-off:nfrs -- --repo <target-dir> --findings <yaml>
```

Findings YAML:

```yaml
warnings_responded:
  - id: NFR-THRESHOLD-MEASURABLE
    response: n-a
    reason: "NFR-DATA-002 is a deliberate non-requirement (no durability); behavioural, not threshold-bearing"
rubric_findings:
  - id: RUBRIC-NFR-REALISTIC
    verdict: pass
    detail: "every performance NFR cites the steady-state load profile from NFR-PERF-001"
    response: resolved
    reason: "agent verdict accepted"
```

## Checks in this gate

### Hard errors

- `ACCEPTANCE-SCENARIO-GWT` — every scenario has When + Then in a
  ```gherkin block

### Warnings

- `NFR-THRESHOLD-MEASURABLE` — every NFR has a digit / percentage /
  time / percentile token (otherwise must be marked n-a with reason)

### Rubrics (in SKILL.md prose, emitted via engagement loop)

- `RUBRIC-NFR-REALISTIC` — numbers are realistic, not aspirational

## Decision Log

Per SUITE-DESIGN §5.5 Decision Log. NFRs concentrate semantic
choices that no check can validate (every number is a judgement
call). Emit `decisions:` for the load-bearing ones:

```yaml
decisions:
  - id: AVAIL-TARGET-99.5
    summary: "Set NFR-AVAIL-001 API uptime to 99.5% (not 99.9%)."
    rationale: "Realistic single-walker SaaS target — 99.9% costs
      meaningfully more without proportional value at this scale."
    affects: [docs/specifications/nfr.md]
```

### Decision-prone areas in this phase

- **Load profile assumptions** baked into latency / throughput
  numbers. What workload shape were the thresholds set against?
- **Retention windows** for events, photos, invoices, logs. What
  regulatory or operational basis drove the choice?
- **Availability targets.** 99.5% vs 99.9% vs 99.99% are all
  defensible; the choice trades cost for resilience.
- **Rate-limit policy.** Where, how strict, what window?
- **Token lifetimes** (access vs refresh). Trade-off between
  security and re-login friction.
- **Behavioural NFRs marked n-a** on `NFR-THRESHOLD-MEASURABLE`.
  Each n-a is a judgement that this NFR is qualitative; record
  why.

## What this skill never does

- Never accepts vague qualitative language ("fast", "scalable",
  "robust") in nfr.md without explicit user push-back via the
  measurability question.
- Never writes a scenario without explicit user confirmation of the
  When + Then steps.

## Files this phase signs

- `docs/specifications/nfr.md`
- `docs/specifications/acceptance-scenarios.md`
