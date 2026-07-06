"""Cross-reference check: every error code the catalogue defines is
actually returnable by the OpenAPI contract.

The existing ERROR-CODE-IN-CATALOGUE check runs contract→catalogue
(no undefined codes). This check runs the opposite direction,
catalogue→contract, in two tiers:

1. Status tier — the code's documented HTTP status must be declared
   by at least one operation. Catches a catalogue (or NFR-mandated)
   status like 429 that no operation can return.
2. Enum tier — when the contract's response schemas enumerate `code`
   values at all, every catalogue code must appear in at least one
   `code` enum bound at its documented status. Catches the
   "unreturnable code" class: the code exists in some schema enum,
   but every response declared at its status refs a schema whose
   enum forbids it.

Contracts that model `code` as a plain string skip tier 2 — there is
nothing mechanical to hold them to.
"""

from __future__ import annotations

import pathlib

from shared.check_result import CheckResult
from shared.spec_parsers import (
    error_catalogue_code_statuses,
    load_yaml,
    openapi_error_code_bindings,
)

metadata = {
    "id": "ERROR-CODE-REPRESENTABLE",
    "category": "cross-reference",
    "phases": ["contracts", "audit"],
    "severity_by_phase": {"contracts": "error", "audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/error-catalogue.md"},
        {"file_exists": "docs/specifications/contracts/openapi.yaml"},
    ],
}


def run(repo_root: pathlib.Path) -> CheckResult:
    catalogue = repo_root / "docs" / "specifications" / "error-catalogue.md"
    openapi = load_yaml(repo_root / "docs" / "specifications" / "contracts" / "openapi.yaml")

    code_statuses = error_catalogue_code_statuses(catalogue)
    declared_statuses, enums_by_status = openapi_error_code_bindings(openapi)
    contract_enumerates_codes = bool(enums_by_status)

    problems: list[str] = []
    for code, status in sorted(code_statuses.items()):
        if status not in declared_statuses:
            problems.append(
                f"{code} is documented as {status}, but no operation declares a {status} response"
            )
            continue
        if contract_enumerates_codes and code not in enums_by_status.get(status, set()):
            problems.append(
                f"{code} is documented as {status}, but every response "
                f"schema bound at {status} forbids it (code enum admits: "
                f"{sorted(enums_by_status.get(status, set())) or 'nothing'})"
            )

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "The error catalogue defines codes a compliant server could "
        "never return — the contract either doesn't declare the "
        "documented status, or binds it to a response schema whose "
        "`code` enum excludes the value. For each of these, should the "
        "operation's response admit the code, or should the catalogue "
        "entry change?",
        details=problems,
    )
