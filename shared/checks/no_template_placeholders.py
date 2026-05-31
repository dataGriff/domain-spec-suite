"""Audit check: no template placeholder strings remain in the spec set.

Scans every markdown and YAML file under `docs/specifications/`.
Looks for the standard placeholder shapes: `[Resource1]`,
`[Domain]`, and `{{...}}`. Template skeletons (with placeholders
intact) live in the suite at `<suite>/templates/` and are outside
this directory, so they're not scanned.
"""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult

metadata = {
    "id": "NO-TEMPLATE-PLACEHOLDERS",
    "category": "structural",
    "phases": ["audit"],
    "severity_by_phase": {"audit": "error"},
    "prerequisites": [],
}

PLACEHOLDER = re.compile(r"\[Resource1\]|\[Domain\]|\{\{")


def run(repo_root: pathlib.Path) -> CheckResult:
    specs = repo_root / "docs" / "specifications"
    if not specs.is_dir():
        return CheckResult.fail(
            "There's no docs/specifications/ directory to scan. "
            "Has Phase 0 (Bootstrap) been run against this repo?",
        )

    offenders: list[str] = []
    for path in sorted(specs.rglob("*")):
        if not path.is_file():
            continue
        if "_template" in path.parts:
            continue
        if path.suffix not in {".md", ".yaml", ".yml"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if PLACEHOLDER.search(line):
                offenders.append(f"{path.relative_to(repo_root)}:{line_no}  {line.strip()[:80]}")

    if not offenders:
        return CheckResult.ok()

    return CheckResult.fail(
        "Template placeholders are still in the spec set. Each of the "
        "lines below carries a `[Resource1]`, `[Domain]`, or `{{...}}` "
        "marker that should have been replaced with real domain content "
        "by the phase that produced the file. Which value belongs in "
        "each of these positions?",
        details=offenders,
    )
