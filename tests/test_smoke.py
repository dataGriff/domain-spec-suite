"""Smoke tests for the suite repo scaffolding (BUILD-PLAN Task 2.1).

These confirm the marker files and directory structure that every later
milestone assumes are present. They do not exercise any skill logic —
that arrives in M2.2 onward.
"""

from __future__ import annotations

import pathlib

import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent


def test_design_and_plan_docs_present() -> None:
    assert (REPO / "SUITE-DESIGN.md").is_file()
    assert (REPO / "BUILD-PLAN.md").is_file()


def test_version_files_parse() -> None:
    suite = yaml.safe_load((REPO / "suite-version.yaml").read_text())
    gate = yaml.safe_load((REPO / "gate-version.yaml").read_text())
    assert suite["suite_version"]
    assert gate["gate_version"]


def test_gate_version_has_changelog_entry() -> None:
    """SUITE-DESIGN §10: the suite refuses to release a new gate
    version without a matching gate-changelog.md entry. This is the
    mechanical refusal — bumping gate-version.yaml without writing the
    changelog heading fails CI."""
    gate = yaml.safe_load((REPO / "gate-version.yaml").read_text())
    changelog = (REPO / "gate-changelog.md").read_text()
    heading = f"## `{gate['gate_version']}`"
    assert heading in changelog, (
        f"gate-version.yaml says {gate['gate_version']!r} but gate-changelog.md "
        f"has no {heading!r} heading — write the changelog entry before bumping "
        "(SUITE-DESIGN §10)"
    )


def test_template_manifest_versions_match_live_version_files() -> None:
    """The bootstrap manifest embeds the suite/gate versions it was
    generated under. If they drift from the live version files, the
    manifest needs regenerating (`python scripts/regenerate_manifest.py`)."""
    manifest = yaml.safe_load(
        (REPO / "skills" / "domain-bootstrap" / "template_manifest.yaml").read_text()
    )
    suite = yaml.safe_load((REPO / "suite-version.yaml").read_text())
    gate = yaml.safe_load((REPO / "gate-version.yaml").read_text())
    assert manifest["suite_version"] == suite["suite_version"]
    assert manifest["gate_version"] == gate["gate_version"]


def test_skills_directories_exist() -> None:
    expected = {
        "domain-orchestrator",
        "domain-bootstrap",
        "domain-discovery",
        "domain-modeling",
        "domain-access-control",
        "domain-flows",
        "domain-nfrs",
        "domain-contracts",
        "domain-openapi",
        "domain-asyncapi",
        "domain-datacontract",
        "domain-conformance-audit",
    }
    found = {p.name for p in (REPO / "skills").iterdir() if p.is_dir()}
    assert expected <= found, f"missing skill directories: {expected - found}"


def test_supporting_directories_exist() -> None:
    for path in ("shared/checks", "tests/fixtures", "scripts", "docs"):
        assert (REPO / path).is_dir(), f"missing directory: {path}"


def test_taskfile_lists_canonical_targets() -> None:
    taskfile = (REPO / "Taskfile.yml").read_text()
    for target in (
        "setup:",
        "lint:",
        "test:",
        "test:bootstrap:",
        "test:audit:",
        "fixtures:seed-signoffs:",
        "suite:force-advance:",
        "suite:accept-force:",
        "suite:upgrade-shell:",
        "suite:reset-phase:",
    ):
        assert target in taskfile, f"Taskfile missing target: {target}"
