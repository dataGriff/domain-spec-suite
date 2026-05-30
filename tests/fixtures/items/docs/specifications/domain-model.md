# Domain Model — Items

## Overview

The **Items** domain is a small shared catalogue of named entries
owned by the team members who add them. Each item has an
`active`/`archived` lifecycle and is associated with exactly one
contributor. Two roles operate on the catalogue: `contributor`
(creates and curates entries) and `viewer` (read-only).

---

## Entities

### User

Represents an authenticated user of the system.

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | UUID | Yes | Unique identifier |
| `email` | string (email) | Yes | User's email address (unique) |
| `password` | string (hashed) | Yes | Stored as a hash via an adaptive password-hashing algorithm (see `nfr.md` NFR-SEC-002); never returned in API responses |
| `firstName` | string | Yes | Given name |
| `lastName` | string | Yes | Family name |
| `role` | enum | Yes | `contributor` or `viewer` |
| `createdAt` | ISO 8601 | Yes | Registration timestamp |

**Business Rules:**
- Email must be unique across all users.
- The stored password is a hash; the plaintext form is never returned in
  any API response and never logged.
- Role is set at registration and cannot be changed via the API.

---

### Item

Represents a named entry in the catalogue, owned by a contributor.

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | UUID | Yes | Unique identifier |
| `name` | string | Yes | Display name (min 1 char) |
| `description` | string \| null | No | Optional longer description |
| `status` | enum | Yes | `active` or `archived` |
| `contributorId` | UUID | Yes | ID of the user who created this item |
| `createdAt` | ISO 8601 | Yes | Creation timestamp |
| `updatedAt` | ISO 8601 | Yes | Last update timestamp |

**Business Rules:**
- `status` defaults to `active` on creation.
- Only the contributor who added an item may edit or remove it.
- Items cannot be transferred between contributors — `contributorId` is
  immutable after creation.
- Viewers may list and view any item but cannot modify them.

---

## Relationships

```
User (role=contributor) ──── creates many ──── Item
Item ──── belongs to ──────────────────────── User (contributorId)
```

A user in the `viewer` role does not create items; they only read them.

---

## Domain Events

| Event | Trigger | Channel |
|-------|---------|---------|
| `ItemAdded` | POST /v1/items → 201 | `items.item.added` |
| `ItemEdited` | PATCH /v1/items/{itemId} → 200 | `items.item.edited` |
| `ItemRemoved` | DELETE /v1/items/{itemId} → 204 | `items.item.removed` |

---

## Status Lifecycle

### Item Status

```
active ⟷ archived
```

| From | To | Trigger |
|------|----|---------|
| `active` | `archived` | PATCH /v1/items/{itemId} with `status: "archived"` |
| `archived` | `active` | PATCH /v1/items/{itemId} with `status: "active"` |

Items can be toggled between `active` and `archived` freely by their
owning contributor. There is no third state; archival is reversible.
