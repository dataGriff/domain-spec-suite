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

Task 2.0 ensures the Items reference fixture is actually a complete,
audit-passing spec set *before* any audit code is written against it. The
current `domain-api-template` is missing four spec docs, all the state
files, the pre-push hook, and the audit workflow — without 2.0 the
subsequent tasks have nothing valid to test against.

### 2.0 Upgrade `domain-api-template` to v1.0 completeness — [ ]

Author the missing artefacts so the Items fixture (used by Tasks 2.3 and
onward) is a known-good, audit-passing spec set against the schemas defined
in `SUITE-DESIGN.md` §4 and §8.

Sub-tasks:

- [ ] Write `docs/specifications/glossary.md` covering every entity and
      attribute in the existing `domain-model.md`.
- [ ] Write `docs/specifications/error-catalogue.md` with the error codes
      referenced in `contracts/openapi.yaml`.
- [ ] Write `docs/specifications/nfr.md` with concrete measurable thresholds
      (numbers, percentages, or time units — no aspirational language).
- [ ] Write `docs/specifications/acceptance-scenarios.md` (Given/When/Then
      structure) mapping to PRD user stories.
- [ ] Write `docs/specifications/_progress.yaml` with all eight phases
      marked passed, `force_advances: []`, and the session_log section.
- [ ] Write `docs/specifications/_phase-{0..7}-passed.yaml` sidecars in the
      schema defined in `SUITE-DESIGN.md` §4 (`checks_passed`,
      `warnings_responded`, `rubric_findings`, `files_signed`). sha256s are
      seeded by hand for this fixture; `task fixtures:seed-signoffs`
      (introduced in 2.1) will regenerate them whenever fixture content
      changes.
- [ ] Write `docs/specifications/_ambiguities.md` with an empty Resolved
      section (Items has no open ambiguities by design).
- [ ] Write `docs/specifications/_bootstrap.yaml` recording the suite and
      gate version that produced the shell.
- [ ] Author `.githooks/pre-push` per `SUITE-DESIGN.md` §9 Tier 2 (Spectral
      on contracts, datacontract-cli, cross-file consistency, <15 s
      target).
- [ ] Author `.github/workflows/audit.yml` per §9 Tier 3 (full audit on
      PR, blocks merge).
- [ ] Reconcile `.github/instructions/` against the bootstrap manifest. The
      directory currently contains four files
      (`api-implementation.instructions.md`,
      `domain-template.instructions.md`, `specs.instructions.md`,
      `taskfile.instructions.md`). Decide whether
      `domain-template.instructions.md` survives the absorption (it
      describes the template itself, which no longer exists as a separate
      thing); if dropped, remove it; if kept, list it in the bootstrap
      manifest authored in 2.2.

**Exit criterion:** A hand-walk of every Phase 7 check enumerated in
`SUITE-DESIGN.md` §8 passes against `domain-api-template/`. Specifically:
no template placeholders remain, `_ambiguities.md` has no audit-required
unresolved items, every `_phase-N-passed.yaml` is present with sha256s
that match current file contents, and `force_advances:` is empty.

🛑 **Review checkpoint:** Walk through the fixture together. Confirm the
specs are realistic, the state files are coherent, and the hooks are
sensible before proceeding to 2.1.

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
- `task fixtures:seed-signoffs` — regenerate sha256s in every
  `tests/fixtures/*/docs/specifications/_phase-*-passed.yaml` against
  current file contents. Run whenever fixture content changes so the
  fixture's sign-off files stay valid against the staleness check.
- `task suite:force-advance` — wrapper that calls
  `shared/scripts/force_advance.py <phase> --reason '<text>'` on the
  current working domain repo. Used during dev to test the audit's
  force-advance handling. Writes an entry to `_progress.yaml`'s
  `force_advances:` array.
- `task suite:accept-force` — marks a `force_advances:` entry as
  `accepted: true` with a reason. Required to clear an audit failure
  caused by a force-advance.
- `task suite:upgrade-shell` — manifest-aware re-bootstrap that preserves
  spec content. Reads the target's `_template_manifest.yaml`, diffs
  against the bootstrap skill's templates, applies updates only to
  manifest entries. Never touches `docs/specifications/*.md` or
  `_*.yaml` state files.
- `task suite:reset-phase <phase>` — for dev only. Deletes the phase's
  sign-off file and the outputs it produced, so the phase can be re-run
  from scratch. Useful while iterating on a phase skill.

Also create `CLAUDE.md` at the suite repo root. Per the user's global
conventions, this is required so future Claude Code sessions know:
- the suite is Python-based (3.x pinned in `.mise.toml`)
- Taskfile is the single entry point for every check operation
- `tests/fixtures/items/` is the canonical reference fixture
- `SUITE-DESIGN.md` and `BUILD-PLAN.md` are mandatory reading at the start
  of every session
- conventional commit messages reference task IDs (e.g. `feat(2.2):
  bootstrap copies templates`)

Commit the scaffolding.

**Exit criterion:** Directory structure matches the layout above. `task --list`
runs cleanly even though most tasks are stubs. `CLAUDE.md` is in place.
`task fixtures:seed-signoffs` runs against the Items fixture from 2.0 and
produces no diff (sha256s already match).

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
  the bootstrap produces. Seed it once from `domain-api-template/` (the
  template is being absorbed into the suite per SUITE-DESIGN §1). From
  this point forward, all shell changes happen here.
  - `Taskfile.yml` (domain-repo Taskfile, with linting and docs tasks)
  - `.spectral-openapi.yaml`
  - `.spectral-asyncapi.yaml`
  - `.mise.toml`
  - `.gitignore`
  - `README.md.template` (with `{{domain_name}}` placeholder)
  - `mkdocs.yml.template`
  - `docs/index.md.template`
  - `docs/specifications/_template/*` (the blank spec templates,
    including glossary/error-catalogue/nfr/acceptance-scenarios
    skeletons added in M2.0)
  - `scripts/generate_domain_overview.py`
  - `.githooks/pre-commit`
  - `.githooks/pre-push` (authored in 2.0)
  - `.github/workflows/audit.yml` (authored in 2.0)
  - `.github/workflows/docs.yml` (GitHub Pages deploy)
  - `.github/CODEOWNERS`
- **Deliberate omissions: no agent guidance files.** The bootstrap does
  *not* install `CLAUDE.md`, `AGENTS.md`, or `.github/instructions/*.md`.
  This is the "strict skill-only" stance — the orchestrator and phase
  skills are the only sanctioned interface for spec-set changes. See
  SUITE-DESIGN §2 "Phase 0: Bootstrap specifics" for the rationale.
- [ ] Author `skills/domain-bootstrap/template_manifest.yaml` listing
  every file the bootstrap owns (path + expected sha256). The bootstrap's
  `--force` re-run consults this manifest to decide what may be
  overwritten; `task suite:upgrade-shell` consults the same manifest to
  compute its diff. The manifest is the *contract* between the suite and
  any domain repo it has bootstrapped.
- [ ] Implement the bootstrap logic: walk templates dir, copy each file to
  the target, substitute placeholders where present, create empty
  `_progress.yaml` (with `force_advances: []`) with Phase 0 marked passed,
  create `_bootstrap.yaml` recording suite/gate versions, copy the
  manifest into the target as `_template_manifest.yaml`.
- [ ] Implement non-empty-directory handling: refuse by default with a
  message pointing at `--force` or `task suite:upgrade-shell`; `--force`
  overwrites only files listed in the manifest, never spec content or
  `_*.yaml` state.
- [ ] Write a test (`task test:bootstrap`) that runs bootstrap in a temp
  directory and diffs the output against an expected snapshot. Also test
  the non-empty-directory paths (refuse, `--force`, manifest-respecting).

**Exit criterion:** Running the bootstrap skill in an empty directory
produces a repo whose contents match the canonical shell. `task test:bootstrap`
passes.

### 2.3 Build the audit skill (Phase 7) — [ ]

This is the second bookend gate. It's read-only and runs every
cross-reference check defined across all phases.

Sub-tasks:

- [ ] **Populate `shared/checks/` first.** Per SUITE-DESIGN §5.5 and §8,
  every cross-phase check lives here once as a Python module with the
  standard `metadata` block (id, category, phases, severity_by_phase,
  prerequisites) and `run(repo_root)` function. The audit skill references
  these check ids; M3 contracts skill reuses the same modules. No
  duplication. Modules to author at minimum:
  - `entity_in_glossary.py` — domain-model ↔ glossary
  - `entity_in_openapi_schema.py` — domain-model ↔ contracts/openapi
  - `field_match_domain_openapi.py` — field names align
  - `write_op_has_asyncapi_channel.py` — OpenAPI ↔ contracts/asyncapi
  - `event_in_datacontract.py` — asyncapi ↔ contracts/datacontract
  - `auth_matrix_openapi_match.py` — auth-matrix ↔ openapi
  - `error_code_in_catalogue.py` — openapi responses ↔ error-catalogue
  - `prd_story_persona_link.py` — prd stories ↔ prd personas
  - `lifecycle_in_flows.py` — domain-model lifecycles ↔ sequence-diagrams
  - `no_template_placeholders.py` — no `[Resource1]`, `[Domain]`, `{{`
  - `signoff_sha256_matches.py` — `_phase-N-passed.yaml` ↔ file sha256s
  - `ambiguities_no_audit_required.py` — `_ambiguities.md` has no
    audit-required open items
  - `force_advances_all_accepted.py` — `_progress.yaml` `force_advances:`
    has no `accepted: false` entries
- [ ] Create `skills/domain-conformance-audit/SKILL.md` referencing the
  prompting style in §7 and the rubric handling in §5.5 (audit itself has
  no rubric checks — it's purely mechanical re-verification).
- [ ] Create `skills/domain-conformance-audit/gate.yaml` listing the
  shared-check ids the audit runs, in order. Categories the audit covers:
  - Structural integrity (all expected files present, all parse)
  - Cross-reference (the shared modules above)
  - Tool checks (Spectral on OpenAPI/AsyncAPI, datacontract-cli)
  - Sign-off integrity (`signoff_sha256_matches`)
  - No unresolved deferrals (`ambiguities_no_audit_required`)
  - No unaccepted force-advances (`force_advances_all_accepted`)
  - No template placeholders (`no_template_placeholders`)
  - Generator script produces clean output, per the tightened SUITE-DESIGN
    §8 Phase 7 definition (exit 0, no placeholders, every entity present,
    no stderr noise). Author this as a Python script that invokes the
    generator and verifies the four conditions.
- [ ] The skill produces a structured report:
  - Pass/fail per check
  - Failure messages phrased as interview questions (not lint diagnostics)
  - Summary of total counts
- [ ] Set up the test fixture: copy `domain-api-template/` (now in its
  v1.0-complete state from Task 2.0) into `tests/fixtures/items/`. This
  is the known-good reference spec set.

**Exit criterion:** Running the audit against the Items fixture produces
"audit passed" with all checks green. Every shared module has at least one
unit test in the suite's own test suite.

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

- [ ] Create `skills/domain-contracts/SKILL.md`. No rubric checks for
  contracts (purely mechanical).
- [ ] Create `skills/domain-contracts/gate.yaml` referencing shared-check
  ids authored in 2.3. **Reuse only — do not duplicate.** The same
  `auth_matrix_openapi_match`, `entity_in_openapi_schema`, etc., modules
  that the audit consumes are the ones contracts consumes; their
  `phases:` metadata already lists `contracts`. The contracts skill adds
  only:
  - Tool checks: Spectral on OpenAPI, Spectral on AsyncAPI, datacontract-cli
    (these are wrapped as shared modules too:
    `spectral_openapi.py`, `spectral_asyncapi.py`, `datacontract_lint.py`
    — author them under `shared/checks/` here if they weren't already
    needed by the audit).
- [ ] Implement: skill loads contracts (or copies templates if absent),
  runs the §5 gate loop, and refuses sign-off via `shared/sign_off.py`
  while any check fails (the mechanical-enforcement path per §5.5).
- [ ] Sign-off writes `_phase-6-passed.yaml` with sha256s and timestamp.

**Exit criterion:** Skill against the Items fixture produces clean sign-off.
Skill against deliberately malformed contracts produces actionable failures
and refuses sign-off.

### 3.2 Validate hard gate enforcement — [ ]

- [ ] Confirm the skill cannot produce a sign-off file while
  `task gate:contracts` exits non-zero. The test should attempt every
  obvious bypass (asking the agent nicely, providing a hand-rolled
  sign-off file path) and confirm none of them works — only
  `shared/sign_off.py` writes the file, and it refuses on non-zero exit.
- [ ] Confirm the only escape is `task suite:force-advance contracts
  --reason '<text>'`. The test verifies:
  - A `force_advances:` entry is appended to `_progress.yaml` with
    `accepted: false`.
  - The phase is signed off despite the failure.
  - Running the audit immediately reports
    `force_advances_all_accepted` as FAIL with an actionable message.
  - `task suite:accept-force contracts --reason '<text>'` flips the
    entry to `accepted: true` and a re-audit then passes.

**Exit criterion:** Hard gate is genuinely hard. No path to false sign-off
exists. The force-advance escape is honest — visible in `_progress.yaml`
and fails the audit until explicitly accepted.

🛑 **Review checkpoint:** Demo contracts skill, including failure mode and
the `--force-advance` audit trail.

---

## Milestone 4: Discovery Skill (Phase 1) and Orchestrator

**Goal:** First-class user-facing entry point exists. A new user can start
in an empty directory and be walked through Bootstrap + Discovery, ending
with a valid `prd.md`.

### 4.1 Build the orchestrator — [x]

- [x] Create `skills/domain-orchestrator/SKILL.md`. Description triggers on
  starting any spec work or being invoked by name.
- [x] Implement state reading via `scripts/orchestrator_status.py` — the
  script is the single mechanical-enforcement path (sha256-based
  staleness per §6); SKILL.md instructs the agent to invoke it via
  `task suite:status -- --json` and render in §7 voice.
- [x] Implement phase routing: SKILL.md walks each `next_action` value
  (bootstrap / start / resume / update-mode / accept-force-advances /
  not-implemented / complete) and prescribes the prompt+handoff.
- [x] Implement update mode (Section 6 of SUITE-DESIGN.md): on stale
  detection, present the three options and route accordingly.
- [x] Stub-friendly: phases without skills surface as `not-implemented`
  so the agent tells the user honestly rather than routing into a stub.

**Exit criterion:** Running the orchestrator in a bootstrapped-but-otherwise-
empty domain repo correctly prompts to begin Phase 1.
**Status:** ✅ verified by `tests/test_orchestrator.py` (fresh repo →
bootstrap; post-bootstrap → discovery; modified PRD → update-mode;
force-advance → accept-force-advances; un-implemented phase → not-
implemented; full Items fixture → complete).

### 4.2 Build the discovery skill — [x]

This is the most design-heavy skill because the question bank drives PRD
elicitation quality.

- [x] Create `skills/domain-discovery/SKILL.md` with a `## Rubric checks`
  section carrying the two Phase 1 rubric rules
  (`RUBRIC-PROBLEM-USER-PAIN`, `RUBRIC-METRICS-MEASURABLE`). Prose
  describes the pass/warn conditions; SUITE-DESIGN §5.5 governs how
  the agent emits findings into `_phase-1-passed.yaml`.
- [x] `skills/domain-discovery/gate.yaml` references the 8 structural
  check ids from SUITE-DESIGN §8 Phase 1. Six modules live under
  `skills/domain-discovery/checks/` (phase-local); `PRD-STORY-PERSONA-LINK`
  is the shared cross-reference module (also re-run by audit).
- [x] `skills/domain-discovery/questions.md` carries one rich-schema
  entry per gate-check id. Coverage is enforced by
  `scripts/check_questions_coverage.py`, wired into `task lint`.
- [x] Loop spec lives in SKILL.md (load PRD → init from template if
  absent → run gate → for each failure look up question by
  `binds_to_check` → ask `lead_in` → probes if vague → reflect →
  re-run → sign off when clean). The interactive loop is the agent's
  responsibility at runtime; the mechanical pieces (gate, sign-off,
  template copy) are all Python.
- [x] Reflect-before-writing is documented as the §7 Hard Rule 3
  contract; SKILL.md instructs the agent never to silently write
  after a free-text answer.

**Exit criterion:** Starting from an empty bootstrapped repo, the
orchestrator + discovery skill can drive a user through producing a valid
`prd.md` that passes Phase 1's hard gate. Test on a new domain (not Items —
choose something different to avoid overfitting). Confirm `rubric_findings:`
appear in the resulting `_phase-1-passed.yaml` with the user's responses.
**Status:** ✅ machine-verified by `tests/test_discovery.py` (gate passes
against Items, every BUILD-PLAN id appears in gate + questions, 8
deliberate breaks each fail their expected check). End-to-end on a
non-Items domain is the M4.3 / 🛑 review demo.

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

### 5.0 Soft-gate enforcement in sign_off — [x]

- [x] `shared/sign_off.py` collects warning-severity outcomes and refuses
  to write the sidecar unless every warning has a corresponding entry in
  `warnings_responded` (resolved / deferred / n-a, with `reason` and —
  when deferred — `required_by: <phase>`)
- [x] Validates response shape (no stale entries, valid response value,
  deferred entries carry required_by)
- [x] Tests: `tests/test_soft_gate.py` (6 cases — refuses missing, accepts
  resolved/n-a/deferred-with-required_by, rejects stale/invalid/deferred-
  without-required_by)

### 5.1 Modeling skill (Phase 2) — [x]

- [x] `SKILL.md`, `gate.yaml`, `questions.md`. Templates already in
  bootstrap (`_template/domain-model.md`, `_template/glossary.md`)
- [x] Mandatory-engagement loop documented in SKILL.md
- [x] Cross-references via shared `ENTITY-IN-GLOSSARY` and
  `GLOSSARY-COVERS-ATTRIBUTES` (both also run at audit)
- [x] 6 phase-local checks (3 hard error, 3 warning) + 1 shared cross-ref
- [x] Sign-off writes `_phase-2-passed.yaml`
- [ ] Known v1 limitation: no PRD-ENTITY-IN-MODEL heuristic (false-positive
  cost too high; documented in SKILL.md)

**Exit:** Skill runs cleanly against the Items fixture, produces 6 PASS +
1 WARN (User has no `updatedAt` — fixture marks n-a in soft-gate loop).

### 5.2 Access Control skill (Phase 3) — [x]

- [x] `SKILL.md`, `gate.yaml`, `questions.md`. Templates from bootstrap.
- [x] Cross-references via new shared `AUTH-ROLE-TRACES-TO-PERSONA` (PRD
  personas) and reused `AUTH-MATRIX-OPENAPI-MATCH` /
  `ERROR-CODE-IN-CATALOGUE`
- [x] Produces both `auth-matrix.md` and `error-catalogue.md`
- [x] 3 phase-local hard checks + 1 shared warning + 2 shared
  cross-refs (one skipped at AC phase, promoted at contracts/audit)

**Exit:** Skill runs cleanly against Items fixture, 6/6 PASS.

### 5.3 Flows skill (Phase 4) — [x]

- [x] `SKILL.md`, `gate.yaml`, `questions.md`. Templates from bootstrap.
- [x] Cross-references via new shared `STORY-HAS-FLOW` and reused
  `LIFECYCLE-IN-FLOWS`
- [x] Produces Mermaid sequence diagrams
- [x] 2 phase-local checks (1 hard error, 1 warning) + 2 shared warnings

**Exit:** All flow checks pass against Items fixture (after Flow 1
rename to "Authentication — Register and Log In" to cross-reference
the Authentication story group cleanly).

### 5.4 NFRs skill (Phase 5) — [x]

- [x] `SKILL.md`, `gate.yaml`, `questions.md`. Templates from bootstrap.
- [x] Produces both `nfr.md` and `acceptance-scenarios.md`
- [x] Push-back via questions.md probes + RUBRIC-NFR-REALISTIC rubric in
  SKILL.md prose
- [x] 1 phase-local hard check + 1 warning

**Exit:** Items fixture passes hard check (every scenario has When+Then);
1 expected warning fires on the 3 behavioural NFRs (NFR-DATA-002,
NFR-OBS-003, NFR-COMPAT-001), each addressable as n-a via the
engagement loop.

**Design correction from build:** the original BUILD-PLAN said "skill
refuses to record an NFR without a measurable threshold". That's too
strict — real NFRs include behavioural guarantees ("no field removed
within a major version") and deliberate non-requirements ("no
durability requirement for v1"). Softened to a warning that the
engagement loop captures.

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
