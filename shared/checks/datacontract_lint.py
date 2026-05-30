"""Contracts-phase tool check: datacontract-cli validates the ODCS 3.1
data contract at contracts/datacontract.yaml.

Subprocesses the `datacontract` CLI. Skipped (not failed) on machines
where datacontract-cli isn't installed.
"""

from __future__ import annotations

import pathlib
import subprocess

from shared.check_result import CheckResult

metadata = {
    "id": "DATACONTRACT-LINT",
    "category": "structural",
    "phases": ["contracts", "audit"],
    "severity_by_phase": {"contracts": "error", "audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/contracts/datacontract.yaml"},
        {"binary_exists": "datacontract"},
    ],
}


def run(repo_root: pathlib.Path) -> CheckResult:
    contract = repo_root / "docs/specifications/contracts/datacontract.yaml"

    proc = subprocess.run(
        ["datacontract", "lint", str(contract)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        return CheckResult.ok()

    return CheckResult.fail(
        "datacontract-cli reported errors in contracts/datacontract.yaml. "
        "The ODCS 3.1 data contract isn't valid. What's the underlying "
        "violation? Run `task lint:datacontract` in the target repo to "
        "reproduce, then fix the schema definition.",
        details=[line for line in (proc.stdout + proc.stderr).splitlines() if line.strip()],
    )
