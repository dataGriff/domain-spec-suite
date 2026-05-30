---
description: "Use when reading, referencing, or being asked about the business specifications in docs/specs/. These are authoritative business requirements — do not modify them to match code. Code must conform to specs, not the other way around."
applyTo: "docs/specifications/**"
---

# Specification Files — Read-Only Business Requirements

Files in `docs/specifications/` are **authoritative business requirements**. They are the source of truth for the entire codebase.

## Rules

- **Never modify a spec file to match existing code.** If code and spec disagree, the code is wrong.
- **Only change a spec file when there is an explicit, deliberate business decision** to do so — and that intent must be clear in the user's request. Spec changes must be reviewed separately from code changes.
- **Do not make incidental edits** to specs while working on code tasks (e.g. don't fix a spec "while you're in there").

## What each spec file governs

| File | Governs |
|------|---------|
| `specifications/prd.md` | Goals, personas, user stories — the *why* of every feature |
| `specifications/domain-model.md` | Entity names, attributes, relationships, business rules — naming must match in all code |
| `specifications/auth-matrix.md` | Which roles may perform which operations — all access control logic must match this exactly |
| `specifications/sequence-diagrams.md` | Interaction flows — the expected order of API calls and system events |
| `specifications/contracts/openapi.yaml` | REST API shapes, status codes, route paths — route handlers must conform to this |
| `specifications/contracts/asyncapi.yaml` | Domain event schemas and channel bindings — event publishers must conform to this |
| `specifications/contracts/datacontract.yaml` | ODCS 3.1 data contract — historical event payload field names, types, and constraints |

## Spec interdependencies

Specs are not independent — changing one often requires reviewing others.

**When changing `openapi.yaml`:** check whether the change introduces a new state transition (e.g. an entity is approved, archived, published). If yes, `asyncapi.yaml` likely needs a new channel/message and `datacontract.yaml` likely needs the payload schema.

**When changing `domain-model.md`:** check whether any renamed or added field appears in an event payload. If yes, update `datacontract.yaml` field names to match.

**Read-only GET endpoints and auth/parameter-only changes** do not produce state changes — no AsyncAPI or data contract review needed.

The test: *did the state of any domain entity change as a result of this operation?* If yes, review AsyncAPI and data contract before closing the change.

## When asked to update a spec

Confirm the intent is a deliberate business change before editing. Ask: "This would change the authoritative spec — is this a deliberate business decision?"

## Language in specs

Use business language throughout — name user stories, operations, and events with domain verbs (e.g. "Add item to catalogue", "Archive item", "Remove item") rather than generic CRUD verbs ("Create", "Update", "Delete"). Specs should read like business requirements, not database documentation.
