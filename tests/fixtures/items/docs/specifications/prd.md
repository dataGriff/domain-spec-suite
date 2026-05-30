# Product Requirements Document — Items

## Problem Statement

Small teams who share custody of a list of named things — stock, kit,
samples, fixtures, props, ingredients — currently track them in shared
spreadsheets or chat threads. Two recurring failure modes follow from
that: read-only colleagues accidentally edit (or break) the list, and
nobody can tell who last changed what or why. The team needs a
catalogue that separates **who may read** from **who may change**,
records ownership of each entry, and emits a record every time the
catalogue changes.

The **Items** domain is that catalogue. It is deliberately minimal — a
named entry with a short description, an `active`/`archived` lifecycle,
and ownership by the team member who added it — so that the access
rules and event flow are the interesting parts, not the data shape.

## Target Users / Personas

### Stockroom Lead — Sam

Sam runs the team's stockroom. They add and curate every item the team
shares: tools, sensors, sample kits. Sam has been keeping the inventory
in a Google Sheet, manually pasting in new items as they arrive and
ticking a "retired?" column when something leaves rotation.

- **Goal:** Add new items as they come in, mark stale items archived,
  fix typos in names and descriptions, and trust that the catalogue
  reflects what's actually on the shelf.
- **Frustration:** The shared sheet has been silently overwritten three
  times in the last quarter when colleagues opened it to *look* and
  accidentally edited a cell. There is no audit trail and Sam cannot
  tell who broke what.

### Operations Analyst — Olu

Olu reports on stockroom utilisation to the operations meeting every
fortnight. They consume the catalogue, they don't curate it. Today Olu
pulls the spreadsheet into a notebook, cleans it, and produces the
report.

- **Goal:** Browse and search the current catalogue without the risk
  of accidentally changing it; consume the change history as a stream
  rather than diffing snapshots of a spreadsheet each fortnight.
- **Frustration:** Each fortnight Olu has to reconcile what changed by
  hand because the spreadsheet has no event log. When Olu suspects an
  item was archived early, there's no way to confirm without asking
  Sam.

## Goals

1. Give the team a catalogue where read access and write access are
   genuinely separated, so that colleagues who only want to look cannot
   change data by accident.
2. Tie every catalogue entry to the team member who added it so
   ownership and accountability are visible at the entry level.
3. Emit a domain event for every change to the catalogue so consumers
   can drive reporting, alerting, or downstream sync without polling.
4. Keep the surface small enough that a new team member can understand
   the entire domain — entities, roles, lifecycle, events — in one
   sitting.

## Non-Goals

1. **A real vertical product.** Items deliberately stays generic; it is
   not a stock-control system, an asset register, or an inventory
   platform. It is a catalogue of named entries.
2. **Complex state machines.** The lifecycle is `active ⟷ archived` and
   that is the entire state model. No approvals, no draft states, no
   review queues.
3. **Persistent storage.** Durability of catalogue data is out of scope
   for this reference spec set (see `nfr.md` NFR-DATA-002).
   Implementations MAY choose ephemeral storage.
4. **Nested resources.** Items have no sub-entities, no categories, no
   tags. If those are needed for a real domain, that is a different
   spec set.

## User Stories

### Authentication

#### US-001: Register as a contributor or viewer

**As a** new team member,
**I want to** register with my name, email, password, and intended role,
**So that** I can start using the catalogue at the right access level.

**Acceptance Criteria:**
- POST /v1/auth/register accepts `contributor` or `viewer` role
- Returns access token + refresh token on success
- Returns 409 with `EMAIL_ALREADY_REGISTERED` if the email is already
  in use

#### US-002: Log in and receive tokens

**As a** registered team member,
**I want to** log in with my email and password,
**So that** I can get a fresh access token without re-registering.

**Acceptance Criteria:**
- POST /v1/auth/login returns 200 with tokens on valid credentials
- Returns 401 with `INVALID_CREDENTIALS` on wrong email or wrong
  password (indistinguishable to avoid leaking which field was wrong)

### Items

#### US-003: Add an item to the catalogue

**As a** stockroom lead,
**I want to** add a new item with a name and optional description,
**So that** it appears in the catalogue and is tied to me as the
contributor.

**Acceptance Criteria:**
- POST /v1/items creates an item with `status: active`
- The new item is associated with the authenticated contributor's id
- Viewers cannot add items (403 with `FORBIDDEN`)
- An `ItemAdded` event is published on the `items.item.added` channel

#### US-004: List all items

**As a** stockroom lead or operations analyst,
**I want to** list all items with pagination,
**So that** I can browse the catalogue without loading every entry at
once.

**Acceptance Criteria:**
- GET /v1/items returns a paginated list
- Both roles can list items
- Page size is capped at 100 (NFR-PERF-004)

#### US-005: View a single item

**As a** stockroom lead or operations analyst,
**I want to** view the details of a single item,
**So that** I can see its full name, description, status, and
contributor.

**Acceptance Criteria:**
- GET /v1/items/{itemId} returns the item
- Returns 404 with `ITEM_NOT_FOUND` if the id does not exist

#### US-006: Edit my own item

**As a** stockroom lead,
**I want to** edit the name, description, or status of an item I added,
**So that** I can correct typos, refine descriptions, and toggle items
between `active` and `archived` as they enter and leave rotation.

**Acceptance Criteria:**
- PATCH /v1/items/{itemId} edits the item
- Returns 403 with `FORBIDDEN` if the item belongs to a different
  contributor
- Viewers cannot edit items (403 with `FORBIDDEN`)
- An `ItemEdited` event is published on `items.item.edited`

#### US-007: Remove my own item from the catalogue

**As a** stockroom lead,
**I want to** remove an item I added,
**So that** it no longer appears in the catalogue once it is genuinely
out of service (not just archived).

**Acceptance Criteria:**
- DELETE /v1/items/{itemId} removes the item
- Returns 403 with `FORBIDDEN` if the item belongs to a different
  contributor
- Viewers cannot remove items (403 with `FORBIDDEN`)
- An `ItemRemoved` event is published on `items.item.removed`

## Constraints

1. **Implementation-agnostic.** The spec set does not constrain
   runtime, framework, database, broker, or hosting. Any stack that
   satisfies the contracts in `contracts/` and the thresholds in
   `nfr.md` is conformant.
2. **Two roles only.** `contributor` and `viewer` are the only roles
   in v1. Multi-role users, role hierarchies, and administrative
   override roles are out of scope.

## Success Metrics

1. **Contract integrity.** All three contract files
   (`contracts/openapi.yaml`, `contracts/asyncapi.yaml`,
   `contracts/datacontract.yaml`) validate against their respective
   linting rulesets without errors or warnings.
2. **Cross-spec consistency.** Every entity named in
   `domain-model.md` appears in `glossary.md` and has a matching
   schema in `contracts/openapi.yaml`. Every domain event named in
   `domain-model.md` has a matching channel in
   `contracts/asyncapi.yaml` and a matching record in
   `contracts/datacontract.yaml`.
3. **Time to comprehension.** A new team member reading the spec set
   end to end can describe the domain (entities, roles, lifecycle,
   events) accurately within **5 minutes** of finishing the read.
