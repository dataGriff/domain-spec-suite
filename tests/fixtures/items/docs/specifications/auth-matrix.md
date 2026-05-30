# Auth Matrix — Items

## Roles

| Role | Description | Traces to persona |
|------|-------------|-------------------|
| `contributor` | Can add items and edit/remove their own items | Stockroom Lead (PRD §Target Users) |
| `viewer` | Read-only access to items | Operations Analyst (PRD §Target Users) |

## Authentication

All protected routes require a `Bearer` JWT token in the
`Authorization` header. Unauthenticated requests to protected routes
return `401` with code `AUTHENTICATION_REQUIRED`.

Tokens are issued via `POST /v1/auth/login` and refreshed via
`POST /v1/auth/refresh`. Token lifetimes are defined in `nfr.md`
NFR-SEC-001.

## Auth Matrix

| Operation | Endpoint | Public | contributor | viewer |
|-----------|----------|--------|-------------|--------|
| Register | `POST /v1/auth/register` | 🌐 | 🌐 | 🌐 |
| Login | `POST /v1/auth/login` | 🌐 | 🌐 | 🌐 |
| Refresh token | `POST /v1/auth/refresh` | 🌐 | 🌐 | 🌐 |
| Logout | `POST /v1/auth/logout` | ❌ | ✅ | ✅ |
| List items | `GET /v1/items` | ❌ | ✅ | ✅ |
| Add item | `POST /v1/items` | ❌ | ✅ | ❌ |
| View item | `GET /v1/items/{itemId}` | ❌ | ✅ | ✅ |
| Edit item | `PATCH /v1/items/{itemId}` | ❌ | 🔒 own | ❌ |
| Remove item | `DELETE /v1/items/{itemId}` | ❌ | 🔒 own | ❌ |

**Legend:**

- 🌐 Public — no auth required
- ✅ Allowed — any user holding this role may call the operation
- 🔒 own — Allowed only if the resource's ownership field matches the
  caller's user id
- ❌ Forbidden

## Ownership Rule

A `contributor` may only edit or remove items where
`item.contributorId` matches their user id (`req.user.sub`).
Attempting to modify another contributor's item returns `403` with
code `FORBIDDEN`. The same code is used for both *wrong role* and
*not the owner* failures, deliberately — the response does not reveal
which check failed.

## Error Responses

Every error returned by an auth check carries one of the codes
defined in `error-catalogue.md`. The mapping below is the auth
matrix's own short reference; `error-catalogue.md` is the
authoritative definition.

| Scenario | HTTP Status | Error Code |
|----------|-------------|------------|
| No token provided | `401` | `AUTHENTICATION_REQUIRED` |
| Token expired | `401` | `TOKEN_EXPIRED` |
| Login: wrong email or password | `401` | `INVALID_CREDENTIALS` |
| Refresh: invalid refresh token | `401` | `INVALID_REFRESH_TOKEN` |
| Valid token, wrong role | `403` | `FORBIDDEN` |
| Valid token, not item owner | `403` | `FORBIDDEN` |
