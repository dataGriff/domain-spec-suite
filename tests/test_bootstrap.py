"""Tests for the domain-bootstrap skill (BUILD-PLAN Task 2.2)."""

from __future__ import annotations

import hashlib
import pathlib
import stat
import subprocess
import sys

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from shared import spec_paths  # noqa: E402

BOOTSTRAP = REPO / "scripts" / "bootstrap.py"
TEMPLATES_DIR = REPO / "skills" / "domain-bootstrap" / "templates"
MANIFEST = yaml.safe_load(
    (REPO / "skills" / "domain-bootstrap" / "template_manifest.yaml").read_text()
)

pytestmark = pytest.mark.bootstrap


def run_bootstrap(*args: str) -> subprocess.CompletedProcess:
    """Invoke the bootstrap script as a subprocess and return the result."""
    return subprocess.run(
        [sys.executable, str(BOOTSTRAP), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def spec_target(tmp_path: pathlib.Path, name: str = "spec-sample") -> pathlib.Path:
    """Create and return a spec-prefixed subdirectory under tmp_path.
    Bootstrap refuses non-prefixed targets unless --allow-non-prefix
    is passed, so every test that doesn't specifically test that flag
    needs a prefixed target."""
    target = tmp_path / name
    target.mkdir()
    return target


# ── manifest integrity ────────────────────────────────────────────


def test_manifest_matches_templates_dir() -> None:
    """Every file under templates/ appears in the manifest with the
    correct sha256, and nothing in the manifest is missing on disk.
    Regenerate with `task suite:regenerate-manifest` if this fails."""
    on_disk = {
        p.relative_to(TEMPLATES_DIR).as_posix()
        for p in TEMPLATES_DIR.rglob("*")
        if p.is_file() and p.name != ".gitkeep"
    }
    in_manifest = {e["path"] for e in MANIFEST["files"]}
    assert on_disk == in_manifest, (
        f"templates/ contents diverge from manifest:\n"
        f"  only on disk:    {on_disk - in_manifest}\n"
        f"  only in manifest: {in_manifest - on_disk}"
    )
    for entry in MANIFEST["files"]:
        src = TEMPLATES_DIR / entry["path"]
        assert sha256(src) == entry["sha256"], f"manifest sha256 stale for {entry['path']}"


# ── happy path: empty dir ─────────────────────────────────────────


def test_bootstrap_in_empty_dir_succeeds(tmp_path: pathlib.Path) -> None:
    target = spec_target(tmp_path)
    result = run_bootstrap(
        "--target",
        str(target),
        "--domain-name",
        "Sample",
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "Bootstrap complete" in result.stdout

    # Every manifest file landed at its destination (with .template stripped).
    for entry in MANIFEST["files"]:
        dst_rel = entry["path"]
        if dst_rel.endswith(".template"):
            dst_rel = dst_rel[: -len(".template")]
        assert (target / dst_rel).is_file(), f"missing: {dst_rel}"

    # State files exist and parse.
    progress = yaml.safe_load(spec_paths.progress_path(target).read_text())
    bootstrap_record = yaml.safe_load(spec_paths.bootstrap_path(target).read_text())
    template_manifest = yaml.safe_load(spec_paths.template_manifest_path(target).read_text())

    assert progress["domain_name"] == "Sample"
    assert progress["phases"]["bootstrap"]["status"] == "passed"
    assert progress["force_advances"] == []
    assert bootstrap_record["domain_name"] == "Sample"
    assert template_manifest["files"]  # mirror of the suite's manifest


def test_bootstrap_substitutes_placeholders(tmp_path: pathlib.Path) -> None:
    target = spec_target(tmp_path)
    result = run_bootstrap(
        "--target",
        str(target),
        "--domain-name",
        "Catalogue",
    )
    assert result.returncode == 0, result.stderr

    readme = (target / "README.md").read_text()
    assert "Catalogue" in readme
    assert "{{domain_name}}" not in readme

    index = (target / "docs" / "index.md").read_text()
    assert "Catalogue" in index
    assert "{{" not in index

    mkdocs = (target / "mkdocs.yml").read_text()
    assert "Catalogue" in mkdocs
    assert "{{" not in mkdocs


def test_bootstrap_preserves_executable_bit_on_hooks(tmp_path: pathlib.Path) -> None:
    target = spec_target(tmp_path)
    result = run_bootstrap(
        "--target",
        str(target),
        "--domain-name",
        "Sample",
    )
    assert result.returncode == 0, result.stderr

    for hook in (".githooks/pre-commit", ".githooks/pre-push"):
        mode = (target / hook).stat().st_mode
        assert mode & stat.S_IXUSR, f"{hook} not executable for user"


def test_bootstrap_phase_0_gate_present(tmp_path: pathlib.Path) -> None:
    """Sign-off claims four named checks passed."""
    target = spec_target(tmp_path)
    result = run_bootstrap(
        "--target",
        str(target),
        "--domain-name",
        "Sample",
    )
    assert result.returncode == 0
    for check in (
        "BOOTSTRAP-FILES-EXIST",
        "BOOTSTRAP-FILES-PARSE",
        "BOOTSTRAP-PROGRESS-INITIALIZED",
        "BOOTSTRAP-MANIFEST-PRESENT",
    ):
        assert check in result.stdout


# ── non-empty target: refuses by default ──────────────────────────


def test_bootstrap_refuses_on_non_empty_without_force(tmp_path: pathlib.Path) -> None:
    target = spec_target(tmp_path)
    (target / "user-file.txt").write_text("hand-authored content\n")

    result = run_bootstrap(
        "--target",
        str(target),
        "--domain-name",
        "Sample",
    )
    assert result.returncode == 1
    assert "non-empty" in result.stderr
    assert "--force" in result.stderr
    # Should not have written anything else.
    assert {p.name for p in target.iterdir()} == {"user-file.txt"}


def test_bootstrap_force_refreshes_manifest_files(tmp_path: pathlib.Path) -> None:
    """First bootstrap; mutate a manifest file and a spec file; --force
    restores the manifest file but leaves the spec file alone."""
    target = spec_target(tmp_path)
    assert (
        run_bootstrap(
            "--target",
            str(target),
            "--domain-name",
            "Sample",
        ).returncode
        == 0
    )

    # Mutate a manifest-owned file.
    taskfile = target / "Taskfile.yml"
    original_taskfile = taskfile.read_text()
    taskfile.write_text("# tampered\n")

    # Drop a user-authored spec file that isn't in the manifest.
    user_spec = target / "docs" / "specifications" / "prd.md"
    user_spec.parent.mkdir(parents=True, exist_ok=True)
    user_spec.write_text("# my domain PRD\n")

    # Also mutate a state file — should also survive --force.
    progress = spec_paths.progress_path(target)
    original_progress = progress.read_text()

    result = run_bootstrap(
        "--target",
        str(target),
        "--domain-name",
        "Sample",
        "--force",
    )
    assert result.returncode == 0, result.stderr

    # Manifest file restored.
    assert taskfile.read_text() == original_taskfile
    # User spec untouched.
    assert user_spec.read_text() == "# my domain PRD\n"
    # State file preserved as-is (not rewritten on --force).
    assert progress.read_text() == original_progress, (
        "state files must survive --force without being clobbered"
    )


# ── error handling ────────────────────────────────────────────────


def test_bootstrap_missing_target_directory_errors(tmp_path: pathlib.Path) -> None:
    nonexistent = tmp_path / "spec-does-not-exist"
    result = run_bootstrap(
        "--target",
        str(nonexistent),
        "--domain-name",
        "Sample",
    )
    assert result.returncode == 1
    assert "does not exist" in result.stderr


def test_bootstrap_requires_domain_name(tmp_path: pathlib.Path) -> None:
    target = spec_target(tmp_path)
    result = run_bootstrap("--target", str(target))
    assert result.returncode != 0
    assert "--domain-name" in result.stderr


# ── spec- prefix enforcement (v1.0.1 backlog) ─────────────────────


def test_bootstrap_refuses_non_prefixed_target(tmp_path: pathlib.Path) -> None:
    """A target dir whose name doesn't start with `spec-` is rejected
    with a clear message pointing at the convention and the --allow-
    non-prefix escape."""
    target = tmp_path / "dog-walking"  # no spec- prefix
    target.mkdir()

    result = run_bootstrap("--target", str(target), "--domain-name", "DogWalking")
    assert result.returncode == 1
    assert "spec-" in result.stderr
    assert "--allow-non-prefix" in result.stderr
    # No files written.
    assert list(target.iterdir()) == []


def test_bootstrap_allow_non_prefix_bypass(tmp_path: pathlib.Path) -> None:
    """`--allow-non-prefix` bypasses the convention for legacy targets."""
    target = tmp_path / "legacy-domain"
    target.mkdir()

    result = run_bootstrap(
        "--target",
        str(target),
        "--domain-name",
        "Legacy",
        "--allow-non-prefix",
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert (target / "README.md").is_file()


def test_bootstrap_force_preserves_progress_yaml(tmp_path: pathlib.Path) -> None:
    """--force must NOT clobber progress.yaml, bootstrap.yaml,
    ambiguities.md, or phase-0-passed.yaml. These accumulate user
    state (phase progress, force-advance entries, ambiguity log,
    decisions) and a shell refresh shouldn't wipe them."""
    target = spec_target(tmp_path)
    first = run_bootstrap("--target", str(target), "--domain-name", "Sample")
    assert first.returncode == 0

    # Simulate state accumulation: mark discovery as passed in progress
    # and add an ambiguity.
    progress_path = spec_paths.progress_path(target)
    progress = yaml.safe_load(progress_path.read_text())
    progress["phases"]["discovery"] = {
        "status": "passed",
        "signed_off_at": "2026-01-01T00:00:00Z",
        "gate_version": "1.0",
    }
    progress_path.write_text(yaml.safe_dump(progress))

    ambig_path = spec_paths.ambiguities_path(target)
    ambig_path.write_text(
        "# Open Ambiguities\n\n## Deferred to: audit\n\n"
        "### ITEM-001: tax handling\n- Recorded in phase: nfrs\n"
    )

    # Re-bootstrap --force; state should survive.
    result = run_bootstrap("--target", str(target), "--domain-name", "Sample", "--force")
    assert result.returncode == 0, result.stderr

    progress_after = yaml.safe_load(progress_path.read_text())
    assert progress_after["phases"]["discovery"]["status"] == "passed", (
        "--force clobbered discovery phase status — state files must be preserved"
    )
    assert "ITEM-001" in ambig_path.read_text(), "--force clobbered ambiguities.md"
