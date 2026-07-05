# Non-Functional Requirements — [Domain]

> Quantified thresholds the [Domain] domain must meet. Every NFR
> carries a measurable target (number, percentage, or time unit).
> Aspirational language ("fast", "scalable", "robust") is not
> permitted here — if a threshold cannot yet be set, it belongs in
> `.spec-suite/ambiguities.md` as a deferral, not in this file.

---

## Performance

### NFR-PERF-001: Read latency

[Operation set] complete with **p95 ≤ [number] ms** and **p99 ≤
[number] ms**, measured server-side from request received to response
flushed, under a steady-state load of [N requests per second] against
a populated dataset of [N records].

### NFR-PERF-002: Write latency

[Operation set] complete with **p95 ≤ [number] ms** and **p99 ≤
[number] ms** under the same load profile as NFR-PERF-001. The budget
includes synchronous event publication.

---

## Availability

### NFR-AVAIL-001: API uptime

The HTTP API is available **≥ [percentage] %** of the time, measured
monthly.

### NFR-AVAIL-002: Event delivery

Domain events are delivered to the broker **≥ [percentage] %** of the
time. Event publication is best-effort within the API request —
failed publication does not block the API response.

---

## Throughput

### NFR-THRU-001: Steady-state request rate

[Define throughput target, e.g. ≥ N requests per second sustained for
M minutes, under [read/write mix]%, without exceeding latency budgets.]

---

## Security

### NFR-SEC-001: Token lifetime

Access tokens expire **[number] s** after issue. Refresh tokens
expire **[number] s** after issue.

### NFR-SEC-002: Password hashing

Passwords are stored using an **adaptive password-hashing algorithm**
configured so that a single hash takes **≥ [number] ms** of CPU time
on commodity hardware. Plaintext passwords are never logged and never
returned in API responses.

### NFR-SEC-003: Transport encryption

All non-local traffic is served over **TLS [version] or higher**.

### NFR-SEC-004: Authentication coverage

**100 %** of routes outside [explicit allowlist] require a valid
bearer token. Routes without a declared `security` block in
`contracts/openapi.yaml` are a build-time audit failure.

### NFR-SEC-005: Rate limiting

[List every rate-limited endpoint with its limit, e.g. ≤ N requests
per minute per IP.] The list MUST include every publicly reachable
endpoint whose sole authentication is a token or secret in the
request itself (invite acceptance, password reset confirmation) —
those are brute-forceable and need limits at least as tight as
login. Exceeding a limit returns the catalogue's 429 code
(`RATE_LIMITED` by convention) — the code must exist in
`error-catalogue.md` and be declared as a response in
`contracts/openapi.yaml`, otherwise this NFR is untestable.

---

## Data retention

### NFR-DATA-001: Event retention

Domain events are retained on the broker for **[number] days** (must
match `contracts/datacontract.yaml` `slaProperties.retention`).

### NFR-DATA-002: Domain data durability

[Either state durability guarantees with a measurable RPO/RTO, or
explicitly declare durability is not required for this reference
spec set. Use implementation-free language — describe the property,
not the mechanism.]

---

## Privacy & data rights

> Required whenever the domain stores personal data (names, contact
> details, health information — human or otherwise identifying).
> "Deferred to a future GDPR phase" is only acceptable as an
> `ambiguities.md` deferral with a required-by phase, not as silence.

### NFR-PRIV-001: Retention ceilings

Personal data is retained **no longer than [number] months** after
[triggering event, e.g. account closure or last activity]. Retention
floors (NFR-DATA-*) must each have a matching ceiling here — "at
least N months" with no maximum is not a complete retention policy.

### NFR-PRIV-002: Data-subject rights

[State how access/export and deletion requests are satisfied at the
contract level — which operations, or which documented manual
process, and within what period (e.g. ≤ 30 days). If deletion is
tombstone-based because of the event stream's immutability, say so
and state what is erased vs anonymised.]

### NFR-PRIV-003: PII inventory

Every attribute carrying personal data is listed here (or in a
referenced section of `domain-model.md`) so the other NFR-PRIV
targets have a definite scope: [list of `Entity.attribute`].

---

## Observability

### NFR-OBS-001: Request log coverage

**100 %** of incoming HTTP requests emit a structured log line
recording method, path, status code, latency in milliseconds, and
the authenticated `user.id` if present. No request bodies are
logged.

### NFR-OBS-002: Error sampling

**100 %** of `5xx` responses and **≥ [percentage] %** of `4xx`
responses produce a structured error log recording the error `code`,
the operation `operationId`, and the `user.id` if present.

### NFR-OBS-003: Event publish observability

Every successful event publish records the channel, the CloudEvents
`id`, and the publish latency in milliseconds. Failed publishes
record the same fields plus the broker error.

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
`contracts/datacontract.yaml` exactly. Drift is a hard audit failure.
