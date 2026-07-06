---
name: domain-implement
description: |
  Drives the implementation of a completed domain spec set. Runs
  after audit is green, against a SEPARATE implementation repository
  — never the spec repo. Interviews the user for the stack choices
  the spec deliberately doesn't make (language, framework,
  persistence, hosting), scaffolds the implementation repo (including
  its AGENTS.md binding back to the specs), then works story by story
  in acceptance-scenario order with the scenarios as the acceptance
  test suite. The content authority is the spec repo's
  docs/implementation-guide.md — this skill is the interactive
  walk-through of that playbook, and adds no rules of its own.
prerequisites:
  - The spec repo's Phase 7 (audit) has signed off and `task audit`
    is green. Never implement from a spec set that doesn't pass its
    own gates.
  - An implementation target: an empty (or designated) repository
    separate from the spec repo.
trigger_phrases:
  - "implement the domain"
  - "implement this spec"
  - "build the api from the spec"
  - "start the implementation"
  - "domain implement"
---

# Domain Implement

The spec set is complete and audited; this skill turns it into a
running service. It is the interactive layer over the spec repo's
canonical playbook, `docs/implementation-guide.md` — read that file
first and treat it as the content authority (reading order, authority
map, build workflow, verification loop). If this skill and the guide
ever disagree, the guide wins and the disagreement is a suite bug.

## Ground rules

- **The spec repo is read-only from here.** Implementation work never
  edits `docs/specifications/`. When the implementation needs
  something the specs don't say — or reveals a spec bug — stop,
  surface it, and route it through the `domain-orchestrator` skill in
  the spec repo (update mode, sign-off, audit) before building
  against it.
- **The specs choose behaviour; the user chooses technology.** Never
  infer a stack from habit. Every technology decision is asked, not
  assumed.
- Follow SUITE-DESIGN §7's prompting style for all interview steps:
  one question per turn, reflect before acting, no filler.

## Step 1 — Pre-flight

1. Locate the spec repo (the directory the user names, or the cwd if
   it is one). Run `task audit` there; refuse to continue unless it
   exits green, pointing the user back at the orchestrator otherwise.
2. Read, in full: `docs/implementation-guide.md`, then the spec set
   in the guide's reading order.
3. Note the spec repo's current commit (and gate version from
   `.spec-suite/progress.yaml`) — the implementation pins against it.

## Step 2 — Stack interview

One question per turn, recording each answer. Cover at minimum:

- **Language + framework** for the API service.
- **Persistence** (engine + how migrations are managed). Remind the
  user the domain model constrains behaviour (uniqueness,
  immutability, lifecycles, aggregate atomicity), not schema style.
- **Event transport** (broker/bus) and how the transactional-outbox
  (or equivalent) will honour the delivery guarantee in `nfr.md`.
- **Auth mechanics** (JWT signing/rotation approach consistent with
  the auth NFRs).
- **Hosting/runtime target** and how NFR thresholds will be observed
  (metrics/logging stack).
- **Contract tooling**: how types/clients are generated from
  `openapi.yaml`/`asyncapi.yaml` in this stack.

Reflect the full stack back for confirmation before scaffolding.
These are implementation-repo decisions — record them in that repo
(README or ADRs), never in the spec repo.

## Step 3 — Scaffold the implementation repo

In the (separate) implementation repository:

1. Repo shell per the chosen stack's conventions (the user's
   conventions win; suggest a Taskfile/mise setup mirroring the spec
   repo's task-first principle so agents, developers, and CI run the
   same entry points).
2. **`AGENTS.md` at the implementation-repo root** (per the guide's
   "bind the implementation repo back to the specs" section): the
   spec repo URL + pinned commit/version, specs-are-upstream rule,
   pointer to the guide, scenarios-are-the-test-suite statement.
3. Contract-derived types/stubs (guide workflow step 1).
4. CI skeleton: contract validation + the acceptance-scenario test
   harness wired from day one, even while empty.

## Step 4 — Build loop

Follow the guide's build workflow order: types → persistence → auth
middleware → error surface → then **story by story** in
`acceptance-scenarios.md` order. Per story:

1. Read the story's PRD entry and its scenario section (they
   cross-link).
2. Implement the operations and event publications the scenarios
   exercise.
3. Automate that story's scenarios as end-to-end tests; run them.
   Green scenarios = the story is done; move to the next.
4. Surface every spec ambiguity or gap immediately (don't batch, and
   don't fill with invented behaviour).

Close with the guide's NFR pass and full verification loop.

## What this skill does NOT do

- No mechanical gate or sign-off exists for implementation (yet) —
  the acceptance-scenario suite is the enforcement. Real-world use
  will drive what gets mechanised (candidates: a scenario-coverage
  runner, a contract-conformance check against the pinned spec
  version).
- It never modifies the spec repo, its sidecars, or its progress
  state.
