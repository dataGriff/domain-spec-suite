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
