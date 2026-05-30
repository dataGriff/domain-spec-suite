---
name: domain-contracts
description: |
  Phase 6. Validates the three contract files
  (`contracts/openapi.yaml`, `contracts/asyncapi.yaml`,
  `contracts/datacontract.yaml`) against tool linters AND against every
  upstream spec (domain model, glossary, auth matrix, error catalogue).
  Hard gate: no warnings, no rubric judgements — every check is
  mechanical and every check must pass for sign-off. The only escape
  is `task suite:force-advance contracts --reason '<text>'`, which the
  audit then surfaces until accepted.
prerequisites:
  - Phases 1-5 have signed off (the contracts gate cross-references
    every prior phase's outputs).
  - Target repo has `spectral` and `datacontract` on PATH (pinned via
    the target's `.mise.toml`; the bootstrap installs that for you).
trigger_phrases:
  - "phase 6"
  - "run the contracts gate"
  - "sign off contracts"
  - "validate the contracts"
---

# Phase 6 — Contracts

This skill is **purely mechanical**. There are no rubric checks and
no question bank — contracts are right or they aren't. The skill's
job is to run the gate against the target repo and either write the
sign-off sidecar (`_phase-6-passed.yaml`) or report exactly which
checks failed.

## What this skill does

1. Resolves the target repo (current working directory by default).
2. Verifies all earlier phases (1-5) have signed off — refuses if not.
3. Invokes the runner (`shared/run_phase.py contracts --repo <target>`)
   which runs every check listed in `gate.yaml`.
4. If every check passes: invokes `shared/sign_off.py contracts` which
   computes sha256s for the three contract files and writes
   `_phase-6-passed.yaml`.
5. If any check fails: reports the failing check ids verbatim. Does
   not write the sign-off file. Tells the user to either fix the
   underlying issues or, in genuine emergencies, run
   `task suite:force-advance contracts --reason '<text>'` (which
   writes a `force_advances` entry to `_progress.yaml` that the audit
   surfaces until cleared via `task suite:accept-force`).

## How to run

From any directory:

```bash
mise exec -- task gate:contracts -- --repo <target-dir>
```

Or directly:

```bash
python <suite-root>/shared/run_phase.py contracts --repo <target-dir>
```

Sign-off (only proceeds if the gate passes):

```bash
python <suite-root>/shared/sign_off.py contracts --repo <target-dir>
```

## Checks in this gate

Listed in `gate.yaml`. Two categories:

- **Tool checks** (subprocess linters; skipped if the tool isn't on
  PATH):
  - `SPECTRAL-OPENAPI` — `spectral lint contracts/openapi.yaml`
  - `SPECTRAL-ASYNCAPI` — `spectral lint contracts/asyncapi.yaml`
  - `DATACONTRACT-LINT` — `datacontract lint contracts/datacontract.yaml`
- **Cross-phase consistency** (shared modules; the audit re-runs the
  same modules at error severity):
  - `ENTITY-IN-OPENAPI-SCHEMA` — domain entity ↔ OpenAPI schema
  - `FIELD-MATCH-DOMAIN-OPENAPI` — attribute names align
  - `WRITE-OP-HAS-ASYNCAPI-CHANNEL` — every write op has an event
  - `EVENT-IN-DATACONTRACT` — every event has a datacontract record
  - `AUTH-MATRIX-OPENAPI-MATCH` — auth-matrix operations ↔ openapi
  - `ERROR-CODE-IN-CATALOGUE` — error codes traced back to catalogue

## What this skill never does

- Never edits a contract file. Contracts are user-authored.
- Never relaxes a check. Every failure is surfaced; the user fixes
  the contract or force-advances.
- Never writes the sign-off file directly. That's
  `shared/sign_off.py`'s sole prerogative — and it refuses unless
  `task gate:contracts` exits 0 (or `--force-advance` is given).

## Files this phase signs

Listed in `gate.yaml` under `signs_files:`:

- `docs/specifications/contracts/openapi.yaml`
- `docs/specifications/contracts/asyncapi.yaml`
- `docs/specifications/contracts/datacontract.yaml`

`shared/sign_off.py` computes sha256 for each and records it in
`_phase-6-passed.yaml`. The audit's `SIGNOFF-SHA256-MATCHES` check
verifies these later.
