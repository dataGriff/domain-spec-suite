# Domain Model

> **Template placeholder.** Do not edit in place. The suite's modeling
> skill copies this into `docs/specifications/domain-model.md` when
> Phase 2 starts (or run `task domain:init` to copy every template at
> once).

---

## Overview

<!-- Briefly describe the domain and its core purpose. -->

TODO: Replace with your domain overview.

## Entities

<!--
For each entity: name, description, attributes, and business rules.

Attribute Description prefixes the parser recognizes:
- `[secret]` — sensitive value, excluded from event payloads + datacontract
  records (e.g. `passwordHash`, signed-URL fragments). The attribute is
  still required by OpenAPI request/response shapes where applicable.

Type column also recognizes `enum:Name` to reference a closed-set value
declared in `## Enumerations` below.
-->

### [Entity1]

**Description:** TODO

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | UUID | Yes | Unique identifier |
| `createdAt` | ISO 8601 | Yes | Creation timestamp |
| `updatedAt` | ISO 8601 | Yes | Last update timestamp |
| TODO | TODO | TODO | TODO |

**Business Rules:**
- TODO

---

### [Entity2]

**Description:** TODO

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | UUID | Yes | Unique identifier |
| `createdAt` | ISO 8601 | Yes | Creation timestamp |
| `updatedAt` | ISO 8601 | Yes | Last update timestamp |
| TODO | TODO | TODO | TODO |

**Business Rules:**
- TODO

---

## Relationships

<!-- Describe how entities relate to each other. -->

```
[Entity1] ──── has many ──── [Entity2]
[Entity2] ──── belongs to ── [Entity1]
```

TODO: Replace with your domain's entity relationships.

## Aggregates

<!-- Which entities form aggregate roots? What are the boundaries? -->

| Aggregate Root | Entities Contained | Description |
|---------------|-------------------|-------------|
| TODO | TODO | TODO |

## Domain Events

<!-- What significant state changes produce domain events? -->

| Event | Trigger | Description |
|-------|---------|-------------|
| `[Entity]Created` | POST /[entity] → 201 | TODO |
| `[Entity]Updated` | PATCH /[entity]/{id} → 200 | TODO |

## Status Lifecycles

<!-- For any entity with a `status` field, define all valid states and transitions. -->

### [Entity] Status

```
[initial] → [next] → [terminal]
```

| From | To | Trigger |
|------|----|---------|
| TODO | TODO | TODO |

## Enumerations

<!--
Closed-set values used by one or more attributes. Each enum named
here MUST appear in `contracts/openapi.yaml` as
`components.schemas.<Name>` with matching values (enforced by
`ENUM-VALUES-CONSISTENT` at Phase 6 + audit). Reference from
attribute tables via `enum:<Name>` in the Type column.

Delete this section if your domain has no named enums yet — the
convention is opt-in.
-->

### [EnumName]

| Value | Notes |
|---|---|
| `value-1` | TODO |
| `value-2` | TODO |
