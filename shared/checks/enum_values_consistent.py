"""Cross-contract check: named enums in `domain-model.md`'s
`## Enumerations` section have matching values everywhere they're
declared — OpenAPI, AsyncAPI, and the data contract.

The domain model is the authority. For each enum named in the model:

- OpenAPI MUST declare `components.schemas.<Name>` with `enum: [...]`
  whose values exactly match the model. The model's enum *is* the
  API surface; an unconstrained `string` here is the most common
  drift pattern.
- AsyncAPI and Datacontract MUST match the model IF they declare an
  enum named `<Name>`. Silence is fine (not every enum flows through
  every contract), but a divergent declaration is a bug.

Designed as a single check rather than three because the common
failure mode is "someone added a value in one contract and forgot
the other two" — one check surfaces all divergences in a single
failure rather than scattering them across three.
"""

from __future__ import annotations

import pathlib

from shared.check_result import CheckResult
from shared.spec_parsers import (
    contract_named_enums,
    datacontract_named_enums,
    domain_model_enums,
    load_yaml,
)

metadata = {
    "id": "ENUM-VALUES-CONSISTENT",
    "category": "cross-reference",
    "phases": ["contracts", "audit"],
    "severity_by_phase": {"contracts": "error", "audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/domain-model.md"},
        {"file_exists": "docs/specifications/contracts/openapi.yaml"},
    ],
}


def run(repo_root: pathlib.Path) -> CheckResult:
    specs = repo_root / "docs" / "specifications"
    model_enums = domain_model_enums(specs / "domain-model.md")
    if not model_enums:
        # No named enums declared — convention is opt-in. Nothing to check.
        return CheckResult.ok()

    openapi_enums = contract_named_enums(load_yaml(specs / "contracts" / "openapi.yaml"))

    asyncapi_path = specs / "contracts" / "asyncapi.yaml"
    asyncapi_enums = (
        contract_named_enums(load_yaml(asyncapi_path)) if asyncapi_path.is_file() else {}
    )

    datacontract_path = specs / "contracts" / "datacontract.yaml"
    datacontract_enums = (
        datacontract_named_enums(load_yaml(datacontract_path))
        if datacontract_path.is_file()
        else {}
    )

    problems: list[str] = []
    for name, model_values in model_enums.items():
        expected = list(model_values)

        # OpenAPI is required.
        openapi_values = openapi_enums.get(name)
        if openapi_values is None:
            problems.append(
                f"{name}: missing from OpenAPI components.schemas — "
                f"expected enum {expected}. Add `{name}: {{type: string, "
                f"enum: {expected}}}` to openapi.yaml and reference it "
                f"with `$ref: '#/components/schemas/{name}'` where used."
            )
        elif sorted(openapi_values) != sorted(expected):
            problems.append(
                f"{name}: OpenAPI enum {sorted(openapi_values)} != model {sorted(expected)}"
            )

        # AsyncAPI: only check if declared.
        asyncapi_values = asyncapi_enums.get(name)
        if asyncapi_values is not None and sorted(asyncapi_values) != sorted(expected):
            problems.append(
                f"{name}: AsyncAPI enum {sorted(asyncapi_values)} != model {sorted(expected)}"
            )

        # Datacontract: only check if declared.
        datacontract_values = datacontract_enums.get(name)
        if datacontract_values is not None and sorted(datacontract_values) != sorted(expected):
            problems.append(
                f"{name}: Datacontract enum {sorted(datacontract_values)} "
                f"!= model {sorted(expected)}"
            )

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "Named enums in domain-model.md's `## Enumerations` section "
        "must declare the same values everywhere they're materialized. "
        "When the values drift, an event publisher could emit a value "
        "the API would reject — or vice versa. The model is the "
        "authority; update whichever contract diverged.",
        details=problems,
    )
