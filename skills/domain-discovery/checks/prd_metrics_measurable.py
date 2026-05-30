"""Phase 1 structural check: every success metric in prd.md contains
either a number (digit) or a measurable verb (validate, count,
appear, ...).

The rubric judgement of whether the threshold is *realistic and concrete*
lives in SKILL.md prose (the second rubric check). This check just
catches metrics that are purely aspirational — "be great", "delight
users" — where there's nothing concrete to evaluate."""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult
from shared.spec_parsers import _section

metadata = {
    "id": "PRD-METRICS-MEASURABLE",
    "category": "structural",
    "phases": ["discovery"],
    "severity_by_phase": {"discovery": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/prd.md"},
    ],
}

DIGIT_RE = re.compile(r"\d")
MEASURABLE_VERBS = {
    "validate",
    "validates",
    "count",
    "counts",
    "appears",
    "appear",
    "match",
    "matches",
    "matching",
    "succeed",
    "succeeds",
    "passes",
    "pass",
    "describe",
    "describes",
    "lints",
    "lint",
}
LIST_ITEM_RE = re.compile(r"(?m)^\s*(?:\d+\.|[-*])\s+(?P<text>.+?)$")
PLACEHOLDER_TEXT = {"todo", "tbd", "tbc"}


def _is_measurable(text: str) -> bool:
    if DIGIT_RE.search(text):
        return True
    lowered = text.lower()
    return any(verb in lowered for verb in MEASURABLE_VERBS)


def run(repo_root: pathlib.Path) -> CheckResult:
    prd = repo_root / "docs" / "specifications" / "prd.md"
    text = prd.read_text(encoding="utf-8")
    section = _section(text, r"^##\s+Success Metrics\s*$")
    section = re.sub(r"<!--.*?-->", "", section, flags=re.DOTALL)

    items: list[str] = []
    for match in LIST_ITEM_RE.finditer(section):
        body = match.group("text").strip()
        if body.lower() in PLACEHOLDER_TEXT:
            continue
        items.append(body)

    if not items:
        return CheckResult.fail(
            "No success metrics listed. How will you know this domain is "
            "doing its job? Capture at least one measurable signal — a "
            "number, a count, a validation that either passes or doesn't."
        )

    # Each metric is a numbered list item plus any indented continuation
    # text that follows on subsequent lines. We approximate that by
    # treating the whole bullet-paragraph as one metric.
    paragraphs = re.split(r"(?m)^\s*\d+\.\s+", section)
    metrics = [p.strip() for p in paragraphs if p.strip()]

    problems: list[str] = []
    for i, metric in enumerate(metrics, start=1):
        if metric.lower() in PLACEHOLDER_TEXT:
            continue
        if not _is_measurable(metric):
            problems.append(f"metric #{i}: no number or measurable verb in {metric[:80]!r}")

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "Some success metrics aren't measurable as written. For each "
        "one below, what's the specific number, count, or pass/fail "
        "check that would prove the metric was met? 'Delight users' "
        "isn't a metric; 'NPS ≥ 30 within 90 days' is.",
        details=problems,
    )
