# Error Catalogue — Items

> Canonical error codes returned by the Items API. Every error code referenced
> in `contracts/openapi.yaml` responses or in `auth-matrix.md` appears here
> with its HTTP status, meaning, and the conditions that trigger it. Code
> implementations must use these codes exactly.

---

## Authentication errors (401)

### `AUTHENTICATION_REQUIRED`

**HTTP status:** 401 Unauthorized

**Meaning:** The request reached a protected route but did not include a
bearer token in the `Authorization` header.

**Triggered by:**
- Any authenticated route called with no `Authorization` header.
- An `Authorization` header that does not start with `Bearer `.

**Response shape:** `Error` (`code`, `message`).

### `TOKEN_EXPIRED`

**HTTP status:** 401 Unauthorized

**Meaning:** The bearer token presented was a valid signature but its
`exp` claim is in the past.

**Triggered by:**
- An access token used after its expiry (`expiresIn` seconds after issue).

**Resolution path:** Call `POST /v1/auth/refresh` with the refresh token
to obtain a fresh access token, then retry the original request.

**Response shape:** `Error` (`code`, `message`).

### `INVALID_CREDENTIALS`

**HTTP status:** 401 Unauthorized

**Meaning:** Login was attempted with credentials that do not match any
registered user.

**Triggered by:**
- `POST /v1/auth/login` with an email that does not exist.
- `POST /v1/auth/login` with a valid email but wrong password.

**Note:** The two cases are deliberately indistinguishable to the caller —
the response does not reveal which field was wrong.

**Response shape:** `Error` (`code`, `message`).

### `INVALID_REFRESH_TOKEN`

**HTTP status:** 401 Unauthorized

**Meaning:** The refresh token presented to `POST /v1/auth/refresh` is
malformed, expired, or has been revoked.

**Triggered by:**
- A refresh token that fails signature verification.
- A refresh token whose `exp` claim is in the past.
- A refresh token that has already been rotated out.

**Response shape:** `Error` (`code`, `message`).

---

## Authorization errors (403)

### `FORBIDDEN`

**HTTP status:** 403 Forbidden

**Meaning:** The caller is authenticated but lacks permission for this
operation. Used both for role-based denials and ownership-based denials.

**Triggered by:**
- A `viewer` attempting any write operation (POST/PATCH/DELETE on
  `/v1/items*`).
- A `contributor` attempting to edit or remove an item whose
  `contributorId` does not match their `id`.

**Response shape:** `Error` (`code`, `message`).

---

## Not-found errors (404)

### `ITEM_NOT_FOUND`

**HTTP status:** 404 Not Found

**Meaning:** The item referenced by the `itemId` path parameter does not
exist (or has been removed).

**Triggered by:**
- `GET /v1/items/{itemId}`, `PATCH /v1/items/{itemId}`, or
  `DELETE /v1/items/{itemId}` for an `itemId` that is not present in the
  catalogue.

**Response shape:** `Error` (`code`, `message`).

---

## Conflict errors (409)

### `EMAIL_ALREADY_REGISTERED`

**HTTP status:** 409 Conflict

**Meaning:** Registration was attempted with an email address that is
already associated with an existing user.

**Triggered by:**
- `POST /v1/auth/register` with an email that matches a `User.email`
  already in the store.

**Response shape:** `Error` (`code`, `message`).

---

## Validation errors (400)

### `VALIDATION_FAILED`

**HTTP status:** 400 Bad Request

**Meaning:** The request body or query parameters failed schema
validation against the OpenAPI contract.

**Triggered by:**
- Any field violating its `type`, `format`, `enum`, `minLength`,
  `minimum`, `maximum`, or `required` constraint as defined in
  `contracts/openapi.yaml`.
- `PATCH /v1/items/{itemId}` with an empty request body (violates
  `UpdateItemRequest.minProperties: 1`).

**Response shape:** `ValidationError` (`code`, `message`, `details[]`).
Each entry in `details` names the offending `field` and a one-line
`issue` description.

---

## Error code → HTTP status reference

| Code | HTTP | Used by operations |
|------|------|-------------------|
| `AUTHENTICATION_REQUIRED` | 401 | All authenticated operations |
| `TOKEN_EXPIRED` | 401 | All authenticated operations |
| `INVALID_CREDENTIALS` | 401 | `POST /v1/auth/login` |
| `INVALID_REFRESH_TOKEN` | 401 | `POST /v1/auth/refresh` |
| `FORBIDDEN` | 403 | `POST /v1/items`, `PATCH /v1/items/{itemId}`, `DELETE /v1/items/{itemId}` |
| `ITEM_NOT_FOUND` | 404 | `GET /v1/items/{itemId}`, `PATCH /v1/items/{itemId}`, `DELETE /v1/items/{itemId}` |
| `EMAIL_ALREADY_REGISTERED` | 409 | `POST /v1/auth/register` |
| `VALIDATION_FAILED` | 400 | All operations with a request body |

---

## Authoring rules

1. **Codes are SCREAMING_SNAKE_CASE.** Stable across versions.
2. **Codes are domain-meaningful, not HTTP-restating.** `ITEM_NOT_FOUND`,
   not `NOT_FOUND_404`.
3. **One trigger per code where possible.** `INVALID_CREDENTIALS` covers
   both unknown-email and wrong-password deliberately, to avoid leaking
   which one failed — that's the only intentional ambiguity.
4. **Messages are human-readable, not localised.** Localisation is
   downstream of v1.
