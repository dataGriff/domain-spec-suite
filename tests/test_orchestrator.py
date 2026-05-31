"""Tests for the orchestrator status reader (BUILD-PLAN Milestone 4.1).

Covers:
- Fresh (un-bootstrapped) repo → action 'bootstrap'
- Bootstrapped but Phase 1 not started → action 'start' with phase
  'discovery'
- All phases passed → action 'complete'
- Hand-mutated PRD without re-sign → discovery 'stale' → action
  'update-mode'
- Unaccepted force-advance present → action 'accept-force-advances'
"""

from __future__ import annotations

import pathlib
import shutil
import sys

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent
ITEMS_FIXTURE = REPO / "tests" / "fixtures" / "items"

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts import force_advance, orchestrator_status  # noqa: E402
from shared import spec_paths  # noqa: E402

pytestmark = pytest.mark.orchestrator


def _copy_fixture(tmp_path: pathlib.Path) -> pathlib.Path:
    target = tmp_path / "items"
    shutil.copytree(ITEMS_FIXTURE, target)
    return target


# ── fresh repo ────────────────────────────────────────────────────


def test_fresh_repo_routes_to_bootstrap(tmp_path: pathlib.Path) -> None:
    """A bare directory with no _progress.yaml → action 'bootstrap'."""
    report = orchestrator_status.build_report(tmp_path)
    assert report.bootstrapped is False
    assert report.next_action["action"] == "bootstrap"
    assert report.next_action["phase"] == "bootstrap"
    assert report.phases == []


# ── all phases passed ─────────────────────────────────────────────


def test_items_fixture_is_complete() -> None:
    """The Items fixture has every phase signed off — orchestrator
    should declare complete."""
    report = orchestrator_status.build_report(ITEMS_FIXTURE)
    assert report.bootstrapped is True
    assert report.domain_name == "items"
    assert all(p.status == "passed" for p in report.phases), (
        "expected every phase 'passed', got "
        + ", ".join(f"{p.phase}={p.status}" for p in report.phases)
    )
    assert report.next_action["action"] == "complete"


# ── bootstrapped, discovery not started ───────────────────────────


def test_bootstrapped_only_routes_to_discovery(tmp_path: pathlib.Path) -> None:
    """Tear off everything past bootstrap; orchestrator should
    propose starting discovery."""
    target = _copy_fixture(tmp_path)
    # Remove all phase sign-offs except bootstrap and clear the
    # progress phase entries that imply later phases ran.
    for phase_num in range(1, 8):
        sidecar = spec_paths.phases_dir(target) / f"phase-{phase_num}-passed.yaml"
        if sidecar.is_file():
            sidecar.unlink()

    progress_path = spec_paths.progress_path(target)
    progress = yaml.safe_load(progress_path.read_text())
    progress["phases"] = {"bootstrap": progress["phases"]["bootstrap"]}
    progress["force_advances"] = []
    progress_path.write_text(yaml.safe_dump(progress, sort_keys=False))

    report = orchestrator_status.build_report(target)
    assert report.bootstrapped is True
    bootstrap_phase = next(p for p in report.phases if p.phase == "bootstrap")
    discovery_phase = next(p for p in report.phases if p.phase == "discovery")
    assert bootstrap_phase.status == "passed"
    assert discovery_phase.status == "not-started"
    assert report.next_action["action"] == "start"
    assert report.next_action["phase"] == "discovery"


# ── stale phase ───────────────────────────────────────────────────


def test_modified_prd_marks_discovery_stale(tmp_path: pathlib.Path) -> None:
    """Edit prd.md without re-signing → discovery 'stale' → action
    'update-mode'."""
    target = _copy_fixture(tmp_path)
    prd = target / "docs/specifications/prd.md"
    prd.write_text(prd.read_text() + "\n\n<!-- unauthorised edit -->\n")

    report = orchestrator_status.build_report(target)
    discovery_phase = next(p for p in report.phases if p.phase == "discovery")
    assert discovery_phase.status == "stale"
    assert "docs/specifications/prd.md" in discovery_phase.stale_files
    assert report.next_action["action"] == "update-mode"
    assert report.next_action["phase"] == "discovery"


# ── pending force-advance ─────────────────────────────────────────


def test_unaccepted_force_advance_blocks_complete(tmp_path: pathlib.Path) -> None:
    """An unaccepted force-advance entry surfaces as the next action,
    even when every phase otherwise passed."""
    target = _copy_fixture(tmp_path)
    force_advance.force_advance(target, "contracts", "spectral upstream bug")

    report = orchestrator_status.build_report(target)
    assert len(report.pending_force_advances) == 1
    assert report.next_action["action"] == "accept-force-advances"
    assert "contracts" in report.next_action.get("pending", [])


# ── not-yet-implemented phases ───────────────────────────────────


def test_status_reports_unimplemented_phases_honestly(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the next phase has no skill implementation, orchestrator
    surfaces 'not-implemented' rather than routing into a stub. All
    seven phase skills currently ship, so this test fakes-out
    IMPLEMENTED_PHASES via monkeypatch to keep the no-stub-routing
    contract guarded as future phases are added."""
    target = _copy_fixture(tmp_path)
    for phase_num in range(2, 8):
        sidecar = spec_paths.phases_dir(target) / f"phase-{phase_num}-passed.yaml"
        if sidecar.is_file():
            sidecar.unlink()
    progress_path = spec_paths.progress_path(target)
    progress = yaml.safe_load(progress_path.read_text())
    progress["phases"] = {
        "bootstrap": progress["phases"]["bootstrap"],
        "discovery": progress["phases"]["discovery"],
    }
    progress["force_advances"] = []
    progress_path.write_text(yaml.safe_dump(progress, sort_keys=False))

    # Pretend modeling+later are not-yet-implemented for this test.
    monkeypatch.setattr(
        orchestrator_status,
        "IMPLEMENTED_PHASES",
        {"bootstrap", "discovery"},
    )

    report = orchestrator_status.build_report(target)
    modeling_phase = next(p for p in report.phases if p.phase == "modeling")
    assert modeling_phase.status == "not-started"
    assert modeling_phase.implemented is False
    assert report.next_action["action"] == "not-implemented"
    assert report.next_action["phase"] == "modeling"
