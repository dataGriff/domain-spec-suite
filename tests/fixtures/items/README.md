# domain-api-template

A **design-and-contracts-only** repository for long-lived domain requirements, rules, and API/event/data contracts.

> **Full documentation:** [`docs/index.md`](docs/index.md) (also published as a [MkDocs site](https://datagriff.github.io/domain-api-template/)).

---

## Quick Start

```bash
task domain:init
task domain:check
```

---

## What's in the Box

| Area | Location |
|------|----------|
| Product + domain requirements | `docs/specifications/*.md` |
| API/event/data contracts | `docs/specifications/contracts/*.yaml` |
| Implementation conformance guidance | `.github/instructions/api-implementation.instructions.md` |
| Blank spec templates | `docs/specifications/_template/` |
| Contract linting + docs tasks | `Taskfile.yml` |
| Published docs config | `mkdocs.yml`, `docs/`, `.github/workflows/docs.yml` |

---

## Goal

This repository intentionally contains no runnable API implementation. It is the reusable source of truth for:

- business requirements
- rules and permissions
- REST contracts
- event contracts
- data contracts

Implementations should live in separate repositories that consume this template.
When instantiated, these specs and instructions become the source of truth for that repository's implementation.
Use `.github/instructions/api-implementation.instructions.md` to keep implementation conformance consistent while remaining technology-agnostic.
