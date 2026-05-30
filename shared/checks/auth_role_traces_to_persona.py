"""Cross-reference check: every role in auth-matrix.md either traces
to a PRD persona OR is explicitly justified as a system role in the
'Traces to persona' column.

The Items fixture's auth-matrix Roles table has the shape:

    | Role | Description | Traces to persona |
    |------|-------------|-------------------|
    | `contributor` | ... | Stockroom Lead (PRD §Target Users) |

The third column must either name a known persona (case-insensitive
match against the PRD's `### <persona>` headings) or contain the
literal word `system` (case-insensitive) indicating a system role.

Warning at access-control phase; error at audit."""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult
from shared.spec_parsers import _section, prd_persona_names

metadata = {
    "id": "AUTH-ROLE-TRACES-TO-PERSONA",
    "category": "cross-reference",
    "phases": ["access-control", "audit"],
    "severity_by_phase": {"access-control": "warning", "audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/auth-matrix.md"},
        {"file_exists": "docs/specifications/prd.md"},
    ],
}

ROLE_ROW = re.compile(
    r"^\|\s*`(?P<role>[a-z][a-z0-9_-]*)`\s*\|\s*[^|]+?\s*\|\s*(?P<trace>[^|]+?)\s*\|",
    re.MULTILINE,
)


def run(repo_root: pathlib.Path) -> CheckResult:
    auth = repo_root / "docs/specifications/auth-matrix.md"
    prd = repo_root / "docs/specifications/prd.md"

    text = auth.read_text(encoding="utf-8")
    section = _section(text, r"^##\s+Roles\s*$")
    personas = {p.lower() for p in prd_persona_names(prd)}

    problems: list[str] = []
    for match in ROLE_ROW.finditer(section):
        role = match.group("role")
        trace = match.group("trace").strip().lower()
        if not trace or trace in {"todo", "tbd", "---"}:
            problems.append(f"`{role}`: 'Traces to persona' column is empty")
            continue
        if "system" in trace:
            continue  # explicit system role — acceptable
        if any(persona_token in trace for persona_token in personas):
            continue
        problems.append(
            f"`{role}`: traces to {trace!r} which doesn't match any PRD persona "
            "or contain 'system' (system role)"
        )

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "Some auth-matrix roles don't trace cleanly to a PRD persona "
        "or declare themselves as system roles. For each one below: "
        "which PRD persona does this role serve — or is it a system "
        "role (write the word `system` in the Traces column)?",
        details=problems,
    )
