"""Tests for the operator scripts behind `task suite:upgrade-shell`
and `task suite:reset-phase` (BUILD-PLAN Task 2.1 wrappers, SUITE-DESIGN
§1/§2 and §11)."""

from __future__ import annotations

import pathlib
import subprocess
import sys

import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from shared import spec_paths  # noqa: E402

BOOTSTRAP = REPO / "scripts" / "bootstrap.py"
UPGRADE_SHELL = REPO / "scripts" / "upgrade_shell.py"
RESET_PHASE = REPO / "scripts" / "reset_phase.py"


def run_script(script: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def bootstrapped_repo(tmp_path: pathlib.Path) -> pathlib.Path:
    target = tmp_path / "spec-sample"
    target.mkdir()
    result = run_script(BOOTSTRAP, "--target", str(target), "--domain-name", "Sample")
    assert result.returncode == 0, result.stderr
    return target


# ── upgrade_shell ─────────────────────────────────────────────────


def test_upgrade_shell_refreshes_manifest_files_and_preserves_specs(
    tmp_path: pathlib.Path,
) -> None:
    target = bootstrapped_repo(tmp_path)

    # Drift a manifest-owned file and author a spec file.
    taskfile = target / "Taskfile.yml"
    taskfile.write_text("# locally mutated\n")
    spec = target / "docs" / "specifications" / "prd.md"
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text("# My PRD\n")

    result = run_script(UPGRADE_SHELL, "--repo", str(target))
    assert result.returncode == 0, result.stderr

    assert taskfile.read_text() != "# locally mutated\n", "manifest file not refreshed"
    assert spec.read_text() == "# My PRD\n", "spec content must never be touched"


def test_upgrade_shell_recovers_domain_name_from_state(tmp_path: pathlib.Path) -> None:
    target = bootstrapped_repo(tmp_path)
    result = run_script(UPGRADE_SHELL, "--repo", str(target))
    assert result.returncode == 0, result.stderr
    # README was re-interpolated with the recorded name, not a blank.
    assert "Sample" in (target / "README.md").read_text()


def test_upgrade_shell_refuses_unbootstrapped_target(tmp_path: pathlib.Path) -> None:
    bare = tmp_path / "spec-bare"
    bare.mkdir()
    (bare / "keep.txt").write_text("not a spec repo\n")
    result = run_script(UPGRADE_SHELL, "--repo", str(bare))
    assert result.returncode != 0
    assert "doesn't look bootstrapped" in result.stderr


# ── reset_phase ───────────────────────────────────────────────────


def _sign_discovery(target: pathlib.Path) -> pathlib.Path:
    """Simulate a signed discovery phase: a PRD, a sidecar recording it,
    and progress marked passed."""
    prd = target / "docs" / "specifications" / "prd.md"
    prd.parent.mkdir(parents=True, exist_ok=True)
    prd.write_text("# PRD\n")

    sidecar = spec_paths.phase_sidecar_path(target, "discovery")
    sidecar.write_text(
        yaml.safe_dump(
            {
                "phase": "discovery",
                "files_signed": [{"path": "docs/specifications/prd.md", "sha256": "x"}],
            }
        )
    )

    progress_path = spec_paths.progress_path(target)
    progress = yaml.safe_load(progress_path.read_text())
    progress["phases"]["discovery"] = {"status": "passed"}
    progress_path.write_text(yaml.safe_dump(progress, sort_keys=False))
    return prd


def test_reset_phase_dry_run_changes_nothing(tmp_path: pathlib.Path) -> None:
    target = bootstrapped_repo(tmp_path)
    prd = _sign_discovery(target)

    result = run_script(RESET_PHASE, "discovery", "--repo", str(target))
    assert result.returncode == 0, result.stderr
    assert "dry run" in result.stdout
    assert prd.is_file()
    assert spec_paths.phase_sidecar_path(target, "discovery").is_file()
    progress = yaml.safe_load(spec_paths.progress_path(target).read_text())
    assert progress["phases"]["discovery"]["status"] == "passed"


def test_reset_phase_yes_deletes_and_marks_not_started(tmp_path: pathlib.Path) -> None:
    target = bootstrapped_repo(tmp_path)
    prd = _sign_discovery(target)

    result = run_script(RESET_PHASE, "discovery", "--repo", str(target), "--yes")
    assert result.returncode == 0, result.stderr
    assert not prd.exists(), "signed output must be deleted"
    assert not spec_paths.phase_sidecar_path(target, "discovery").exists()

    progress = yaml.safe_load(spec_paths.progress_path(target).read_text())
    assert progress["phases"]["discovery"] == {"status": "not-started"}
    assert any(
        e.get("event") == "phase-reset" and e.get("phase") == "discovery"
        for e in progress["session_log"]
    )


def test_reset_phase_refuses_bootstrap(tmp_path: pathlib.Path) -> None:
    target = bootstrapped_repo(tmp_path)
    result = run_script(RESET_PHASE, "bootstrap", "--repo", str(target), "--yes")
    assert result.returncode != 0
    assert "upgrade-shell" in result.stderr


def test_reset_phase_rejects_unknown_phase(tmp_path: pathlib.Path) -> None:
    target = bootstrapped_repo(tmp_path)
    result = run_script(RESET_PHASE, "not-a-phase", "--repo", str(target), "--yes")
    assert result.returncode != 0
    assert "unknown phase" in result.stderr
