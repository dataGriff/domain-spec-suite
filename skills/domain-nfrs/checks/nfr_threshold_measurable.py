"""Phase 5 soft check: every NFR section (`### NFR-XXX-NNN`) carries
at least one measurable threshold (digit, percentage, or time unit).

Warning, not error: some NFRs are legitimately non-numeric (behavioural
guarantees like 'every event publish records its channel id', or
backwards-compat policies like 'no field is removed within a major
version'). The soft-gate engagement loop captures these as n-a with
a reason — keeping a hard error here would block sign-off for
realistic spec sets."""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult

metadata = {
    "id": "NFR-THRESHOLD-MEASURABLE",
    "category": "structural",
    "phases": ["nfrs"],
    "severity_by_phase": {"nfrs": "warning"},
    "prerequisites": [
        {"file_exists": "docs/specifications/nfr.md"},
    ],
}

NFR_BLOCK_RE = re.compile(
    r"(?m)^###\s+(?P<id>NFR-[A-Z]+-\d+)(?:\s*:\s*[^\n]*)?\n(?P<body>.*?)(?=^###\s+NFR-|\Z)",
    re.DOTALL,
)
THRESHOLD_TOKEN = re.compile(r"\d|\bp50\b|\bp95\b|\bp99\b", re.IGNORECASE)


def run(repo_root: pathlib.Path) -> CheckResult:
    nfr = repo_root / "docs/specifications/nfr.md"
    text = nfr.read_text(encoding="utf-8")

    problems: list[str] = []
    found = 0
    for match in NFR_BLOCK_RE.finditer(text):
        found += 1
        nfr_id = match.group("id")
        body = match.group("body")
        # Strip comments + blank lines for the threshold check.
        body_clean = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
        if not THRESHOLD_TOKEN.search(body_clean):
            problems.append(
                f"{nfr_id}: no digit / percentage / time unit / p95/p99 token found in the body"
            )

    if found == 0:
        return CheckResult.fail(
            "nfr.md has no `### NFR-XXX-NNN` sections. Every NFR needs "
            "an id and a measurable threshold."
        )

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "Some NFRs have no measurable threshold. For each one below: "
        "what specific number, percentage, time, or pXX percentile "
        "defines 'meeting' this NFR? If the threshold genuinely can't "
        "be set yet, move the entry to .spec-suite/ambiguities.md with a "
        "required-by phase rather than leaving it here.",
        details=problems,
    )
