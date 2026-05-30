"""Cross-reference check: every error code referenced in auth-matrix.md
is defined in error-catalogue.md.

OpenAPI's response shapes are generic ($ref to ValidationError,
ForbiddenError, etc.) — they don't carry the actual code strings. So
the authoritative reference points for code strings are auth-matrix.md
(short reference) and error-catalogue.md (canonical definitions). This
check ensures every code the auth matrix mentions has a matching entry
in the catalogue.
"""

from __future__ import annotations

import pathlib

from shared.check_result import CheckResult
from shared.spec_parsers import auth_matrix_error_codes, error_catalogue_codes

metadata = {
    "id": "ERROR-CODE-IN-CATALOGUE",
    "category": "cross-reference",
    "phases": ["access-control", "contracts", "audit"],
    "severity_by_phase": {
        "access-control": "warning",
        "contracts": "error",
        "audit": "error",
    },
    "prerequisites": [
        {"file_exists": "docs/specifications/auth-matrix.md"},
        {"file_exists": "docs/specifications/error-catalogue.md"},
    ],
}


def run(repo_root: pathlib.Path) -> CheckResult:
    auth_matrix = repo_root / "docs" / "specifications" / "auth-matrix.md"
    error_catalogue = repo_root / "docs" / "specifications" / "error-catalogue.md"

    referenced = auth_matrix_error_codes(auth_matrix)
    defined = error_catalogue_codes(error_catalogue)

    missing = sorted(referenced - defined)
    if not missing:
        return CheckResult.ok()

    return CheckResult.fail(
        "Error codes named in auth-matrix.md aren't defined in "
        "error-catalogue.md. Every code that appears anywhere in the "
        "spec set has to have one canonical definition (HTTP status, "
        "meaning, triggers) in the catalogue. What does each of these "
        "codes mean, and which HTTP status does it map to?",
        details=[f"code referenced but not defined: {c}" for c in missing],
    )
