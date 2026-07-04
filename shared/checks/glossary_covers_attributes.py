"""Phase 2 hard check: every attribute named in domain-model.md's
entity tables appears in glossary.md.

The audit also runs this — sync issues between model and glossary
should fail at both checkpoints."""

from __future__ import annotations

import pathlib

from shared.check_result import CheckResult
from shared.spec_parsers import domain_model_attributes, glossary_attributes

metadata = {
    "id": "GLOSSARY-COVERS-ATTRIBUTES",
    "category": "structural",
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

    model_attrs = domain_model_attributes(domain_model)
    glossary_attrs = glossary_attributes(glossary)

    problems: list[str] = []
    for entity, attrs in model_attrs.items():
        covered = set(glossary_attrs.get(entity, []))
        missing = [a for a in attrs if a not in covered]
        if missing:
            problems.append(f"{entity}: {', '.join(missing)} not in glossary")

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "Some attributes in domain-model.md aren't documented in "
        "glossary.md. Each attribute the model declares should have a "
        "`### <attribute>` heading under `## <Entity> attributes` in "
        "the glossary. What does each attribute below mean in business "
        "terms? (`task glossary:skeleton` can stub the entries.)",
        details=problems,
    )
