"""Phase 2 soft check: every entity in domain-model.md declares the
three baseline attributes `id`, `createdAt`, `updatedAt`.

Warning, not error: some entities legitimately omit one (value objects
without identity, immutable records with no `updatedAt`). The modeling
phase surfaces these as warnings so the user must explicitly defer or
mark n-a per the soft-gate engagement loop.
"""

from __future__ import annotations

import pathlib

from shared.check_result import CheckResult
from shared.spec_parsers import domain_model_attributes, domain_model_entities

metadata = {
    "id": "MODEL-ENTITY-HAS-ID-TIMESTAMPS",
    "category": "structural",
    "phases": ["modeling"],
    "severity_by_phase": {"modeling": "warning"},
    "prerequisites": [
        {"file_exists": "docs/specifications/domain-model.md"},
    ],
}

REQUIRED = ("id", "createdAt", "updatedAt")


def run(repo_root: pathlib.Path) -> CheckResult:
    domain_model = repo_root / "docs/specifications/domain-model.md"
    attrs = domain_model_attributes(domain_model)
    entities = domain_model_entities(domain_model)

    problems: list[str] = []
    for entity in entities:
        entity_attrs = set(attrs.get(entity, []))
        missing = [req for req in REQUIRED if req not in entity_attrs]
        if missing:
            problems.append(f"{entity}: missing {', '.join(missing)}")

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "Some entities don't declare the baseline timestamps and id. "
        "For each one below, is this entity genuinely identity-less or "
        "immutable, or should it gain the standard fields? Resolve, "
        "defer, or mark n-a (with a reason for the latter two).",
        details=problems,
    )
