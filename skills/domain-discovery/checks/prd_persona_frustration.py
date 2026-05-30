"""Phase 1 structural check: every persona in prd.md declares a
Frustration of at least 10 characters."""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult
from shared.spec_parsers import _section

metadata = {
    "id": "PRD-PERSONA-FRUSTRATION",
    "category": "structural",
    "phases": ["discovery"],
    "severity_by_phase": {"discovery": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/prd.md"},
    ],
}

PERSONA_BLOCK_RE = re.compile(
    r"(?m)^###\s+(?P<name>\S[^\n]*)\n(?P<body>.*?)(?=^###\s+|\Z)", re.DOTALL
)
FRUSTRATION_RE = re.compile(
    r"-\s*\*\*Frustration:\*\*\s*(?P<text>.+?)(?:\n\s*-\s*\*\*|\n\n|\Z)", re.DOTALL
)
PLACEHOLDER_TEXT = {"todo", "tbd", "tbc"}
MIN_FRUSTRATION_CHARS = 10


def run(repo_root: pathlib.Path) -> CheckResult:
    prd = repo_root / "docs" / "specifications" / "prd.md"
    text = prd.read_text(encoding="utf-8")
    section = _section(text, r"^##\s+Target Users(?:\s*/\s*Personas)?\s*$")

    problems: list[str] = []
    for match in PERSONA_BLOCK_RE.finditer(section):
        name = match.group("name").strip()
        frustration_match = FRUSTRATION_RE.search(match.group("body"))
        if frustration_match is None:
            problems.append(f"{name!r}: no Frustration line found")
            continue
        frustration = frustration_match.group("text").strip().rstrip(",.;")
        if frustration.lower() in PLACEHOLDER_TEXT or len(frustration) < MIN_FRUSTRATION_CHARS:
            problems.append(f"{name!r}: Frustration is too thin or still TODO: {frustration!r}")

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "One or more personas have no real Frustration recorded. For "
        "each one below: what specifically frustrates them about how "
        "they work today? Push for the concrete moment, not the abstract "
        "wish for a better tool.",
        details=problems,
    )
