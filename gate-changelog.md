# Gate Version Changelog

Records every bump of `gate-version.yaml` and what changed. Bumping
requires both a manual edit to `gate-version.yaml` AND an entry below.
See `SUITE-DESIGN.md` §10 for the policy.

---

## `1.3` — 2026-07-06 — FIELD-MATCH skips `[secret]` attributes

Found while actioning the dog-walking critique's L5 under gate 1.2.
`FIELD-MATCH-DOMAIN-OPENAPI` used the raw attribute parser, so a
`[secret]`-marked model attribute (a password hash, an opaque token)
was *required* to appear as a property of the entity's OpenAPI
schema — forcing contracts to advertise fields the API must never
return, precisely what the marker exists to prevent.

Changed semantics:

- `FIELD-MATCH-DOMAIN-OPENAPI` now uses
  `domain_model_published_attributes` (the `[secret]`-stripping
  parser `EVENT-PAYLOAD-COVERS-ENTITY-STATE` already uses), so
  `[secret]` attributes are exempt from the model→OpenAPI direction.
  Request schemas may still take secret inputs (e.g. `password` on a
  register request) — this check only inspects entity schemas.

Pure loosening: every spec set green under `1.2` stays green under
`1.3`. The Items fixture is unaffected (its `User` is represented by
`UserSummary`, which FIELD-MATCH never keyed on).

---

## `1.2` — 2026-07-05 — closure checks (critique-driven hardening)

Driven by the adversarial review of the dog-walking spec set
(`spec-dog-walking/.spec-suite/reviews/2026-07-05T14-48-07Z.md`).
The gates through `1.1` validated *mirroring of what exists*
(enum equality, channel-per-event); `1.2` adds *closure* — that
what the spec promises is actually reachable, resolvable, and
exercised.

New checks:

- `ERROR-CODE-REPRESENTABLE` (contracts, audit — error): every
  catalogue code's documented status is declared by ≥1 operation,
  and (where response schemas enumerate `code` values) the code is
  admitted by ≥1 schema bound at that status.
- `OPERATION-HAS-SCENARIO` (contracts, audit — error): every OpenAPI
  operation is exercised by ≥1 acceptance scenario.
- `SCENARIO-REFS-VALID` (contracts, audit — error): scenario
  endpoints, error codes, enum literals (2xx scenarios only), and
  event types are legal against the contracts.
- `EVENT-FK-RESOLVABLE` (contracts, audit — error): entity-named FKs
  in datacontract records resolve to a record publishing that entity.
- `DATACONTRACT-REFS-RESOLVE` (contracts, audit — error): every
  datacontract ref resolves to a real openapi schema.
- `ENTITY-HAS-EVENT` (modeling — warning; audit — error): every
  non-aggregate-child entity appears in the Domain Events table.

Changed semantics:

- `NO-TEMPLATE-PLACEHOLDERS` also flags `TODO`/`TBD`/`FIXME` in spec
  files.
- Datacontract record-candidate resolution ranks entity-qualified
  names before the bare domain name, so multi-entity domains resolve
  per-entity records (affects `EVENT-IN-DATACONTRACT` and
  `EVENT-PAYLOAD-COVERS-ENTITY-STATE`).

The Items fixture was upgraded to the new bar (it failed
`ENTITY-HAS-EVENT` for `User`, exactly the class the check exists to
catch): `UserRegistered` event + `items.user.registered` channel +
`user` datacontract record, with `password` `[secret]`-marked. This
is the intended outcome of the tightening, per SUITE-DESIGN §10 —
existing spec sets signed under earlier gate versions remain valid;
re-audit is opt-in and the dog-walking set is known to fail 1.2
until its critique findings are actioned.

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

---

## `1.0` — initial

The suite ships at gate-version `1.0`. All checks defined in
`SUITE-DESIGN.md` §8 plus the audit-only checks in §8 Phase 7 are
considered the baseline. No prior versions exist.
