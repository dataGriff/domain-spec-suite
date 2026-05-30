"""Cross-reference check: every AsyncAPI channel has a corresponding
record in contracts/datacontract.yaml.

The match is by stem — given an AsyncAPI channel like
`items.item.added`, look for a datacontract schema named `items` (the
canonical record) or `items_added` (a per-event variant). The data
contract represents the *historical* payload, so a single record per
entity is the common case.
"""

from __future__ import annotations

import pathlib

from shared.check_result import CheckResult
from shared.spec_parsers import (
    asyncapi_channels,
    datacontract_schema_names,
    load_yaml,
)

metadata = {
    "id": "EVENT-IN-DATACONTRACT",
    "category": "cross-reference",
    "phases": ["contracts", "audit"],
    "severity_by_phase": {"contracts": "error", "audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/contracts/asyncapi.yaml"},
        {"file_exists": "docs/specifications/contracts/datacontract.yaml"},
    ],
}


def _candidates(channel: str) -> list[str]:
    """Possible datacontract record names for a channel.

    Channel `domain.entity.action` → tries (in order):
        domain, entity, action,
        domain_action, entity_action, domain_entity, domain_entity_action.

    A single data contract record per *domain* is the common case
    (e.g. items.item.added / items.item.edited both map to a single
    `items` record carrying the current state). Per-action records
    (e.g. `items_removed` for a reduced payload) are also matched.
    """
    parts = channel.split(".")
    if len(parts) >= 3:
        domain, entity, action = parts[0], parts[1], parts[-1]
        return [
            domain,
            entity,
            action,
            f"{domain}_{action}",
            f"{entity}_{action}",
            f"{domain}_{entity}",
            f"{domain}_{entity}_{action}",
        ]
    if len(parts) == 2:
        return [parts[0], parts[1], "_".join(parts)]
    return [channel]


def run(repo_root: pathlib.Path) -> CheckResult:
    asyncapi = load_yaml(repo_root / "docs" / "specifications" / "contracts" / "asyncapi.yaml")
    datacontract = load_yaml(
        repo_root / "docs" / "specifications" / "contracts" / "datacontract.yaml"
    )

    records = datacontract_schema_names(datacontract)
    problems: list[str] = []

    for channel in asyncapi_channels(asyncapi):
        candidates = _candidates(channel)
        if not any(c in records for c in candidates):
            problems.append(
                f"channel '{channel}' has no datacontract record (tried: {', '.join(candidates)})"
            )

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "AsyncAPI channels have no matching record in datacontract.yaml. "
        "The data contract is the historical schema of every event "
        "payload — downstream pipelines, analytics, and reporting "
        "depend on it. What record name should each channel map to?",
        details=problems,
    )
