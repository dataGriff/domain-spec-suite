"""Phase 2 soft check: relationships in the `## Relationships` section
are stated in both directions (if `A creates many B` appears, then
`B belongs to A` should appear too).

Warning: genuinely-unidirectional relationships exist (e.g. a side
that's a system actor, or a one-way audit log reference). The user
marks n-a in those cases.

Implementation: the convention in domain-model.md's relationships
block uses ASCII-art style:

    A ──── creates many ──── B
    B ──── belongs to ────── A

The check looks for `A ... B` and verifies a `B ... A` line is also
present anywhere in the section."""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult
from shared.spec_parsers import _section

metadata = {
    "id": "MODEL-RELATIONSHIP-BIDIRECTIONAL",
    "category": "structural",
    "phases": ["modeling"],
    "severity_by_phase": {"modeling": "warning"},
    "prerequisites": [
        {"file_exists": "docs/specifications/domain-model.md"},
    ],
}

# Match "Word ... Word" lines with the ASCII-art relationship style.
# Captures the two anchor words (entity names, plausibly with a
# parenthesised qualifier).
LINE_RE = re.compile(
    r"^(?P<lhs>[A-Z][A-Za-z]+)\s*(?:\([^)]*\))?\s*[─-]{2,}.*?"
    r"[─-]{2,}\s*(?P<rhs>[A-Z][A-Za-z]+)",
    re.MULTILINE,
)


def run(repo_root: pathlib.Path) -> CheckResult:
    domain_model = repo_root / "docs/specifications/domain-model.md"
    text = domain_model.read_text(encoding="utf-8")
    section = _section(text, r"^##\s+Relationships\s*$")

    pairs: set[tuple[str, str]] = set()
    for match in LINE_RE.finditer(section):
        lhs = match.group("lhs")
        rhs = match.group("rhs")
        if lhs == rhs:
            continue
        pairs.add((lhs, rhs))

    problems: list[str] = []
    for lhs, rhs in pairs:
        if (rhs, lhs) not in pairs:
            problems.append(f"{lhs} → {rhs} has no matching {rhs} → {lhs} line")

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "Some relationships are only stated in one direction. For each "
        "one below: is the reverse genuinely absent (a one-way "
        "reference, mark n-a) or just missing (resolve by adding it)?",
        details=problems,
    )
