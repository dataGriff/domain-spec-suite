"""Audit check: every file recorded in a _phase-N-passed.yaml sidecar
still hashes to the recorded sha256.

If a sidecar's recorded hash differs from the current file content, the
file has been edited since sign-off — the phase is stale and the
re-sign workflow (via the orchestrator's update mode) must run before
audit can pass.
"""

from __future__ import annotations

import hashlib
import pathlib
import re

from shared.check_result import CheckResult

metadata = {
    "id": "SIGNOFF-SHA256-MATCHES",
    "category": "structural",
    "phases": ["audit"],
    "severity_by_phase": {"audit": "error"},
    "prerequisites": [],
}

# Matches the shape produced by sign-off:
#   - path: docs/specifications/prd.md
#     sha256: "abc..."
ENTRY = re.compile(
    r"-\s*path:\s*(?P<path>\S+)\s*\n\s*sha256:\s*\"(?P<sha>[0-9a-f]+)\"",
    re.MULTILINE,
)


def run(repo_root: pathlib.Path) -> CheckResult:
    specs = repo_root / "docs" / "specifications"
    if not specs.is_dir():
        return CheckResult.fail(
            "There's no docs/specifications/ directory to scan. "
            "Has Phase 0 (Bootstrap) been run against this repo?",
        )

    sidecars = sorted(specs.glob("_phase-*-passed.yaml"))
    if not sidecars:
        return CheckResult.fail(
            "No phase sign-off sidecars (_phase-*-passed.yaml) found. "
            "Audit can't run before at least Phase 0 (Bootstrap) has "
            "signed off. Has the bootstrap script been run?",
        )

    mismatches: list[str] = []
    checked = 0
    for sidecar in sidecars:
        text = sidecar.read_text(encoding="utf-8")
        for match in ENTRY.finditer(text):
            checked += 1
            path = match.group("path")
            recorded = match.group("sha")
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
