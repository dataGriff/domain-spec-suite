"""Audit check: every file recorded in a _phase-N-passed.yaml sidecar
still hashes to the recorded sha256.

If a sidecar's recorded hash differs from the current file content, the
file has been edited since sign-off — the phase is stale and the
re-sign workflow (via the orchestrator's update mode) must run before
audit can pass.

The sidecar is parsed as YAML (not regex-matched) because YAML's
quote-stripping for plain strings means sha256 values can be either
quoted ("abc...") or bare (abc...) depending on the writer — the
regex approach silently misses bare values.
"""

from __future__ import annotations

import hashlib
import pathlib

import yaml

from shared import spec_paths
from shared.check_result import CheckResult

metadata = {
    "id": "SIGNOFF-SHA256-MATCHES",
    "category": "structural",
    "phases": ["audit"],
    "severity_by_phase": {"audit": "error"},
    "prerequisites": [],
}


def run(repo_root: pathlib.Path) -> CheckResult:
    if not spec_paths.state_dir(repo_root).is_dir():
        return CheckResult.fail(
            "There's no .spec-suite/ directory to scan. "
            "Has Phase 0 (Bootstrap) been run against this repo?",
        )

    sidecars = spec_paths.all_phase_sidecars(repo_root)
    if not sidecars:
        return CheckResult.fail(
            "No phase sign-off sidecars in .spec-suite/phases/. "
            "Audit can't run before at least Phase 0 (Bootstrap) has "
            "signed off. Has the bootstrap script been run?",
        )

    mismatches: list[str] = []
    for sidecar in sidecars:
        doc = yaml.safe_load(sidecar.read_text(encoding="utf-8")) or {}
        for entry in doc.get("files_signed") or []:
            if not isinstance(entry, dict):
                continue
            path = entry.get("path")
            recorded = entry.get("sha256")
            if not path or not recorded:
                continue
            target = repo_root / path
            if not target.is_file():
                mismatches.append(f"{sidecar.name}: '{path}' referenced but file does not exist")
                continue
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            if actual != recorded:
                mismatches.append(
                    f"{sidecar.name}: {path}\n"
                    f"            recorded {recorded[:12]}…  actual {actual[:12]}…"
                )

    if not mismatches:
        return CheckResult.ok()

    return CheckResult.fail(
        "Sign-off sidecars are out of sync with the spec files. Each "
        "mismatch below means a file changed after its phase was "
        "signed off — the phase is now stale. Re-run the affected "
        "phase via the orchestrator's update mode so its sign-off "
        "matches reality, then re-run audit.",
        details=mismatches,
    )
