# Acceptance Scenarios — [Domain]

> Given/When/Then scenarios at contract level. Every user story in
> `prd.md` has at least one scenario here — and every OpenAPI
> operation is exercised by at least one scenario
> (`OPERATION-HAS-SCENARIO`). Scenarios are written at the
> HTTP-request level — they reference operation IDs, paths, status
> codes, and response shapes from `contracts/openapi.yaml` directly,
> so they can drive contract-level test suites in any implementation.

## Authoring rules

1. **Every Given names the actor and the resource state.** "Given a
   walk exists" is ambiguous between 400/403/404/409 — write "Given
   an owner is logged in And a walk in status `requested` exists for
   their dog". Without both, the expected response is undefined.
2. **Literals must be legal.** Enum values, error codes, endpoints,
   and event types in scenarios are validated against the contracts
   (`SCENARIO-REFS-VALID`). In rejection scenarios (non-2xx),
   deliberately illegal values are fine — that's the point.
3. **Assertions use schema property paths.** Assert on the property
   names the response schema declares (`id`, not `dogId`; bare
   entity, not an invented wrapper key) so scenarios bind to the
   contract, not to a remembered shape.
4. **Every Then is observable at the contract surface.** A response
   field, header, status, subsequent API call, or published event.
   "All other sessions are revoked" is untestable unless an endpoint
   or event exposes it.
5. **POST scenarios carry the `Idempotency-Key` header** when the
   contract requires it — strictly read, a POST scenario without it
   tests a 400.
6. **Every `## US-xxx` section opens with a back-link to its PRD
   story** (`*Story: [US-xxx](prd.md#us-xxx-title-slug)*`), mirroring
   the PRD's forward link. The generated traceability matrix
   (`task docs:generate` → `traceability.html`) shows the full
   story → scenario → operation → event → error-code picture.

---

## US-001: [User story title]

*Story: [US-001](prd.md#us-001-title-slug)*

### Scenario US-001-A: [Happy-path scenario name]

```gherkin
Given [precondition]
When I [action]
Then the response status is [code]
And the response body matches schema [SchemaName]
And [further assertions]
```

### Scenario US-001-B: [Edge case]

```gherkin
Given [precondition]
When I [action that should be rejected]
Then the response status is [code]
And the response body code equals "[ERROR_CODE]"
```

---

## US-002: [User story title]

*Story: [US-002](prd.md#us-002-title-slug)*

### Scenario US-002-A: [Happy-path]

```gherkin
Given [precondition]
When I [action]
Then the response status is [code]
And [further assertions, including any domain event published]
```

---

## Cross-cutting

### Scenario CROSS-A: [Cross-cutting concern — e.g. expired token, refresh flow]

```gherkin
Given [precondition]
When I [action]
Then the response status is [code]
And [further assertions]
```
