"""Cross-reference check: every OpenAPI write operation has at least
one AsyncAPI channel.

A "write operation" is any POST/PATCH/PUT/DELETE on a non-auth path.
The match heuristic looks for a channel whose name carries the
operation's "lifecycle verb" (e.g. POST → 'added' or 'created';
PATCH → 'edited' or 'updated'; DELETE → 'removed' or 'deleted'). This
is a soft check — domains that publish events under non-conventional
channel names should rename the channels rather than disable the check.
"""

from __future__ import annotations

import pathlib

from shared.check_result import CheckResult
from shared.spec_parsers import (
    asyncapi_channels,
    load_yaml,
    openapi_write_operations,
)

metadata = {
    "id": "WRITE-OP-HAS-ASYNCAPI-CHANNEL",
    "category": "cross-reference",
    "phases": ["contracts", "audit"],
    "severity_by_phase": {"contracts": "error", "audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/contracts/openapi.yaml"},
        {"file_exists": "docs/specifications/contracts/asyncapi.yaml"},
    ],
}

# Map HTTP method → list of lifecycle verbs that conventionally appear
# in the channel name for that method.
METHOD_VERBS = {
    "POST": ["added", "created"],
    "PATCH": ["edited", "updated"],
    "PUT": ["edited", "updated", "replaced"],
    "DELETE": ["removed", "deleted"],
}

# Paths whose write operations don't produce domain events (auth flows,
# session management — already covered by their own semantics).
AUTH_PATH_PREFIXES = ("/v1/auth/", "/auth/")


def run(repo_root: pathlib.Path) -> CheckResult:
    openapi = load_yaml(repo_root / "docs" / "specifications" / "contracts" / "openapi.yaml")
    asyncapi = load_yaml(repo_root / "docs" / "specifications" / "contracts" / "asyncapi.yaml")

    channels = asyncapi_channels(asyncapi)
    problems: list[str] = []

    for op in openapi_write_operations(openapi):
        if any(op["path"].startswith(p) for p in AUTH_PATH_PREFIXES):
            continue
        verbs = METHOD_VERBS.get(op["method"], [])
        if not any(any(v in channel for v in verbs) for channel in channels):
            problems.append(
                f"{op['method']} {op['path']} (operationId={op['operationId']}) "
                f"— no AsyncAPI channel containing any of {verbs}"
            )

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "Some write operations in openapi.yaml have no corresponding "
        "AsyncAPI channel. Every state-changing operation should emit a "
        "domain event so downstream consumers can react. What event "
        "channel covers each of these?",
        details=problems,
    )
