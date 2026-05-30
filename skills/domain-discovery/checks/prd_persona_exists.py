"""Phase 1 structural check: at least one persona is declared under
`## Target Users / Personas` in prd.md, and the persona name is real
(not a `Persona N: [Name / Role]` template stub)."""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult
from shared.spec_parsers import prd_persona_names

metadata = {
    "id": "PRD-PERSONA-EXISTS",
    "category": "structural",
    "phases": ["discovery"],
    "severity_by_phase": {"discovery": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/prd.md"},
    ],
}

PLACEHOLDER_RE = re.compile(r"\[[A-Za-z][^\]]*\]")


def run(repo_root: pathlib.Path) -> CheckResult:
    prd = repo_root / "docs" / "specifications" / "prd.md"
    names = prd_persona_names(prd)
    real = [n for n in names if not PLACEHOLDER_RE.search(n)]

    if not names:
        return CheckResult.fail(
            "No personas declared in the PRD. Who's the first user of "
            "this domain? Give me a role and a memorable name."
        )

    if not real:
        return CheckResult.fail(
            "The personas are still template placeholders (e.g. "
            "`Persona 1: [Name / Role]`). Replace them with the real "
            "user roles for your domain.",
            details=[f"placeholder persona: {n!r}" for n in names],
        )

    return CheckResult.ok()
