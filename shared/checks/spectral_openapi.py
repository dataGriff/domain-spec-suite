"""Contracts-phase tool check: Spectral validates contracts/openapi.yaml
against the repo's `.spectral-openapi.yaml` ruleset.

Subprocesses the `spectral` CLI. Skipped (not failed) on machines
where spectral isn't installed — the bootstrap pins it in the target
repo's .mise.toml, so a properly-set-up domain repo always has it;
this skip is a courtesy for the suite's own CI (which only installs
Python).
"""

from __future__ import annotations

import pathlib
import subprocess

from shared.check_result import CheckResult

metadata = {
    "id": "SPECTRAL-OPENAPI",
    "category": "structural",
    "phases": ["contracts", "audit"],
    "severity_by_phase": {"contracts": "error", "audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/contracts/openapi.yaml"},
        {"file_exists": ".spectral-openapi.yaml"},
        {"binary_exists": "spectral"},
    ],
}


def run(repo_root: pathlib.Path) -> CheckResult:
    contract = repo_root / "docs/specifications/contracts/openapi.yaml"
    ruleset = repo_root / ".spectral-openapi.yaml"

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
        "Spectral reported errors in contracts/openapi.yaml. The "
        "contract isn't valid OpenAPI 3.x under the configured ruleset. "
        "What's the underlying violation? Run "
        "`task lint:openapi` in the target repo to reproduce, then fix "
        "each rule violation.",
        details=[line for line in (proc.stdout + proc.stderr).splitlines() if line.strip()],
    )
