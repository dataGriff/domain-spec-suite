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
