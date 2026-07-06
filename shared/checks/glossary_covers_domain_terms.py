"""Phase 2 hard check: the glossary lexicon covers the domain's named
vocabulary beyond entities — every Domain Events row's event name and
every `## Enumerations` name has a `###` entry somewhere in
glossary.md.

Attribute-level glossary coverage was retired at gate 1.4: attributes
are documented once, in domain-model.md's entity tables
(`GLOSSARY-COVERS-ATTRIBUTES` used to force a duplicate `###` heading
per attribute). The glossary is the ubiquitous-language lexicon, and
events + enumerations are language, so they belong there.

Silent (passes) on domains whose model declares neither a
`## Domain Events` table nor an `## Enumerations` section — both are
opt-in conventions."""

from __future__ import annotations

import pathlib

from shared.check_result import CheckResult
from shared.spec_parsers import (
    domain_model_enums,
    domain_model_events,
    glossary_term_names,
)

metadata = {
    "id": "GLOSSARY-COVERS-DOMAIN-TERMS",
    "category": "cross-reference",
    "phases": ["modeling", "audit"],
    "severity_by_phase": {"modeling": "error", "audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/domain-model.md"},
        {"file_exists": "docs/specifications/glossary.md"},
    ],
}


def run(repo_root: pathlib.Path) -> CheckResult:
    domain_model = repo_root / "docs/specifications/domain-model.md"
    glossary = repo_root / "docs/specifications/glossary.md"

    terms = glossary_term_names(glossary)
    problems: list[str] = []

    for row in domain_model_events(domain_model):
        if row["event"] not in terms:
            problems.append(f"event not in glossary: {row['event']}")

    for enum_name in domain_model_enums(domain_model):
        if enum_name not in terms:
            problems.append(f"enumeration not in glossary: {enum_name}")

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "The domain model names events and enumerations that have no "
        "glossary entry. These are part of the ubiquitous language — "
        "a reader meeting the term in a contract or conversation "
        "should find it in glossary.md. What's the one-sentence "
        "definition of each term below?",
        details=problems,
    )
