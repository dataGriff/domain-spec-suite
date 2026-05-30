"""Cross-reference check: attribute names match between domain-model.md
and the corresponding OpenAPI entity schemas.

For each entity that appears in both, ensures every attribute listed in
the domain model exists as a property in the OpenAPI schema. The
reverse direction is intentionally not checked — OpenAPI schemas may
legitimately carry presentation-layer fields (e.g. denormalised
display names) that aren't first-class domain attributes.
"""

from __future__ import annotations

import pathlib

from shared.check_result import CheckResult
from shared.spec_parsers import (
    domain_model_attributes,
    load_yaml,
    openapi_entity_schemas,
)

metadata = {
    "id": "FIELD-MATCH-DOMAIN-OPENAPI",
    "category": "cross-reference",
    "phases": ["contracts", "audit"],
    "severity_by_phase": {"contracts": "error", "audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/domain-model.md"},
        {"file_exists": "docs/specifications/contracts/openapi.yaml"},
    ],
}


def run(repo_root: pathlib.Path) -> CheckResult:
    domain_model = repo_root / "docs" / "specifications" / "domain-model.md"
    openapi = load_yaml(repo_root / "docs" / "specifications" / "contracts" / "openapi.yaml")

    attrs_by_entity = domain_model_attributes(domain_model)
    openapi_schemas = openapi_entity_schemas(openapi)

    problems: list[str] = []
    for entity, expected_attrs in attrs_by_entity.items():
        schema = openapi_schemas.get(entity)
        if schema is None:
            # That's ENTITY-IN-OPENAPI-SCHEMA's job to surface.
            continue
        actual_props = set(schema.get("properties", {}).keys())
        missing = [a for a in expected_attrs if a not in actual_props]
        for a in missing:
            problems.append(f"{entity}.{a} (in domain-model, missing from OpenAPI)")

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "Domain-model attributes are missing from their OpenAPI schemas. "
        "Field names must match exactly so client code generators and "
        "spec-driven tests agree on what each entity carries. For each "
        "row below, either add the property to the OpenAPI schema (with "
        "the same name) or remove it from the domain model.",
        details=problems,
    )
