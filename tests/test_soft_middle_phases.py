"""Smoke tests for the four soft-middle skills (M5.1–5.4).

For each phase:
- gate.yaml is parseable and lists the expected check ids
- questions.md is parseable YAML with one entry per gate check
- the gate, when run against the Items fixture, has no hard-error
  failures (warnings are allowed; the engagement loop covers them)
"""

from __future__ import annotations

import pathlib
import sys

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent
ITEMS_FIXTURE = REPO / "tests" / "fixtures" / "items"

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from shared import run_phase  # noqa: E402

PHASE_EXPECTATIONS = {
    "modeling": {
        "expected_ids": {
            "MODEL-ENTITY-NAME-UNIQUE",
            "ENTITY-IN-GLOSSARY",
            "GLOSSARY-COVERS-DOMAIN-TERMS",
            "MODEL-ENTITY-HAS-ID-TIMESTAMPS",
            "MODEL-ENTITY-BUSINESS-RULE",
            "MODEL-LIFECYCLE-DEFINED",
            "MODEL-RELATIONSHIP-BIDIRECTIONAL",
            "ENTITY-HAS-EVENT",
        },
        "expected_warnings_for_items": {"MODEL-ENTITY-HAS-ID-TIMESTAMPS"},
    },
    "access-control": {
        "expected_ids": {
            "AUTH-ROLE-HAS-DESCRIPTION",
            "AUTH-MATRIX-COMPLETE",
            "ERROR-CATALOGUE-COMPLETE",
            "ERROR-CODE-IN-CATALOGUE",
            "AUTH-ROLE-TRACES-TO-PERSONA",
            "AUTH-MATRIX-OPENAPI-MATCH",
        },
        "expected_warnings_for_items": set(),
    },
    "flows": {
        "expected_ids": {
            "FLOW-DIAGRAM-HAS-TITLE-PARTICIPANTS",
            "FLOW-PARTICIPANT-IS-ROLE-OR-SYSTEM",
            "STORY-HAS-FLOW",
            "LIFECYCLE-IN-FLOWS",
        },
        "expected_warnings_for_items": set(),
    },
    "nfrs": {
        "expected_ids": {
            "NFR-THRESHOLD-MEASURABLE",
            "ACCEPTANCE-SCENARIO-GWT",
            "US-HAS-SCENARIO",
        },
        "expected_warnings_for_items": {"NFR-THRESHOLD-MEASURABLE"},
    },
}


@pytest.mark.parametrize(
    "phase",
    list(PHASE_EXPECTATIONS.keys()),
    ids=lambda p: p,
)
def test_gate_manifest_matches_expectation(phase: str) -> None:
    gate_path = REPO / f"skills/domain-{phase}/gate.yaml"
    gate = yaml.safe_load(gate_path.read_text())
    ids = {entry["id"] for entry in gate.get("checks", [])}
    expected = PHASE_EXPECTATIONS[phase]["expected_ids"]
    assert ids == expected, (
        f"{phase} gate has {ids - expected} extra and is missing {expected - ids}"
    )


@pytest.mark.parametrize(
    "phase",
    list(PHASE_EXPECTATIONS.keys()),
    ids=lambda p: p,
)
def test_questions_md_covers_every_check(phase: str) -> None:
    qpath = REPO / f"skills/domain-{phase}/questions.md"
    questions = yaml.safe_load(qpath.read_text())
    bindings = {q.get("binds_to_check") for q in questions}
    expected = PHASE_EXPECTATIONS[phase]["expected_ids"]
    missing = expected - bindings
    assert not missing, f"{phase}/questions.md missing entries for: {missing}"


@pytest.mark.parametrize(
    "phase",
    list(PHASE_EXPECTATIONS.keys()),
    ids=lambda p: p,
)
def test_gate_has_no_errors_against_items_fixture(phase: str) -> None:
    """Hard errors block sign-off. Items fixture must produce zero
    error-severity failures at every soft-middle phase. Warnings are
    expected (they're handled by the engagement loop)."""
    exit_code, outcomes = run_phase.run_phase(phase, ITEMS_FIXTURE)
    errors = [o for o in outcomes if not o.passed and not o.skipped and o.severity == "error"]
    assert exit_code == 0, (
        f"{phase} gate has hard-error failures against the Items fixture:\n"
        + "\n".join(f"  {o.id}: {o.message}" for o in errors)
    )
    assert errors == []


@pytest.mark.parametrize(
    "phase",
    list(PHASE_EXPECTATIONS.keys()),
    ids=lambda p: p,
)
def test_expected_warnings_fire_against_items_fixture(phase: str) -> None:
    """Sanity check that the *expected* warnings (and only those) fire
    against Items. Catches drift if a check becomes too strict / too
    loose."""
    _exit, outcomes = run_phase.run_phase(phase, ITEMS_FIXTURE)
    fired = {o.id for o in outcomes if not o.passed and not o.skipped and o.severity == "warning"}
    expected = PHASE_EXPECTATIONS[phase]["expected_warnings_for_items"]
    assert fired == expected, f"{phase} fired warnings {fired}, expected {expected}"
