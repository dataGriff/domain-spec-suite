# domain-spec-suite

A suite of Claude skills that walks a user from *"I have an idea for a
domain"* to *"I have a complete, internally-consistent,
implementation-agnostic spec set that can drive multiple implementations
forever."*

## Status

Active build — see [`BUILD-PLAN.md`](./BUILD-PLAN.md) for the operational
checklist and [`SUITE-DESIGN.md`](./SUITE-DESIGN.md) for the
architectural specification.

The suite is at version `1.0.13`. Gate version is `1.1` (see
[`gate-changelog.md`](./gate-changelog.md)).

## What it produces

The suite drives a user through eight phases (Bootstrap → Discovery →
Modeling → Access Control → Flows → NFRs → Contracts → Audit). The
output is a populated domain repository containing:

- `prd.md`, `domain-model.md`, `glossary.md`, `auth-matrix.md`,
  `error-catalogue.md`, `sequence-diagrams.md`, `nfr.md`,
  `acceptance-scenarios.md`
- `contracts/openapi.yaml`, `contracts/asyncapi.yaml`,
  `contracts/datacontract.yaml`
- Suite state files: `_progress.yaml`, `_bootstrap.yaml`,
  `_ambiguities.md`, eight `_phase-N-passed.yaml` sidecars
- Repository shell: `Taskfile.yml`, linting configs, `mkdocs.yml`,
  generator scripts, hooks, CI workflows, agent instruction files

Once the audit phase passes, the spec set is declared complete and
ready to drive implementations.

## How it works

- **`domain-orchestrator`** — entry-point skill. Reads `_progress.yaml`,
  identifies the current phase, hands off to the phase skill.
- **Eight phase skills** — each carries a `gate.yaml`, a `questions.md`
  bank, prose templates, and (where the gate is mechanical) Python
  check scripts.
- **`shared/checks/`** — cross-phase Python check modules with
  per-phase severity metadata.
- **`shared/sign_off.py`** — the only path that writes
  `_phase-N-passed.yaml`. Refuses if `task gate:<phase>` exits non-zero.

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
│   └── domain-conformance-audit/
├── shared/checks/                        ← cross-phase Python check modules
├── scripts/                              ← operator scripts (seed_signoffs, force_advance, …)
├── tests/fixtures/                       ← reference spec sets (Items copied here in M2.3)
└── docs/                                 ← suite documentation (not a domain's docs)
```

## Setup

```bash
task setup       # mise install + pip dev deps
task --list      # discover available tasks
task test        # run the smoke test suite
task lint        # ruff lint + format check
```

Requires [mise](https://mise.jdx.dev/) for Python and tooling version
pinning.
