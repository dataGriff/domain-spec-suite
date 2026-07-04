---
name: domain-bootstrap
description: |
  Lays down the canonical domain spec repository shell in an empty
  directory (or in-place on a non-empty directory with --force).
  Invoked at the start of any new domain spec set, or by the orchestrator
  when it detects an unbootstrapped target. Produces the Taskfile,
  linting configs, mise tooling pins, hooks, CI workflows, skeleton
  scripts, and the initial `.spec-suite/progress.yaml`,
  `.spec-suite/bootstrap.yaml`, and `.spec-suite/template-manifest.yaml`
  state files. Deliberately ships no agent guidance files; blank spec
  templates stay in the suite and are served by `task init:<phase>`.
  Phase 0 in the suite's eight-phase model.
prerequisites:
  - Target directory exists.
  - Target directory is empty, OR `--force` is set (manifest-aware
    overwrite — never touches spec content or `.spec-suite/` state).
trigger_phrases:
  - "set up a new domain spec repo"
  - "bootstrap a domain"
  - "initialise a domain spec set"
  - "phase 0"
---

# Phase 0 — Bootstrap

This skill is **mechanical**. Almost all of the work is done by a
Python script (`scripts/bootstrap.py`); your job as the agent is to
gather one piece of input from the user, run the script, and report
the result.

## What this skill produces

A populated repository shell containing:

- `Taskfile.yml`, `.spectral-openapi.yaml`, `.spectral-asyncapi.yaml`,
  `.mise.toml`, `.gitignore`
- `README.md`, `mkdocs.yml`, `docs/index.md` (interpolated for the
  target domain)
- `.github/CODEOWNERS`
- `.githooks/pre-commit`, `.githooks/pre-push` (executable)
- `.github/workflows/audit.yml` (Tier 3 conformance check on PRs)
- `.github/workflows/docs.yml` (deploys the MkDocs site + generated
  domain overview to GitHub Pages on every push to main, so the
  spec set is shareable as soon as it has merged)
- `scripts/` skeleton + lint helpers (`openapi_skeleton.py`,
  `asyncapi_skeleton.py`, `datacontract_skeleton.py`,
  `glossary_skeleton.py`, `lint_fix_descriptions.py`). The domain
  overview generator is NOT copied — it lives in the suite
  (`<suite>/scripts/generate_domain_overview.py`); the installed
  `task docs:generate` delegates to it via `DOMAIN_SPEC_SUITE_ROOT`,
  the same resolution `task audit` uses.

**The bootstrap deliberately ships no agent guidance files** (no
`CLAUDE.md`, no `AGENTS.md`, no `.github/instructions/*.md`). All
spec-set changes go through the suite's orchestrator and phase
skills — those are the only sanctioned interface. A bootstrapped
domain repo is intentionally a slate that the skills drive.
- `.spec-suite/progress.yaml` (Phase 0 marked passed,
  `force_advances: []`)
- `.spec-suite/bootstrap.yaml` (suite + gate version
  recording)
- `.spec-suite/ambiguities.md` (empty)
- `.spec-suite/template-manifest.yaml` (the manifest of files
  this skill installed — consulted by `--force` re-bootstrap and by
  `task suite:upgrade-shell`)

It does **not** produce any populated spec files — those are written
by Phases 1–6 as the user walks through the rest of the suite.

## How to run it

1. **Confirm the target directory with the user.** Bootstrap usually
   runs in the current working directory (`pwd`). If the user is in
   the wrong directory, stop and ask before proceeding. Quote the
   target path back to the user verbatim and ask "set up this directory
   as a domain spec repo? This will create [N] files."

   **Naming convention.** The target directory MUST be named
   `spec-<domain-slug>` (e.g. `spec-items`, `spec-dog-walking`,
   `spec-orders`). Bootstrap refuses other names with a clear error.
   If the user picked a non-prefixed name, recommend renaming. Use
   `--allow-non-prefix` only for documented legacy targets.

2. **Ask for the `domain_name`.** This populates `{{domain_name}}`
   placeholders in `README.md`, `mkdocs.yml`, `docs/index.md`.
   Use the user's words (e.g. "Items", "Orders",
   "Catalogue") — title case, no quoting.
3. **Run the script** via Bash. From any directory:

   ```bash
   python <suite-root>/scripts/bootstrap.py \
     --target <target-dir> \
     --domain-name "<Domain Name>"
   ```

   `<suite-root>` is the directory containing this skill — relative
   from this `SKILL.md`, it is `../../`. `<target-dir>` is the
   absolute path to the target.

   Add `--force` only if the user has explicitly confirmed they want
   to refresh a non-empty bootstrapped directory (e.g. for a shell
   upgrade). `--force` never touches spec content or `.spec-suite/` state
   — it only overwrites files listed in `template_manifest.yaml`.

4. **Report what the script printed.** The script prints one line per
   file written and a final summary. Pass that summary to the user
   verbatim — don't paraphrase or pretty-print.

5. **Hand off to the orchestrator.** After a successful bootstrap, tell
   the user: *"Bootstrap complete. The next step is Phase 1 (Discovery)
   — invoke the `domain-orchestrator` skill to begin."*

## When to refuse

- **Target directory does not exist.** Don't create it on the user's
  behalf — ask them to `mkdir` it first so they're explicit about
  where the shell will land.
- **Target directory is non-empty and the user has not asked for a
  refresh.** Quote the existing files to the user and ask: "this
  directory already contains [N] files. Are you trying to refresh an
  existing bootstrap (`--force`), or did you mean a different
  directory?"
- **Bootstrap script exits non-zero.** Report the exit code and
  stderr verbatim. Do not retry.

## What this skill never does

- Never populates `docs/specifications/<spec>.md` — those are written
  by Phases 1–6.
- Never edits `.spec-suite/progress.yaml` after creation — that's the orchestrator's
  and phase skills' responsibility.
- Never re-runs Phase 1+ checks — Phase 0 has its own trivial gate
  (every expected file exists and parses); other phases run independently.
- Never deletes files. Even `--force` is overwrite-only against the
  manifest; nothing outside the manifest is touched.

## Phase 0 gate (what the script verifies before declaring success)

Per `SUITE-DESIGN.md` §8 Phase 0:

- All expected files exist at expected paths.
- All YAML files parse, all markdown is well-formed.
- `.spec-suite/progress.yaml` is present and has Phase 0 marked `passed`.
- `.spec-suite/bootstrap.yaml` records the suite and gate version.
- `.spec-suite/template-manifest.yaml` is present and lists every file the
  bootstrap owns.

The script raises and exits non-zero if any of these fail. If you see
that, do not attempt to fix the output manually — re-run the script.
