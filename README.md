# domain-spec-suite

A suite of Claude skills that walks a user from *"I have an idea for a
domain"* to *"I have a complete, internally-consistent,
implementation-agnostic spec set that can drive multiple implementations
forever."*

## Quickstart — spec a new domain

You need [mise](https://mise.jdx.dev/), [Task](https://taskfile.dev/),
and Claude Code with this repo's skills available.

1. Create an **empty** directory named `spec-<your-domain>` as a
   sibling of this checkout (e.g. `spec-orders` next to
   `domain-spec-suite/`). The `spec-` prefix is enforced.
2. Open Claude Code in that directory and invoke the
   **`domain-orchestrator`** skill (or just say "set up a new domain
   spec repo").
3. The orchestrator bootstraps the repo shell, then interviews you
   phase by phase — one question at a time, in business language.
   Expect 2–4 sessions for a moderately complex domain; you can stop
   at any point and the orchestrator resumes where you left off.

What the walk looks like:

- **Eight phases in fixed order**: Bootstrap → Discovery → Modeling →
  Access Control → Flows → NFRs → Contracts → Audit. Each phase
  produces specific files (see below) and ends with a **sign-off**.
- **Gates are mechanical.** Every phase has Python checks
  (`task gate:<phase>`); sign-off is refused while any check fails.
  Hard-gate phases (Discovery, Contracts, Audit) must fully pass.
  Soft-gate phases (Modeling → NFRs) let you resolve, defer, or mark
  warnings not-applicable — but every warning needs an explicit
  response; nothing is dismissed silently.
- **Audit is the closing gate.** It re-runs every cross-file check at
  error severity and chases down anything deferred earlier. When it
  passes, the spec set is complete.
- **Escape hatch**: `task suite:force-advance <phase> --reason '…'`
  advances past a genuinely stuck check, visibly — the audit fails
  until the force is explicitly accepted.

To update a finished spec set, invoke the orchestrator again: it
detects which files changed (sha256), marks the affected phases stale,
and walks only what needs re-signing (update mode).

A complete worked example lives at
[`tests/fixtures/items/`](./tests/fixtures/items/) — the canonical
known-good Items spec set every gate and audit test runs against.

## Status

Active build — see [`BUILD-PLAN.md`](./BUILD-PLAN.md) for the operational
checklist and [`SUITE-DESIGN.md`](./SUITE-DESIGN.md) for the
architectural specification.

Current versions are recorded in [`suite-version.yaml`](./suite-version.yaml)
and [`gate-version.yaml`](./gate-version.yaml); gate history is in
[`gate-changelog.md`](./gate-changelog.md).

## What it produces

The output is a populated domain repository containing:

- `prd.md`, `domain-model.md`, `glossary.md`, `auth-matrix.md`,
  `error-catalogue.md`, `sequence-diagrams.md`, `nfr.md`,
  `acceptance-scenarios.md`
- `contracts/openapi.yaml`, `contracts/asyncapi.yaml`,
  `contracts/datacontract.yaml`
- Generated views: domain overview, interactive API/AsyncAPI/data
  contract references, and a story→scenario→operation→event
  traceability matrix
- Agent-agnostic consumption guidance:
  `docs/implementation-guide.md` (the canonical build playbook) plus
  thin discovery pointers — `AGENTS.md` (cross-agent standard) and
  `.github/instructions/api-implementation.instructions.md` (Copilot)
- Suite state under `.spec-suite/`: `progress.yaml`, `bootstrap.yaml`,
  `ambiguities.md`, `template-manifest.yaml`, and eight
  `phases/phase-N-passed.yaml` sidecars
- Repository shell: `Taskfile.yml`, linting configs, `mkdocs.yml`,
  skeleton scripts, hooks, CI workflows. Deliberately **no**
  spec-authoring agent guidance (no `CLAUDE.md`; the shipped
  `AGENTS.md` exists to say "don't edit specs directly") — the
  orchestrator and phase skills are the only sanctioned interface for
  changing the spec set (SUITE-DESIGN §2)

Once the audit phase passes, the spec set is declared complete and
ready to drive implementations.

## How it works

- **`domain-orchestrator`** — entry-point skill. Reads
  `.spec-suite/progress.yaml`, identifies the current phase, hands off
  to the phase skill.
- **Eight phase skills** — each carries a `gate.yaml`, a `questions.md`
  bank, and (where the gate is mechanical) Python check scripts.
  Phase 6 also has three authoring sub-skills (`domain-openapi`,
  `domain-asyncapi`, `domain-datacontract`). Outside the phase
  progression sit two post-audit skills: `domain-review` (qualitative
  pass over the spec set) and `domain-implement` (drives building a
  service from the finished specs, in a separate implementation repo).
- **`shared/checks/`** — cross-phase Python check modules with
  per-phase severity metadata.
- **`shared/sign_off.py`** — the only path that writes
  `.spec-suite/phases/phase-N-passed.yaml`. Refuses if
  `task gate:<phase>` exits non-zero.

Sign-off enforcement is mechanical, not instructional: a skill can ask
the agent to write things, but only the runner produces the signed
record, and only when the Python gate passes.

## Layout

```
domain-spec-suite/
├── SUITE-DESIGN.md, BUILD-PLAN.md      ← architectural spec + operational checklist
├── README.md, CLAUDE.md                 ← repo intro / agent guidance
├── .mise.toml                            ← Python 3.11
├── pyproject.toml                        ← project metadata, dev deps, ruff + pytest config
├── Taskfile.yml                          ← suite-internal task entry points
├── suite-version.yaml, gate-version.yaml, gate-changelog.md
├── skills/
│   ├── domain-orchestrator/
│   ├── domain-bootstrap/
│   ├── domain-{discovery,modeling,access-control,flows,nfrs,contracts}/
│   ├── domain-{openapi,asyncapi,datacontract}/   ← Phase 6 authoring sub-skills
│   ├── domain-review/                    ← post-audit qualitative review
│   ├── domain-implement/                 ← post-audit implementation driver
│   └── domain-conformance-audit/
├── shared/checks/                        ← cross-phase Python check modules
├── scripts/                              ← operator scripts (bootstrap, upgrade_shell, reset_phase, …)
├── templates/                            ← blank spec templates served by task init:<phase>
├── tests/fixtures/items/                 ← canonical known-good reference spec set
└── docs/                                 ← suite documentation (not a domain's docs)
```

## Setup (suite development)

```bash
task setup       # mise install + pip dev deps
task --list      # discover available tasks
task test        # run the smoke test suite
task lint        # ruff lint + format check
```

Requires [mise](https://mise.jdx.dev/) for Python and tooling version
pinning.
