"""Phase 3 hard check: every error code in error-catalogue.md declares
a HTTP status, a meaning, and a 'Triggered by' clause."""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult

metadata = {
    "id": "ERROR-CATALOGUE-COMPLETE",
    "category": "structural",
    "phases": ["access-control"],
    "severity_by_phase": {"access-control": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/error-catalogue.md"},
    ],
}

ERROR_BLOCK_RE = re.compile(
    r"(?m)^###\s+`(?P<code>[A-Z][A-Z0-9_]+)`\n(?P<body>.*?)(?=^###\s+`|\Z)", re.DOTALL
)


def run(repo_root: pathlib.Path) -> CheckResult:
    catalogue = repo_root / "docs/specifications/error-catalogue.md"
    text = catalogue.read_text(encoding="utf-8")

    problems: list[str] = []
    for match in ERROR_BLOCK_RE.finditer(text):
        code = match.group("code")
        body = match.group("body")
        if "**HTTP status:**" not in body:
            problems.append(f"`{code}`: no `**HTTP status:**` line")
        if "**Meaning:**" not in body:
            problems.append(f"`{code}`: no `**Meaning:**` line")
        if "**Triggered by:**" not in body:
            problems.append(f"`{code}`: no `**Triggered by:**` line")

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "Some errors in error-catalogue.md are incomplete. Every "
        "error needs HTTP status, Meaning, and Triggered-by — the "
        "contract phase will reference these and downstream API "
        "consumers rely on them to disambiguate failures.",
        details=problems,
    )
