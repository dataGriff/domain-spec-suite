---
description: "Use when reading, writing, or adding tasks to Taskfile.yml. Covers naming conventions, structure, when to add a new task, and how to avoid duplicate or ad-hoc commands."
applyTo: "Taskfile*.yml"
---

# Taskfile Conventions

## Taskfile location

| File | Contains |
|------|----------|
| `Taskfile.yml` | Project-wide tasks for contract linting, docs generation, docs publishing, and bootstrap |

## Naming convention

Follow the existing `namespace:action` pattern:

```
lint:openapi
lint:asyncapi
lint:datacontract
docs:generate
domain:init
```

- Namespaces are lowercase, hyphen-separated (`line-items`, not `lineItems`)
- Use consistent verbs: `list`, `get`, `create`, `update`, `delete`, `start`, `complete`, `cancel`, `submit`, `accept`, `decline`, `send`
- Qualifier (e.g. a role name like `contributor`) goes last when disambiguating

## Required fields for every new task

Every task must have a `desc:` so it appears in `task --list`:

```yaml
my:new:task:
  desc: Brief description of what this task does
  cmds:
    - ...
```

## When to add a new task

Add a task whenever you would otherwise run a raw CLI command during development, CI, or demos:
- A new contract quality check is introduced → add it to `Taskfile.yml`
- A docs build or publish step is introduced → add it to `Taskfile.yml`
- A script or tool is run more than once → it belongs in a task

**Do not** run raw `curl`, `npm`, `spectral`, `mkdocs`, or other CLI commands directly. Add a task first.

## Checking for duplicates before adding

Before adding a task, run `task --list` to confirm no equivalent already exists. If a similar task exists, extend or alias it rather than creating a near-duplicate.
