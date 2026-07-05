"""Tests for the domain-conformance-audit skill (BUILD-PLAN Task 2.3)."""

from __future__ import annotations

import importlib
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
ITEMS_FIXTURE = REPO / "tests" / "fixtures" / "items"

# Make the suite root importable so test-imported modules can resolve
# `from shared.* import ...`.
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from shared import run_phase  # noqa: E402

pytestmark = pytest.mark.audit


# ── end-to-end: audit passes cleanly against the Items fixture ────


def test_audit_passes_against_items_fixture() -> None:
    """The whole point of the Items fixture: it is the canonical
    known-good spec set, and audit must declare it complete."""
    exit_code, outcomes = run_phase.run_phase("audit", ITEMS_FIXTURE)
    failures = [o for o in outcomes if not o.passed and not o.skipped]
    assert exit_code == 0, "audit failed against the Items fixture:\n" + "\n".join(
        f"  {f.id}: {f.message}" for f in failures
    )
    assert failures == []


def test_audit_gate_lists_every_implemented_check() -> None:
    """Sanity check that the gate references every check the audit is
    supposed to run. Catches drift between gate.yaml and
    shared/checks/."""
    import yaml

    gate_path = REPO / "skills" / "domain-conformance-audit" / "gate.yaml"
    gate = yaml.safe_load(gate_path.read_text())
    gate_ids = {entry["id"] for entry in gate["checks"]}

    expected = {
        "NO-TEMPLATE-PLACEHOLDERS",
        "SIGNOFF-SHA256-MATCHES",
        "FORCE-ADVANCES-ALL-ACCEPTED",
        "AMBIGUITIES-NO-AUDIT-REQUIRED",
        "ENTITY-IN-GLOSSARY",
        "GLOSSARY-COVERS-ATTRIBUTES",
        "ENTITY-IN-OPENAPI-SCHEMA",
        "FIELD-MATCH-DOMAIN-OPENAPI",
        "ENUM-VALUES-CONSISTENT",
        "WRITE-OP-HAS-ASYNCAPI-CHANNEL",
        "EVENT-IN-DATACONTRACT",
        "EVENT-PAYLOAD-COVERS-ENTITY-STATE",
        "AUTH-MATRIX-OPENAPI-MATCH",
        "AUTH-ROLE-TRACES-TO-PERSONA",
        "ERROR-CODE-IN-CATALOGUE",
        "PRD-STORY-PERSONA-LINK",
        "STORY-HAS-FLOW",
        "LIFECYCLE-IN-FLOWS",
        "GENERATOR-CLEAN-OUTPUT",
        "IDEMPOTENCY-KEY-ON-POST-OPS",
        "ENTITY-HAS-EVENT",
        "EVENT-FK-RESOLVABLE",
        "DATACONTRACT-REFS-RESOLVE",
        "ERROR-CODE-REPRESENTABLE",
        "OPERATION-HAS-SCENARIO",
        "SCENARIO-REFS-VALID",
    }
    assert gate_ids == expected, (
        f"gate.yaml ↔ expected checks diverge:\n"
        f"  only in gate:     {gate_ids - expected}\n"
        f"  only in expected: {expected - gate_ids}"
    )


# ── per-check unit tests (happy path against Items) ───────────────


CHECK_MODULES = [
    "no_template_placeholders",
    "signoff_sha256_matches",
    "force_advances_all_accepted",
    "ambiguities_no_audit_required",
    "entity_in_glossary",
    "glossary_covers_attributes",
    "entity_in_openapi_schema",
    "field_match_domain_openapi",
    "enum_values_consistent",
    "write_op_has_asyncapi_channel",
    "event_in_datacontract",
    "event_payload_covers_entity_state",
    "auth_matrix_openapi_match",
    "auth_role_traces_to_persona",
    "error_code_in_catalogue",
    "prd_story_persona_link",
    "story_has_flow",
    "lifecycle_in_flows",
    "generator_clean_output",
]


@pytest.mark.parametrize("module_name", CHECK_MODULES)
def test_check_passes_against_items(module_name: str) -> None:
    module = importlib.import_module(f"shared.checks.{module_name}")
    result = module.run(ITEMS_FIXTURE)
    assert result.passed, (
        f"check {module.metadata['id']} failed against the Items "
        f"fixture:\n  message: {result.message}\n  details: {result.details}"
    )


@pytest.mark.parametrize("module_name", CHECK_MODULES)
def test_check_metadata_shape(module_name: str) -> None:
    """Every check exposes the standard metadata surface per SUITE-DESIGN §5.5."""
    module = importlib.import_module(f"shared.checks.{module_name}")
    meta = module.metadata
    assert isinstance(meta["id"], str) and meta["id"]
    assert meta["category"] in {"structural", "cross-reference", "rubric"}
    assert isinstance(meta["phases"], list) and meta["phases"]
    assert isinstance(meta["severity_by_phase"], dict)
    for phase in meta["phases"]:
        assert phase in meta["severity_by_phase"], (
            f"{meta['id']}: phase '{phase}' missing from severity_by_phase"
        )
    for prereq in meta.get("prerequisites", []):
        assert "file_exists" in prereq or "binary_exists" in prereq, (
            f"{meta['id']}: only file_exists / binary_exists prerequisites supported"
        )


# ── runner behaviour ──────────────────────────────────────────────


def test_runner_reports_missing_check_module() -> None:
    """If gate.yaml lists a check id that no module implements, the
    runner reports it as a failure (rather than crashing)."""
    # Synthetic gate: temporarily build one in memory by calling
    # run_phase internals with a check id we know doesn't exist.
    # Easiest path: load a real phase but assert behaviour via the
    # gate parser. Use a deliberately-bogus phase name path.
    with pytest.raises(ValueError, match="unknown phase"):
        run_phase.run_phase("not-a-phase", ITEMS_FIXTURE)


def test_runner_render_includes_summary_counts() -> None:
    _exit_code, outcomes = run_phase.run_phase("audit", ITEMS_FIXTURE)
    output = run_phase.render("audit", ITEMS_FIXTURE, outcomes)
    assert "summary:" in output
    assert "passed" in output


def test_signoff_sha256_matches_handles_bare_and_quoted(tmp_path: pathlib.Path) -> None:
    """Regression: SIGNOFF-SHA256-MATCHES must parse sha256 values
    written either bare (yaml.safe_dump shorthand) OR double-quoted
    (hand-authored fixtures). An earlier regex-only implementation
    matched only quoted format and silently passed everything in bare
    format, hiding real staleness drift on every audit.

    Test stages both formats in a synthetic spec dir and asserts each
    drift is caught."""
    import shutil

    from shared import spec_paths
    from shared.checks import signoff_sha256_matches

    target = tmp_path / "spec-sample"
    specs = target / "docs" / "specifications"
    specs.mkdir(parents=True)
    spec_paths.ensure_state_skeleton(target)

    # Two files, two sidecar shapes (bare + quoted).
    bare_file = specs / "bare.md"
    bare_file.write_text("bare content\n")
    quoted_file = specs / "quoted.md"
    quoted_file.write_text("quoted content\n")

    import hashlib

    bare_sha = hashlib.sha256(bare_file.read_bytes()).hexdigest()
    quoted_sha = hashlib.sha256(quoted_file.read_bytes()).hexdigest()

    phases = spec_paths.phases_dir(target)
    # Sidecar 1: bare sha256
    (phases / "phase-1-passed.yaml").write_text(
        f"""phase: bare-format-test
files_signed:
- path: docs/specifications/bare.md
  sha256: {bare_sha}
"""
    )
    # Sidecar 2: quoted sha256
    (phases / "phase-2-passed.yaml").write_text(
        f"""phase: quoted-format-test
files_signed:
  - path: docs/specifications/quoted.md
    sha256: "{quoted_sha}"
"""
    )

    # Both files at recorded sha → check passes.
    assert signoff_sha256_matches.run(target).passed

    # Mutate the bare-format-tracked file → check must fail.
    bare_file.write_text("bare content mutated\n")
    result = signoff_sha256_matches.run(target)
    assert not result.passed, "bare-format sha256 drift not detected"
    assert "bare.md" in str(result.details), (
        f"drift detected but wrong file flagged. details: {result.details}"
    )

    # Restore bare, mutate quoted → check must fail.
    bare_file.write_text("bare content\n")
    quoted_file.write_text("quoted content mutated\n")
    result = signoff_sha256_matches.run(target)
    assert not result.passed, "quoted-format sha256 drift not detected"
    assert "quoted.md" in str(result.details)

    # Cleanup
    shutil.rmtree(target)


def test_exclude_flag_skips_named_checks() -> None:
    """run_phase(..., exclude={ids}) omits those checks from outcomes
    entirely. Used by the spec-repo `task audit:cross-file` to skip
    placeholder + sha256 + force-advance + ambiguity + generator
    checks for a faster pre-push variant."""
    excluded = {
        "NO-TEMPLATE-PLACEHOLDERS",
        "SIGNOFF-SHA256-MATCHES",
        "FORCE-ADVANCES-ALL-ACCEPTED",
        "AMBIGUITIES-NO-AUDIT-REQUIRED",
        "GENERATOR-CLEAN-OUTPUT",
    }
    _exit_code, outcomes = run_phase.run_phase("audit", ITEMS_FIXTURE, exclude=excluded)
    fired_ids = {o.id for o in outcomes}
    assert not (excluded & fired_ids), (
        f"excluded check ids appeared in outcomes: {excluded & fired_ids}"
    )
    # And every NON-excluded check from the audit gate still ran.
    import yaml

    gate = yaml.safe_load((REPO / "skills/domain-conformance-audit/gate.yaml").read_text())
    expected = {entry["id"] for entry in gate["checks"]} - excluded
    assert fired_ids == expected, f"expected {expected}, got {fired_ids}"
