# Domain Model

> **Template placeholder.** Replace this file with your domain's model.  
> Run `task domain:init` to copy this template, then edit the copy in `docs/specifications/`.

---

## Overview

<!-- Briefly describe the domain and its core purpose. -->

TODO: Replace with your domain overview.

## Entities

<!-- For each entity: name, description, attributes, and business rules. -->

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
