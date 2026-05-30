"""Audit check: _ambiguities.md has no items still flagged as required
by the audit.

Items deferred during soft-gate phases can name a `required_by` value
(typically `audit`). The audit refuses to declare complete while any
such item remains unresolved — the spec set has known holes.
"""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult

metadata = {
    "id": "AMBIGUITIES-NO-AUDIT-REQUIRED",
    "category": "structural",
    "phases": ["audit"],
    "severity_by_phase": {"audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/_ambiguities.md"},
    ],
}

# Matches: "Resolution required before: audit phase" or any line
# carrying a `required_by: audit` indicator inside the Deferred section.
AUDIT_REQUIRED = re.compile(
    r"(?im)^(?:-\s*)?(?:resolution\s+)?required(?:_by| before)?\s*[:\s].*audit",
)

# Resolved items are below a heading like "## Resolved". We want to
# only scan entries above that.
RESOLVED_HEADING = re.compile(r"(?im)^##\s+resolved\s*$")


def run(repo_root: pathlib.Path) -> CheckResult:
    path = repo_root / "docs" / "specifications" / "_ambiguities.md"
    text = path.read_text(encoding="utf-8")

    # Trim to the section above the Resolved heading.
    resolved_match = RESOLVED_HEADING.search(text)
    pending_section = text[: resolved_match.start()] if resolved_match else text

    offenders: list[str] = []
    for line_no, line in enumerate(pending_section.splitlines(), start=1):
        if AUDIT_REQUIRED.search(line):
            offenders.append(f"line {line_no}: {line.strip()[:100]}")

    if not offenders:
        return CheckResult.ok()

    return CheckResult.fail(
        "_ambiguities.md still has items flagged for resolution before "
        "the audit phase. The audit refuses to declare the spec set "
        "complete while these are open. Either resolve each item (and "
        "move it under the ## Resolved heading), or accept the deferral "
        "via a force-advance entry on the originating phase.",
        details=offenders,
    )
