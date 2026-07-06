"""Cross-reference check: acceptance-scenario literals are legal
against the contracts they claim to test.

Scenarios are executable intent — a scenario that references an
endpoint that doesn't exist, asserts an error code the catalogue
never defined, or sends an enum value the schema rejects will fail
in every implementation while reading as if the implementation is
wrong. Three sub-rules:

1. Every `METHOD /path` mention resolves to an OpenAPI operation.
2. Every error code asserted on a `code`-mentioning line is defined
   in the error catalogue.
3. In scenarios that assert a 2xx response, every literal paired
   with an enum-typed property name — quoted prose or a gherkin
   data-table row (`| breed | Border Collie |`) — must be a legal
   member (fails when the enum value is `border-collie`). Non-2xx
   scenarios are exempt — sending an illegal value on purpose is
   how rejection is tested.
4. Every quoted dotted event type on an event-assertion line
   (`event with type "dogwalking.dog.added"`) is a declared
   AsyncAPI channel.
"""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult
from shared.spec_parsers import (
    acceptance_scenario_blocks,
    asyncapi_channels,
    endpoint_mentions,
    endpoint_path_matches,
    error_catalogue_codes,
    load_yaml,
    openapi_enum_properties,
    openapi_operations,
)

metadata = {
    "id": "SCENARIO-REFS-VALID",
    "category": "cross-reference",
    "phases": ["contracts", "audit"],
    "severity_by_phase": {"contracts": "error", "audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/acceptance-scenarios.md"},
        {"file_exists": "docs/specifications/contracts/openapi.yaml"},
        {"file_exists": "docs/specifications/error-catalogue.md"},
    ],
}

CODE_ASSERTION = re.compile(r"(?im)^.*\bcode\b[^\"`\n]*[\"`]([A-Z][A-Z0-9_]{2,})[\"`]")
SUCCESS_STATUS = re.compile(r"\bstatus\s+is\s+(2\d\d)\b")
TABLE_ROW = re.compile(r"(?m)^\s*\|\s*(\w+)\s*\|\s*([^|\n]+?)\s*\|\s*$")
EVENT_TYPE = re.compile(r"(?im)^.*\bevent\b[^\"\n]*\"([a-z0-9_-]+(?:\.[a-z0-9_-]+)+)\"")


def run(repo_root: pathlib.Path) -> CheckResult:
    specs = repo_root / "docs" / "specifications"
    openapi = load_yaml(specs / "contracts" / "openapi.yaml")
    catalogue_codes = error_catalogue_codes(specs / "error-catalogue.md")
    operations = openapi_operations(openapi)
    enum_props = openapi_enum_properties(openapi)
    asyncapi_path = specs / "contracts" / "asyncapi.yaml"
    channels = set(asyncapi_channels(load_yaml(asyncapi_path))) if asyncapi_path.exists() else None

    problems: list[str] = []
    for block in acceptance_scenario_blocks(specs / "acceptance-scenarios.md"):
        heading, text = block["heading"], block["text"]

        for method, path in endpoint_mentions(text):
            if not any(
                op["method"] == method and endpoint_path_matches(path, op["path"])
                for op in operations
            ):
                problems.append(f"{heading}: {method} {path} is not in openapi.yaml")

        for match in CODE_ASSERTION.finditer(text):
            code = match.group(1)
            if code not in catalogue_codes:
                problems.append(
                    f"{heading}: asserts error code {code}, which the "
                    f"error catalogue doesn't define"
                )

        if SUCCESS_STATUS.search(text):
            literals: list[tuple[str, str]] = [
                (prop, literal)
                for prop, values in enum_props.items()
                for literal in re.findall(rf"\b{re.escape(prop)}\b[^\"\n]*\"([^\"]+)\"", text)
            ]
            literals += [
                (field, value) for field, value in TABLE_ROW.findall(text) if field in enum_props
            ]
            for prop, literal in literals:
                values = enum_props[prop]
                if literal not in values:
                    problems.append(
                        f'{heading}: sends {prop} "{literal}" in a '
                        f"success scenario, but the contract enum "
                        f"only admits: {sorted(values)[:8]}"
                        f"{' …' if len(values) > 8 else ''}"
                    )

        if channels is not None:
            for event_type in EVENT_TYPE.findall(text):
                if event_type not in channels:
                    problems.append(
                        f'{heading}: asserts event type "{event_type}", '
                        f"which is not a declared AsyncAPI channel"
                    )

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "Some acceptance scenarios reference endpoints, error codes, or "
        "enum values the contracts don't recognise — as written they "
        "would fail against a fully compliant implementation. For each, "
        "is the scenario wrong or is the contract missing something?",
        details=problems,
    )
