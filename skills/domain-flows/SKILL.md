---
name: domain-flows
description: |
  Phase 4. Drives `sequence-diagrams.md` authoring. Soft + engagement
  gate. Hard error on missing diagram titles or participants; warnings
  on participants outside the known role/persona/system set, on PRD
  user-story groups without a matching flow, and on lifecycle
  transitions not appearing in any flow.
prerequisites:
  - Phase 1 (discovery) signed off — for user stories.
  - Phase 2 (modeling) signed off — for lifecycle transitions to
    cross-reference.
trigger_phrases:
  - "phase 4"
  - "start flows"
  - "draft the sequence diagrams"
  - "sign off flows"
---

# Phase 4 — Flows

Produces `sequence-diagrams.md` — Mermaid `sequenceDiagram` blocks
that walk through how the actors in the domain interact, with
explicit `participant` declarations and method-level arrows.

## What this skill does

1. Verifies discovery + modeling have signed off.
2. **Author half.** If `sequence-diagrams.md` is missing, runs
   `task init:flows -- --repo <target>`. Then walks the user through
   one flow per user-story-group:
   - Title (`## Flow N: <Group> — <descriptive title>`)
   - Mermaid block with `sequenceDiagram` and explicit `participant`
     declarations
   - Arrows for each request/response/event
3. **Validate half.** Hard error: every flow has a title + at least
   one participant. Warnings: participants are recognised; every
   story group has a matching flow; every lifecycle transition
   appears in some flow.
4. **Sign off.** Same shape as modeling — write findings YAML with
   `warnings_responded:` and pass via `--findings`.

## Authoring

The starting point is the PRD's user-story groups and the modeling
phase's lifecycle tables. Suggested workflow:

- One Mermaid block per story group (Authentication, Items, Walks,
  etc.). Title the block `## Flow N: <Group> — <verb-phrase>`.
- Inside each block, declare every participant up-front (`participant
  Client`, `participant API`, `participant EventBus`).
- For each user story in the group, draw the request arrow with
  HTTP method + path + (truncated) payload, then the response
  arrow, then any event publish arrow.
- For lifecycle transitions: add a `Note over API` comment within
  the relevant arrow showing the state change ("Note over API: item
  moves active → archived").

Mermaid's quirks: avoid `|` in payload text (breaks rendering),
escape colons in JSON examples (use `:` as text rather than YAML
syntax), keep arrow lines short (Mermaid wraps awkwardly).

## Soft-gate engagement loop

Same shape as Modeling. Warnings need responses (resolved / deferred
/ n-a). Typical n-a reasons:

- `FLOW-PARTICIPANT-IS-ROLE-OR-SYSTEM` n-a: a domain-specific
  external system that's not in the auth-matrix (e.g.
  `PaymentProvider`); document inline in the flow prose.
- `STORY-HAS-FLOW` n-a: a story group whose interactions are
  trivially captured in a single GET (no multi-step sequence to
  diagram).
- `LIFECYCLE-IN-FLOWS` n-a: a system-internal transition (e.g.
  scheduled expiry) that has no inbound API call.

## How to run

```bash
mise exec -- task init:flows -- --repo <target-dir>
mise exec -- task gate:flows -- --repo <target-dir>
mise exec -- task sign-off:flows -- --repo <target-dir> --findings <yaml>
```

Findings YAML:

```yaml
warnings_responded:
  - id: STORY-HAS-FLOW
    response: n-a
    reason: "Authentication group is covered by Flow 1's title rename — see Flow 1 'Authentication — Register and Log In'"
rubric_findings: []
```

## Checks in this gate

### Hard errors

- `FLOW-DIAGRAM-HAS-TITLE-PARTICIPANTS` — every flow block has a
  title + at least one `participant`

### Warnings

- `FLOW-PARTICIPANT-IS-ROLE-OR-SYSTEM` — participants are recognised
  roles / personas / system actors
- `STORY-HAS-FLOW` — every PRD user-story group has a matching flow
- `LIFECYCLE-IN-FLOWS` — every domain-model lifecycle transition is
  represented in some flow

## What this skill never does

- Never edits `sequence-diagrams.md` without confirmation.
- Never invents a flow not motivated by a user story or lifecycle.

## Files this phase signs

- `docs/specifications/sequence-diagrams.md`
