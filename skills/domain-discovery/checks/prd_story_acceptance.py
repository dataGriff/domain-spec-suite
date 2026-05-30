"""Phase 1 structural check: every `#### US-N` user story in prd.md
declares at least one acceptance criterion that isn't a `- [ ] TODO`
placeholder. Also enforces that at least one user story exists at all."""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult
from shared.spec_parsers import prd_user_story_blocks

metadata = {
    "id": "PRD-STORY-ACCEPTANCE",
    "category": "structural",
    "phases": ["discovery"],
    "severity_by_phase": {"discovery": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/prd.md"},
    ],
}

ACCEPTANCE_HEADER_RE = re.compile(r"\*\*Acceptance Criteria:\*\*", re.IGNORECASE)
LIST_ITEM_RE = re.compile(r"(?m)^\s*-\s+(?:\[\s*[xX]?\s*\]\s*)?(?P<text>.+)$")
PLACEHOLDER_TEXT = {"todo", "tbd", "tbc"}


def _real_criteria(block_after_header: str) -> list[str]:
    """Pick up `- something` bullets until the next blank-line gap or
    `####` story heading. Drops empty checklist items (`- [ ] TODO`)."""
    criteria: list[str] = []
    for line in block_after_header.splitlines():
        if line.startswith("#### "):
            break
        if not line.strip():
            if criteria:  # stop at first blank line after first item
                break
            continue
        match = LIST_ITEM_RE.match(line)
        if not match:
            continue
        body = match.group("text").strip()
        if body.lower() in PLACEHOLDER_TEXT or not body:
            continue
        criteria.append(body)
    return criteria


def run(repo_root: pathlib.Path) -> CheckResult:
    prd = repo_root / "docs" / "specifications" / "prd.md"
    blocks = prd_user_story_blocks(prd)

    if not blocks:
        return CheckResult.fail(
            "No user stories declared in the PRD. What's the first thing "
            "a user wants to do with this domain? Capture it as `US-001` "
            "with at least one acceptance criterion."
        )

    problems: list[str] = []
    for block in blocks:
        story_id_match = re.match(r"####\s+(US-\d+)", block)
        story_id = story_id_match.group(1) if story_id_match else "<unknown story>"
        header_match = ACCEPTANCE_HEADER_RE.search(block)
        if header_match is None:
            problems.append(f"{story_id}: no '**Acceptance Criteria:**' block found")
            continue
        criteria = _real_criteria(block[header_match.end() :])
        if not criteria:
            problems.append(f"{story_id}: acceptance criteria block is empty or all-TODO")

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "Some user stories have no real acceptance criteria. For each "
        "story below, what specifically needs to be true for the story "
        "to be 'done'? A criterion should be checkable by a reviewer "
        "without asking the author what they meant.",
        details=problems,
    )
