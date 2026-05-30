"""Phase 2 soft check: every entity in domain-model.md that has a
`status` attribute must declare a lifecycle table somewhere in the
file (under `## Status Lifecycle` typically, with `### <Entity> Status`
sub-headings).

Warning: an entity might have a status field that's really just a flag
(no transitions, no state machine), in which case the user marks n-a.
"""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult
from shared.spec_parsers import _section, domain_model_attributes

metadata = {
    "id": "MODEL-LIFECYCLE-DEFINED",
    "category": "structural",
    "phases": ["modeling"],
    "severity_by_phase": {"modeling": "warning"},
    "prerequisites": [
        {"file_exists": "docs/specifications/domain-model.md"},
    ],
}


def run(repo_root: pathlib.Path) -> CheckResult:
    domain_model = repo_root / "docs/specifications/domain-model.md"
    text = domain_model.read_text(encoding="utf-8")
    attrs = domain_model_attributes(domain_model)

    lifecycle_section = _section(text, r"^##\s+Status Lifecycle\s*$")
    lifecycle_entities = {
        match.group(1).strip()
        for match in re.finditer(r"(?m)^###\s+(\S[^\n]*?)\s+Status\s*$", lifecycle_section)
    }

    problems: list[str] = []
    for entity, entity_attrs in attrs.items():
        if "status" not in entity_attrs:
            continue
        if entity not in lifecycle_entities:
            problems.append(
                f"{entity}: has a `status` attribute but no `### {entity} Status` lifecycle table"
            )

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "Some entities have a `status` attribute with no documented "
        "state lifecycle. For each one below: is `status` a real state "
        "machine (define the transitions) or just a flag (mark n-a)?",
        details=problems,
    )
