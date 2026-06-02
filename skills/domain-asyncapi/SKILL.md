---
name: domain-asyncapi
description: |
  Authoring conventions for `contracts/asyncapi.yaml` (AsyncAPI
  2.6, CloudEvents 1.0 envelope). Invoked from `domain-contracts`
  (Phase 6) when the user is drafting or refining the event
  surface. This skill does not run any gate of its own — the
  lint check (`SPECTRAL-ASYNCAPI`) and every cross-reference
  check (write-op-has-channel, event-in-datacontract,
  event-payload-covers-entity-state, enum-values-consistent) are
  owned by `domain-contracts`.
prerequisites:
  - Phases 1-5 have signed off (entities + events table + NFRs
    are the inputs).
  - Target repo has `spectral` on PATH (pinned via `.mise.toml`).
trigger_phrases:
  - "asyncapi authoring"
  - "draft the asyncapi contract"
  - "event payload conventions"
---

# `contracts/asyncapi.yaml` — Authoring

AsyncAPI 2.6 wrapping a CloudEvents 1.0 envelope. The contract
is **derived** from the `## Domain Events` table in
`domain-model.md` and the entity tables. Walk the user through
each section; reflect each significant edit back before
committing it.

## Sections

- **`channels`**: one channel per domain event row. Channel name
  comes from the table directly (e.g. `items.item.added`,
  `dogwalking.walk.completed`). Convention is
  `<domain>.<entity-slug>.<lifecycle-action>`.
- **`components.messages`**: one message per channel.
  CloudEvents 1.0 envelope (`specversion`, `type`, `source`,
  `id`, `time`, `datacontenttype`) wrapping a `data` payload.
- **`info.contact`**: same RFC 2606 example values as
  openapi.yaml.

## Events carry full domain state

(Per SUITE-DESIGN §4.5 — load-bearing principle.)

Every event payload's `data` carries the **full state of the
affected entity at the moment of the event** — every required
attribute from the model's entity table (minus those tagged
`[secret]`). This is what makes the data contract an audit-grade
historic record: a downstream consumer can reconstruct what
happened from the event stream alone, without re-querying the
live API.

Thin events (payloads with only identifiers) are an
anti-pattern. `EVENT-PAYLOAD-COVERS-ENTITY-STATE` (owned by
`domain-contracts`) enforces presence at Phase 6 + audit.

**Removal events** (action ∈ `removed` / `deleted` / `expired`)
are exempt: the entity is gone, so a minimal payload (id +
timestamp) is the right shape.

## Aggregate roots carry their children

(Per SUITE-DESIGN §4.5 and the suite v1.0.8 convention.)

When the affected entity is declared in `domain-model.md`'s
`## Aggregates` section, the event payload MUST carry every
declared child collection in the same payload. The payload's
`data.<collection>` is an array of objects whose item schema
covers the child's published attributes:

```yaml
components:
  schemas:
    RateCardEntryPayload:
      type: object
      required: [id, rateCardId, walkType, durationMinutes, priceCents, ...]
      properties:
        id: { type: string, format: uuid }
        rateCardId: { type: string, format: uuid }
        walkType: { type: string }
        ...

    RateCardUpdatedEnvelope:
      allOf:
        - $ref: '#/components/schemas/CloudEventsBase'
        - type: object
          properties:
            data:
              type: object
              required: [rateCardId, walkerId, currency, ..., entries]
              properties:
                rateCardId: { type: string, format: uuid }
                ...
                entries:
                  type: array
                  items: { $ref: '#/components/schemas/RateCardEntryPayload' }
```

Both events on an aggregate root carry the children — e.g.
`InvoiceIssued` AND `InvoicePaid` both carry `lineItems`, since
they're both events on the same aggregate.

## Named enum alignment

Named enums declared in `domain-model.md`'s `## Enumerations`
section must use the same values in any payload field that
references them. If an asyncapi schema declares the enum
inline, values must match openapi.yaml + datacontract.yaml.
`ENUM-VALUES-CONSISTENT` enforces this.

## Tools

Bootstrap-installed tasks for AsyncAPI authoring:

- **`task asyncapi:skeleton`** — derives a complete asyncapi.yaml
  skeleton from `domain-model.md`'s events table + entities +
  `## Aggregates` + `## Enumerations`. One channel per event,
  CloudEvents envelope wired, full-state payloads, aggregate
  children carried via `$ref` to per-child payload schemas.
  Removal events get the minimal id+timestamp payload. Idempotent
  (refuses to overwrite a real asyncapi.yaml unless `--force`).
- **`task lint:asyncapi`** — Spectral against the suite's
  `.spectral-asyncapi.yaml` ruleset.
- **`task lint:fix-descriptions`** — auto-inserts `description:`
  lines on every `operationId:` that lacks one. Run after the
  skeleton.
- **`task gate:contracts`** — runs the full Phase 6 gate.

## Worked YAML patterns

### CloudEvents envelope (declared once, allOf-extended)

```yaml
components:
  schemas:
    CloudEventsBase:
      type: object
      required: [specversion, type, source, id, time, datacontenttype]
      properties:
        specversion: { type: string, const: '1.0' }
        type: { type: string }
        source: { type: string, format: uri-reference }
        id: { type: string, format: uuid }
        time: { type: string, format: date-time }
        datacontenttype: { type: string, const: application/json }
```

### Full-state event payload (single entity)

```yaml
DogAddedEnvelope:
  allOf:
    - $ref: '#/components/schemas/CloudEventsBase'
    - type: object
      required: [data]
      properties:
        data:
          type: object
          required: [dogId, name, breed, ownerId, createdAt, updatedAt]
          properties:
            dogId: { type: string, format: uuid }
            name: { type: string }
            breed: { $ref: '#/components/schemas/Breed' }
            ownerId: { type: string, format: uuid }
            createdAt: { type: string, format: date-time }
            updatedAt: { type: string, format: date-time }
```

Note: model's `id` becomes `<entity>Id` in payloads
(`Dog.id` → `dogId`). The check accepts either.

### Aggregate-root event carrying its children

```yaml
RateCardEntryPayload:
  type: object
  required: [id, rateCardId, walkType, durationMinutes, priceCents, createdAt, updatedAt]
  properties:
    id: { type: string, format: uuid }
    rateCardId: { type: string, format: uuid }
    walkType: { type: string }
    durationMinutes: { type: integer, minimum: 1 }
    priceCents: { type: integer, minimum: 1 }
    createdAt: { type: string, format: date-time }
    updatedAt: { type: string, format: date-time }

RateCardUpdatedEnvelope:
  allOf:
    - $ref: '#/components/schemas/CloudEventsBase'
    - type: object
      required: [data]
      properties:
        data:
          type: object
          required: [rateCardId, walkerId, currency, createdAt, updatedAt, entries]
          properties:
            rateCardId: { type: string, format: uuid }
            walkerId: { type: string, format: uuid }
            currency: { type: string, minLength: 3, maxLength: 3 }
            createdAt: { type: string, format: date-time }
            updatedAt: { type: string, format: date-time }
            entries:
              type: array
              items: { $ref: '#/components/schemas/RateCardEntryPayload' }
```

## Common pitfalls

| Anti-pattern | Check that catches it |
|---|---|
| Thin event payload (id + timestamp only) on a non-removal event | `EVENT-PAYLOAD-COVERS-ENTITY-STATE` |
| Aggregate root event missing its declared child collection | `EVENT-PAYLOAD-COVERS-ENTITY-STATE` (aggregate block) |
| Write op in openapi but no corresponding asyncapi channel | `WRITE-OP-HAS-ASYNCAPI-CHANNEL` |
| `[secret]` field appearing in an event payload | `EVENT-PAYLOAD-COVERS-ENTITY-STATE` (the secret marker excludes it from the must-appear set, so adding it back creates asymmetry with datacontract — caught) |
| asyncapi enum values diverge from openapi or datacontract | `ENUM-VALUES-CONSISTENT` |
| Forgetting to rename `id` → `<entity>Id` in the payload | Soft: the check accepts both, but the convention is `<entity>Id` for top-level + `id` for nested aggregate items |
| Child item schema misses one of the child's published attributes | `EVENT-PAYLOAD-COVERS-ENTITY-STATE` (asyncapi vs model edge) |

## Authoring-time validation

After every significant section change, run the gate from the
target repo to surface lint and cross-reference errors early:

```bash
task gate:contracts
```

Iterate until clean, then return to `domain-contracts` for
Phase 6 sign-off.

## Decision-prone areas

These choices have no mechanical check; surface them through the
Decision Log when the user makes them:

- **CloudEvents envelope choices.** What goes in `type`, the URI
  scheme for `source`, where the domain id lives.
- **Per-event opt-outs from full-state coverage.** Today every
  non-removal event carries full state. A future `payload:
  minimal` marker (see v1.0.10+ backlog) would let some events
  opt out. Not in scope until a real driver appears.
- **Channel granularity.** Whether a single state transition
  warrants two channels (`requested` + `scheduled`) or one
  (`status-changed`).
