---
name: domain-openapi
description: |
  Authoring conventions for `contracts/openapi.yaml` (OpenAPI
  3.0.3). Invoked from `domain-contracts` (Phase 6) when the
  user is drafting or refining the REST surface. This skill does
  not run any gate of its own — the lint check
  (`SPECTRAL-OPENAPI`) and every cross-reference check
  (entity-in-schema, field-match-domain, auth-matrix-match,
  idempotency-key-on-post, error-code-in-catalogue) are owned by
  `domain-contracts`.
prerequisites:
  - Phases 1-5 have signed off (operations, entities, roles,
    error codes, NFRs are the inputs).
  - Target repo has `spectral` on PATH (pinned via `.mise.toml`).
trigger_phrases:
  - "openapi authoring"
  - "draft the openapi contract"
  - "openapi conventions"
---

# `contracts/openapi.yaml` — Authoring

OpenAPI 3.0.3. The job is **mechanical synthesis** from upstream
specs, not creative writing. Walk the user through each section
in order; reflect each significant edit back before committing
it (per SUITE-DESIGN §7 Hard Rule 3).

## Sections

- **`info`**: title from the PRD's domain name; version starts
  at `1.0.0`; contact uses the RFC 2606 example-domain pattern
  for Spectral's `info-contact` rule.
- **`paths`**: one path per row in `auth-matrix.md`'s operations
  table. Method, path, and rough `operationId` are all there.
  `operationId` uses business verbs per the SUITE convention
  (`addDog`, `scheduleWalk`) rather than CRUD verbs.
- **`components.schemas`**: one schema per entity in
  `domain-model.md`, with one property per attribute. Use the
  type hints from the domain-model attribute table:
  - `UUID` → `string` + `format: uuid`
  - `ISO 8601` → `string` + `format: date-time`
  - `enum:<Name>` → `$ref: '#/components/schemas/<Name>'`

  Sensitive attributes (e.g. password hashes) belong in a
  `<Entity>Summary` projection, not the bare entity.
- **Named enums** declared in `domain-model.md`'s
  `## Enumerations` section MUST also appear under
  `components.schemas` as `<Name>: {type: string, enum: [...]}`
  with values matching the model exactly.
  `ENUM-VALUES-CONSISTENT` enforces this. The same schema name
  in AsyncAPI + Datacontract must match too (if declared at all).
- **`components.responses`**: one entry per `4xx`/`5xx` code from
  `error-catalogue.md`, all bound to a generic `Error` shape
  (`{code, message}`) plus `ValidationError` for 400 (which
  additionally has `details[]`).
- **`info.contact`**: same RFC 2606 example values as
  asyncapi.yaml.

## Idempotency-Key on every POST

(Per SUITE-DESIGN §4.6 "Idempotent Mutating Ops" and the suite
v1.0.9 convention.)

Declare a reusable parameter under
`components.parameters.IdempotencyKey` and `$ref` it from every
POST operation's `parameters` list:

```yaml
components:
  parameters:
    IdempotencyKey:
      name: Idempotency-Key
      in: header
      required: true
      description: >
        Client-generated UUID per intent. Lets the server replay
        the original response on retry.
      schema:
        type: string
        format: uuid
```

Then on every POST op:

```yaml
paths:
  /v1/walks:
    post:
      operationId: scheduleWalk
      parameters:
        - $ref: '#/components/parameters/IdempotencyKey'
      ...
```

Add an `IDEMPOTENCY_KEY_CONFLICT` (409) row to the error
catalogue for the same-key-different-body case. POST is the only
verb that creates new state from scratch; without an idempotency
key, a retried POST produces duplicates. PUT/PATCH/DELETE are
verb-idempotent so the header is **optional** there. The
`IDEMPOTENCY-KEY-ON-POST-OPS` check (owned by `domain-contracts`)
enforces this convention.

Server-side replay-store implementation is a runtime concern
(typical: a Redis or Postgres TTL table at ~24h); not gated by
the suite.

## Authoring-time validation

After every significant section change, run the gate from the
target repo to surface lint and cross-reference errors early:

```bash
task gate:contracts
```

Iterate until clean, then return to `domain-contracts` for
Phase 6 sign-off.

## Decision-prone areas

These choices have no mechanical check; surface them through
the Decision Log when the user makes them:

- **Pagination defaults and caps.** Where `pageSize` maxima sit
  and why.
- **Enum extension policy.** Closed enums vs open ("MUST be one
  of X, MAY add Y in minor versions"). Often pinned by
  NFR-COMPAT but the decision is recorded here too.
- **Photo / file upload model.** Direct upload (multipart) vs
  URL vs signed-URL flow.
- **Currency / units.** `priceCents` (integer minor units) vs
  decimal vs string. Locks every downstream implementation.
- **Token / session lifetime in OpenAPI responses.** Whether
  tokens are exposed as opaque strings or with explicit expiry
  claims in the response shape.
