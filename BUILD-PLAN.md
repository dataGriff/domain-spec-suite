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

> **Checkbox reconciliation (2026-07-04):** this milestone (and M3)
> shipped during the v1.0.x build — the scaffold, bootstrap, audit,
> and their tests all exist and are exercised by CI — but the boxes
> were never ticked. Checked retroactively; the git history
> (`feat(2.x)` / `feat(3.x)` commits) is the per-task record.

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

### 2.0 Upgrade `domain-api-template` to v1.0 completeness — [x]

Author the missing artefacts so the Items fixture (used by Tasks 2.3 and
onward) is a known-good, audit-passing spec set against the schemas defined
in `SUITE-DESIGN.md` §4 and §8.

Sub-tasks:

- [x] Write `docs/specifications/glossary.md` covering every entity and
      attribute in the existing `domain-model.md`.
- [x] Write `docs/specifications/error-catalogue.md` with the error codes
      referenced in `contracts/openapi.yaml`.
- [x] Write `docs/specifications/nfr.md` with concrete measurable thresholds
      (numbers, percentages, or time units — no aspirational language).
- [x] Write `docs/specifications/acceptance-scenarios.md` (Given/When/Then
      structure) mapping to PRD user stories.
- [x] Write `.spec-suite/progress.yaml` with all eight phases
      marked passed, `force_advances: []`, and the session_log section.
- [x] Write `.spec-suite/phases/phase-{0..7}-passed.yaml` sidecars in the
      schema defined in `SUITE-DESIGN.md` §4 (`checks_passed`,
      `warnings_responded`, `rubric_findings`, `files_signed`). sha256s are
      seeded by hand for this fixture; `task fixtures:seed-signoffs`
      (introduced in 2.1) will regenerate them whenever fixture content
      changes.
- [x] Write `.spec-suite/ambiguities.md` with an empty Resolved
      section (Items has no open ambiguities by design).
- [x] Write `.spec-suite/bootstrap.yaml` recording the suite and
      gate version that produced the shell.
- [x] Author `.githooks/pre-push` per `SUITE-DESIGN.md` §9 Tier 2 (Spectral
      on contracts, datacontract-cli, cross-file consistency, <15 s
      target).
- [x] Author `.github/workflows/audit.yml` per §9 Tier 3 (full audit on
      PR, blocks merge).
- [x] Reconcile `.github/instructions/` against the bootstrap manifest. The
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
no template placeholders remain, `.spec-suite/ambiguities.md` has no audit-required
unresolved items, every `.spec-suite/phases/phase-N-passed.yaml` is present with sha256s
that match current file contents, and `force_advances:` is empty.

🛑 **Review checkpoint:** Walk through the fixture together. Confirm the
specs are realistic, the state files are coherent, and the hooks are
sensible before proceeding to 2.1.

### 2.1 Scaffold the suite repo itself — [x]

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
  `tests/fixtures/*/.spec-suite/phases/phase-*-passed.yaml` against
  current file contents. Run whenever fixture content changes so the
  fixture's sign-off files stay valid against the staleness check.
- `task suite:force-advance` — wrapper that calls
  `shared/scripts/force_advance.py <phase> --reason '<text>'` on the
  current working domain repo. Used during dev to test the audit's
  force-advance handling. Writes an entry to `.spec-suite/progress.yaml`'s
  `force_advances:` array.
- `task suite:accept-force` — marks a `force_advances:` entry as
  `accepted: true` with a reason. Required to clear an audit failure
  caused by a force-advance.
- `task suite:upgrade-shell` — manifest-aware re-bootstrap that preserves
  spec content. Reads the target's `.spec-suite/template-manifest.yaml`, diffs
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

### 2.2 Build the bootstrap skill (Phase 0) — [x]

This skill, when invoked, populates an empty target repo with all the files
a domain spec repo needs.

Sub-tasks:

- [x] Create `skills/domain-bootstrap/SKILL.md` with:
  - Description that triggers on "set up a new domain spec repo" or being
    invoked by the orchestrator on a fresh directory
  - Prerequisites: target directory exists and is empty (or `--force`)
  - Instructions for what to do
- [x] Create `skills/domain-bootstrap/templates/` containing every file
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
  - `.spec-suite/templates/*` (the blank spec templates,
    including glossary/error-catalogue/nfr/acceptance-scenarios
    skeletons added in M2.0)
  - `scripts/generate_domain_overview.py` *(later moved into the suite
    in v1.0.13/§6.17; since v1.0.14/§6.19 bootstrap installs no copy —
    `task docs:generate` delegates to the suite-side script)*
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
- [x] Author `skills/domain-bootstrap/template_manifest.yaml` listing
  every file the bootstrap owns (path + expected sha256). The bootstrap's
  `--force` re-run consults this manifest to decide what may be
  overwritten; `task suite:upgrade-shell` consults the same manifest to
  compute its diff. The manifest is the *contract* between the suite and
  any domain repo it has bootstrapped.
- [x] Implement the bootstrap logic: walk templates dir, copy each file to
  the target, substitute placeholders where present, create empty
  `.spec-suite/progress.yaml` (with `force_advances: []`) with Phase 0 marked passed,
  create `.spec-suite/bootstrap.yaml` recording suite/gate versions, copy the
  manifest into the target as `.spec-suite/template-manifest.yaml`.
- [x] Implement non-empty-directory handling: refuse by default with a
  message pointing at `--force` or `task suite:upgrade-shell`; `--force`
  overwrites only files listed in the manifest, never spec content or
  `_*.yaml` state.
- [x] Write a test (`task test:bootstrap`) that runs bootstrap in a temp
  directory and diffs the output against an expected snapshot. Also test
  the non-empty-directory paths (refuse, `--force`, manifest-respecting).

**Exit criterion:** Running the bootstrap skill in an empty directory
produces a repo whose contents match the canonical shell. `task test:bootstrap`
passes.

### 2.3 Build the audit skill (Phase 7) — [x]

This is the second bookend gate. It's read-only and runs every
cross-reference check defined across all phases.

Sub-tasks:

- [x] **Populate `shared/checks/` first.** Per SUITE-DESIGN §5.5 and §8,
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
  - `signoff_sha256_matches.py` — `.spec-suite/phases/phase-N-passed.yaml` ↔ file sha256s
  - `ambiguities_no_audit_required.py` — `.spec-suite/ambiguities.md` has no
    audit-required open items
  - `force_advances_all_accepted.py` — `.spec-suite/progress.yaml` `force_advances:`
    has no `accepted: false` entries
- [x] Create `skills/domain-conformance-audit/SKILL.md` referencing the
  prompting style in §7 and the rubric handling in §5.5 (audit itself has
  no rubric checks — it's purely mechanical re-verification).
- [x] Create `skills/domain-conformance-audit/gate.yaml` listing the
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
- [x] The skill produces a structured report:
  - Pass/fail per check
  - Failure messages phrased as interview questions (not lint diagnostics)
  - Summary of total counts
- [x] Set up the test fixture: copy `domain-api-template/` (now in its
  v1.0-complete state from Task 2.0) into `tests/fixtures/items/`. This
  is the known-good reference spec set.

**Exit criterion:** Running the audit against the Items fixture produces
"audit passed" with all checks green. Every shared module has at least one
unit test in the suite's own test suite.

### 2.4 Validate audit catches breaks — [x]

Create a test that deliberately introduces breaks and confirms the audit
catches each.

For each break below, the test:
1. Copies the clean Items fixture to a temp directory
2. Applies one specific break
3. Runs the audit
4. Confirms the audit fails with a specific expected error code/message
5. Confirms the failure message reads like an interview question

Breaks to test:

- [x] Rename a field in `domain-model.md` but not in `openapi.yaml`
- [x] Remove an AsyncAPI channel that corresponds to a write operation
- [x] Add a role to `auth-matrix.md` that isn't in the `RegisterRequest`
  enum in `openapi.yaml`
- [x] Leave an unreplaced `[Resource1]` placeholder somewhere
- [x] Add a user story in `prd.md` that mentions a nonexistent persona
- [x] Modify `prd.md` without re-signing Phase 1 (staleness detection)
- [x] Remove an event from AsyncAPI but leave its entry in `datacontract.yaml`
- [x] Add an OpenAPI operation with no auth-matrix entry
- [x] Add an entity to `domain-model.md` with no glossary entry
- [x] Leave a deferred ambiguity marked `required-by: audit` unresolved

**Exit criterion:** All breaks caught, all failure messages actionable. Tests
run via `task test:audit` and all pass.

🛑 **Review checkpoint:** Demo the audit skill against the Items fixture and
against several deliberate breaks. Confirm failure messages are clear and
actionable before proceeding to Milestone 3.

---

## Milestone 3: Contracts Skill (Phase 6)

**Goal:** Hard-gated skill that orchestrates contract linting and cross-file
consistency, refusing sign-off unless all checks pass.

### 3.1 Build the contracts skill — [x]

- [x] Create `skills/domain-contracts/SKILL.md`. No rubric checks for
  contracts (purely mechanical).
- [x] Create `skills/domain-contracts/gate.yaml` referencing shared-check
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
- [x] Implement: skill loads contracts (or copies templates if absent),
  runs the §5 gate loop, and refuses sign-off via `shared/sign_off.py`
  while any check fails (the mechanical-enforcement path per §5.5).
- [x] Sign-off writes `.spec-suite/phases/phase-6-passed.yaml` with sha256s and timestamp.

**Exit criterion:** Skill against the Items fixture produces clean sign-off.
Skill against deliberately malformed contracts produces actionable failures
and refuses sign-off.

### 3.2 Validate hard gate enforcement — [x]

- [x] Confirm the skill cannot produce a sign-off file while
  `task gate:contracts` exits non-zero. The test should attempt every
  obvious bypass (asking the agent nicely, providing a hand-rolled
  sign-off file path) and confirm none of them works — only
  `shared/sign_off.py` writes the file, and it refuses on non-zero exit.
- [x] Confirm the only escape is `task suite:force-advance contracts
  --reason '<text>'`. The test verifies:
  - A `force_advances:` entry is appended to `.spec-suite/progress.yaml` with
    `accepted: false`.
  - The phase is signed off despite the failure.
  - Running the audit immediately reports
    `force_advances_all_accepted` as FAIL with an actionable message.
  - `task suite:accept-force contracts --reason '<text>'` flips the
    entry to `accepted: true` and a re-audit then passes.

**Exit criterion:** Hard gate is genuinely hard. No path to false sign-off
exists. The force-advance escape is honest — visible in `.spec-suite/progress.yaml`
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
  the agent emits findings into `.spec-suite/phases/phase-1-passed.yaml`.
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
appear in the resulting `.spec-suite/phases/phase-1-passed.yaml` with the user's responses.
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
  bootstrap (`.spec-suite/templates/domain-model.md`, `.spec-suite/templates/glossary.md`)
- [x] Mandatory-engagement loop documented in SKILL.md
- [x] Cross-references via shared `ENTITY-IN-GLOSSARY` and
  `GLOSSARY-COVERS-ATTRIBUTES` (both also run at audit)
- [x] 6 phase-local checks (3 hard error, 3 warning) + 1 shared cross-ref
- [x] Sign-off writes `.spec-suite/phases/phase-2-passed.yaml`
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

### 6.1 Choose a non-Items test domain — [x]

**Chosen:** Dog Walking (single-walker, multi-client). Materially
different from Items: 13 entities (vs 2), 2 roles with cross-client
ownership semantics, 4 lifecycles (vs 1), photo uploads, invoicing.

**Status:** ✅ Demoed end-to-end in M6.2 at `/tmp/dogwalk-demo`.

### 6.2 Run the full suite — [x]

Start with an empty directory. Run the orchestrator. Walked all 8
phases: Bootstrap → Discovery → Modeling → Access Control → Flows →
NFRs → Contracts → Audit. 17/17 audit checks green.

**Status:** ✅ Complete. Findings in M6.3 commit notes.

### 6.3 Test update mode — [x]

Amended `/tmp/dogwalk-demo/docs/specifications/prd.md` with US-019
(optional tip on mark-paid). Orchestrator detected PRD staleness;
walked 5 affected phases (discovery → modeling → nfrs → contracts →
flows) in dependency order; final audit 17/17 green again. Each
re-sign emitted Decision Log entries via the new findings interface.

**Status:** ✅ Update mode works end-to-end with real downstream
effects.

### 6.4 Decision Log mechanism — [x]

Surfaced during M6.2 review: spec authors need to **discover what was
decided** silently to revise after sign-off. Added a `decisions:`
block to the sidecar shape with id/summary/rationale/affects/ts.
sign_off.py accepts decisions via the `--findings` YAML interface
(extended) or the Python API. Each soft-middle and contracts SKILL.md
carries a `## Decision Log` section listing decision-prone areas.
SUITE-DESIGN §4 and §5.5 updated.

**Status:** ✅ Mechanism shipped; dog-walking sidecars retrofitted
with full decisions blocks as a populated reference.

### 6.6 v1.0.2 — domain-review skill + audit-bug fix — [x]

Independent review of the dog-walking spec set surfaced 4 categories
of issue the mechanical suite couldn't catch (cross-doc type drift,
orphan operations, semantic contradictions in attribute prose,
missing decision-log notes for design intent). Codified the
review methodology as a new suite skill.

- ✅ `skills/domain-review/SKILL.md`: walks 5 review categories;
  produces structured markdown report; read-only.
- ✅ `scripts/domain_review.py`: pre-flight (audit green), context
  bundle, `--write-report` mode for persisting agent output.
- ✅ Suite Taskfile: `task review` invokes the runner.
- ✅ Bootstrap Taskfile: `task review` shells to the suite via the
  same `DOMAIN_SPEC_SUITE_ROOT` / sibling-fallback pattern as audit.
- ✅ SUITE-DESIGN §6 "Qualitative review layer" documents the
  mechanism.
- ✅ Real bug fix: `SIGNOFF-SHA256-MATCHES` regex required quoted
  sha256 values but `sign_off.py` emits bare via `yaml.safe_dump`,
  so the check was silently passing on every audit since M3. Fixed
  by switching to YAML-parser approach; regression test in
  `tests/test_audit.py` covers both bare + quoted formats.
- ✅ Dog-walking spec set fixed for the 4 review-surfaced findings:
  InvoiceLineItem.priceCents minimum tightened, snapshot-timing
  prose disambiguated, US-020 view-dog story added, Walker no-API
  note explicit, 3 minor prose fixes. Re-signed affected phases
  with Decision Log entries.

135/135 tests green (was 134, +1 sha256 regression).

### 6.5 v1.0.1 backlog — [x]

All 6 items surfaced during M6.2 / M6.3 / M6.4 now addressed:

- ✅ **#1 Audit-respects-prior-engagement.** `shared/prior_engagement.py`
  reads each prior phase's `warnings_responded`, downgrades matching
  audit-error outcomes to warning, synthesises carry-forward responses.
  Documented in SUITE-DESIGN §6 ("Audit respects prior-phase engagement").
- ✅ **#2 Null in OpenAPI enum.** Generator handles `None` from PyYAML's
  literal-null parsing instead of crashing on `str.join`.
- ✅ **#3 pyyaml install path.** Bootstrap now prints explicit
  next-steps (`mise install` → `task setup`) so users hit the right
  install sequence.
- ✅ **#4 Spectral description auto-fix.** New
  `scripts/lint_fix_descriptions.py` (bootstrap-installed) +
  `task lint:fix-descriptions`. Idempotent.
- ✅ **#5 mkdocs install discoverability.** README quick-start now
  shows the full `mise trust → mise install → task setup` sequence.
- ✅ **#6 Glossary skeleton generator.** New
  `scripts/glossary_skeleton.py` (bootstrap-installed) +
  `task glossary:skeleton`. Reads domain-model attribute tables and
  emits ~90 glossary stubs in one shot. Modeling SKILL.md points
  the agent at it.

🛑 **Final review.** Declare suite v1.0.0 complete if user agrees.

### 6.7 v1.0.3 — hoist suite bookkeeping out of docs/specifications/ — [x]

After the v1.0.2 review session it became obvious that the spec
folder had drifted: ~26 entries with only 35% actual spec content,
the rest suite bookkeeping (sidecars, progress, ambiguities,
template stash, growing review archive). The mix was noise to any
human opening the folder to read the spec.

Decision: move all suite-managed state to `.spec-suite/` at repo
root, mirroring `.git/` / `.github/`. `docs/specifications/`
becomes purely the publishable spec view (markdown + contracts +
generated HTML).

- ✅ `shared/spec_paths.py` central helper — every read/write of
  suite state routes through `state_dir`, `phases_dir`,
  `reviews_dir`, `templates_dir`, `progress_path`,
  `bootstrap_path`, `ambiguities_path`,
  `template_manifest_path`, `phase_sidecar_path`,
  `all_phase_sidecars`, `ensure_state_skeleton`.
- ✅ Suite-side migration: `shared/sign_off.py`,
  `shared/prior_engagement.py`, `scripts/bootstrap.py`,
  `scripts/init_phase.py`, `scripts/orchestrator_status.py`,
  `scripts/force_advance.py`, `scripts/accept_force.py`,
  `scripts/domain_review.py`, and the three audit-only checks
  (`signoff_sha256_matches`, `force_advances_all_accepted`,
  `ambiguities_no_audit_required`) all route through
  `spec_paths`.
- ✅ Bootstrap-installed templates moved:
  `skills/domain-bootstrap/templates/.spec-suite/templates/*`
  (was `docs/specifications/_template/*`);
  `task domain:init` Taskfile loop reads from the new location;
  `mkdocs.yml.template` `exclude_docs` no longer needed
  (`.spec-suite/` is outside `docs/`).
- ✅ `scripts/migrate_to_spec_suite_dir.py` — idempotent migration
  for existing spec repos: moves files, rewrites `files_signed`
  paths in sidecars, recomputes sha256 from new file locations.
- ✅ `tests/fixtures/items/` migrated to the new layout; all
  test helpers updated to import + use `spec_paths`.
- ✅ Bonus: `tests/test_audit_breaks.py` `_reseed_signoffs` was
  using regex line edits (the source of the M6.6 sha256 bug);
  rewritten to use `yaml.safe_load` + `yaml.safe_dump`.
- ✅ SUITE-DESIGN.md, BUILD-PLAN.md, and every SKILL.md updated
  to reference the new paths.

135/135 tests green throughout.

### 6.8 v1.0.4 — templates live in suite, not spec repos — [x]

Spotted while reviewing a freshly-migrated dog-walking spec set:
`.spec-suite/templates/` was just dead weight in a completed repo —
every spec file is authored, the templates never run again, and they
duplicate content that already lives in the suite. They were
bootstrap-installed in v1.0.3 only because `task init:<phase>` read
from the target's own `.spec-suite/templates/`.

Move templates into the suite itself; have `task init:<phase>`
resolve them from `<suite>/templates/` (same `DOMAIN_SPEC_SUITE_ROOT`
lookup `task audit` / `task review` already use). Templates become
single-source-of-truth alongside the gate code that consumes their
outputs.

- ✅ Moved `skills/domain-bootstrap/templates/.spec-suite/templates/*`
  → `<suite>/templates/`.
- ✅ `scripts/init_phase.py` reads from `SUITE_ROOT / "templates"`;
  adds `all` mode (one shot across every authoring phase).
- ✅ Bootstrap Taskfile `domain:init` delegates to the suite
  (same shape as `task audit` / `task review`).
- ✅ `shared/spec_paths.py` drops `templates_dir()` and stops
  creating `.spec-suite/templates/` on bootstrap.
- ✅ `scripts/migrate_to_spec_suite_dir.py` cleans up
  `.spec-suite/templates/` from v1.0.3-migrated repos.
- ✅ Regenerated `template_manifest.yaml` — 25 → 16 files.
- ✅ Fixture (`tests/fixtures/items/`) Taskfile + mkdocs + README
  refreshed to the new bootstrap-installed shape.

End-to-end verified on `/tmp/spec-test-v104` (fresh bootstrap +
init_phase all) and on `~/dev/domainapps/spec-dog-walking`
(post-cleanup audit: 17/17). 135/135 tests green.

### 6.9 v1.0.5 — enum consistency check + Enumerations convention — [x]

User spotted that `Dog.breed` was declared `string` in the
dog-walking domain model even though it's a closed set — and that
nothing in the suite would catch openapi/asyncapi/datacontract
divergence on an enum's values. Common drift pattern: someone adds
a value in OpenAPI, forgets the other two.

- ✅ New `## Enumerations` section convention in
  `domain-model.md`. Each `### Name` declares one named enum with
  a `| Value | Notes |` table. Attributes reference it as
  `enum:Name` in the Type column.
- ✅ `shared/spec_parsers.py` — `domain_model_enums()`,
  `contract_named_enums()`, `datacontract_named_enums()`.
- ✅ `shared/checks/enum_values_consistent.py` — single
  cross-contract check `ENUM-VALUES-CONSISTENT`. Model is the
  authority. OpenAPI must declare every named enum with matching
  values; AsyncAPI + Datacontract must match if they declare it.
- ✅ Wired into `domain-contracts/gate.yaml` (Phase 6) and
  `domain-conformance-audit/gate.yaml` (Phase 7) at error
  severity.
- ✅ `templates/domain-model.md` carries an `## Enumerations`
  stub explaining when to use named enums vs strings.
- ✅ `domain-modeling/SKILL.md` documents the convention
  (when to declare named enum vs leave as `string` vs inline
  enum); `domain-contracts/SKILL.md` documents the
  `$ref: '#/components/schemas/<Name>'` materialization pattern.
- ✅ Two regression tests in `tests/test_contracts.py` cover the
  missing-from-openapi failure and the value-mismatch failure.

137/137 tests green (was 135, +2 enum regression tests). Convention
is opt-in — silent on domains without an `## Enumerations`
section, so existing fixtures (Items) are unaffected.

### 6.10 v1.0.6 — events carry full domain state — [x]

User flagged that the data contract should be the historic record:
downstream analytics, audit logs, and time-travel reconstructions
all depend on events carrying enough to recover what happened
without re-querying the live API. Survey of dog-walking confirmed
the problem is pervasive — 8 of 13 events are "thin" or "very
thin" (mostly identifiers), and DogUpdated carries field *names*
without values.

Codifies a new architectural position in SUITE-DESIGN §4.5 plus a
new mechanical check.

- ✅ New SUITE-DESIGN.md §4.5 **Events carry full domain state**
  states the principle, the `[secret]` exception, the removal-event
  exception, and the v1.0.7 aggregate-children deferral.
- ✅ `[secret]` marker convention: an attribute whose Description
  column begins with `[secret]` is excluded from the
  must-appear-in-events set. Visible inline; no separate file.
- ✅ Three new parsers in `shared/spec_parsers.py`:
  - `domain_model_published_attributes()` — wraps
    `domain_model_attributes()` filtering `[secret]` rows.
  - `asyncapi_event_payloads()` — walks every
    `components.messages.<Name>.payload` (resolving `$ref`),
    locates the envelope's `data` property (in `allOf` or inline),
    returns `{event_name: {field_name: schema}}`.
  - `datacontract_record_fields()` — walks
    `schema[*].properties[*]` per ODCS, returns
    `{record_name: {field_name: prop_dict}}`.
- ✅ New check `EVENT-PAYLOAD-COVERS-ENTITY-STATE`. For every
  event in `## Domain Events`: resolve the entity from the
  channel slug; verify (a) every published attribute appears in
  the matching AsyncAPI payload, (b) same in the matching
  datacontract record, (c) AsyncAPI payload and datacontract
  record field sets are equal (modulo the `id` ↔ `<entity>Id`
  naming convention).
- ✅ Removal events (action ∈ `removed` / `deleted` / `expired`)
  are exempt; minimal payload accepted.
- ✅ Wired into both Phase 6 (`domain-contracts`) and Phase 7
  (`domain-conformance-audit`) gates at error severity.
- ✅ Modeling + contracts + audit SKILL.md updated; template
  `domain-model.md` carries an inline comment documenting the
  `[secret]` and `enum:Name` description-column conventions.
- ✅ Four regression tests covering: missing-from-asyncapi
  failure, missing-from-datacontract failure, asyncapi-vs-
  datacontract divergence, `[secret]` exemption.
- ✅ Bonus: fixed a latent bug in `datacontract_named_enums`
  (was reading `.fields` dict; ODCS actually uses
  `.properties` list).

145/145 tests green (was 139, +6: 2 from new check picked up by
the parametrized happy-path test, 4 from new regression tests).
Convention is opt-in: silent on domains without a `## Domain
Events` table.

### 6.11 v1.0.7 — data contract HTML rendering convention — [x]

After v1.0.6 fattened every event payload to carry full entity
state, the data contract became the audit-grade historic record
the user wanted — but the spec site only exposed it as raw YAML
or as duplicated inline tables in `domain-overview.html`. The
other two contracts already had dedicated interactive reference
pages (OpenAPI via Scalar, AsyncAPI via AsyncAPI-React); the
datacontract had no peer.

`datacontract-cli` already ships an HTML exporter
(`datacontract export html <yaml> --output <path>`); it produces
a self-contained Tailwind-styled page. This version codifies its
use as the third contract-reference convention.

- ✅ `skills/domain-contracts/SKILL.md` — new "Publishing the
  contract as HTML" subsection prescribing the exporter command
  + the `docs/specifications/datacontract-reference.html`
  destination convention.
- ✅ No new phase-gate check. `DATACONTRACT-LINT` already proves
  the YAML is exportable; render failure would also fail lint.
- ✅ spec-dog-walking adopted the convention: new
  `docs:render-datacontract` Taskfile task; `docs:generate`
  invokes it alongside `generate_domain_overview.py`; home-page
  nav links the new reference; `generate_domain_overview.py`
  trims its inline Data Contract section in favour of a
  link-out paragraph; `.github/workflows/docs.yml` installs
  `datacontract-cli` before `task docs:build`.
- ✅ Decision Log entry on the contracts sidecar:
  `DATACONTRACT-HTML-EXPORT-CONVENTION`.

### 6.12 v1.0.8 — aggregate-child coverage — [x]

Closes follow-up #1 from the v1.0.7 deferral list:
`EVENT-PAYLOAD-COVERS-ENTITY-STATE` now extends to aggregate
roots. When the model declares a `## Aggregates` section, events
on the root entity must carry every declared child collection,
in both the asyncapi payload and the datacontract record, with
the child's full published-attribute set.

- ✅ New `## Aggregates` markdown convention. Table format
  `| Root | Child | Collection |` with backtick-wrapped values.
  Opt-in; absent section = no aggregate enforcement.
- ✅ `shared/spec_parsers.py` — new `domain_model_aggregates`,
  `asyncapi_array_item_properties`,
  `datacontract_array_item_properties`.
- ✅ `shared/checks/event_payload_covers_entity_state.py` — new
  aggregate-coverage block after the single-entity coverage
  block. Verifies collection presence, item-shape coverage of
  child published attrs, and asyncapi↔datacontract item-shape
  symmetry.
- ✅ `skills/domain-modeling/SKILL.md` — new "Aggregates"
  subsection prescribing the convention.
- ✅ `skills/domain-contracts/SKILL.md` — bullet under
  asyncapi.yaml authoring noting the aggregate carry-rule.
- ✅ `SUITE-DESIGN.md` §4.5 — expanded aggregate paragraph with
  the new convention.
- ✅ Tests in `tests/test_contracts.py`: parser pass + empty
  paths; pass case (well-formed aggregate); fail cases
  (missing collection, thin items, asyncapi↔datacontract
  divergence).

### 6.13 v1.0.9 — Idempotency-Key on POST ops — [x]

A multi-channel review surfaced that the suite gave consumers
(mobile, agentic, chat) no safe-retry semantics. Codifies the
Stripe / IETF `draft-ietf-httpapi-idempotency-key-header`
convention as a suite-level rule: every POST must declare a
required `Idempotency-Key` header parameter.

- ✅ `shared/checks/idempotency_key_on_post_ops.py` — new
  Phase 6 + audit check `IDEMPOTENCY-KEY-ON-POST-OPS`. Walks
  `paths[*].post` (and path-level parameters), resolves
  `$ref`s against `components.parameters`, accepts any header
  named Idempotency-Key (case-insensitive) marked
  `required: true`.
- ✅ Registered in `skills/domain-contracts/gate.yaml` and
  `skills/domain-conformance-audit/gate.yaml`.
- ✅ `skills/domain-contracts/SKILL.md` — new authoring bullet
  on the openapi.yaml section and a new check entry.
- ✅ `SUITE-DESIGN.md` §4.6 — new "Idempotent Mutating Ops"
  section explaining the convention, scope (POST only), and
  why PUT/PATCH/DELETE are exempt.
- ✅ Items fixture extended: `components.parameters.IdempotencyKey`
  declared once and `$ref`-ed from all 5 POSTs.
- ✅ Tests in `tests/test_contracts.py`: pass-on-fixture,
  fail-when-omitted, accepts-inline, rejects-required-false,
  silent-when-no-posts, accepts-path-level.

### 6.14 v1.0.10 — split contract authoring into three sub-skills — [x]

A multi-channel design review surfaced that
`skills/domain-contracts/SKILL.md` had grown to 269 lines mixing
OpenAPI, AsyncAPI, and ODCS authoring with cross-reference rules
— every recent v1.0.x increment landed content in the same file
even though each piece of guidance belongs to one contract.

Splits the authoring guidance into three sibling sub-skills,
leaving the parent skill focused on the Phase 6 gate and
cross-reference rules. No Phase 6 mechanics change: same gate,
same sign-off, same sidecar. dog-walking is unaffected.

- ✅ `skills/domain-openapi/SKILL.md` — OpenAPI 3.0.3 conventions
  including the Idempotency-Key on POST convention.
- ✅ `skills/domain-asyncapi/SKILL.md` — AsyncAPI 2.6 + CloudEvents
  conventions, full-state-in-events, aggregate-child collections.
- ✅ `skills/domain-datacontract/SKILL.md` — ODCS 3.1 conventions,
  nested aggregate fields, HTML rendering convention.
- ✅ `skills/domain-contracts/SKILL.md` slimmed from 269 → ~206
  lines, focused on gate orchestration + sub-skill routing.
- ✅ `SUITE-DESIGN.md` §5 — new "Parent + sub-skill phases"
  subsection documenting the pattern.
- ✅ `tests/test_smoke.py::test_skills_directories_exist` — three
  new skill names added to the expected set.

### 6.15 v1.0.11 — make contract sub-skills useful — [x]

After v1.0.10 split the contract authoring into three sibling
sub-skills, the sub-skill content was largely *rules* with no
worked examples and no scaffolding scripts. v1.0.11 fills both
gaps with three new bootstrap-installed skeleton scripts (one
per contract) and a content augmentation pass on each sub-skill
SKILL.md.

- ✅ `skills/domain-bootstrap/templates/scripts/openapi_skeleton.py`
  — derives openapi.yaml from auth-matrix.md + domain-model.md +
  error-catalogue.md; wires Idempotency-Key on every POST,
  entity + enum schemas, generic Error/ValidationError schemas,
  reusable parameters + responses. Refuses to overwrite a real
  openapi.yaml unless `--force`.
- ✅ `skills/domain-bootstrap/templates/scripts/asyncapi_skeleton.py`
  — derives asyncapi.yaml from domain-model.md events + entities
  + aggregates. CloudEvents envelope (allOf-extended), full-state
  payloads, aggregate-child collections via $ref to per-child
  payload schemas, removal events with minimal id+timestamp
  payload.
- ✅ `skills/domain-bootstrap/templates/scripts/datacontract_skeleton.py`
  — derives datacontract.yaml from asyncapi.yaml (post-author)
  + nfr.md. Mirrors event payloads into ODCS records grouped by
  entity, with nested array fields for aggregate children.
- ✅ Bootstrap Taskfile template gains three new entries
  (`openapi:skeleton`, `asyncapi:skeleton`,
  `datacontract:skeleton`).
- ✅ Items fixture: scripts copied to `tests/fixtures/items/scripts/`
  + matching Taskfile entries.
- ✅ `skills/domain-openapi/SKILL.md`, `skills/domain-asyncapi/SKILL.md`,
  `skills/domain-datacontract/SKILL.md` each gain three new
  sections: **Tools** (skeleton + lint + fix-descriptions +
  gate task references), **Worked YAML patterns** (2-3 concrete
  snippets showing the correct shape), **Common pitfalls**
  (anti-patterns paired with the check that catches each).
- ✅ `skills/domain-bootstrap/template_manifest.yaml` regenerated
  to include the three new scripts.

### 6.16 v1.0.12 — expandable enums + enum audit — [x]

`ENUM-VALUES-CONSISTENT` enforced strict equality between the
model's enum table and every contract's enum schema. That
worked for closed sets (Role, WalkStatus) but blocked any enum
that's intentionally large or growable (dog breeds, currency
codes, MIME types from a known authority).

v1.0.12 introduces an **(open) marker** on the model heading so
the check can support both modes:

- Closed (default): strict equality (existing behaviour).
- Open (`### Breed (open)`): model values ⊆ contract values.
  The model lists a representative subset; the contract carries
  the authoritative full list.

Minimum-viable shape: no new files, no new build steps, no
parser duplication. The marker is the only new syntax.

- ✅ `shared/spec_parsers.py:domain_model_enums` — returns
  `{name: {"values": [...], "open": bool}}`. Parses `(open)` or
  `[open]` (case-insensitive) from the H3 heading.
- ✅ `shared/checks/enum_values_consistent.py` — open enums use
  subset check (model ⊆ contract); closed enums keep strict
  equality.
- ✅ `skills/domain-modeling/SKILL.md` — new "Closed vs open
  enums" subsection under Enumerations.
- ✅ `skills/domain-openapi/SKILL.md` — bullet on the open-enum
  authority semantics.
- ✅ `tests/test_contracts.py` — 4 new tests: closed-perfect,
  closed-mismatch (regression), open-superset, open-model-extra,
  plus marker-variant parser test.

### 6.17 v1.0.13 — promote overview generator into the suite — [x]

`generate_domain_overview.py` previously lived in each consumer
spec repo (`spec-dog-walking/scripts/`). That meant a new
consumer would have to copy the script — the single most concrete
coupling between the suite and dog-walking's local tooling.

v1.0.13 lifts the script into the suite as
`scripts/generate_domain_overview.py`, with a `--repo PATH` arg
matching the audit pattern. Consumer Taskfiles delegate
`docs:generate` to the suite-side script via the same
`{{.DOMAIN_SPEC_SUITE_ROOT | default "../domain-spec-suite"}}`
resolution as `task audit`.

- ✅ `scripts/generate_domain_overview.py` — lifted from
  dog-walking, made `--repo`-driven. Includes a deterministic
  fix for ERD relationship inference (length-desc candidate
  ordering, so longer entity names like `Walker` beat shorter
  prefixes like `Walk` on ambiguous foreign-key fields).
- ✅ `shared/checks/generator_clean_output.py` — prereq changed
  from `scripts/generate_domain_overview.py` to
  `docs/specifications/contracts/openapi.yaml`; generator path
  resolved relative to the check (suite root). Subprocess
  passes `--repo <repo_root>`.
- Gate version unchanged (no check semantics changed; only
  the generator's location moved). `suite-version.yaml` not
  touched — consistent with prior v1.0.x increments which did
  not per-bump that field.
- ✅ spec-dog-walking — local `scripts/generate_domain_overview.py`
  deleted; `Taskfile.yml` `docs:generate` delegates to the
  suite-side script with the same suite-resolution pattern as
  `task audit`.

### 6.18 Future backlog — per-event opt-outs + type alignment

Two remaining follow-ups from the v1.0.7 deferral list, neither
of which has a current driver:

1. **Per-event opt-outs.** Some non-removal events legitimately
   don't need full state (e.g. a future low-value "telemetry"
   event). Mechanism: a `payload: minimal` marker on the Domain
   Events table row. Not needed for current dog-walking events;
   wait for a real case.
2. **Type alignment across edges.** Today the
   `EVENT-PAYLOAD-COVERS-ENTITY-STATE` check enforces *presence*.
   Enum value alignment is covered by `ENUM-VALUES-CONSISTENT`.
   Plain-type alignment (e.g. the model says `string` but
   openapi says `integer`) is uncovered. Worth a
   `FIELD-TYPE-CONSISTENT` follow-up.

### 6.19 v1.0.14 — suite-consistency release (gate 1.1) — [x]

A full drift review of the suite against its own design contract.
No new spec-authoring features; everything here closes gaps between
what SUITE-DESIGN/BUILD-PLAN promised and what the repo did.

- ✅ **Gate 1.1 (retroactive changelog).** The checks added in
  v1.0.5–v1.0.12 shipped without the §10 gate bump.
  `gate-version.yaml` → `1.1` with a full `gate-changelog.md`
  entry; two new smoke tests make the policy mechanical (a bump
  without a changelog heading fails CI, as does a stale
  `template_manifest.yaml` version header). `suite-version.yaml`
  unfrozen from `1.0.0-alpha` (now tracks the real release).
- ✅ **Audit re-runs tool lints.** `SPECTRAL-OPENAPI`,
  `SPECTRAL-ASYNCAPI`, `DATACONTRACT-LINT` added to the audit
  gate per Task 2.3's original category list; they skip where the
  CLIs aren't installed.
- ✅ **Generator single-sourced.** Bootstrap no longer installs a
  copy of `generate_domain_overview.py` (the template copy had
  drifted and carried Items-specific role text); `task
  docs:generate` delegates to the suite via
  `DOMAIN_SPEC_SUITE_ROOT`, same as `task audit`.
- ✅ **Operator stubs implemented.** `scripts/upgrade_shell.py`
  (manifest-aware shell refresh, recovers domain name from state),
  `scripts/reset_phase.py` (SUITE-DESIGN §11 open question 1;
  dry-run by default), and a real `fixtures:reset`.
- ✅ **run_phase.py** no longer advertises the ungated bootstrap
  phase (was a guaranteed FileNotFoundError).
- ✅ **Deliberate-break coverage** for the 8 previously-untested
  audit checks (12 → 20 breaks); four checks' `on_fail` copy
  rewritten interview-style per §7 Hard Rule 10.
- ✅ **Docs reconciled.** README (layout, skill list, state-file
  names, bogus "agent instruction files" claim), CLAUDE.md,
  SUITE-DESIGN §1/§8 naming, M2/M3 checkbox back-fill, stale
  `_*.yaml` naming in comments/descriptions, Items fixture
  cleanup (`.spec-suite/templates/` leftover removed,
  `template-manifest.yaml` added).

**Still open after this release:** Task 4.3 (resumption demo —
needs a live interactive session, can't be a pytest), and the 6.18
backlog items.

---

### 6.20 v1.0.15 / gate 1.2 — critique-driven gate hardening — [x]

An adversarial four-pass review of the dog-walking spec set
(`spec-dog-walking/.spec-suite/reviews/2026-07-05T14-48-07Z.md`)
produced 44 findings. The systemic pattern: existing checks validate
*mirroring of what exists* (enum equality, channel-per-event) but
nothing validates *closure* — that a catalogued error code is
emittable, an event-stream FK resolvable, a scenario literal legal,
an invented operation traceable. This task hardens the gates against
those classes. Gate-version bump: `1.1 → 1.2` (6.19 took `1.1` as a
retroactive reconciliation of checks shipped without a bump).

New shared checks (each: module + gate.yaml wiring + regression
tests; questions.md entries where the owning phase has one):

- ✅ `ERROR-CODE-REPRESENTABLE` (`shared/checks/error_code_representable.py`)
  — catalogue→openapi direction. Every catalogue code's HTTP status is
  declared by ≥1 operation; where openapi response schemas enumerate
  `code` values, every catalogue code appears in ≥1 enum bound at its
  documented status. Catches unreturnable codes (3× 400s,
  IDEMPOTENCY_KEY_CONFLICT, missing 429).
- ✅ `OPERATION-HAS-SCENARIO` (`shared/checks/operation_has_scenario.py`)
  — reverse traceability: every openapi operation is referenced by ≥1
  acceptance scenario (operationId or `METHOD /path`). Catches
  contract-time inventions with no test surface (registerWalker,
  listClients, listDogs).
- ✅ `SCENARIO-REFS-VALID` (`shared/checks/scenario_refs_valid.py`)
  — scenario literals validated against contracts: error codes exist
  in the catalogue, `METHOD /path` mentions exist in openapi,
  enum-typed field literals are legal members (catches
  `"Border Collie"` vs `border-collie`).
- ✅ `EVENT-FK-RESOLVABLE` (`shared/checks/event_fk_resolvable.py`)
  — every `<entity>Id` field in a datacontract record, where
  `<entity>` is a domain-model entity, resolves to a datacontract
  record for that entity. Catches the invisible-Walker/User class
  (dangling FKs in the historic record).
- ✅ `DATACONTRACT-REFS-RESOLVE` (`shared/checks/datacontract_refs_resolve.py`)
  — every `ref`/`$ref` in datacontract properties resolves locally or
  to `openapi.yaml#/components/schemas/<X>` (unqualified
  `#/components/…` treated as the openapi shorthand; target must
  exist). Catches dangling pointers and renamed-schema drift.
- ✅ `ENTITY-HAS-EVENT` (`shared/checks/entity_has_event.py`)
  — modeling-phase warning, audit error: every entity (except
  aggregate children) appears in ≥1 Domain Events row. Catches
  entities born via auth flows escaping the historic record.

Check + template + skill amendments:

- ✅ `NO-TEMPLATE-PLACEHOLDERS` also flags `TODO`/`TBD`/`FIXME` in
  spec files (the dog-walking PRD shipped `Constraints: 1. TODO`).
- ✅ `templates/nfr.md`: Privacy & data rights category (retention
  ceilings, data-subject rights, PII inventory) + rate-limiting slot
  that names its catalogue code.
- ✅ `templates/error-catalogue.md`: 429 section stub; trigger
  guidance for invalid-signature 401s and never-existed tokens.
- ✅ `templates/acceptance-scenarios.md`: conventions block — every
  scenario's Given names actor + resource state; assertions use
  schema property paths; POST scenarios carry `Idempotency-Key`.
- ✅ `skills/domain-access-control/SKILL.md`: Decision Log prompts
  for 403-vs-404 existence leakage; singleton-resource ownership
  pattern; FK-bearing-create ownership consistency.
- ✅ `skills/domain-asyncapi/SKILL.md`: open-enum representation must
  match openapi (no silent string downgrade); envelope requires
  `data`; per-channel lifecycle-status `const` narrowing.
- ✅ `skills/domain-datacontract/SKILL.md`: qualified-ref convention;
  open enums must not be pinned closed.
- ✅ `skills/domain-modeling/SKILL.md`: every entity needs an origin
  event; temporal invariants must name the attribute that persists
  them.
- ✅ `skills/domain-review/SKILL.md`: new prompts — NFR↔asyncapi
  delivery-semantics consistency; dead contract surface; unobservable
  Then clauses.
- ✅ `gate-version.yaml` → 1.2 + `gate-changelog.md` entry
  (suite-version.yaml stays 1.0.0-alpha per current release
  practice — the v1.0.15 label is the milestone name).
- ✅ ~~Incidental fix: `seed_signoffs.py` stale glob~~ — superseded by
  6.19's YAML-based rewrite, which fixed the same bug on main.

### 6.21 v1.0.16 / gate 1.3 — FIELD-MATCH skips [secret] attributes — [x]

Found while actioning the dog-walking critique's L5 under gate 1.2.
`FIELD-MATCH-DOMAIN-OPENAPI` used the raw attribute parser, so a
`[secret]`-marked model attribute (`User.passwordHash`,
`Invite.token`) was *required* to appear in the entity's OpenAPI
schema — forcing spec sets to advertise response-schema properties
the API must never return, precisely what the marker exists to
prevent.

- ✅ `shared/checks/field_match_domain_openapi.py` uses
  `domain_model_published_attributes` (the `[secret]`-stripping
  parser already used by `EVENT-PAYLOAD-COVERS-ENTITY-STATE`).
  Request schemas may still take secret inputs — the check only
  inspects entity schemas.
- ✅ Regression test (`tests/test_contracts.py`): a `[secret]`
  attribute absent from the OpenAPI schema passes; a non-secret
  absent attribute still fails.
- ✅ Items fixture unaffected — its `User` is represented by
  `UserSummary`, which FIELD-MATCH never keyed on.
- ✅ `gate-version.yaml` → 1.3 + `gate-changelog.md` entry. Pure
  loosening: every spec set green under 1.2 stays green under 1.3.

### 6.22 v1.0.17 — bootstrap CI templates clone the suite — [x]

Found when spec-dog-walking's Audit workflow turned out to have been
red since 2026-06-06: `docs:generate` (and later `task audit`) were
delegated to suite-side scripts, but the bootstrap-installed CI
workflows never cloned `domain-spec-suite`, so every bootstrapped
repo's CI died at "suite not found" and fell back to nothing. No gate
change — templates only.

- ✅ `skills/domain-bootstrap/templates/.github/workflows/audit.yml` +
  `docs.yml`: check out the domain repo and the suite as sibling
  paths (matching the local layout the Taskfile assumes), install the
  toolchain via `mise install` from `.mise.toml`, and run everything
  through the same Taskfile targets hooks and agents use
  (`mise exec -- task lint / audit / docs:generate / docs:build`) —
  no CI-only command paths. The audit fallback to `task domain:check`
  is gone (`task audit` has existed since M2.3).
- ✅ `template_manifest.yaml` regenerated.
- ✅ Fix proven on spec-dog-walking PR #2: first green Audit run since
  2026-06-06.

---

## Post-v1 Backlog

Things noted during design but not in scope for v1:

- ADR (Architectural Decision Record) support — phase or fold into existing
- Multi-user collaboration — locking, merge resolution
- Field-level update mode — finer than phase-level
- Generic (non-SKILL.md) packaging for portability to other agents
- Capacity / sizing doc as a separate phase
- Integrations / external dependencies doc

### Distribution / packaging (v1.1 candidate)

**Intent:** package the suite as a **Claude plugin** (skills + bundled
Python + bootstrap templates) so users install with one command
matching the ecosystem they already use, not a separate pipx step.

**Why skill-first, not pipx-first:** users today install Claude skills
via the plugin / marketplace mechanism. Asking them to also run
`pipx install domain-spec-suite` is friction. The plugin format can
bundle the Python helpers the skills call, so one install gives both
the skills (Claude auto-discovers) and the supporting machinery.

**Recommended shape:**

```
domain-spec-suite/                       ← published plugin
├── plugin.json
├── skills/
│   ├── domain-orchestrator/SKILL.md
│   ├── ... 8 skills total ...
├── scripts/                             ← bundled Python (the current shared/ + scripts/)
└── templates/                           ← bootstrap-installed spec-repo shell
```

Plugin install would also drop a thin `dss` shim onto PATH so spec
repos / CI / Taskfiles can call `dss audit --repo .` without needing
Claude running.

**Open questions to research before building:**

- Exact Claude plugin format (`plugin.json` schema, marketplace.json,
  how bundled scripts are referenced from SKILL.md via
  `${CLAUDE_PLUGIN_ROOT}` or similar).
- Marketplace publishing path: single-repo marketplace vs contributing
  to `@anthropics/skills` vs other.
- Plugin update / pin / uninstall lifecycle.
- Whether plugins can install PATH shims, or whether `dss` needs a
  separate `pipx install` step.
- Test story: how to CI-test a plugin (load skills in a sandboxed
  Claude env, run the audit, assert green).

**Status:** deferred. Until packaged, distribution is git-clone +
sibling-checkout convention (see `task audit` resolution order in
the bootstrap-installed README).

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
