"""Tests for the domain-contracts skill and the sign_off + force-advance
machinery (BUILD-PLAN Milestone 3).

Covers the M3.1 + M3.2 exit criteria:
- Contracts gate passes cleanly against the Items fixture.
- sign_off REFUSES to write the sidecar when the gate fails.
- sign_off WITH --force-advance writes the sidecar AND records an
  unaccepted entry in _progress.yaml.
- accept_force flips the entry to accepted: true.
- After a force-advance, the audit's FORCE-ADVANCES-ALL-ACCEPTED
  check fails until accept_force runs.
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

from scripts import accept_force, force_advance  # noqa: E402
from shared import run_phase, sign_off  # noqa: E402

pytestmark = pytest.mark.contracts


# ── helpers ──────────────────────────────────────────────────────


def _copy_fixture(tmp_path: pathlib.Path) -> pathlib.Path:
    target = tmp_path / "items"
    shutil.copytree(ITEMS_FIXTURE, target)
    return target


def _progress(repo: pathlib.Path) -> dict:
    return yaml.safe_load((repo / "docs/specifications/_progress.yaml").read_text())


def _sidecar_path(repo: pathlib.Path, phase: str = "contracts") -> pathlib.Path:
    return repo / "docs/specifications/_phase-6-passed.yaml"


# ── gate against the fixture ─────────────────────────────────────


def test_contracts_gate_passes_against_items_fixture() -> None:
    """The fixture's contracts must validate cleanly under the
    contracts gate. Tool checks (Spectral, datacontract) may skip if
    their binaries aren't on PATH; cross-reference checks always run."""
    exit_code, outcomes = run_phase.run_phase("contracts", ITEMS_FIXTURE)
    failures = [o for o in outcomes if not o.passed and not o.skipped]
    assert exit_code == 0, "contracts gate failed against the Items fixture:\n" + "\n".join(
        f"  {f.id}: {f.message}" for f in failures
    )
    assert failures == []


# ── sign_off mechanical enforcement ──────────────────────────────


def test_sign_off_writes_sidecar_on_passing_gate(tmp_path: pathlib.Path) -> None:
    target = _copy_fixture(tmp_path)
    sidecar = _sidecar_path(target)
    sidecar.unlink()  # remove fixture's pre-existing sidecar

    rc = sign_off.sign_off("contracts", target)
    assert rc == 0
    assert sidecar.is_file(), "sign_off must write the sidecar on a passing gate"

    doc = yaml.safe_load(sidecar.read_text())
    assert doc["phase"] == "contracts"
    assert doc["gate_version"]
    paths_signed = {entry["path"] for entry in doc["files_signed"]}
    assert paths_signed == {
        "docs/specifications/contracts/openapi.yaml",
        "docs/specifications/contracts/asyncapi.yaml",
        "docs/specifications/contracts/datacontract.yaml",
    }


def test_sign_off_refuses_when_gate_fails(tmp_path: pathlib.Path) -> None:
    """Deliberately break a contract; sign_off must refuse to write
    the sidecar."""
    target = _copy_fixture(tmp_path)
    sidecar = _sidecar_path(target)
    sidecar.unlink()  # pristine start

    # Break: remove the ItemAdded channel — WRITE-OP-HAS-ASYNCAPI-CHANNEL fails
    asyncapi_path = target / "docs/specifications/contracts/asyncapi.yaml"
    asyncapi = yaml.safe_load(asyncapi_path.read_text())
    asyncapi["channels"].pop("items.item.added")
    asyncapi_path.write_text(yaml.safe_dump(asyncapi, sort_keys=False))

    rc = sign_off.sign_off("contracts", target)
    assert rc == 1, "sign_off must return non-zero when the gate fails"
    assert not sidecar.exists(), (
        "sign_off must NOT write the sidecar when the gate fails — "
        "this is the load-bearing mechanical-enforcement promise"
    )


def test_sign_off_force_advance_writes_sidecar_and_records_bypass(tmp_path: pathlib.Path) -> None:
    """`sign_off --force-advance --reason 'X'` MUST write the sidecar
    even when the gate is failing, but MUST also append an entry to
    `_progress.yaml`'s force_advances[] with accepted: false."""
    target = _copy_fixture(tmp_path)
    sidecar = _sidecar_path(target)
    sidecar.unlink()

    # Break the contracts: same as above
    asyncapi_path = target / "docs/specifications/contracts/asyncapi.yaml"
    asyncapi = yaml.safe_load(asyncapi_path.read_text())
    asyncapi["channels"].pop("items.item.added")
    asyncapi_path.write_text(yaml.safe_dump(asyncapi, sort_keys=False))

    rc = sign_off.sign_off(
        "contracts",
        target,
        force_advance="spectral upstream regression — engaging vendor",
    )
    assert rc == 0
    assert sidecar.is_file(), "force-advance sign_off must write the sidecar"

    progress = _progress(target)
    entries = progress.get("force_advances", [])
    assert len(entries) == 1, f"expected one force_advances entry, got {entries}"
    entry = entries[0]
    assert entry["phase"] == "contracts"
    assert "vendor" in entry["reason"]
    assert entry["accepted"] is False


# ── force-advance / accept-force scripts ─────────────────────────


def test_force_advance_appends_entry(tmp_path: pathlib.Path) -> None:
    target = _copy_fixture(tmp_path)
    rc = force_advance.force_advance(target, "contracts", "smoke test")
    assert rc == 0
    entries = _progress(target).get("force_advances", [])
    assert len(entries) == 1
    assert entries[0]["phase"] == "contracts"
    assert entries[0]["accepted"] is False


def test_accept_force_flips_most_recent_entry(tmp_path: pathlib.Path) -> None:
    target = _copy_fixture(tmp_path)
    force_advance.force_advance(target, "contracts", "first")
    force_advance.force_advance(target, "contracts", "second")

    rc = accept_force.accept_force(target, "contracts", "reviewed by ops")
    assert rc == 0

    entries = _progress(target).get("force_advances", [])
    assert len(entries) == 2
    # First entry untouched
    assert entries[0]["accepted"] is False
    # Second (most recent) entry flipped
    assert entries[1]["accepted"] is True
    assert entries[1]["accepted_reason"] == "reviewed by ops"
    assert entries[1]["accepted_at"]


def test_accept_force_errors_when_no_unaccepted_entry(tmp_path: pathlib.Path) -> None:
    target = _copy_fixture(tmp_path)
    rc = accept_force.accept_force(target, "contracts", "nothing to accept")
    assert rc == 1


# ── integration: force-advance → audit fails → accept-force → audit passes ──


def test_force_advance_round_trip_through_audit(tmp_path: pathlib.Path) -> None:
    target = _copy_fixture(tmp_path)

    # 1. Record a force-advance.
    force_advance.force_advance(target, "contracts", "upstream bug")

    # 2. Audit fails on FORCE-ADVANCES-ALL-ACCEPTED.
    exit_code, outcomes = run_phase.run_phase("audit", target)
    assert exit_code != 0
    failing = [o for o in outcomes if not o.passed and not o.skipped]
    assert any(o.id == "FORCE-ADVANCES-ALL-ACCEPTED" for o in failing), (
        f"expected FORCE-ADVANCES-ALL-ACCEPTED to fail; got: {[o.id for o in failing]}"
    )

    # 3. Accept the entry.
    accept_force.accept_force(target, "contracts", "reviewed")

    # 4. Audit passes again.
    exit_code, _ = run_phase.run_phase("audit", target)
    assert exit_code == 0
