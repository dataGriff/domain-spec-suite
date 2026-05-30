"""Audit check: every force-advance entry in _progress.yaml must be
explicitly accepted before the audit can pass.

Force-advances are an honesty mechanism (SUITE-DESIGN §11/Decision 5):
they bypass a hard gate with a recorded reason, but the audit blocks
the spec set from being declared complete until each is either
resolved (the underlying check now passes) or accepted via
`task suite:accept-force <phase> --reason '<text>'`.
"""

from __future__ import annotations

import pathlib

import yaml

from shared.check_result import CheckResult

metadata = {
    "id": "FORCE-ADVANCES-ALL-ACCEPTED",
    "category": "structural",
    "phases": ["audit"],
    "severity_by_phase": {"audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/_progress.yaml"},
    ],
}


def run(repo_root: pathlib.Path) -> CheckResult:
    progress_path = repo_root / "docs" / "specifications" / "_progress.yaml"
    progress = yaml.safe_load(progress_path.read_text())
    entries = progress.get("force_advances") or []
    if not isinstance(entries, list):
        return CheckResult.fail(
            "force_advances in _progress.yaml is not a list — the file "
            "may have been edited by hand. Restore the [] / list-of-"
            "objects shape (see SUITE-DESIGN §4) and re-run audit.",
        )

    unaccepted = [e for e in entries if not e.get("accepted")]
    if not unaccepted:
        return CheckResult.ok()

    lines = []
    for entry in unaccepted:
        phase = entry.get("phase", "<unknown phase>")
        reason = entry.get("reason", "<no reason recorded>")
        forced_at = entry.get("forced_at", "<no timestamp>")
        lines.append(f"phase={phase}  forced_at={forced_at}\n            reason: {reason}")

    return CheckResult.fail(
        "Force-advance entries remain unaccepted. The audit will not "
        "declare the spec set complete while a hard gate was bypassed "
        "without explicit acceptance. For each entry below, either "
        "resolve the underlying check failure (and remove the entry) "
        "or run `task suite:accept-force <phase> --reason '<text>'` "
        "to record an explicit acceptance.",
        details=lines,
    )
