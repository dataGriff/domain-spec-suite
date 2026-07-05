# Gate Version Changelog

Records every bump of `gate-version.yaml` and what changed. Bumping
requires both a manual edit to `gate-version.yaml` AND an entry below.
See `SUITE-DESIGN.md` §10 for the policy.

---

## `1.1` — closure checks (critique-driven hardening)

Driven by the adversarial review of the dog-walking spec set
(`spec-dog-walking/.spec-suite/reviews/2026-07-05T14-48-07Z.md`).
The 1.0 gates validated *mirroring of what exists*; 1.1 adds
*closure* — that what the spec promises is actually reachable,
resolvable, and exercised.

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
existing spec sets signed under 1.0 remain valid; re-audit is opt-in
and the dog-walking set is known to fail 1.1 until its critique
findings are actioned.

---

## `1.0` — initial

The suite ships at gate-version `1.0`. All checks defined in
`SUITE-DESIGN.md` §8 plus the audit-only checks in §8 Phase 7 are
considered the baseline. No prior versions exist.
