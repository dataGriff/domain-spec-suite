"""Phase 1 structural check: at least one non-goal is declared under
`## Non-Goals` in prd.md, and it isn't a placeholder TODO."""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult
from shared.spec_parsers import _section

metadata = {
    "id": "PRD-NON-GOAL",
    "category": "structural",
    "phases": ["discovery"],
    "severity_by_phase": {"discovery": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/prd.md"},
    ],
}

LIST_ITEM_RE = re.compile(r"(?m)^\s*(?:\d+\.|[-*])\s+(?P<text>.+)$")
PLACEHOLDER_TEXT = {"todo", "tbd", "tbc"}


def run(repo_root: pathlib.Path) -> CheckResult:
    prd = repo_root / "docs" / "specifications" / "prd.md"
    text = prd.read_text(encoding="utf-8")
    section = _section(text, r"^##\s+Non-Goals\s*$")
    section = re.sub(r"<!--.*?-->", "", section, flags=re.DOTALL)

    items: list[str] = []
    for match in LIST_ITEM_RE.finditer(section):
        body = match.group("text").strip()
        if body.lower() in PLACEHOLDER_TEXT:
            continue
        items.append(body)

    if not items:
        return CheckResult.fail(
            "No real non-goals listed. What's explicitly out of scope for "
            "this domain? Naming the things you're deliberately NOT "
            "building protects later phases from scope creep.",
        )

    return CheckResult.ok()
