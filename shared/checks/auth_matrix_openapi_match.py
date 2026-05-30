"""Cross-reference check: every operation in auth-matrix.md has a
matching path+method in contracts/openapi.yaml.

Operation endpoints in the auth matrix are parsed from the "Endpoint"
column (e.g. `POST /v1/auth/register`, `GET /v1/items`). The match is
exact: the same method on the same path must exist in OpenAPI.
"""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult
from shared.spec_parsers import auth_matrix_operations, load_yaml

metadata = {
    "id": "AUTH-MATRIX-OPENAPI-MATCH",
    "category": "cross-reference",
    "phases": ["access-control", "contracts", "audit"],
    "severity_by_phase": {
        "access-control": "warning",
        "contracts": "error",
        "audit": "error",
    },
    "prerequisites": [
        {"file_exists": "docs/specifications/auth-matrix.md"},
        {"file_exists": "docs/specifications/contracts/openapi.yaml"},
    ],
}

ENDPOINT = re.compile(r"^(?P<method>[A-Z]+)\s+(?P<path>/\S+)$")


def run(repo_root: pathlib.Path) -> CheckResult:
    auth_matrix = repo_root / "docs" / "specifications" / "auth-matrix.md"
    openapi = load_yaml(repo_root / "docs" / "specifications" / "contracts" / "openapi.yaml")

    openapi_ops: set[tuple[str, str]] = set()
    for path, item in openapi.get("paths", {}).items():
        for method in item:
            if method.lower() in {"get", "post", "patch", "put", "delete", "options", "head"}:
                openapi_ops.add((method.upper(), path))

    problems: list[str] = []
    for entry in auth_matrix_operations(auth_matrix):
        match = ENDPOINT.match(entry["endpoint"])
        if match is None:
            problems.append(
                f"auth-matrix row '{entry['operation']}' has unparseable "
                f"endpoint '{entry['endpoint']}'"
            )
            continue
        method = match.group("method")
        path = match.group("path")
        if (method, path) not in openapi_ops:
            problems.append(
                f"auth-matrix names '{method} {path}' but openapi.yaml has no such operation"
            )

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "auth-matrix.md references operations that openapi.yaml doesn't "
        "expose. The auth matrix is the source of truth for who may do "
        "what — every operation it names must exist in the REST "
        "contract. Either add the operation to openapi.yaml or remove "
        "the auth-matrix row.",
        details=problems,
    )
