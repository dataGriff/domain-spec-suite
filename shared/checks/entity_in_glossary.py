"""Cross-reference check: every entity declared in domain-model.md has a
glossary entry."""

from __future__ import annotations

import pathlib

from shared.check_result import CheckResult
from shared.spec_parsers import domain_model_entities, glossary_entities

metadata = {
    "id": "ENTITY-IN-GLOSSARY",
    "category": "cross-reference",
    "phases": ["modeling", "audit"],
    "severity_by_phase": {"modeling": "error", "audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/domain-model.md"},
        {"file_exists": "docs/specifications/glossary.md"},
    ],
}


def run(repo_root: pathlib.Path) -> CheckResult:
    domain_model = repo_root / "docs" / "specifications" / "domain-model.md"
    glossary = repo_root / "docs" / "specifications" / "glossary.md"

    in_model = domain_model_entities(domain_model)
    in_glossary = set(glossary_entities(glossary))

    missing = [e for e in in_model if e not in in_glossary]
    if not missing:
        return CheckResult.ok()

    return CheckResult.fail(
        "Entities defined in domain-model.md don't appear in glossary.md. "
        "The glossary is the single place readers and downstream code "
        "look up domain language — every entity belongs there. What's the "
        "one- or two-sentence definition of each of these?",
        details=[f"missing from glossary: {name}" for name in missing],
    )
