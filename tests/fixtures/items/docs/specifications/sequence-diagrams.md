# Sequence Diagrams — Items

Interaction flows for the Items domain. Diagrams reference operation
paths from `contracts/openapi.yaml` and event channels from
`contracts/asyncapi.yaml` by name.

---

## Flow 1: Register and Log In

```mermaid
sequenceDiagram
    participant Client
    participant API

    Client->>API: POST /v1/auth/register<br/>{ email, password, role: "contributor" }
    API-->>Client: 201 { accessToken, refreshToken, user }

    Client->>API: POST /v1/auth/login<br/>{ email, password }
    API-->>Client: 200 { accessToken, refreshToken, user }
```

---

## Flow 2: Contributor Creates and Manages Items

```mermaid
sequenceDiagram
    participant Contributor
    participant API
    participant EventBus

    Contributor->>API: POST /v1/items<br/>{ name: "My Item" }<br/>Authorization: Bearer <token>
    API-->>Contributor: 201 { id, name, status: "active", contributorId, ... }
    API->>EventBus: publish items.item.added

    Contributor->>API: GET /v1/items<br/>Authorization: Bearer <token>
    API-->>Contributor: 200 { data: [...], pagination: { page, pageSize, total } }

    Contributor->>API: PATCH /v1/items/{itemId}<br/>{ status: "archived" }<br/>Authorization: Bearer <token>
    API-->>Contributor: 200 { id, name, status: "archived", ... }
    API->>EventBus: publish items.item.edited

    Contributor->>API: DELETE /v1/items/{itemId}<br/>Authorization: Bearer <token>
    API-->>Contributor: 204
    API->>EventBus: publish items.item.removed
```

---

## Flow 3: Viewer Browses Items

```mermaid
sequenceDiagram
    participant Viewer
    participant API

    Viewer->>API: POST /v1/auth/login<br/>{ email, password }
    API-->>Viewer: 200 { accessToken, ... }

    Viewer->>API: GET /v1/items<br/>Authorization: Bearer <token>
    API-->>Viewer: 200 { data: [...], pagination: { ... } }

    Viewer->>API: GET /v1/items/{itemId}<br/>Authorization: Bearer <token>
    API-->>Viewer: 200 { id, name, description, status, ... }

    Viewer->>API: POST /v1/items<br/>{ name: "Viewer Item" }<br/>Authorization: Bearer <token>
    API-->>Viewer: 403 { code: "FORBIDDEN" }
```

---

## Flow 4: Token Refresh

```mermaid
sequenceDiagram
    participant Client
    participant API

    Note over Client: Access token has expired

    Client->>API: GET /v1/items<br/>Authorization: Bearer <expired_token>
    API-->>Client: 401 { code: "TOKEN_EXPIRED" }

    Client->>API: POST /v1/auth/refresh<br/>{ refreshToken }
    API-->>Client: 200 { accessToken, refreshToken }

    Client->>API: GET /v1/items<br/>Authorization: Bearer <new_token>
    API-->>Client: 200 { data: [...] }
```

---

## Flow 5: Non-Owner Edit Rejected

A contributor attempts to edit or remove an item that belongs to a
different contributor. The ownership check (see `auth-matrix.md`)
rejects the request and no `ItemEdited` event is published.

```mermaid
sequenceDiagram
    participant OtherContributor as Contributor (C2)
    participant API
    participant EventBus

    Note over API: An item exists with contributorId = C1

    OtherContributor->>API: PATCH /v1/items/{itemId}<br/>{ name: "Hijacked" }<br/>Authorization: Bearer <C2 token>
    API-->>OtherContributor: 403 { code: "FORBIDDEN" }
    Note over EventBus: no event published

    OtherContributor->>API: DELETE /v1/items/{itemId}<br/>Authorization: Bearer <C2 token>
    API-->>OtherContributor: 403 { code: "FORBIDDEN" }
    Note over EventBus: no event published
```

---

## Notes

- All authenticated requests include `Authorization: Bearer <token>`
  (omitted from some labels for brevity).
- Every `4xx` error path is enumerated in `auth-matrix.md` and
  `error-catalogue.md`. The flows above show the happy paths plus the
  two most diagnostically interesting failure paths (Viewer-attempts-write
  in Flow 3, Non-owner-edit/remove in Flow 5).
- Event publication is shown as a fire-and-forget message to an
  abstract `EventBus`; the concrete transport binding lives in
  `contracts/asyncapi.yaml` and is not part of this flow.
