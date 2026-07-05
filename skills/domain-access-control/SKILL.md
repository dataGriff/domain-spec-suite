---
name: domain-access-control
description: |
  Phase 3. Drives `auth-matrix.md` and `error-catalogue.md` authoring.
  Soft + engagement gate. Hard errors (role with no description,
  empty matrix cell, incomplete error entry) refuse sign-off; warnings
  (role doesn't trace to a PRD persona) must each have an explicit
  response.
prerequisites:
  - Phase 1 (discovery) signed off — for persona traceability.
  - Phase 2 (modeling) signed off — for entity field references in
    ownership rules.
trigger_phrases:
  - "phase 3"
  - "start access control"
  - "draft the auth matrix"
  - "sign off access control"
---

# Phase 3 — Access Control

Produces two files: `auth-matrix.md` (roles, the operation×role
permission matrix, ownership rules) and `error-catalogue.md` (the
canonical error codes for the domain, with HTTP statuses and trigger
conditions).

## What this skill does

1. Verifies discovery + modeling have signed off.
2. **Author half.** If either output file is missing, runs
   `task init:access-control -- --repo <target>`. Then walks the user
   through:
   - Roles section: name, description, traces-to-persona (from PRD)
   - Auth Matrix table: every operation × role gets a permission
     marker (Public / Allowed / Allowed-if-owner / Forbidden)
   - Ownership Rule prose: how 'Allowed-if-owner' is checked
     (typically resource.field == caller.id)
   - Error catalogue: every error code with HTTP status, meaning,
     triggered-by
3. **Validate half.** Hard errors block sign-off; warnings need
   responses per the soft-gate engagement loop.
4. **Sign off.** Same shape as modeling — write a findings YAML with
   `warnings_responded:` and pass it via `--findings`.

## Authoring

The starting point is the PRD's personas + the modeling phase's
entities:

- Each PRD persona maps to one role in the auth matrix (sometimes a
  persona splits into multiple roles, sometimes two personas share
  a role).
- Each entity from the model becomes a noun in the operation column
  ("List items", "Edit walk", "Add invoice").
- Each operation × role cell needs an explicit permission decision.
  The Items convention uses emoji (🌐 Public, ✅ Allowed, 🔒 Owner,
  ❌ Forbidden) but the legend is the source of truth.

Error catalogue entries are pulled from the user stories' acceptance
criteria — every story that mentions a 4xx/5xx code by name needs a
matching catalogue entry.

Three matrix shapes that routinely get skipped — handle each
explicitly rather than leaving the row pattern to imply it:

- **Singleton resources** (`GET /v1/rate-card` — no id in the path).
  The row-per-endpoint ownership pattern assumes a resource id to
  gate on; a singleton's ownership rule must instead name the
  *implicit* scope ("the authenticated caller's walker") and define
  the empty state (what does a GET return before the first PUT —
  404, or 200 with an empty shape?).
- **Creates with body-referenced ids** (`POST /v1/walks` carrying
  `dogId`). The ownership qualifier on the row must cover the
  referenced entity ("🔒 own dog"), and the catalogue must say what
  a nonexistent body id returns (404 vs 403 vs 400) — path-parameter
  not-found rules don't cover it.
- **Token-addressed public endpoints** (invite acceptance, password
  reset). The matrix marks them 🌐, but the token *is* the
  credential: they need a rate-limit note and a defined never-existed
  response, or they're a brute-force surface.

## Soft-gate engagement loop

Same shape as Modeling (see that skill's SKILL.md). The one warning
in this phase's gate is `AUTH-ROLE-TRACES-TO-PERSONA` — when a role's
'Traces to persona' column is empty or doesn't match a PRD persona,
the user must either (a) fix the trace (resolved), (b) mark it as a
system role with `system` in the column (resolved), or (c) defer with
`required_by: <phase>`.

## How to run

```bash
mise exec -- task init:access-control -- --repo <target-dir>
mise exec -- task gate:access-control -- --repo <target-dir>
mise exec -- task sign-off:access-control -- --repo <target-dir> --findings <yaml>
```

Findings YAML shape:

```yaml
warnings_responded:
  - id: AUTH-ROLE-TRACES-TO-PERSONA
    response: resolved
    reason: "added 'system (scheduler)' to the Traces column for the cron-runner role"
rubric_findings: []
```

## Checks in this gate

### Hard errors (must pass)

- `AUTH-ROLE-HAS-DESCRIPTION` — every role has non-empty description
- `AUTH-MATRIX-COMPLETE` — no empty cells in the operation×role grid
- `ERROR-CATALOGUE-COMPLETE` — every error has HTTP status, meaning,
  triggered-by
- `ERROR-CODE-IN-CATALOGUE` — every error code referenced in the
  auth-matrix or downstream files appears in the catalogue

### Warnings (must each have a response)

- `AUTH-ROLE-TRACES-TO-PERSONA` — every role traces to a declared
  PRD persona or is marked `system`

### Skipped here, promoted at later phases

- `AUTH-MATRIX-OPENAPI-MATCH` — skipped when contracts/openapi.yaml
  doesn't exist yet. Promoted to error at Phase 6 (contracts) and
  Phase 7 (audit).

## Decision Log

Per SUITE-DESIGN §5.5 Decision Log. Access control is the highest-
stakes spec — silent decisions here ship as security regressions.
Emit `decisions:` entries for any non-mechanical choice:

```yaml
decisions:
  - id: OWNERSHIP-VIA-FK-TRAVERSAL
    summary: "Ownership rule traverses Client.invitedByWalkerId rather
      than embedding walkerId on every owned resource."
    rationale: "Single source of truth — changing a client's walker
      (if ever supported) updates one row, not many."
    affects: [docs/specifications/auth-matrix.md]
```

### Decision-prone areas in this phase

- **Ownership rule semantics.** FK traversal vs embedded ownership
  field on every resource. Which traversal path resolves "is this
  caller the owner of this resource?".
- **FORBIDDEN vs NOT_FOUND policy.** Whether 403 and 404 are
  distinguished or collapsed. Distinguishing is an existence oracle:
  cross-tenant 403 + nonexistent 404 lets an attacker probe ids to
  learn "exists but not yours" vs "doesn't exist". Collapsing (404
  for both) hides existence but complicates debugging. Either is
  defensible — but it MUST be an explicit Decision Log entry; the
  matrix's anti-leak rationale has to consider existence leakage,
  not just role leakage.
- **System roles.** Whether a non-user actor (scheduler, webhook
  receiver, background worker) gets a row in the matrix as a
  `system (...)` role or is left out of access control entirely.
- **Rate-limit scope.** Per-IP vs per-email vs per-user. Each is
  defensible for different threat models.
- **Cross-role permission decisions** the user gave a fast answer
  on. e.g. "Can owners mark their own invoices paid? No." — that's
  a real policy decision worth recording.
- **Authentication scope for token-bearing endpoints.** Invite
  accept and password-reset confirm are public-but-token-gated;
  record why this is treated differently from `BearerAuth`.

## What this skill never does

- Never writes a permission cell without explicit user confirmation.
  Access control is the highest-stakes spec — a wrong "Allowed" cell
  ships as a real security regression.
- Never relaxes the soft-gate engagement check. Every warning needs
  a response.

## Files this phase signs

- `docs/specifications/auth-matrix.md`
- `docs/specifications/error-catalogue.md`
