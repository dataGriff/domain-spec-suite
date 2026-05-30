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

This skill has two halves: **author** (produce three contract YAML
files from upstream specs) and **validate + sign-off** (mechanical
gate against the result). The validate half is purely mechanical —
contracts are right or they aren't, no rubric checks. The author half
is interactive: the skill reads upstream specs and walks the user
through filling in the templates.

## What this skill does

1. Resolves the target repo (current working directory by default).
2. Verifies all earlier phases (1-5) have signed off — refuses if not.
3. **Author half.** If any of `contracts/openapi.yaml`,
   `contracts/asyncapi.yaml`, `contracts/datacontract.yaml` is missing,
   runs `task init:contracts -- --repo <target>` to copy the blank
   `_template/contracts/*.yaml` skeletons into place. Never
   overwrites existing files (the user's authored work is safe).
   Then walks the user through populating each section using the
   upstream specs as the source of truth (see "Authoring" below).
4. **Validate half.** Invokes the runner
   (`shared/run_phase.py contracts --repo <target>`), which runs
   every check listed in `gate.yaml`.
5. If every check passes: invokes `shared/sign_off.py contracts`
   which computes sha256s for the three contract files and writes
   `_phase-6-passed.yaml`.
6. If any check fails: reports the failing check ids verbatim. Does
   not write the sign-off file. Tells the user to either fix the
   underlying issues or, in genuine emergencies, run
   `task suite:force-advance contracts --reason '<text>'` (which
   writes a `force_advances` entry to `_progress.yaml` that the audit
   surfaces until cleared via `task suite:accept-force`).

## Authoring

The three contracts are largely *derivable* from upstream specs — the
job is mechanical synthesis, not creative writing. Walk the user
through each contract in order. Reflect each significant edit back
to the user before committing it (per SUITE-DESIGN §7 Hard Rule 3).

### `contracts/openapi.yaml`

- **`info`**: title from the PRD's domain name; version starts at
  `1.0.0`; contact uses the RFC 2606 example-domain pattern for
  Spectral's `info-contact` rule.
- **`paths`**: one path per row in `auth-matrix.md`'s operations
  table. Method, path, and rough operationId are all there.
- **`components.schemas`**: one schema per entity in
  `domain-model.md`, with one property per attribute. Use the type
  hints from the domain-model attribute table (`UUID` → `string` +
  `format: uuid`, `ISO 8601` → `string` + `format: date-time`,
  enum strings → `enum`). Sensitive attributes (e.g. password hashes)
  belong in a `<Entity>Summary` projection, not the bare entity.
- **`components.responses`**: one entry per `4xx`/`5xx` code from
  `error-catalogue.md`, all bound to a generic `Error` shape
  (`{code, message}`) plus `ValidationError` for 400 (which
  additionally has `details[]`).

### `contracts/asyncapi.yaml`

- **`channels`**: one channel per domain event row in
  `domain-model.md`'s Domain Events table. Channel name comes from
  the table directly (e.g. `items.item.added`).
- **`components.messages`**: one message per channel. CloudEvents 1.0
  envelope (`specversion`, `type`, `source`, `id`, `time`,
  `datacontenttype`) wrapping a `data` payload that matches the
  entity's domain-model attributes.
- **`info.contact`**: same RFC 2606 example values as openapi.yaml.

### `contracts/datacontract.yaml`

- **`schema[*]`**: one record per *family* of channels (typically
  one per entity, plus reduced-payload variants for removal events).
  Field names + types come straight from the AsyncAPI message
  payload.
- **`slaProperties`**: `availability` and `retention` come from
  `nfr.md` (NFR-AVAIL-002, NFR-DATA-001 in the Items example).

After every contract section, run `task gate:contracts -- --repo
<target>` to surface lint and cross-reference errors early. Iterate
until clean, then sign off.

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
