# Working in the domain-spec-suite

> **Every session:** read `SUITE-DESIGN.md` and `BUILD-PLAN.md` in full
> before touching anything else. The design doc is the architectural
> contract; the build plan is the operational checklist.

## Conventions

- **Python 3.11+**, pinned via `.mise.toml`. Use `mise exec -- …` to run
  Python, pytest, or ruff with the project-pinned interpreter when
  outside a mise-activated shell.
- **Taskfile is the single entry point.** Skills, hooks, and CI all
  invoke the same `task gate:<phase>` / `task audit` targets. Don't
  add ad-hoc scripts outside the Taskfile.
- **Ruff** handles lint + format. **pytest** runs tests. Both configured
  in `pyproject.toml`.
- **`tests/fixtures/items/`** is the canonical reference fixture — the
  known-good Items spec set every audit/gate test runs against. Keep
  its sign-off sha256s valid with `task fixtures:seed-signoffs` after
  editing fixture content.

## Where check code and skill code live

- **`shared/checks/<id>.py`** — cross-phase Python check modules with a
  `metadata` dict (id, phases, severity_by_phase, prerequisites) and a
  `run(repo_root) → CheckResult` function. See SUITE-DESIGN §5.5.
- **`skills/<phase>/checks/<id>.py`** — phase-local checks following
  the same module shape.
- **`shared/sign_off.py`** — the only path that writes
  `.spec-suite/phases/phase-N-passed.yaml`. Mechanical enforcement,
  not instructional.
- **`scripts/`** — operator scripts invoked via Taskfile
  (`seed_signoffs.py`, `force_advance.py`, `accept_force.py`,
  `upgrade_shell.py`, `reset_phase.py`).

## Commit conventions

- **Conventional commits with the BUILD-PLAN task id.** Examples:
  `feat(2.2): bootstrap copies templates`,
  `fix(3.2): force-advance writes to progress.yaml`,
  `docs(0): clarify rubric handling in §5.5`.
- **One commit per task** (not per milestone). Commits are the
  vertical slice between two checkpoints in the build plan.
- **Stop at every 🛑 review checkpoint.** Summarise what was done and
  wait for confirmation before continuing.

## Working style (from BUILD-PLAN.md)

- **Small commits.** After each task, not at milestone boundaries.
- **Test as you go.** Write → test → fix → commit. Don't batch.
- **Surface assumptions.** If anything in SUITE-DESIGN.md is
  ambiguous when applied to actual code, stop and ask.
- **Honest progress.** Hitting a problem or running long? Say so;
  don't silently expand scope or paper over issues.

## Hard rules

- **Do not invent new files or directories** not specified in
  BUILD-PLAN. If you find a gap, surface it before filling it.
- **Tests are not optional.** Each milestone exit criterion references
  real tests. Don't claim a task complete because the code "looks
  right" — only when tests confirm it works.
- **Never bypass mechanical sign-off.** The runner refuses for a
  reason. Use `task suite:force-advance` (with a written reason) if
  you genuinely must advance with a failing check.
