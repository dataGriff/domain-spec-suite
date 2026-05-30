---
name: domain-orchestrator
description: |
  Entry point for the domain-spec-suite. Reads `_progress.yaml` and
  per-phase sidecars in the target repo, identifies what's done /
  in-progress / stale / next, and routes the user into the appropriate
  phase skill with explicit confirmation. Never auto-advances between
  phases; never edits spec files itself.
trigger_phrases:
  - "start a new domain"
  - "where am i in the suite"
  - "what's next"
  - "run the orchestrator"
  - "resume domain work"
  - "begin spec set"
---

# Domain orchestrator

The orchestrator is the user's front door to the spec suite. Every
session of spec work goes through it. Its single job is to read the
target repo's state, decide what the user should do next, and route
into the right phase skill with an explicit confirmation.

## What this skill does

1. **Resolve the target repo.** Default: current working directory.
2. **Read state mechanically.** Invoke
   `python scripts/orchestrator_status.py --repo <target> --json`
   and parse the JSON report. This is the only source of truth — do
   not reconstruct phase status by reading sidecars or progress
   yourself; the script enforces sha256-based staleness detection
   per SUITE-DESIGN §6 and you cannot drift from it.
3. **Decide the action.** The report's `next_action.action` is one of:
   - `bootstrap` — no `_progress.yaml`. Confirm with the user, set
     expectations per SUITE-DESIGN §7, route into `domain-bootstrap`.
   - `start` — next phase is implemented and not started. Prompt the
     user with phase name, what it produces, what later phases depend
     on it, rough effort estimate. End with explicit confirmation
     ("Ready to begin Phase N?"). Hand off to the matching skill.
   - `resume` — phase is in-progress. Re-enter the phase skill; it
     reads existing outputs as the starting point.
   - `update-mode` — one or more phases are stale (file sha256 has
     drifted since sign-off). Present the three options from
     SUITE-DESIGN §6 (Targeted / Full / Audit-only) and route
     accordingly.
   - `accept-force-advances` — every phase passed but force-advance
     entries are unaccepted. Walk the user through each entry
     (phase, reason, forced_at, operator), then route them to
     `task suite:accept-force <phase> --reason '<text>'`. Audit
     will fail until cleared.
   - `not-implemented` — next phase is one the suite doesn't yet have
     a skill for (modeling, access-control, flows, nfrs at the time of
     M4). Tell the user honestly: "The next phase is X, but the suite
     doesn't implement that skill yet. M5 of BUILD-PLAN.md adds it.
     We can either pause here or skip to a later phase that is
     implemented."
   - `complete` — every phase signed off and audit is green. Declare
     completion per §3 ("Spec set complete. Audited against
     gate-version X at timestamp. Ready to drive implementations.").
4. **Hand off, don't drive.** When routing into a phase skill, let
   that skill run its own interview loop. The orchestrator does not
   ask phase-specific questions, does not run phase gates itself, and
   does not write any spec files.
5. **On phase completion, re-read state.** The just-finished skill
   updates `_progress.yaml` and writes its sidecar via
   `shared/sign_off.py`. Re-invoke `orchestrator_status.py` to get
   the next action, then prompt the user with the next phase per
   step 3. Never chain phases without acknowledgment (§3).

## Prompting

Use the §7 voice — senior business analyst conducting an interview.
The orchestrator's prompts are mostly handoff-shaped: "Phase 2 of 7
(Modeling) is next. It produces `domain-model.md` and `glossary.md`
and roughly takes 45–90 minutes for a domain this size. Ready to
begin?"

First-run framing comes from §7 "Expectation-setting on first run" —
quote it (lightly adapted) when `action == "bootstrap"` on a fresh
repo.

## State-snapshot map (orchestrator_status.py JSON shape)

```
{
  "repo": "<absolute path>",
  "bootstrapped": true | false,
  "suite_version": "1.0.0",
  "gate_version": "1.0.0",
  "domain_name": "items" | null,
  "phases": [
    {
      "phase": "discovery",
      "number": 1,
      "status": "not-started" | "in-progress" | "passed" | "stale",
      "implemented": true | false,
      "signed_off_at": "...",
      "gate_version": "1.0.0",
      "stale_files": ["docs/specifications/prd.md", ...]
    },
    ...
  ],
  "pending_force_advances": [
    {"phase": "contracts", "reason": "...", "forced_at": "...", "operator": "...", "accepted": false}
  ],
  "next_action": {
    "action": "start" | "resume" | "update-mode" | "accept-force-advances" | "not-implemented" | "complete" | "bootstrap",
    "phase": "discovery",
    "summary": "human-readable hint"
  }
}
```

The `next_action.summary` is *advisory* — render the user-facing
prompt in your own words per §7, don't echo the summary verbatim.

## What this skill never does

- Never runs `task gate:<phase>` itself. Phase skills own their gates.
- Never edits `_progress.yaml`, `_phase-N-passed.yaml`, or any spec
  file. `shared/sign_off.py` is the only writer.
- Never auto-advances between phases — every phase boundary requires
  an explicit "Ready to begin Phase N?" confirmation.
- Never invents a phase skill that doesn't exist. If `next_action.action`
  is `not-implemented`, say so honestly.
- Never reconstructs status without `orchestrator_status.py`. The
  script's sha256-based staleness is the design contract; rolling
  your own is how drift happens.

## Files this skill reads

- `docs/specifications/_progress.yaml` — phase status, force-advance
  log, session log
- `docs/specifications/_phase-N-passed.yaml` (each one that exists)
  — file-level sign-off with sha256 manifest
- `docs/specifications/<file>` for each path in any sidecar's
  `files_signed` (to compare sha256 against the recorded value —
  staleness detection)

All reads go through `scripts/orchestrator_status.py`.

## Files this skill writes

None. The orchestrator is read-only by design; it routes the user to
skills that write.
