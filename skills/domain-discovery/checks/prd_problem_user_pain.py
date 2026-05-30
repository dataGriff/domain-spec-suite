"""Phase 1 structural check: `prd.md` has a non-empty Problem Statement
section that isn't the template placeholder.

The "user pain" angle (whether the prose leads with pain or with
solution) is the rubric in SKILL.md prose — this check just enforces
that *something substantive* is there to evaluate.
"""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult
from shared.spec_parsers import _section

metadata = {
    "id": "PRD-PROBLEM-USER-PAIN",
    "category": "structural",
    "phases": ["discovery"],
    "severity_by_phase": {"discovery": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/prd.md"},
    ],
}

PLACEHOLDER_RE = re.compile(r"TODO|\[\s*[A-Za-z][^\]]*\]")


def run(repo_root: pathlib.Path) -> CheckResult:
    prd = repo_root / "docs" / "specifications" / "prd.md"
    text = prd.read_text(encoding="utf-8")
    section = _section(text, r"^##\s+Problem Statement\s*$").strip()
    # Strip HTML comments — the template carries instructional comments.
    body = re.sub(r"<!--.*?-->", "", section, flags=re.DOTALL).strip()

    if not body:
        return CheckResult.fail(
            "The PRD has no Problem Statement content. Walk me through "
            "the problem your domain solves: who has it, what specifically "
            "goes wrong for them today, and why is that worth fixing?",
        )

    if PLACEHOLDER_RE.search(body) and len(body) < 200:
        return CheckResult.fail(
            "The Problem Statement still looks like the template "
            "placeholder. What's the real problem your domain solves? "
            "Lead with the user pain, not the feature.",
            details=[f"current text (first 120 chars): {body[:120]!r}"],
        )

    if len(body) < 80:
        return CheckResult.fail(
            "The Problem Statement is too thin to evaluate. Give me at "
            "least a couple of sentences: who has the problem, what "
            "specifically goes wrong today, what would change if it were "
            "solved.",
            details=[f"current length: {len(body)} chars"],
        )

    return CheckResult.ok()
