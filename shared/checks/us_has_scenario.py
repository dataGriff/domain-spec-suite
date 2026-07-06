"""Cross-reference check: every PRD user story has an acceptance-
scenario section.

`OPERATION-HAS-SCENARIO` guards the contract surface (every openapi
operation is exercised); this guards the requirements surface — a
story with acceptance criteria but no `## US-xxx` section in
acceptance-scenarios.md has no testable definition of done, and the
gap hides until implementation. Warning at the NFRs phase (the
scenarios' owning phase), error at audit."""

from __future__ import annotations

import pathlib

from shared.check_result import CheckResult
from shared.spec_parsers import prd_user_story_ids, scenario_story_sections

metadata = {
    "id": "US-HAS-SCENARIO",
    "category": "cross-reference",
    "phases": ["nfrs", "audit"],
    "severity_by_phase": {"nfrs": "warning", "audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/prd.md"},
        {"file_exists": "docs/specifications/acceptance-scenarios.md"},
    ],
}


def run(repo_root: pathlib.Path) -> CheckResult:
    prd = repo_root / "docs/specifications/prd.md"
    scenarios = repo_root / "docs/specifications/acceptance-scenarios.md"

    covered = set(scenario_story_sections(scenarios))
    missing = [sid for sid in prd_user_story_ids(prd) if sid not in covered]

    if not missing:
        return CheckResult.ok()

    return CheckResult.fail(
        "Some PRD user stories have no acceptance-scenario section — "
        "their acceptance criteria have no testable definition of "
        "done. What are the Given/When/Then scenarios for each story "
        "below? Add a `## US-xxx` section per story to "
        "acceptance-scenarios.md.",
        details=[f"no scenario section for: {sid}" for sid in missing],
    )
