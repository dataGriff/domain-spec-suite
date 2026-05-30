# Acceptance Scenarios — Items

> Given/When/Then scenarios at contract level. Every user story in `prd.md`
> has at least one scenario here. Scenarios are written at the HTTP-request
> level — they reference operation IDs, paths, status codes, and response
> shapes from `contracts/openapi.yaml` directly, so they can drive
> contract-level test suites in any implementation.

---

## US-001: Register as a contributor or viewer

### Scenario US-001-A: Successful contributor registration

```gherkin
Given no user exists with email "alice@example.com"
When I POST /v1/auth/register with
  | email     | alice@example.com |
  | password  | hunter2hunter     |
  | firstName | Alice             |
  | lastName  | Adams             |
  | role      | contributor       |
Then the response status is 201
And the response body matches schema AuthResponse
And the response body contains a non-empty accessToken
And the response body contains a non-empty refreshToken
And user.role equals "contributor"
And no field named "password" appears anywhere in the response
```

### Scenario US-001-B: Successful viewer registration

```gherkin
Given no user exists with email "bob@example.com"
When I POST /v1/auth/register with role "viewer" and otherwise valid fields
Then the response status is 201
And user.role equals "viewer"
```

### Scenario US-001-C: Duplicate email rejected

```gherkin
Given a user exists with email "alice@example.com"
When I POST /v1/auth/register with email "alice@example.com" and otherwise valid fields
Then the response status is 409
And the response body code equals "EMAIL_ALREADY_REGISTERED"
```

### Scenario US-001-D: Invalid role rejected

```gherkin
When I POST /v1/auth/register with role "admin"
Then the response status is 400
And the response body code equals "VALIDATION_FAILED"
And the response body details contains an entry with field "role"
```

---

## US-002: Log in and receive tokens

### Scenario US-002-A: Successful login

```gherkin
Given a user exists with email "alice@example.com" and password "hunter2hunter"
When I POST /v1/auth/login with
  | email    | alice@example.com |
  | password | hunter2hunter     |
Then the response status is 200
And the response body matches schema AuthResponse
And the response body contains a non-empty accessToken
And the response body contains a non-empty refreshToken
```

### Scenario US-002-B: Wrong password rejected

```gherkin
Given a user exists with email "alice@example.com" and password "hunter2hunter"
When I POST /v1/auth/login with email "alice@example.com" and password "wrong"
Then the response status is 401
And the response body code equals "INVALID_CREDENTIALS"
```

### Scenario US-002-C: Unknown email rejected indistinguishably

```gherkin
Given no user exists with email "ghost@example.com"
When I POST /v1/auth/login with email "ghost@example.com" and any password
Then the response status is 401
And the response body code equals "INVALID_CREDENTIALS"
```

---

## US-003: Add an item to the catalogue

### Scenario US-003-A: Contributor adds an item

```gherkin
Given I am authenticated as a contributor with id "C1"
When I POST /v1/items with
  | name        | My First Item |
  | description | A great item  |
Then the response status is 201
And the response body matches schema Item
And the response body status equals "active"
And the response body contributorId equals "C1"
And the response body has a non-empty id
And the response body createdAt equals updatedAt
And an ItemAdded event is published on channel items.item.added
And the event payload data.id equals the response body id
```

### Scenario US-003-B: Viewer cannot add an item

```gherkin
Given I am authenticated as a viewer
When I POST /v1/items with name "Viewer Item"
Then the response status is 403
And the response body code equals "FORBIDDEN"
And no ItemAdded event is published
```

### Scenario US-003-C: Missing name rejected

```gherkin
Given I am authenticated as a contributor
When I POST /v1/items with no name
Then the response status is 400
And the response body code equals "VALIDATION_FAILED"
And the response body details contains an entry with field "name"
```

---

## US-004: List all items

### Scenario US-004-A: Contributor lists items with default pagination

```gherkin
Given the catalogue contains 25 items
And I am authenticated as a contributor
When I GET /v1/items
Then the response status is 200
And the response body matches schema ItemList
And the response body data has length 20
And the response body pagination.page equals 1
And the response body pagination.pageSize equals 20
And the response body pagination.total equals 25
```

### Scenario US-004-B: Viewer lists items

```gherkin
Given the catalogue contains 3 items
And I am authenticated as a viewer
When I GET /v1/items
Then the response status is 200
And the response body data has length 3
```

### Scenario US-004-C: Custom page size honoured up to the maximum

```gherkin
Given the catalogue contains 150 items
And I am authenticated as a viewer
When I GET /v1/items?page=2&pageSize=50
Then the response status is 200
And the response body data has length 50
And the response body pagination.page equals 2
And the response body pagination.pageSize equals 50
```

### Scenario US-004-D: Page size above maximum rejected

```gherkin
Given I am authenticated as a contributor
When I GET /v1/items?pageSize=200
Then the response status is 400
And the response body code equals "VALIDATION_FAILED"
And the response body details contains an entry with field "pageSize"
```

### Scenario US-004-E: Unauthenticated request rejected

```gherkin
When I GET /v1/items with no Authorization header
Then the response status is 401
And the response body code equals "AUTHENTICATION_REQUIRED"
```

---

## US-005: View a single item

### Scenario US-005-A: Existing item retrieved

```gherkin
Given an item exists with id "I1"
And I am authenticated as a viewer
When I GET /v1/items/I1
Then the response status is 200
And the response body matches schema Item
And the response body id equals "I1"
```

### Scenario US-005-B: Missing item returns 404

```gherkin
Given no item exists with id "I-ghost"
And I am authenticated as a contributor
When I GET /v1/items/I-ghost
Then the response status is 404
And the response body code equals "ITEM_NOT_FOUND"
```

---

## US-006: Edit my own item

### Scenario US-006-A: Owner archives their item

```gherkin
Given an item "I1" exists with status "active" and contributorId "C1"
And I am authenticated as a contributor with id "C1"
When I PATCH /v1/items/I1 with status "archived"
Then the response status is 200
And the response body status equals "archived"
And the response body updatedAt is later than the original updatedAt
And an ItemEdited event is published on channel items.item.edited
And the event payload data.status equals "archived"
```

### Scenario US-006-B: Owner reactivates their item

```gherkin
Given an item "I1" exists with status "archived" and contributorId "C1"
And I am authenticated as a contributor with id "C1"
When I PATCH /v1/items/I1 with status "active"
Then the response status is 200
And the response body status equals "active"
And an ItemEdited event is published
```

### Scenario US-006-C: Non-owner contributor rejected

```gherkin
Given an item "I1" exists with contributorId "C1"
And I am authenticated as a contributor with id "C2"
When I PATCH /v1/items/I1 with name "Hijacked"
Then the response status is 403
And the response body code equals "FORBIDDEN"
And the item's stored name is unchanged
And no ItemEdited event is published
```

### Scenario US-006-D: Viewer cannot edit

```gherkin
Given an item "I1" exists with any contributorId
And I am authenticated as a viewer
When I PATCH /v1/items/I1 with name "Viewer Edit"
Then the response status is 403
And the response body code equals "FORBIDDEN"
```

### Scenario US-006-E: Empty PATCH body rejected

```gherkin
Given an item "I1" exists with contributorId "C1"
And I am authenticated as a contributor with id "C1"
When I PATCH /v1/items/I1 with an empty body
Then the response status is 400
And the response body code equals "VALIDATION_FAILED"
```

---

## US-007: Remove my own item from the catalogue

### Scenario US-007-A: Owner removes their item

```gherkin
Given an item "I1" exists with contributorId "C1"
And I am authenticated as a contributor with id "C1"
When I DELETE /v1/items/I1
Then the response status is 204
And the response body is empty
And an ItemRemoved event is published on channel items.item.removed
And the event payload data.id equals "I1"
And the event payload data.contributorId equals "C1"
And the event payload data.removedAt is a valid ISO 8601 timestamp
And a subsequent GET /v1/items/I1 returns 404 with code "ITEM_NOT_FOUND"
```

### Scenario US-007-B: Non-owner contributor rejected

```gherkin
Given an item "I1" exists with contributorId "C1"
And I am authenticated as a contributor with id "C2"
When I DELETE /v1/items/I1
Then the response status is 403
And the response body code equals "FORBIDDEN"
And the item still exists
And no ItemRemoved event is published
```

### Scenario US-007-C: Viewer cannot remove

```gherkin
Given an item "I1" exists with any contributorId
And I am authenticated as a viewer
When I DELETE /v1/items/I1
Then the response status is 403
And the response body code equals "FORBIDDEN"
```

### Scenario US-007-D: Removing a missing item returns 404

```gherkin
Given no item exists with id "I-ghost"
And I am authenticated as a contributor
When I DELETE /v1/items/I-ghost
Then the response status is 404
And the response body code equals "ITEM_NOT_FOUND"
```

---

## Cross-cutting

### Scenario CROSS-A: Expired access token surfaces TOKEN_EXPIRED

```gherkin
Given my access token's exp claim is 1 second in the past
When I GET /v1/items
Then the response status is 401
And the response body code equals "TOKEN_EXPIRED"
```

### Scenario CROSS-B: Refresh flow yields a fresh token

```gherkin
Given I have a valid refresh token
When I POST /v1/auth/refresh with that refresh token
Then the response status is 200
And the response body matches schema AuthResponse
And the new accessToken differs from any previously issued accessToken
```

### Scenario CROSS-C: Logout invalidates session

```gherkin
Given I am authenticated as any role
When I POST /v1/auth/logout
Then the response status is 204
And the response body is empty
```
