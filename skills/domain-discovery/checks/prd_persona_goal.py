"""Phase 1 structural check: every persona in prd.md declares a Goal of
at least 10 characters.

Goals are matched in the persona block (between one `### ` heading and
the next) as a `- **Goal:** ...` line."""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult
from shared.spec_parsers import _section

metadata = {
    "id": "PRD-PERSONA-GOAL",
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
GOAL_RE = re.compile(r"-\s*\*\*Goal:\*\*\s*(?P<text>.+?)(?:\n\s*-|\n\n|\Z)", re.DOTALL)
PLACEHOLDER_TEXT = {"todo", "tbd", "tbc"}
MIN_GOAL_CHARS = 10


def run(repo_root: pathlib.Path) -> CheckResult:
    prd = repo_root / "docs" / "specifications" / "prd.md"
    text = prd.read_text(encoding="utf-8")
    section = _section(text, r"^##\s+Target Users(?:\s*/\s*Personas)?\s*$")

    problems: list[str] = []
    for match in PERSONA_BLOCK_RE.finditer(section):
        name = match.group("name").strip()
        goal_match = GOAL_RE.search(match.group("body"))
        if goal_match is None:
            problems.append(f"{name!r}: no Goal line found")
            continue
        goal = goal_match.group("text").strip().rstrip(",.;")
        if goal.lower() in PLACEHOLDER_TEXT or len(goal) < MIN_GOAL_CHARS:
            problems.append(f"{name!r}: Goal is too thin or still TODO: {goal!r}")

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "One or more personas have no real Goal recorded. For each one "
        "below, what specifically are they trying to accomplish with this "
        "domain — in concrete terms a colleague would recognise?",
        details=problems,
    )
