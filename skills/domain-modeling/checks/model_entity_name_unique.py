"""Phase 2 hard check: no two entities in domain-model.md share a name.

Error (not warning): a duplicate entity name is a bug, not a judgement
call."""

from __future__ import annotations

import collections
import pathlib

from shared.check_result import CheckResult
from shared.spec_parsers import domain_model_entities

metadata = {
    "id": "MODEL-ENTITY-NAME-UNIQUE",
    "category": "structural",
    "phases": ["modeling"],
    "severity_by_phase": {"modeling": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/domain-model.md"},
    ],
}


def run(repo_root: pathlib.Path) -> CheckResult:
    domain_model = repo_root / "docs/specifications/domain-model.md"
    entities = domain_model_entities(domain_model)
    counts = collections.Counter(entities)
    dupes = [name for name, n in counts.items() if n > 1]

    if not dupes:
        return CheckResult.ok()

    return CheckResult.fail(
        "Some entity names are declared more than once in "
        "domain-model.md. Each entity must have exactly one definition "
        "(merge or rename).",
        details=[f"{name} appears {counts[name]} times" for name in dupes],
    )
