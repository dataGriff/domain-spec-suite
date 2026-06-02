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
