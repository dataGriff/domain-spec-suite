---
name: domain-datacontract
description: |
  Authoring conventions for `contracts/datacontract.yaml`
  (Open Data Contract Standard 3.1). Invoked from
  `domain-contracts` (Phase 6) when the user is drafting or
  refining the historic-record schema. This skill does not run
  any gate of its own — the lint check (`DATACONTRACT-LINT`)
  and every cross-reference check (event-in-datacontract,
  event-payload-covers-entity-state) are owned by
  `domain-contracts`.
prerequisites:
  - Phases 1-5 have signed off (entities, events table, and NFR
    availability + retention values are the inputs).
  - Target repo has `datacontract` (datacontract-cli) on PATH
    (pinned via `.mise.toml`).
trigger_phrases:
  - "datacontract authoring"
  - "draft the data contract"
  - "odcs conventions"
  - "publish the datacontract html"
---

# `contracts/datacontract.yaml` — Authoring

ODCS 3.1. The data contract is the **audit-grade historic
record** of every domain event payload. Field names + types
come straight from the AsyncAPI message payloads — the two
must agree (`EVENT-PAYLOAD-COVERS-ENTITY-STATE` enforces it).

## Sections

- **`schema[*]`**: one record per *family* of channels —
  typically one per entity, plus reduced-payload variants for
  removal events (e.g. `items_removed` carrying only id +
  timestamp).
- **`schema[*].properties[*]`**: one field per asyncapi payload
  property. Use the ODCS type mapping:
  - asyncapi `string, format: uuid` → `logicalType: string,
    physicalType: uuid`
  - asyncapi `string, format: date-time` → `logicalType:
    timestamp`
  - asyncapi `integer` → `logicalType: integer`
- **`slaProperties`**: three properties are required
  (`DATACONTRACT-SLA-COMPLETE`): `availability` and `retention`
  come from `nfr.md` (NFR-AVAIL-002 and NFR-DATA-001 in the Items
  example), and `latency` states the freshness guarantee — how
  long after a domain transition commits its event is readable by
  consumers (derive from the delivery-semantics NFR, e.g. a
  transactional-outbox drain interval). Declare `frequency`
  (expected volume) too when consumers need to capacity-plan.
- **`schema[*].quality`**: state each record's quality
  expectations as `type: text` entries — PK uniqueness per event
  id, required-field completeness, enum fields carrying only
  legal members. `text` is documentation-grade (no runtime engine
  implied); switch to `sql`/`library` rules only when an actual
  quality runner exists downstream.

## Refs and enums

- **Qualified refs only.** ODCS has no `components` section, so an
  OpenAPI-style `ref: '#/components/schemas/X'` resolves to nothing
  inside this document. When a field's vocabulary is defined by an
  openapi schema, use the qualified form
  `ref: 'openapi.yaml#/components/schemas/X'` — the target must
  exist there (`DATACONTRACT-REFS-RESOLVE` enforces both).
- **Don't pin `(open)` enums closed.** An enum the model marks
  `(open)` may grow in openapi with a minor version bump; a
  hard-coded value list here turns every such addition into a data
  contract violation. Reference the authoritative openapi schema
  (qualified ref) and type the field `logicalType: string` with a
  description naming the list, rather than duplicating hundreds of
  values that will drift.
- **Every entity-named FK must be resolvable.** A field named
  `<entity>Id` requires a record in this contract that publishes
  that entity — otherwise consumers must re-query the live API,
  which defeats the historic record (`EVENT-FK-RESOLVABLE`).

## Aggregate-child fields

(Per SUITE-DESIGN §4.5 and the suite v1.0.8 convention.)

When the root entity has children declared in
`domain-model.md`'s `## Aggregates` section, the matching record
carries a nested ODCS array field whose items cover the child's
published attributes:

```yaml
- name: ratecard
  description: >
    RateCard root records plus contained RateCardEntry rows.
  properties:
    - { name: rateCardId, logicalType: string, physicalType: uuid, required: true, ... }
    - { name: walkerId, logicalType: string, physicalType: uuid, required: true }
    - ...
    - name: entries
      description: Rate-card entries on this rate card.
      logicalType: array
      required: true
      items:
        logicalType: object
        properties:
          - { name: id, logicalType: string, physicalType: uuid, required: true }
          - { name: rateCardId, logicalType: string, physicalType: uuid, required: true }
          - { name: walkType, logicalType: string, required: true }
          - ...
```

Both events on an aggregate root share the same record (e.g.
`InvoiceIssued` AND `InvoicePaid` both bind to the `invoice`
record) — so the record covers what BOTH events carry.

## Publishing the contract as HTML

The data contract MUST be published as a standalone HTML
reference at `docs/specifications/datacontract-reference.html`,
generated via the datacontract CLI's HTML exporter. It joins
`api-reference.html` (Scalar) and `asyncapi-reference.html`
(AsyncAPI React) as the third peer contract reference on the
spec site, so consumers have an interactive view of every record
without grepping the YAML.

The exporter is built into `datacontract-cli` (already on PATH
for Phase 6 because of `DATACONTRACT-LINT`). Command shape:

```bash
datacontract export html \
  docs/specifications/contracts/datacontract.yaml \
  --output docs/specifications/datacontract-reference.html
```

Wire this into the target repo's docs build task (typically
`docs:generate` in `Taskfile.yml`) so the page is regenerated
on every docs build and gh-deploy. Rendering is a site-build
concern, not gated by a Phase 6 check — `DATACONTRACT-LINT`
already proves the YAML is exportable, so a failing render
would also fail lint.

## Tools

Bootstrap-installed tasks for datacontract authoring:

- **`task datacontract:skeleton`** — derives a complete
  datacontract.yaml skeleton from `contracts/asyncapi.yaml` (one
  record per channel family, fields mirroring the asyncapi
  payload) + `nfr.md` (best-effort lookup of NFR-AVAIL-002 +
  NFR-DATA-001 for slaProperties). Aggregate-child collections
  emit nested ODCS array fields. Run AFTER `task
  asyncapi:skeleton`. Idempotent (refuses to overwrite a real
  datacontract.yaml unless `--force`).
- **`task lint:datacontract`** — `datacontract lint
  contracts/datacontract.yaml`.
- **`task docs:render-datacontract`** — emits the
  `datacontract-reference.html` peer reference. Wired into
  `task docs:generate` so it regenerates on every docs build.
- **`task gate:contracts`** — runs the full Phase 6 gate.

## Worked YAML patterns

### Simple record (single entity)

```yaml
schema:
  - name: dog
    description: >
      Dog records published via the dogwalking.dog.added and
      dogwalking.dog.updated channels.
    physicalType: topic
    properties:
      - { name: dogId, description: Dog identifier., logicalType: string, physicalType: uuid, required: true, unique: true, primaryKey: true, primaryKeyPosition: 1 }
      - { name: name, description: Dog's display name., logicalType: string, required: true }
      - { name: breed, description: Closed-set breed value., logicalType: string, required: true }
      - { name: ownerId, description: Owner reference., logicalType: string, physicalType: uuid, required: true }
      - { name: createdAt, description: Creation timestamp., logicalType: timestamp, required: true }
      - { name: updatedAt, description: Last update timestamp., logicalType: timestamp, required: true }
```

### Record with nested aggregate-child array

```yaml
- name: ratecard
  description: >
    RateCard root plus contained RateCardEntry rows.
  physicalType: topic
  properties:
    - { name: rateCardId, description: RateCard identifier., logicalType: string, physicalType: uuid, required: true, unique: true, primaryKey: true, primaryKeyPosition: 1 }
    - { name: walkerId, description: Walker whose rate card changed., logicalType: string, physicalType: uuid, required: true }
    - { name: currency, description: ISO 4217 currency code., logicalType: string, required: true }
    - { name: createdAt, description: Creation timestamp., logicalType: timestamp, required: true }
    - { name: updatedAt, description: Last update timestamp., logicalType: timestamp, required: true }
    - name: entries
      description: Rate-card entries on this rate card.
      logicalType: array
      required: true
      items:
        logicalType: object
        properties:
          - { name: id, description: RateCardEntry identifier., logicalType: string, physicalType: uuid, required: true }
          - { name: rateCardId, description: FK to parent RateCard., logicalType: string, physicalType: uuid, required: true }
          - { name: walkType, description: Walk type for this entry., logicalType: string, required: true }
          - { name: durationMinutes, description: Duration in minutes., logicalType: integer, required: true }
          - { name: priceCents, description: Price in minor units., logicalType: integer, required: true }
          - { name: createdAt, description: Entry creation timestamp., logicalType: timestamp, required: true }
          - { name: updatedAt, description: Entry last update timestamp., logicalType: timestamp, required: true }
```

### slaProperties from NFRs

```yaml
slaProperties:
  - property: availability
    value: "99.5"
    unit: "%"
    description: Events are delivered at least 99.5% of the time (NFR-AVAIL-002).
  - property: retention
    value: 30
    unit: d
    description: Events are retained for 30 days for replay (NFR-DATA-001).
  - property: latency
    value: 60
    unit: s
    description: >
      Freshness — an event is readable within 60 seconds of its
      domain transition committing (transactional-outbox drain,
      NFR-AVAIL-002 delivery semantics).
```

### Record-level quality expectations

```yaml
schema:
  - name: walk
    physicalType: topic
    quality:
      - type: text
        description: >
          walkId is unique per event id; every required field is
          present on every record; status only carries legal
          WalkStatus members.
    properties:
      - ...
```

## Common pitfalls

| Anti-pattern | Check that catches it |
|---|---|
| Event in asyncapi without a matching datacontract record | `EVENT-IN-DATACONTRACT` |
| Record field set diverges from the asyncapi payload property set | `EVENT-PAYLOAD-COVERS-ENTITY-STATE` (asyncapi↔datacontract symmetry edge) |
| Aggregate root record missing its declared child collection | `EVENT-PAYLOAD-COVERS-ENTITY-STATE` (aggregate block, datacontract side) |
| Child item field set diverges between asyncapi item schema and datacontract `items.properties` | `EVENT-PAYLOAD-COVERS-ENTITY-STATE` (aggregate item symmetry) |
| Using `logicalType: string` for a UUID field instead of `{logicalType: string, physicalType: uuid}` | `DATACONTRACT-LINT` (loose), but agent convention prefers explicit `physicalType` for clarity |
| Missing `availability` / `retention` / `latency` slaProperty | `DATACONTRACT-SLA-COMPLETE` |
| Unqualified `#/components/schemas/...` ref (resolves to nothing in an ODCS document) | `DATACONTRACT-REFS-RESOLVE` |
| FK to an entity no record publishes (`walkerId` with no walker record) | `EVENT-FK-RESOLVABLE` |
| Hard-coding an `(open)` enum's full value list | No mechanical catch — see Refs and enums above |

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

- **Snapshot / denormalisation on line items.** When line items
  copy fields from their source (e.g. `InvoiceLineItem.walkType`
  copied from Walk) and why.
- **Retention horizon for replay.** The `retention` SLA value.
  Tied to NFR-DATA but recorded here.
- **Availability target.** Same — tied to NFR-AVAIL but
  recorded here.
- **Freshness/latency target.** The `latency` SLA value and the
  delivery mechanism that backs it (outbox drain interval,
  broker replication lag).

## Derived data products (designed — build when a domain needs one)

The event contract answers *what happened* (operational awareness,
audit, replay). It deliberately does not answer summarised or
per-perspective questions — "walker earnings by month",
"walk history for a dog" — those are **derived data products**:
read models computed from the event stream.

When a domain's consumers need one, author it as an additional ODCS
contract at `contracts/data-products/<name>.yaml` (one file per
product), with:

- **`description.purpose`** naming the question the product answers
  and its consumers;
- **`customProperties`** (or description prose) declaring its
  **source events** — the channels it is derived from — so lineage
  back to the event contract is explicit;
- **its own `slaProperties`** — refresh cadence/`latency` (derived
  products are usually staler than the stream), `retention`,
  `availability`;
- **`schema`** describing the product's records (aggregates,
  snapshots), NOT mirrors of event payloads;
- **`quality`** expectations for the derivation (e.g. sums
  reconcile with the underlying events over the retention window).

No gate checks bind `data-products/` yet — the first real product
(expected in the dog-rescue domain) drives what gets mechanised
(see BUILD-PLAN Post-v1 Backlog). Do NOT invent data products a
domain hasn't asked for; the event contract alone is a complete
Phase 6 output.
