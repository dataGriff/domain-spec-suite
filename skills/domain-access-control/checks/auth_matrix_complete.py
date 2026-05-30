"""Phase 3 hard check: every operation × every role in auth-matrix.md
has a non-empty permission cell.

The Auth Matrix table has columns: Operation | Endpoint | Public |
<role1> | <role2> | ... Each role × operation cell must carry a
permission marker (Legend: 🌐 / ✅ / 🔒 / ❌). An empty cell means
'undecided', which the access-control phase must not ship."""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult
from shared.spec_parsers import _section

metadata = {
    "id": "AUTH-MATRIX-COMPLETE",
    "category": "structural",
    "phases": ["access-control"],
    "severity_by_phase": {"access-control": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/auth-matrix.md"},
    ],
}

PLACEHOLDER_CELL = {"", "todo", "tbd", "tbc", "?"}


def _split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def run(repo_root: pathlib.Path) -> CheckResult:
    auth = repo_root / "docs/specifications/auth-matrix.md"
    text = auth.read_text(encoding="utf-8")
    section = _section(text, r"^##\s+Auth Matrix\s*$")

    # Walk the table. First row: header. Second row: separator. Then data.
    lines = [line for line in section.splitlines() if line.strip().startswith("|")]
    if len(lines) < 3:
        return CheckResult.fail("auth-matrix.md has no parseable Auth Matrix table.")

    header = _split_row(lines[0])
    data_rows = lines[2:]

    problems: list[str] = []
    for raw in data_rows:
        cells = _split_row(raw)
        if len(cells) < len(header):
            problems.append(f"row with fewer cells than header: {raw.strip()!r}")
            continue
        operation = cells[0]
        # Find role columns (everything past "Endpoint"). We treat any
        # column after Operation+Endpoint as a permission column.
        if len(header) < 3:
            continue
        for col_idx in range(2, len(header)):
            cell = cells[col_idx].lower()
            # Strip markdown formatting from cells (e.g. emoji combos)
            cell_clean = re.sub(r"[`*]", "", cell).strip()
            if cell_clean in PLACEHOLDER_CELL:
                problems.append(
                    f"{operation!r} × {header[col_idx]!r}: empty/placeholder permission"
                )

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "Some operation × role cells in the Auth Matrix have no "
        "permission marker. Every cell needs an explicit decision "
        "(Public, Allowed, Allowed-if-owner, Forbidden) — undecided "
        "ships as 'whatever the implementation defaults to', which is "
        "how access regressions happen.",
        details=problems,
    )
