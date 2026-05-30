"""Tests for the domain-discovery skill (BUILD-PLAN Milestone 4.2).

Covers:
- Gate passes cleanly against the Items fixture (8 structural checks).
- Every BUILD-PLAN check id is present in gate.yaml and questions.md.
- Deliberate breaks against the fixture each fail the expected check
  with the expected interview-style message.
"""

from __future__ import annotations

import pathlib
import shutil
import sys
from dataclasses import dataclass

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent
ITEMS_FIXTURE = REPO / "tests" / "fixtures" / "items"

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from shared import run_phase  # noqa: E402

pytestmark = pytest.mark.discovery


EXPECTED_CHECK_IDS = {
    "PRD-PROBLEM-USER-PAIN",
    "PRD-PERSONA-EXISTS",
    "PRD-PERSONA-GOAL",
    "PRD-PERSONA-FRUSTRATION",
    "PRD-NON-GOAL",
    "PRD-STORY-ACCEPTANCE",
    "PRD-STORY-PERSONA-LINK",
    "PRD-METRICS-MEASURABLE",
}


# ── gate manifest matches BUILD-PLAN ──────────────────────────────


def test_gate_manifest_matches_build_plan() -> None:
    gate = yaml.safe_load((REPO / "skills/domain-discovery/gate.yaml").read_text())
    gate_ids = {entry["id"] for entry in gate.get("checks", [])}
    assert gate_ids == EXPECTED_CHECK_IDS, (
        f"discovery/gate.yaml has {gate_ids - EXPECTED_CHECK_IDS} extra "
        f"and is missing {EXPECTED_CHECK_IDS - gate_ids}"
    )


def test_questions_md_covers_every_check() -> None:
    """One questions.md entry per gate-check id (§7.5 authoring rule 1)."""
    questions = yaml.safe_load((REPO / "skills/domain-discovery/questions.md").read_text())
    bindings = {q.get("binds_to_check") for q in questions}
    missing = EXPECTED_CHECK_IDS - bindings
    assert not missing, f"questions.md missing entries for: {missing}"


# ── gate passes against the fixture ───────────────────────────────


def test_discovery_gate_passes_against_items_fixture() -> None:
    exit_code, outcomes = run_phase.run_phase("discovery", ITEMS_FIXTURE)
    failures = [o for o in outcomes if not o.passed and not o.skipped]
    assert exit_code == 0, "discovery gate failed against the Items fixture:\n" + "\n".join(
        f"  {f.id}: {f.message}" for f in failures
    )
    assert failures == []


# ── per-repo persona allow-list extension ────────────────────────


def test_persona_allow_list_extension_passes_otherwise_unknown_actor(
    tmp_path: pathlib.Path,
) -> None:
    """Adding an actor to docs/specifications/_persona_allow_list.yaml
    lets PRD-STORY-PERSONA-LINK accept stories that name it."""
    target = tmp_path / "items"
    shutil.copytree(ITEMS_FIXTURE, target)
    prd = target / "docs/specifications/prd.md"
    text = prd.read_text()

    # Inject a story whose actor is a domain-specific pre-onboarding
    # role the baseline doesn't know about.
    insertion = (
        "\n#### US-999: A wandering bard requests a song\n\n"
        "**As a** wandering bard,\n"
        "**I want to** request a song,\n"
        "**So that** I can practice my craft.\n\n"
        "**Acceptance Criteria:**\n"
        "- Bard receives a song\n"
    )
    new_text = text.replace(
        "## Constraints",
        insertion + "\n## Constraints",
        1,
    )
    prd.write_text(new_text)

    # Without the allow-list, the check should fail on the bard.
    exit_code, outcomes = run_phase.run_phase("discovery", target)
    assert exit_code != 0
    failures = [o for o in outcomes if not o.passed and not o.skipped]
    assert any(o.id == "PRD-STORY-PERSONA-LINK" for o in failures)

    # Add the allow-list and re-run; check passes.
    allow_list = target / "docs/specifications/_persona_allow_list.yaml"
    allow_list.write_text("pre_onboarding_actors:\n  - wandering bard\n")
    exit_code, outcomes = run_phase.run_phase("discovery", target)
    failures = [o for o in outcomes if not o.passed and not o.skipped]
    assert exit_code == 0, "with allow-list, discovery gate should pass; failures: " + ", ".join(
        f.id for f in failures
    )


def test_persona_allow_list_missing_file_is_fine(tmp_path: pathlib.Path) -> None:
    """No _persona_allow_list.yaml → baseline GENERIC_ACTORS apply →
    fixture still passes (it does already, but assert it explicitly)."""
    target = tmp_path / "items"
    shutil.copytree(ITEMS_FIXTURE, target)
    allow = target / "docs/specifications/_persona_allow_list.yaml"
    assert not allow.exists(), "fixture should not carry an allow-list"
    exit_code, _ = run_phase.run_phase("discovery", target)
    assert exit_code == 0


# ── deliberate breaks ─────────────────────────────────────────────


def _copy_fixture(tmp_path: pathlib.Path) -> pathlib.Path:
    target = tmp_path / "items"
    shutil.copytree(ITEMS_FIXTURE, target)
    return target


def _read_prd(repo: pathlib.Path) -> str:
    return (repo / "docs/specifications/prd.md").read_text()


def _write_prd(repo: pathlib.Path, text: str) -> None:
    (repo / "docs/specifications/prd.md").write_text(text)


# Each break: a function that mutates a copied fixture's prd.md, and
# the (check_id, message_substring) that should fail as a result.


@dataclass
class Break:
    name: str
    mutate: callable
    expected_id: str
    expected_substring: str


def _erase_problem_statement(repo: pathlib.Path) -> None:
    text = _read_prd(repo)
    # Replace everything between "## Problem Statement" and the next "## "
    import re

    new = re.sub(
        r"(## Problem Statement\n).*?(?=\n## )",
        r"\1\n",
        text,
        count=1,
        flags=re.DOTALL,
    )
    _write_prd(repo, new)


def _wipe_personas_section(repo: pathlib.Path) -> None:
    text = _read_prd(repo)
    import re

    new = re.sub(
        r"(## Target Users / Personas\n).*?(?=\n## )",
        r"\1\n",
        text,
        count=1,
        flags=re.DOTALL,
    )
    _write_prd(repo, new)


def _strip_persona_goals(repo: pathlib.Path) -> None:
    """Replace every persona's Goal line with a TODO."""
    text = _read_prd(repo)
    import re

    new = re.sub(
        r"-\s*\*\*Goal:\*\*\s*[^\n]+(?:\n(?!\s*-|\s*###|\s*##)[^\n]*)*",
        "- **Goal:** TODO",
        text,
    )
    _write_prd(repo, new)


def _strip_persona_frustrations(repo: pathlib.Path) -> None:
    text = _read_prd(repo)
    import re

    new = re.sub(
        r"-\s*\*\*Frustration:\*\*\s*[^\n]+(?:\n(?!\s*-|\s*###|\s*##)[^\n]*)*",
        "- **Frustration:** TODO",
        text,
    )
    _write_prd(repo, new)


def _wipe_non_goals(repo: pathlib.Path) -> None:
    text = _read_prd(repo)
    import re

    new = re.sub(
        r"(## Non-Goals\n).*?(?=\n## )",
        r"\1\n1. TODO\n",
        text,
        count=1,
        flags=re.DOTALL,
    )
    _write_prd(repo, new)


def _strip_acceptance_criteria(repo: pathlib.Path) -> None:
    """Replace every `**Acceptance Criteria:**` block body with just
    `- [ ] TODO`."""
    text = _read_prd(repo)
    import re

    new = re.sub(
        r"(\*\*Acceptance Criteria:\*\*\n)((?:-[^\n]*\n)+)",
        r"\1- [ ] TODO\n",
        text,
    )
    _write_prd(repo, new)


def _rename_story_actor(repo: pathlib.Path) -> None:
    """Replace one `**As a** ...` line with a never-defined actor."""
    text = _read_prd(repo)
    import re

    new = re.sub(
        r"(####\s+US-001:[^\n]*\n\n\*\*As a\*\*)\s+[^,]+,",
        r"\1 vagrant wizard,",
        text,
        count=1,
    )
    _write_prd(repo, new)


def _replace_metrics_with_fluff(repo: pathlib.Path) -> None:
    """Replace Success Metrics section with aspirational fluff (no
    digits, no measurable verbs)."""
    text = _read_prd(repo)
    import re

    new = re.sub(
        r"(## Success Metrics\n).*",
        r"\1\n1. Users love it.\n2. The team feels confident.\n",
        text,
        count=1,
        flags=re.DOTALL,
    )
    _write_prd(repo, new)


BREAKS = [
    Break(
        "erased_problem_statement",
        _erase_problem_statement,
        "PRD-PROBLEM-USER-PAIN",
        "no Problem Statement content",
    ),
    Break(
        "wiped_personas",
        _wipe_personas_section,
        "PRD-PERSONA-EXISTS",
        "No personas declared",
    ),
    Break(
        "todo_persona_goals",
        _strip_persona_goals,
        "PRD-PERSONA-GOAL",
        "Goal",
    ),
    Break(
        "todo_persona_frustrations",
        _strip_persona_frustrations,
        "PRD-PERSONA-FRUSTRATION",
        "Frustration",
    ),
    Break(
        "wiped_non_goals",
        _wipe_non_goals,
        "PRD-NON-GOAL",
        "No real non-goals",
    ),
    Break(
        "todo_acceptance",
        _strip_acceptance_criteria,
        "PRD-STORY-ACCEPTANCE",
        "acceptance criteria",
    ),
    Break(
        "story_renamed_to_unknown_actor",
        _rename_story_actor,
        "PRD-STORY-PERSONA-LINK",
        "wizard",
    ),
    Break(
        "fluffy_metrics",
        _replace_metrics_with_fluff,
        "PRD-METRICS-MEASURABLE",
        "measurable",
    ),
]


@pytest.mark.parametrize("brk", BREAKS, ids=lambda b: b.name)
def test_break_fails_expected_check(tmp_path: pathlib.Path, brk: Break) -> None:
    target = _copy_fixture(tmp_path)
    brk.mutate(target)

    exit_code, outcomes = run_phase.run_phase("discovery", target)
    assert exit_code != 0, f"expected break {brk.name!r} to fail the gate"

    failures = [o for o in outcomes if not o.passed and not o.skipped]
    matching = [o for o in failures if o.id == brk.expected_id]
    assert matching, (
        f"break {brk.name!r} did not fail check {brk.expected_id!r}; "
        f"failed checks were: {[o.id for o in failures]}"
    )

    outcome = matching[0]
    haystack = " ".join([outcome.message] + outcome.details).lower()
    assert brk.expected_substring.lower() in haystack, (
        f"check {outcome.id!r} failed as expected but message didn't "
        f"contain {brk.expected_substring!r}; full message: "
        f"{outcome.message}\ndetails: {outcome.details}"
    )
