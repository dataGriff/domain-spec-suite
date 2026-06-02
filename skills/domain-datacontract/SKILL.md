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
- **`slaProperties`**: `availability` and `retention` come from
  `nfr.md` (NFR-AVAIL-002 and NFR-DATA-001 in the Items
  example).

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
```

## Common pitfalls

| Anti-pattern | Check that catches it |
|---|---|
| Event in asyncapi without a matching datacontract record | `EVENT-IN-DATACONTRACT` |
| Record field set diverges from the asyncapi payload property set | `EVENT-PAYLOAD-COVERS-ENTITY-STATE` (asyncapi↔datacontract symmetry edge) |
| Aggregate root record missing its declared child collection | `EVENT-PAYLOAD-COVERS-ENTITY-STATE` (aggregate block, datacontract side) |
| Child item field set diverges between asyncapi item schema and datacontract `items.properties` | `EVENT-PAYLOAD-COVERS-ENTITY-STATE` (aggregate item symmetry) |
| Using `logicalType: string` for a UUID field instead of `{logicalType: string, physicalType: uuid}` | `DATACONTRACT-LINT` (loose), but agent convention prefers explicit `physicalType` for clarity |
| Forgetting to declare `slaProperties` | Soft — `DATACONTRACT-LINT` may pass but NFR-AVAIL/RETENTION values must surface somewhere |

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
