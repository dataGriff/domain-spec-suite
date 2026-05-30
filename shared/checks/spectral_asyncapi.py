"""Contracts-phase tool check: Spectral validates contracts/asyncapi.yaml
against the repo's `.spectral-asyncapi.yaml` ruleset.

Subprocesses the `spectral` CLI. Skipped (not failed) on machines
where spectral isn't installed — see spectral_openapi.py for the
rationale.
"""

from __future__ import annotations

import pathlib
import subprocess

from shared.check_result import CheckResult

metadata = {
    "id": "SPECTRAL-ASYNCAPI",
    "category": "structural",
    "phases": ["contracts", "audit"],
    "severity_by_phase": {"contracts": "error", "audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/contracts/asyncapi.yaml"},
        {"file_exists": ".spectral-asyncapi.yaml"},
        {"binary_exists": "spectral"},
    ],
}


def run(repo_root: pathlib.Path) -> CheckResult:
    contract = repo_root / "docs/specifications/contracts/asyncapi.yaml"
    ruleset = repo_root / ".spectral-asyncapi.yaml"

    proc = subprocess.run(
        ["spectral", "lint", str(contract), "--ruleset", str(ruleset)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        return CheckResult.ok()

    return CheckResult.fail(
        "Spectral reported errors in contracts/asyncapi.yaml. The "
        "event contract isn't valid AsyncAPI 2.x under the configured "
        "ruleset. What's the underlying violation? Run "
        "`task lint:asyncapi` in the target repo to reproduce, then "
        "fix each rule violation.",
        details=[line for line in (proc.stdout + proc.stderr).splitlines() if line.strip()],
    )
