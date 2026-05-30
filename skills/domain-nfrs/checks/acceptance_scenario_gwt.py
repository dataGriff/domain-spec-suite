"""Phase 5 hard check: every Scenario block in acceptance-scenarios.md
follows Given/When/Then structure inside a ```gherkin fenced block.

Hard error: ad-hoc prose scenarios can't be lifted into contract-level
test suites; the GWT discipline is what makes the file machine-
consumable downstream."""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult

metadata = {
    "id": "ACCEPTANCE-SCENARIO-GWT",
    "category": "structural",
    "phases": ["nfrs"],
    "severity_by_phase": {"nfrs": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/acceptance-scenarios.md"},
    ],
}

SCENARIO_BLOCK_RE = re.compile(
    r"(?m)^###\s+Scenario\s+(?P<id>\S+)[^\n]*\n(?P<body>.*?)(?=^###\s+Scenario|\Z)",
    re.DOTALL,
)
GHERKIN_FENCE = re.compile(r"```gherkin\n(?P<inner>.*?)```", re.DOTALL)


def run(repo_root: pathlib.Path) -> CheckResult:
    path = repo_root / "docs/specifications/acceptance-scenarios.md"
    text = path.read_text(encoding="utf-8")

    problems: list[str] = []
    found = 0
    for match in SCENARIO_BLOCK_RE.finditer(text):
        found += 1
        sid = match.group("id")
        body = match.group("body")
        fence = GHERKIN_FENCE.search(body)
        if fence is None:
            problems.append(f"{sid}: no ```gherkin fenced block found")
            continue
        inner = fence.group("inner")
        # When + Then are required (every scenario triggers something
        # and asserts something). Given is recommended but stateless
        # scenarios — invalid-input rejections, no-auth checks —
        # legitimately have implicit preconditions.
        has_when = re.search(r"(?m)^\s*When\b", inner)
        has_then = re.search(r"(?m)^\s*Then\b", inner)
        missing = [kw for kw, present in (("When", has_when), ("Then", has_then)) if not present]
        if missing:
            problems.append(f"{sid}: missing {', '.join(missing)} step(s)")

    if found == 0:
        return CheckResult.fail(
            "acceptance-scenarios.md has no `### Scenario` blocks. "
            "Every PRD user story needs at least one scenario."
        )

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "Some scenarios don't follow Given/When/Then structure. For "
        "each one below: rewrite the scenario as a ```gherkin block "
        "with Given (precondition), When (the request), Then (the "
        "observable outcome).",
        details=problems,
    )
