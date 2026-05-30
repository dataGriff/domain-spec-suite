# Non-Functional Requirements — Items

> Quantified thresholds the Items domain must meet. Every NFR carries a
> measurable target (number, percentage, or time unit). Aspirational
> language ("fast", "scalable", "robust") is not permitted here — if a
> threshold cannot yet be set, it belongs in `_ambiguities.md` as a
> deferral, not in this file.

---

## Performance

### NFR-PERF-001: Read latency

`GET /v1/items` and `GET /v1/items/{itemId}` complete with **p95 ≤ 150 ms**
and **p99 ≤ 300 ms**, measured server-side from request received to
response flushed, under a steady-state load of 50 requests per second
against a populated catalogue of 10 000 items.

### NFR-PERF-002: Write latency

`POST /v1/items`, `PATCH /v1/items/{itemId}`, and
`DELETE /v1/items/{itemId}` complete with **p95 ≤ 250 ms** and
**p99 ≤ 500 ms** under the same load profile as NFR-PERF-001. The
budget includes synchronous event publication.

### NFR-PERF-003: Auth latency

`POST /v1/auth/login` and `POST /v1/auth/register` complete with
**p95 ≤ 400 ms**. The password-hashing cost mandated by NFR-SEC-002
is the dominant contributor; the budget accommodates a hash that
consumes ≥ 250 ms of CPU per request.

### NFR-PERF-004: List pagination ceiling

`GET /v1/items` returns at most **100 items per page** (enforced by
`PageSize.maximum: 100` in `contracts/openapi.yaml`). A list query with
`pageSize` above 100 is rejected with `VALIDATION_FAILED`.

---

## Availability

### NFR-AVAIL-001: API uptime

The HTTP API is available **≥ 99.9 %** of the time, measured monthly
(no more than 43 minutes of unavailability per 30-day window).

### NFR-AVAIL-002: Event delivery

Domain events are delivered to the broker **≥ 99.9 %** of the time
(matches `datacontract.yaml` `slaProperties.availability`). Event
publication is best-effort within the API request — failed publication
does not block the API response.

---

## Throughput

### NFR-THRU-001: Steady-state request rate

A single API instance sustains **≥ 100 requests per second** of mixed
read/write traffic (90 % reads, 10 % writes) for at least 10 minutes
without exceeding NFR-PERF-001 / NFR-PERF-002 latency budgets.

### NFR-THRU-002: Event publish rate

A single API instance sustains **≥ 50 events per second** of mixed
`ItemAdded` / `ItemEdited` / `ItemRemoved` traffic without dropping
events and without blocking the originating HTTP request for more than
**100 ms** on publication.

---

## Security

### NFR-SEC-001: Token lifetime

Access tokens expire **3600 s (1 hour)** after issue (`AuthResponse.expiresIn`
is `3600`). Refresh tokens expire **2 592 000 s (30 days)** after issue.

### NFR-SEC-002: Password hashing

Passwords are stored using an **adaptive password-hashing algorithm**
configured so that a single hash takes **≥ 250 ms** of CPU time on
commodity 2026 server hardware. Plaintext passwords are never logged
and never returned in API responses (enforced by `User.password`
being absent from `UserSummary` and `Item` schemas).

### NFR-SEC-003: Transport encryption

All non-local traffic is served over **TLS 1.2 or higher**. The local
development server (`http://localhost:3000`) is the only exception.

### NFR-SEC-004: Authentication coverage

**100 %** of routes outside `/v1/auth/register`, `/v1/auth/login`, and
`/v1/auth/refresh` require a valid bearer token. Routes without a
declared `security` block in `contracts/openapi.yaml` are a build-time
audit failure.

---

## Data retention

### NFR-DATA-001: Event retention

Domain events are retained on the broker for **30 days** (matches
`datacontract.yaml` `slaProperties.retention`), making them available
for replay and historical analysis.

### NFR-DATA-002: Domain data durability

Domain data has **no durability requirement** for this reference spec
set. Implementations MAY use ephemeral storage that does not survive
process restart, provided the API surface in `contracts/openapi.yaml`
and the event contracts in `contracts/asyncapi.yaml` and
`contracts/datacontract.yaml` remain conformant across restarts.
Durability is a deliberate non-requirement, not an under-specified
threshold — `_ambiguities.md` does not need an entry.

---

## Observability

### NFR-OBS-001: Request log coverage

**100 %** of incoming HTTP requests emit a single structured log line
recording method, path, status code, latency in milliseconds, and the
authenticated `user.id` if present. No request bodies are logged.

### NFR-OBS-002: Error sampling

**100 %** of `5xx` responses and **≥ 10 %** of `4xx` responses (sampled
deterministically by request id) produce a structured error log
recording the error `code`, the operation `operationId`, and the
`user.id` if present.

### NFR-OBS-003: Event publish observability

Every successful event publish records the channel, the CloudEvents
`id`, and the publish latency in milliseconds. Failed publishes record
the same fields plus the broker error.

---

## Compatibility

### NFR-COMPAT-001: OpenAPI version stability

Within a major version of the OpenAPI contract (`info.version` major
component), no field is removed and no enum value is removed.
Additions are permitted. Major-version bumps are reserved for
breaking changes.

### NFR-COMPAT-002: AsyncAPI / data contract alignment

Field names, types, and required/optional status in
`contracts/asyncapi.yaml` event payloads match
`contracts/datacontract.yaml` exactly. Drift is a hard audit failure
(see Phase 7 cross-reference checks in `SUITE-DESIGN.md`).
