# Gate Version Changelog

Records every bump of `gate-version.yaml` and what changed. Bumping
requires both a manual edit to `gate-version.yaml` AND an entry below.
See `SUITE-DESIGN.md` §10 for the policy.

---

## `1.1` — 2026-07-04

Retroactive reconciliation plus one new addition. The checks below
shipped during the v1.0.5–v1.0.13 suite releases and were wired into
the Phase 6 and/or Phase 7 gates at error severity **without** the
gate-version bump §10 requires. This entry records them so spec sets
signed under gate `1.0` know exactly what a re-audit under `1.1` adds.

New checks since gate `1.0`:

- `ENUM-VALUES-CONSISTENT` (suite v1.0.5) — named enums in
  `domain-model.md` `## Enumerations` must match OpenAPI (and
  AsyncAPI/datacontract where declared). Opt-in: silent on domains
  without an `## Enumerations` section.
- `EVENT-PAYLOAD-COVERS-ENTITY-STATE` (suite v1.0.6; aggregate-child
  coverage added in v1.0.8) — events carry full published entity
  state in both the AsyncAPI payload and the datacontract record.
  Opt-in: silent without a `## Domain Events` table.
- `IDEMPOTENCY-KEY-ON-POST-OPS` (suite v1.0.9) — every OpenAPI POST
  declares a required `Idempotency-Key` header parameter.

Changed semantics since gate `1.0`:

- `ENUM-VALUES-CONSISTENT` (suite v1.0.12) — an `(open)` marker on an
  enum heading relaxes strict equality to a subset check (model ⊆
  contract). Closed enums keep strict equality.

New in this bump:

- The Phase 7 audit gate now re-runs the Phase 6 tool lints
  (`SPECTRAL-OPENAPI`, `SPECTRAL-ASYNCAPI`, `DATACONTRACT-LINT`) as
  BUILD-PLAN 2.3 always specified. Each skips where its CLI isn't
  installed.

Why tightening is right: all three additions catch real drift
observed in the dog-walking reference build (thin events, enum
divergence, unsafe retries). An Items-fixture audit under `1.1`
passes; existing spec sets remain valid at `1.0` per §10's
frozen-with-opt-in-re-audit policy.

## `1.0` — initial

The suite ships at gate-version `1.0`. All checks defined in
`SUITE-DESIGN.md` §8 plus the audit-only checks in §8 Phase 7 are
considered the baseline. No prior versions exist.
