"""Cross-reference check: every OpenAPI POST operation declares a
required `Idempotency-Key` header parameter.

POST is the verb that creates new state from scratch — a retried POST
without an idempotency key produces a duplicate. PUT/PATCH/DELETE are
verb-idempotent (same input → same final state) so the convention is
optional there; this check only enforces it on POST. See SUITE-DESIGN
§4 "Idempotent mutating ops" and the Stripe / IETF
`draft-ietf-httpapi-idempotency-key-header` standard.

A POST operation passes when one of its `parameters` (after `$ref`
resolution against `components.parameters`) has:

- `in: header`
- `name: Idempotency-Key` (case-insensitive match — HTTP header names
  are case-insensitive per RFC 7230)
- `required: true`

The check is silent when openapi.yaml has no `paths` (covered by the
Phase 6 prerequisite that the file exists)."""

from __future__ import annotations

import pathlib

from shared.check_result import CheckResult
from shared.spec_parsers import load_yaml

metadata = {
    "id": "IDEMPOTENCY-KEY-ON-POST-OPS",
    "category": "cross-reference",
    "phases": ["contracts", "audit"],
    "severity_by_phase": {"contracts": "error", "audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/contracts/openapi.yaml"},
    ],
}

HEADER_NAME = "idempotency-key"


def _resolve_parameter(param: dict, components_params: dict) -> dict:
    """If `param` is a single-key `$ref` dict pointing to
    `#/components/parameters/<Name>`, return the referenced parameter
    definition. Otherwise return `param` unchanged."""
    if not isinstance(param, dict):
        return param
    ref = param.get("$ref")
    if not isinstance(ref, str):
        return param
    name = ref.rsplit("/", 1)[-1]
    return components_params.get(name, param)


def _has_required_idempotency_header(parameters: list, components_params: dict) -> bool:
    if not isinstance(parameters, list):
        return False
    for param in parameters:
        resolved = _resolve_parameter(param, components_params)
        if not isinstance(resolved, dict):
            continue
        if resolved.get("in") != "header":
            continue
        name = resolved.get("name", "")
        if not isinstance(name, str) or name.lower() != HEADER_NAME:
            continue
        if resolved.get("required") is True:
            return True
    return False


def run(repo_root: pathlib.Path) -> CheckResult:
    openapi = load_yaml(repo_root / "docs" / "specifications" / "contracts" / "openapi.yaml")
    components_params = (openapi.get("components") or {}).get("parameters") or {}

    problems: list[str] = []
    for path, item in (openapi.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        # Path-level parameters apply to every operation under the path.
        path_level_params = item.get("parameters") or []
        post_op = item.get("post")
        if not isinstance(post_op, dict):
            continue
        op_params = post_op.get("parameters") or []
        combined = list(path_level_params) + list(op_params)
        if not _has_required_idempotency_header(combined, components_params):
            op_id = post_op.get("operationId", "")
            label = f"POST {path}" + (f" (operationId={op_id})" if op_id else "")
            problems.append(f"{label}: missing required `Idempotency-Key` header parameter.")

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "Every POST operation must declare a required `Idempotency-Key` "
        "header parameter so mobile / agentic / chat clients can retry "
        "safely (SUITE-DESIGN §4.6). Add a reusable parameter under "
        "`components.parameters.IdempotencyKey` and `$ref` it from each "
        "operation below — or is one of these POSTs not actually a "
        "create?",
        details=problems,
    )
