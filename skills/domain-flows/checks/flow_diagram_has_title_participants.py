"""Phase 4 hard check: every mermaid sequenceDiagram block in
sequence-diagrams.md sits under a `## Flow N: <title>` heading AND
declares at least one `participant` line."""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult

metadata = {
    "id": "FLOW-DIAGRAM-HAS-TITLE-PARTICIPANTS",
    "category": "structural",
    "phases": ["flows"],
    "severity_by_phase": {"flows": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/sequence-diagrams.md"},
    ],
}

# Match: ## Flow heading followed eventually by a ```mermaid block.
FLOW_BLOCK_RE = re.compile(
    r"(?P<title>^##\s+[^\n]+)\n.*?```mermaid\n(?P<diagram>.*?)```",
    re.DOTALL | re.MULTILINE,
)
PARTICIPANT_RE = re.compile(r"^\s*participant\s+\S", re.MULTILINE)


def run(repo_root: pathlib.Path) -> CheckResult:
    flows = repo_root / "docs/specifications/sequence-diagrams.md"
    text = flows.read_text(encoding="utf-8")

    flows_found = 0
    problems: list[str] = []
    for match in FLOW_BLOCK_RE.finditer(text):
        flows_found += 1
        title = match.group("title").strip().lstrip("#").strip()
        diagram = match.group("diagram")
        if "sequenceDiagram" not in diagram:
            continue  # not a sequence diagram block — skip
        if not PARTICIPANT_RE.search(diagram):
            problems.append(f"{title!r}: no `participant` line in the diagram body")

    if flows_found == 0:
        return CheckResult.fail(
            "sequence-diagrams.md has no mermaid `sequenceDiagram` "
            "blocks. Every PRD user story should be backed by at "
            "least one flow."
        )

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "Some flow diagrams have no `participant` declarations. Every "
        "sequence diagram needs explicit participants so a reader can "
        "tell who's involved before tracing the arrows.",
        details=problems,
    )
