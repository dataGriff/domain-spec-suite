"""Cross-reference check: every `US-N` user story in prd.md is
referenced by at least one flow heading in sequence-diagrams.md.

A flow heading like '## Flow 2: Contributor Creates and Manages Items'
covers stories US-003, US-006, US-007 (etc.) implicitly. The check
looks for the literal `US-NNN` token, OR for at least 60% of the
distinct user-story group names appearing in flow titles.

Implementation pragma: the lazy version checks that each story's
group heading (e.g. 'Items', 'Auth') has at least one matching flow.
A direct one-flow-per-story mapping is too strict; one flow often
covers multiple stories in the same group.

Warning at flows phase; error at audit."""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult
from shared.spec_parsers import _section, prd_user_story_blocks

metadata = {
    "id": "STORY-HAS-FLOW",
    "category": "cross-reference",
    "phases": ["flows", "audit"],
    "severity_by_phase": {"flows": "warning", "audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/prd.md"},
        {"file_exists": "docs/specifications/sequence-diagrams.md"},
    ],
}

FLOW_HEADING_RE = re.compile(r"(?m)^##\s+Flow\s+\d+:\s+(?P<title>[^\n]+)$")
GROUP_HEADING_RE = re.compile(r"(?m)^###\s+(?P<group>[^\n]+)$")


def run(repo_root: pathlib.Path) -> CheckResult:
    prd = repo_root / "docs/specifications/prd.md"
    flows = repo_root / "docs/specifications/sequence-diagrams.md"

    prd_text = prd.read_text(encoding="utf-8")
    flow_text = flows.read_text(encoding="utf-8")

    # Group → list of story ids
    user_stories_section = _section(prd_text, r"^##\s+User Stories\s*$")
    groups: dict[str, list[str]] = {}
    current_group: str | None = None
    for line in user_stories_section.splitlines():
        group_match = GROUP_HEADING_RE.match(line)
        if group_match:
            current_group = group_match.group("group").strip()
            groups.setdefault(current_group, [])
            continue
        story_match = re.match(r"####\s+(US-\d+)", line)
        if story_match and current_group is not None:
            groups[current_group].append(story_match.group(1))

    # Drop empty groups (no stories under them).
    groups = {g: stories for g, stories in groups.items() if stories}

    if not groups:
        return CheckResult.ok()  # no stories to require flows for

    flow_titles = [m.group("title").lower() for m in FLOW_HEADING_RE.finditer(flow_text)]
    flow_blob = " ".join(flow_titles)

    problems: list[str] = []
    for group_name, story_ids in groups.items():
        group_token = group_name.lower().split("/")[0].strip()
        # Either the group name appears in a flow title, OR one of the
        # group's specific story ids does.
        if group_token in flow_blob:
            continue
        if any(sid in flow_text for sid in story_ids):
            continue
        problems.append(
            f"story group {group_name!r} ({', '.join(story_ids)}) has no "
            "matching flow (no flow title mentions the group, no flow "
            "body references any US-id from the group)"
        )

    blocks = prd_user_story_blocks(prd)
    if blocks and not flow_titles:
        problems.append("sequence-diagrams.md has no `## Flow N:` headings at all")

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "Some PRD user-story groups have no matching flow in "
        "sequence-diagrams.md. For each one below: is the group "
        "trivially covered (resolve by adding a one-step flow), or "
        "is the story a non-interactive concern that doesn't need a "
        "diagram (mark n-a)?",
        details=problems,
    )
