"""Cross-contract check: named enums in `domain-model.md`'s
`## Enumerations` section have matching values everywhere they're
declared — OpenAPI, AsyncAPI, and the data contract.

The domain model is the authority. For each enum named in the model:

- OpenAPI MUST declare `components.schemas.<Name>` with `enum: [...]`
  whose values match the model (semantics depends on whether the
  enum is closed or open — see below). The model's enum *is* the
  API surface; an unconstrained `string` here is the most common
  drift pattern.
- AsyncAPI and Datacontract MUST match the model IF they declare an
  enum named `<Name>`. Silence is fine (not every enum flows through
  every contract), but a divergent declaration is a bug.

**Closed vs open enums (per the `(open)` heading marker in
domain-model.md):**

- **Closed enum** (default, no marker): strict equality between
  model values and every contract that declares the enum. Adding
  a value is a breaking change.
- **Open enum** (`### Name (open)`): the model lists a curated
  representative subset; the contract carries the full list and
  MAY exceed it. Every model value must appear in the contract;
  the contract may have additional values. Adding to the contract
  is a minor-version bump.

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

    def _compare(
        name: str,
        contract_label: str,
        contract_values: list[str],
        model_values: list[str],
        is_open: bool,
    ) -> str | None:
        if is_open:
            # Model ⊆ contract. Surface model values missing from contract.
            missing = sorted(set(model_values) - set(contract_values))
            if missing:
                return (
                    f"{name} (open): {contract_label} enum is missing model "
                    f"values {missing}. Open enums require model values ⊆ "
                    f"contract values; the contract may have extras."
                )
            return None
        # Closed: strict equality.
        if sorted(contract_values) != sorted(model_values):
            return (
                f"{name}: {contract_label} enum {sorted(contract_values)} "
                f"!= model {sorted(model_values)}"
            )
        return None

    problems: list[str] = []
    for name, meta in model_enums.items():
        expected = list(meta["values"])
        is_open = meta["open"]

        # OpenAPI is required.
        openapi_values = openapi_enums.get(name)
        if openapi_values is None:
            problems.append(
                f"{name}: missing from OpenAPI components.schemas — "
                f"expected enum with {len(expected)} value(s). Add "
                f"`{name}: {{type: string, enum: [...]}}` to openapi.yaml "
                f"and reference it via `$ref: '#/components/schemas/{name}'`."
            )
        else:
            problem = _compare(name, "OpenAPI", openapi_values, expected, is_open)
            if problem:
                problems.append(problem)

        # AsyncAPI: only check if declared.
        asyncapi_values = asyncapi_enums.get(name)
        if asyncapi_values is not None:
            problem = _compare(name, "AsyncAPI", asyncapi_values, expected, is_open)
            if problem:
                problems.append(problem)

        # Datacontract: only check if declared.
        datacontract_values = datacontract_enums.get(name)
        if datacontract_values is not None:
            problem = _compare(name, "Datacontract", datacontract_values, expected, is_open)
            if problem:
                problems.append(problem)

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
