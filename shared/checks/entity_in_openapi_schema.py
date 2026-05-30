"""Cross-reference check: every entity in domain-model.md has a matching
schema in contracts/openapi.yaml `components.schemas`."""

from __future__ import annotations

import pathlib

from shared.check_result import CheckResult
from shared.spec_parsers import domain_model_entities, load_yaml, openapi_entity_schemas

metadata = {
    "id": "ENTITY-IN-OPENAPI-SCHEMA",
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

    in_model = domain_model_entities(domain_model)
    in_openapi = set(openapi_entity_schemas(openapi).keys())
    # Some entities are deliberately exposed only via a projection
    # (e.g. User → UserSummary, where the bare User shape includes
    # secrets like a password hash that the API must never return).
    # Accept either the bare entity name or a `<Entity>Summary` schema
    # as evidence the entity is represented in the contract.
    all_schemas = set(openapi.get("components", {}).get("schemas", {}).keys())

    missing = [e for e in in_model if e not in in_openapi and f"{e}Summary" not in all_schemas]
    if not missing:
        return CheckResult.ok()

    return CheckResult.fail(
        "Entities defined in domain-model.md don't have a matching "
        "schema in contracts/openapi.yaml. Every domain entity needs an "
        "OpenAPI schema so downstream clients can deserialize it. What "
        "schema definition would each of these need?",
        details=[f"missing OpenAPI schema: {name}" for name in missing],
    )
