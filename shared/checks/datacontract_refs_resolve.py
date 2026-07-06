"""Structural check: every `ref`/`$ref` in the data contract resolves.

ODCS data contracts have no `components` section, so an OpenAPI-style
`#/components/schemas/X` pointer inside datacontract.yaml resolves to
nothing in its own document. The suite convention (domain-datacontract
SKILL.md) is that such refs are shorthand for the OpenAPI contract
sitting next to it — `openapi.yaml#/components/schemas/X` — and the
qualified form is preferred. Either way the target must actually
exist in openapi.yaml's `components.schemas`; a ref whose target
exists nowhere is a dangling pointer that silently decays when the
schema is renamed.
"""

from __future__ import annotations

import pathlib

from shared.check_result import CheckResult
from shared.spec_parsers import load_yaml

metadata = {
    "id": "DATACONTRACT-REFS-RESOLVE",
    "category": "structural",
    "phases": ["contracts", "audit"],
    "severity_by_phase": {"contracts": "error", "audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/contracts/datacontract.yaml"},
        {"file_exists": "docs/specifications/contracts/openapi.yaml"},
    ],
}


def _collect_refs(node, path: str, out: list[tuple[str, str]]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in {"ref", "$ref"} and isinstance(value, str):
                out.append((path, value))
            else:
                _collect_refs(value, f"{path}.{key}", out)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            _collect_refs(value, f"{path}[{i}]", out)


def run(repo_root: pathlib.Path) -> CheckResult:
    contracts = repo_root / "docs" / "specifications" / "contracts"
    datacontract = load_yaml(contracts / "datacontract.yaml")
    openapi_schemas = (load_yaml(contracts / "openapi.yaml").get("components") or {}).get(
        "schemas"
    ) or {}

    refs: list[tuple[str, str]] = []
    _collect_refs(datacontract.get("schema"), "schema", refs)

    problems: list[str] = []
    for where, ref in refs:
        if "#/components/schemas/" in ref:
            target = ref.rsplit("/", 1)[-1]
            if target not in openapi_schemas:
                problems.append(
                    f"{where}: `{ref}` — no schema named {target} in "
                    f"openapi.yaml components.schemas"
                )
        else:
            problems.append(
                f"{where}: `{ref}` — unrecognised ref form; use "
                f"`openapi.yaml#/components/schemas/<Name>`"
            )

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "The data contract carries refs that resolve to nothing. Each "
        "ref must point at a real schema in the neighbouring "
        "openapi.yaml (qualified form preferred: "
        "`openapi.yaml#/components/schemas/<Name>`). What should each "
        "of these point at?",
        details=problems,
    )
