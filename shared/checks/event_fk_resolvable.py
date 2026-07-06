"""Cross-reference check: every entity-referencing FK in the data
contract resolves to a record in the same historic record.

The data contract's promise (SUITE-DESIGN §4.5) is that consumers can
reconstruct what happened from the event stream alone. A field like
`walkerId` on four records is worthless to a consumer if no record in
the contract ever publishes the Walker itself — the id can never be
resolved to a name without re-querying the live API, which is exactly
the coupling the contract exists to remove.

Rule: for every datacontract record field named `<entity>Id`, where
`<entity>` case-insensitively matches an entity in domain-model.md,
some datacontract record must exist for that entity (name match,
singular or plural). Fields that don't match a modelled entity name
(`contributorId` when the entity is `User`) are out of scope — the
naming link is the mechanical signal.
"""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult
from shared.spec_parsers import (
    datacontract_record_fields,
    domain_model_entities,
    load_yaml,
)

metadata = {
    "id": "EVENT-FK-RESOLVABLE",
    "category": "cross-reference",
    "phases": ["contracts", "audit"],
    "severity_by_phase": {"contracts": "error", "audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/contracts/datacontract.yaml"},
        {"file_exists": "docs/specifications/domain-model.md"},
    ],
}


def _record_covers_entity(record_name: str, entity: str) -> bool:
    rec = record_name.lower().replace("_", "").replace("-", "")
    ent = entity.lower().replace(" ", "")
    return rec in {ent, ent + "s", ent + "es"} or rec.startswith(ent)


def run(repo_root: pathlib.Path) -> CheckResult:
    specs = repo_root / "docs" / "specifications"
    datacontract = load_yaml(specs / "contracts" / "datacontract.yaml")
    entities = domain_model_entities(specs / "domain-model.md")

    records = datacontract_record_fields(datacontract)
    entity_by_lower = {e.lower(): e for e in entities}

    problems: list[str] = []
    seen: set[str] = set()
    for fields in records.values():
        for field_name in fields:
            match = re.fullmatch(r"([A-Za-z]+)Id", field_name)
            if match is None:
                continue
            entity = entity_by_lower.get(match.group(1).lower())
            if entity is None:
                continue
            if any(_record_covers_entity(r, entity) for r in records):
                continue
            key = f"{entity}:{field_name}"
            if key in seen:
                continue
            seen.add(key)
            referencing = sorted(r for r, fs in records.items() if field_name in fs)
            problems.append(
                f"`{field_name}` (on {', '.join(referencing)}) references "
                f"entity {entity}, but no datacontract record publishes "
                f"{entity} — the id is unresolvable from the event stream"
            )

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "The data contract carries foreign keys to entities it never "
        "publishes. Downstream consumers can't resolve these ids "
        "without re-querying the live API, which breaks the historic "
        "record's reconstruct-from-events promise. Which event should "
        "publish each of these entities (creation is the usual "
        "answer), or why is the entity legitimately API-only?",
        details=problems,
    )
