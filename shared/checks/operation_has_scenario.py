"""Cross-reference check: every OpenAPI operation is exercised by at
least one acceptance scenario.

Forward traceability (story → flow) is covered by STORY-HAS-FLOW.
This is the reverse direction: an operation that no scenario touches
is usually a contract-time invention (a CRUD-completion habit, an
onboarding endpoint the PRD forgot) that shipped with no test
surface. An operation counts as covered when any scenario mentions
its `operationId` or a matching `METHOD /path` (path templates match
segment-wise, so concrete ids in scenario prose still count).
"""

from __future__ import annotations

import pathlib

from shared.check_result import CheckResult
from shared.spec_parsers import (
    acceptance_scenario_blocks,
    endpoint_mentions,
    endpoint_path_matches,
    load_yaml,
    openapi_operations,
)

metadata = {
    "id": "OPERATION-HAS-SCENARIO",
    "category": "cross-reference",
    "phases": ["contracts", "audit"],
    "severity_by_phase": {"contracts": "error", "audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/contracts/openapi.yaml"},
        {"file_exists": "docs/specifications/acceptance-scenarios.md"},
    ],
}


def run(repo_root: pathlib.Path) -> CheckResult:
    openapi = load_yaml(repo_root / "docs" / "specifications" / "contracts" / "openapi.yaml")
    scenarios = repo_root / "docs" / "specifications" / "acceptance-scenarios.md"

    blocks = acceptance_scenario_blocks(scenarios)
    all_text = "\n".join(b["text"] for b in blocks)
    mentions = endpoint_mentions(all_text)

    uncovered: list[str] = []
    for op in openapi_operations(openapi):
        op_id = op["operationId"]
        if op_id and op_id in all_text:
            continue
        if any(
            method == op["method"] and endpoint_path_matches(path, op["path"])
            for method, path in mentions
        ):
            continue
        uncovered.append(f"{op['method']} {op['path']} (operationId={op_id or '—'})")

    if not uncovered:
        return CheckResult.ok()

    return CheckResult.fail(
        "These operations exist in openapi.yaml but no acceptance "
        "scenario exercises them. If the operation is real, it needs at "
        "least a happy-path scenario (and a PRD story behind it); if it "
        "was invented during contract authoring, should it exist at "
        "all? What's the covering scenario for each?",
        details=uncovered,
    )
