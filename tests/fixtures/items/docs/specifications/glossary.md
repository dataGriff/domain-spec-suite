# Glossary — Items

> The ubiquitous language for the Items domain — a lexicon, not a
> reference manual. Every entity, role, domain event, and key term used
> in `domain-model.md` and the contracts has a one- or two-sentence
> entry here. Attribute-level detail lives in `domain-model.md`'s
> entity tables. Code, docs, and conversation must use these terms.

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

### UserRegistered

Published on the `items.user.registered` channel whenever a new user
registers (POST /v1/auth/register → 201). Registration is a business
event even though it happens on an auth route — consumers need it to
resolve `contributorId` references without re-querying the API.

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
