"""Phase 3 hard check: every role declared in the auth-matrix Roles
table has a non-empty description."""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult
from shared.spec_parsers import _section

metadata = {
    "id": "AUTH-ROLE-HAS-DESCRIPTION",
    "category": "structural",
    "phases": ["access-control"],
    "severity_by_phase": {"access-control": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/auth-matrix.md"},
    ],
}

ROLE_ROW = re.compile(
    r"^\|\s*`(?P<role>[a-z][a-z0-9_-]*)`\s*\|\s*(?P<desc>[^|]+?)\s*\|",
    re.MULTILINE,
)


def run(repo_root: pathlib.Path) -> CheckResult:
    auth = repo_root / "docs/specifications/auth-matrix.md"
    text = auth.read_text(encoding="utf-8")
    section = _section(text, r"^##\s+Roles\s*$")

    problems: list[str] = []
    for match in ROLE_ROW.finditer(section):
        role = match.group("role")
        desc = match.group("desc").strip()
        if not desc or desc.lower() in {"todo", "tbd", "tbc", "---"}:
            problems.append(f"`{role}`: empty or placeholder description")

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "Some roles in auth-matrix.md have no real description. For "
        "each one below: what does this role actually mean — who is "
        "it for, what can they do, what can't they do?",
        details=problems,
    )
