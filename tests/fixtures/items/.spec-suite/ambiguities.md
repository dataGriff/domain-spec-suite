# Open Ambiguities

> Tracks every item the spec authors deliberately left unresolved or chose
> to defer to a later phase. Suite-managed file: orchestrator and phase
> skills append; human readers consult.

## Deferred to: audit

_None._

## Deferred to: post-v1

_None._

## Resolved

### ITEM-000: Should Contributor be its own entity?
- Recorded in phase: modeling
- Resolved in phase: modeling
- Decision: No — contributor is a role on `User`, not a separate entity.
  Items reference the owning user via `contributorId` pointing at
  `User.id`, and the role enum on `User` distinguishes `contributor`
  from `viewer`.
- Resolved at: 2026-05-25T15:15:00Z
