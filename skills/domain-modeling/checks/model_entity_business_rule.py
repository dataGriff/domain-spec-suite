"""Phase 2 soft check: every entity in domain-model.md has at least one
business rule listed under `**Business Rules:**` in its block.

Warning, not error: a pure data carrier may genuinely have no business
rules at the model level, but the user should explicitly defer/n-a
rather than leaving the section absent."""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult
from shared.spec_parsers import _section

metadata = {
    "id": "MODEL-ENTITY-BUSINESS-RULE",
    "category": "structural",
    "phases": ["modeling"],
    "severity_by_phase": {"modeling": "warning"},
    "prerequisites": [
        {"file_exists": "docs/specifications/domain-model.md"},
    ],
}

ENTITY_BLOCK_RE = re.compile(
    r"(?m)^###\s+(?P<name>\S[^\n]*)\n(?P<body>.*?)(?=^###\s+|\Z)", re.DOTALL
)
BUSINESS_RULES_HEADER = re.compile(r"\*\*Business Rules:\*\*", re.IGNORECASE)
BULLET_RE = re.compile(r"(?m)^\s*-\s+\S")


def run(repo_root: pathlib.Path) -> CheckResult:
    domain_model = repo_root / "docs/specifications/domain-model.md"
    text = domain_model.read_text(encoding="utf-8")
    entities_section = _section(text, r"^##\s+Entities\s*$")

    problems: list[str] = []
    for match in ENTITY_BLOCK_RE.finditer(entities_section):
        name = match.group("name").strip().split(" — ")[0].split("—")[0].strip()
        body = match.group("body")
        header_match = BUSINESS_RULES_HEADER.search(body)
        if header_match is None:
            problems.append(f"{name}: no '**Business Rules:**' section")
            continue
        # Look for at least one bullet after the header.
        after = body[header_match.end() :]
        bullets = BULLET_RE.search(after)
        if bullets is None:
            problems.append(f"{name}: business rules section is empty")

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "Some entities have no business rules recorded. For each one "
        "below: is there genuinely nothing to record (pure data carrier) "
        "or has a rule been missed? Defer, resolve, or mark n-a.",
        details=problems,
    )
