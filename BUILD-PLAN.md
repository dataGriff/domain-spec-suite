# BUILD-PLAN.md

> Operational checklist for building the **domain-spec-suite**.
>
> This document is the working brief for every Claude Code session. Read it
> first, identify the current task, work it to its exit criterion, update the
> checkboxes, and stop at the next review checkpoint.
>
> For design intent (the *why* behind decisions), see `SUITE-DESIGN.md`.

---

## How To Use This Document

1. At the start of every Claude Code session, read this file and
   `SUITE-DESIGN.md` in full before doing any other work.
2. Identify the current milestone — the first one not marked complete.
3. Within that milestone, identify the current task — the first not marked
   complete.
4. Work that task to its exit criterion.
5. Update this document by checking off the task.
6. Stop at the next human review checkpoint (marked 🛑) and summarize what
   was done.

Do not skip milestones. Do not skip tasks within a milestone. Do not mark a
task complete unless its exit criterion is genuinely met.

If a previously-checked task is found to have issues, uncheck it, leave a
comment about what went wrong, and address it before continuing.

## Conventions

- 🛑 = human review checkpoint. Stop here, summarize what was done, wait for
  user confirmation before continuing.
- [x] = task complete
- [ ] = task not started or in progress

## Working Style

- **Small commits.** Commit after each task, not at milestone boundaries.
  Commit messages should reference the task ID (e.g., "2.2: bootstrap skill
  copies template files").
- **Test as you go.** Don't write a skill and validate it later. Write,
  test, fix, commit.
- **Surface assumptions.** If anything in `SUITE-DESIGN.md` is ambiguous when
  applied to actual code, stop and ask the user before guessing.
- **Honest progress.** If a task takes longer than expected or hits a
  problem, say so. Don't silently expand scope or paper over issues.

---

## Milestone 1: Design Documents — [x] Complete

Produced in design conversation. `SUITE-DESIGN.md` and `BUILD-PLAN.md` exist
at repo root.

---

## Milestone 2: Repo Scaffolding, Bootstrap Skill, and Audit Skill

**Goal:** Suite repo has its own working structure, a bootstrap skill that
produces a valid domain repo shell, and an audit skill that catches
inconsistencies in an existing spec set.

This milestone tackles both bookends (bootstrap and audit) before any
interactive skills. The audit defines the truth criteria; the bootstrap
defines what files must exist for audit to operate on. Building both first
lets every later skill be tested against real fixtures.

### 2.1 Scaffold the suite repo itself — [ ]

Create the directory structure for the suite repo:

```
domain-spec-suite/
├── SUITE-DESIGN.md              (already present)
├── BUILD-PLAN.md                (already present)
├── README.md                    (new — describe what this repo is)
├── suite-version.yaml           (e.g. "1.0.0-alpha")
├── gate-version.yaml            (e.g. "1.0")
├── gate-changelog.md            (empty placeholder)
├── Taskfile.yml                 (suite-internal tasks)
├── skills/
│   ├── domain-orchestrator/     (empty for now)
│   ├── domain-bootstrap/        (empty for now)
│   ├── domain-discovery/        (empty for now)
│   ├── domain-modeling/         (empty for now)
│   ├── domain-access-control/   (empty for now)
│   ├── domain-flows/            (empty for now)
│   ├── domain-nfrs/             (empty for now)
│   ├── domain-contracts/        (empty for now)
│   └── domain-conformance-audit/ (empty for now)
├── shared/                      (cross-skill check libraries)
│   └── checks/
├── tests/
│   └── fixtures/                (sample domains for testing)
└── docs/                        (suite documentation, not domain docs)
```

Tasks in `Taskfile.yml` (suite-internal — these are different from the tasks
the suite *installs* in domain repos):

- `task test` — run all suite tests
- `task test:bootstrap` — test bootstrap skill against expected output
- `task test:audit` — test audit skill against fixtures
- `task lint` — lint suite's own code/configs
- `task fixtures:reset` — reset test fixtures to known state

Commit the scaffolding.

**Exit criterion:** Directory structure matches the layout above. `task --list`
runs cleanly even though most tasks are stubs.

🛑 **Review checkpoint:** Confirm directory layout matches user's expectation
before building skills.

### 2.2 Build the bootstrap skill (Phase 0) — [ ]

This skill, when invoked, populates an empty target repo with all the files
a domain spec repo needs.

Sub-tasks:

- [ ] Create `skills/domain-bootstrap/SKILL.md` with:
  - Description that triggers on "set up a new domain spec repo" or being
    invoked by the orchestrator on a fresh directory
  - Prerequisites: target directory exists and is empty (or `--force`)
  - Instructions for what to do
- [ ] Create `skills/domain-bootstrap/templates/` containing every file
  the bootstrap produces. This is essentially the contents of the existing
  `domain-api-template` repo, treated as the canonical shell.
  - `Taskfile.yml` (domain-repo Taskfile, with linting and docs tasks)
  - `.spectral-openapi.yaml`
  - `.spectral-asyncapi.yaml`
  - `.mise.toml`
  - `.gitignore`
  - `README.md.template` (with `{{domain_name}}` placeholder)
  - `mkdocs.yml.template`
  - `docs/index.md.template`
  - `docs/specifications/_template/*` (the blank spec templates)
  - `scripts/generate_domain_overview.py`
  - `.githooks/pre-commit`
  - `.githooks/pre-push`
  - `.github/workflows/audit.yml`
  - `.github/CODEOWNERS`
  - `AGENTS.md`
  - `.github/instructions/specs.instructions.md`
  - `.github/instructions/api-implementation.instructions.md`
  - `.github/instructions/taskfile.instructions.md`
- [ ] Implement the bootstrap logic: walk templates dir, copy each file to
  the target, substitute placeholders where present, create empty
  `_progress.yaml` with Phase 0 marked passed, create `_bootstrap.yaml`
  recording suite/gate versions.
- [ ] Write a test (`task test:bootstrap`) that runs bootstrap in a temp
  directory and diffs the output against an expected snapshot.

**Exit criterion:** Running the bootstrap skill in an empty directory
produces a repo whose contents match the canonical shell. `task test:bootstrap`
passes.

### 2.3 Build the audit skill (Phase 7) — [ ]

This is the second bookend gate. It's read-only and runs every
cross-reference check defined across all phases.

Sub-tasks:

- [ ] Create `skills/domain-conformance-audit/SKILL.md`
- [ ] Create `skills/domain-conformance-audit/gate.yaml` enumerating every
  check the audit runs. Categories:
  - Structural integrity (all expected files present, all parse)
  - Cross-reference (entity names match across files, etc.)
  - Tool checks (Spectral, datacontract-cli)
  - Sign-off integrity (`_phase-N-passed.yaml` sha256s match file contents)
  - No unresolved deferrals (`_ambiguities.md` has no audit-required items
    still open)
  - No template placeholders remain
- [ ] Implement each check as a script in
  `skills/domain-conformance-audit/checks/`. Where possible, factor shared
  check logic into `shared/checks/` so the contracts skill (Milestone 3)
  can reuse it.
- [ ] The skill produces a structured report:
  - Pass/fail per check
  - Failure messages phrased as interview questions (not lint diagnostics)
  - Summary of total counts
- [ ] Set up a test fixture: copy the existing `domain-api-template` repo
  (with the Items example specs filled in) into `tests/fixtures/items/`.
  This is the "known-good" reference spec set.

**Exit criterion:** Running the audit against the Items fixture produces
"audit passed" with all checks green.

### 2.4 Validate audit catches breaks — [ ]

Create a test that deliberately introduces breaks and confirms the audit
catches each.

For each break below, the test:
1. Copies the clean Items fixture to a temp directory
2. Applies one specific break
3. Runs the audit
4. Confirms the audit fails with a specific expected error code/message
5. Confirms the failure message reads like an interview question

Breaks to test:

- [ ] Rename a field in `domain-model.md` but not in `openapi.yaml`
- [ ] Remove an AsyncAPI channel that corresponds to a write operation
- [ ] Add a role to `auth-matrix.md` that isn't in the `RegisterRequest`
  enum in `openapi.yaml`
- [ ] Leave an unreplaced `[Resource1]` placeholder somewhere
- [ ] Add a user story in `prd.md` that mentions a nonexistent persona
- [ ] Modify `prd.md` without re-signing Phase 1 (staleness detection)
- [ ] Remove an event from AsyncAPI but leave its entry in `datacontract.yaml`
- [ ] Add an OpenAPI operation with no auth-matrix entry
- [ ] Add an entity to `domain-model.md` with no glossary entry
- [ ] Leave a deferred ambiguity marked `required-by: audit` unresolved

**Exit criterion:** All breaks caught, all failure messages actionable. Tests
run via `task test:audit` and all pass.

🛑 **Review checkpoint:** Demo the audit skill against the Items fixture and
against several deliberate breaks. Confirm failure messages are clear and
actionable before proceeding to Milestone 3.

---

## Milestone 3: Contracts Skill (Phase 6)

**Goal:** Hard-gated skill that orchestrates contract linting and cross-file
consistency, refusing sign-off unless all checks pass.

### 3.1 Build the contracts skill — [ ]

- [ ] Create `skills/domain-contracts/SKILL.md`
- [ ] Create `skills/domain-contracts/gate.yaml` with:
  - Tool checks: Spectral on OpenAPI, Spectral on AsyncAPI, datacontract-cli
  - Cross-reference checks: domain-model entities match OpenAPI schemas,
    write operations have AsyncAPI channels, event payloads match
    datacontract, auth-matrix operations match OpenAPI, error codes match
    error-catalogue
- [ ] Implement: skill loads contracts (or copies templates if absent),
  runs the gate loop (Section 5 of SUITE-DESIGN.md), and refuses sign-off
  while any check fails.
- [ ] Where checks duplicate audit checks, use shared library code from
  `shared/checks/`.
- [ ] Sign-off writes `_phase-6-passed.yaml` with sha256s and timestamp.

**Exit criterion:** Skill against the Items fixture produces clean sign-off.
Skill against deliberately malformed contracts produces actionable failures
and refuses sign-off.

### 3.2 Validate hard gate enforcement — [ ]

- [ ] Confirm skill cannot be told to sign off while checks fail.
- [ ] Confirm the only escape is the explicit `--force-advance` mechanism,
  which gets logged in `_progress.yaml`.
- [ ] Confirm the audit (Milestone 2) catches a forced advance as a
  finding.

**Exit criterion:** Hard gate is genuinely hard. No path to false sign-off
exists.

🛑 **Review checkpoint:** Demo contracts skill, including failure mode and
the `--force-advance` audit trail.

---

## Milestone 4: Discovery Skill (Phase 1) and Orchestrator

**Goal:** First-class user-facing entry point exists. A new user can start
in an empty directory and be walked through Bootstrap + Discovery, ending
with a valid `prd.md`.

### 4.1 Build the orchestrator — [ ]

- [ ] Create `skills/domain-orchestrator/SKILL.md`. Description triggers on
  starting any spec work or being invoked by name.
- [ ] Implement state reading: parse `_progress.yaml`, identify current
  phase, identify staleness.
- [ ] Implement phase routing: prompt user with phase description and
  confirmation, hand off to phase skill, accept sign-off, prompt for next
  phase.
- [ ] Implement update mode (Section 6 of SUITE-DESIGN.md): on detecting
  staleness, present the three options and route accordingly.
- [ ] Stub-friendly: phase skills not yet implemented should be invoked
  gracefully and the orchestrator should handle "phase not yet implemented"
  responses by reporting honestly to the user.

**Exit criterion:** Running the orchestrator in a bootstrapped-but-otherwise-
empty domain repo correctly prompts to begin Phase 1.

### 4.2 Build the discovery skill — [ ]

This is the most design-heavy skill because the question bank drives PRD
elicitation quality.

- [ ] Create `skills/domain-discovery/SKILL.md`
- [ ] Create `skills/domain-discovery/gate.yaml` with the structural and
  rubric checks listed in SUITE-DESIGN.md Section 8 Phase 1
- [ ] Create `skills/domain-discovery/questions.md` — the elicitation bank.
  This is a structured set of questions per gate check, with example good
  and bad answers, and follow-up probes for vague responses.
- [ ] Implement the loop:
  - Load `prd.md` if exists, else copy from template
  - Run checks, collect failures
  - For each failure, pick the question from `questions.md` and ask
  - Receive answer, reflect-before-writing, apply edit, re-run checks
  - When all checks pass, write sign-off, return to orchestrator
- [ ] Implement reflect-before-writing for structural changes
  (adding/removing personas, stories, metrics). Trivial edits (typo fixes)
  can be quiet writes.

**Exit criterion:** Starting from an empty bootstrapped repo, the
orchestrator + discovery skill can drive a user through producing a valid
`prd.md` that passes Phase 1's hard gate. Test on a new domain (not Items —
choose something different to avoid overfitting).

### 4.3 Test resumption — [ ]

- [ ] Start a discovery session, get partway through, end the conversation
  (simulate by exiting Claude Code mid-session).
- [ ] Start a new conversation, invoke orchestrator.
- [ ] Confirm it correctly identifies the in-progress state, summarizes
  what's been captured so far, and resumes at the right question.

**Exit criterion:** Resumption works without state loss. The user does not
have to re-answer questions already answered.

🛑 **Review checkpoint:** Demo orchestrator + discovery end-to-end on a new
domain. Confirm PRD output quality and resumption behavior.

---

## Milestone 5: Soft Middle Skills

**Goal:** All four soft-gate phase skills exist and integrate with the
orchestrator.

Each of these is structurally similar to discovery but with soft+engagement
gates instead of hard gates. They can be built in any order or in parallel.

### 5.1 Modeling skill (Phase 2) — [ ]

- [ ] `SKILL.md`, `gate.yaml`, `questions.md`, `templates/`
- [ ] Mandatory-engagement loop: warnings can become passes, deferrals, or
  non-applicable-with-reason
- [ ] Cross-references PRD entities
- [ ] Sign-off writes `_phase-2-passed.yaml`

**Exit:** Skill runs cleanly against a real PRD, produces valid
`domain-model.md` and `glossary.md`, deferrals get logged correctly.

### 5.2 Access Control skill (Phase 3) — [ ]

- [ ] `SKILL.md`, `gate.yaml`, `questions.md`, `templates/`
- [ ] Cross-references PRD personas and domain-model entities
- [ ] Produces both `auth-matrix.md` and `error-catalogue.md`

**Exit:** Skill produces valid access control specs that cross-reference
upstream phases correctly.

### 5.3 Flows skill (Phase 4) — [ ]

- [ ] `SKILL.md`, `gate.yaml`, `questions.md`, `templates/`
- [ ] Cross-references PRD user stories and domain-model lifecycles
- [ ] Produces Mermaid sequence diagrams

**Exit:** Every PRD user story has at least one sequence diagram. Every
state lifecycle transition appears in a flow.

### 5.4 NFRs skill (Phase 5) — [ ]

- [ ] `SKILL.md`, `gate.yaml`, `questions.md`, `templates/`
- [ ] Produces both `nfr.md` and `acceptance-scenarios.md`
- [ ] Push-back on vague thresholds is critical here — the prompting style
  rules apply heavily

**Exit:** Skill refuses to record an NFR without a measurable threshold.

🛑 **Review checkpoint after all four are built:** Demo each skill running
on a real domain. Confirm soft-gate mechanics (defer/resolve/non-applicable)
work correctly.

---

## Milestone 6: End-to-End Validation

**Goal:** The full suite, used as designed, produces a usable spec set for
a non-Items domain.

### 6.1 Choose a non-Items test domain — [ ]

User picks. Suggested characteristics:
- Materially different from Items (more entities, more roles, real state
  transitions)
- Not so complex it takes weeks
- Realistic enough that the audit output looks like something a real team
  would use

**Exit:** A short brief written for the chosen domain that the user is
comfortable being walked through.

### 6.2 Run the full suite — [ ]

Start with an empty directory. Run the orchestrator. Walk through:
- Phase 0: Bootstrap
- Phase 1: Discovery
- Phase 2: Modeling
- Phase 3: Access Control
- Phase 4: Flows
- Phase 5: NFRs
- Phase 6: Contracts
- Phase 7: Audit

Note any friction, confusion, or skill bugs during the run. After the run,
log issues for v1.0.1.

**Exit:** Audit passes. Spec set looks like something the user would hand
to an implementation team with confidence.

### 6.3 Test update mode — [ ]

After audit passes:
- Amend the PRD (add a new user story that introduces a new entity or role)
- Re-invoke orchestrator
- Confirm update mode walks through affected phases
- Final audit passes again

**Exit:** Update mode works end-to-end with real downstream effects.

### 6.4 Document any bugs/improvements found — [ ]

Whatever was noted during 6.2 and 6.3, capture in a `v1.0.1-backlog.md`
file. These don't block v1.0.0 unless they're genuinely broken.

🛑 **Final review.** Declare suite v1.0.0 complete if user agrees.

---

## Post-v1 Backlog

Things noted during design but not in scope for v1:

- ADR (Architectural Decision Record) support — phase or fold into existing
- Multi-user collaboration — locking, merge resolution
- Field-level update mode — finer than phase-level
- Generic (non-SKILL.md) packaging for portability to other agents
- Capacity / sizing doc as a separate phase
- Integrations / external dependencies doc

---

## Notes for Claude Code

A few reminders that apply throughout:

**Read the design doc first.** Every session. The design doc is short
enough to re-read, and it prevents drift.

**Don't invent new files or directories not in this plan.** If you think
something is missing, stop and ask. The plan is deliberately complete; if
you find a gap, the user wants to know about it before you fill it.

**Tests are not optional.** Each milestone's exit criteria reference real
tests. Don't claim a task complete because the code "looks right" — only
because tests confirm it works.

**Commit messages reference task IDs.** "2.2: bootstrap copies templates"
not "added bootstrap." This makes the git history map to the plan.

**Surface scope creep.** If a task is taking much longer than expected, or
revealing complexity not anticipated in the plan, stop and report rather
than expanding scope silently.

**The user reviews at every 🛑.** Don't push past one of these without an
explicit user response.

---

*End of BUILD-PLAN.md*
