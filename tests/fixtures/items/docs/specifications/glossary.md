# Glossary — Items

> The ubiquitous language for the Items domain. Every entity name and every
> attribute name used in `domain-model.md`, `contracts/openapi.yaml`,
> `contracts/asyncapi.yaml`, and `contracts/datacontract.yaml` appears here
> exactly as it is used. Code, docs, and conversation must use these terms.

---

## Entities

### Item

A named entry in the catalogue, owned by a contributor. Has a simple
`active` / `archived` lifecycle. Items are the primary resource the API
manages.

### User

An authenticated user of the system. Holds exactly one role — either
`contributor` or `viewer` — and that role is set at registration and
cannot be changed via the API.

---

## Item attributes

### id

UUID. Unique identifier of an item. Immutable.

### name

String, minimum length 1. The display name of an item. Required at creation
and editable by the owning contributor.

### description

String or `null`. Optional longer description of an item. May be cleared
back to `null` via edit.

### status

Enum: `active` or `archived`. Defaults to `active` at creation. The owning
contributor may toggle freely between the two values.

### contributorId

UUID. References the `id` of the `User` who added this item. Immutable
after creation — items cannot be transferred between contributors.

### createdAt

ISO 8601 timestamp. The moment the item was added to the catalogue.
Immutable.

### updatedAt

ISO 8601 timestamp. The moment the item was last edited. Updated by every
successful PATCH operation, including status toggles.

---

## User attributes

### id

UUID. Unique identifier of a user. Immutable.

### email

String, email format. The user's email address. Unique across all users
and used as the login credential.

### password

String, stored as a hash via an adaptive password-hashing algorithm
(see `nfr.md` NFR-SEC-002). Never returned in any API response. Set at
registration and updated through dedicated password flows (not in
scope for v1).

### firstName

String, minimum length 1. The user's given name.

### lastName

String, minimum length 1. The user's family name.

### role

Enum: `contributor` or `viewer`. Determines which operations the user may
perform — see `auth-matrix.md`. Set at registration and immutable
thereafter.

### createdAt

ISO 8601 timestamp. The moment the user registered. Immutable.

---

## Roles

### contributor

A user role that may add items to the catalogue and may edit or remove
items they own. May also list and view items, like a viewer. Cannot
modify items belonging to other contributors.

### viewer

A user role with read-only access to the catalogue. May list and view
items. Cannot add, edit, or remove items.

---

## Domain events

### ItemAdded

Published on the `items.item.added` channel whenever a contributor
successfully adds a new item (POST /v1/items → 201). Payload is the full
item record.

### ItemEdited

Published on the `items.item.edited` channel whenever an item's `name`,
`description`, or `status` changes (PATCH /v1/items/{itemId} → 200).
Payload is the full item record post-edit.

### ItemRemoved

Published on the `items.item.removed` channel whenever an item is removed
from the catalogue (DELETE /v1/items/{itemId} → 204). Payload is reduced
to `id`, `contributorId`, and `removedAt` only.

---

## Other terms

### catalogue

The complete set of items in the system, regardless of status. Both
`active` and `archived` items are part of the catalogue.

### lifecycle

The set of status transitions an item may go through. For Items, the
lifecycle is `active ⟷ archived` — both directions are permitted at any
time by the owning contributor.

### ownership

The relationship between a contributor and the items they have added.
Represented by the `contributorId` attribute on `Item`. Used by the
auth matrix to scope edit and remove operations to the owning
contributor only.

### pagination

The list-endpoint pattern of returning a subset of results plus metadata
(`page`, `pageSize`, `total`). All list endpoints in this domain
paginate.

### access token

A short-lived JWT issued by the login or refresh endpoints. Carried in
the `Authorization: Bearer <token>` header on every authenticated
request.

### refresh token

A longer-lived token issued alongside the access token. Exchanged at
`POST /v1/auth/refresh` for a new access/refresh pair when the access
token expires.
