"""Tests for soft-gate enforcement in shared/sign_off.py (M5.0).

The sign_off script must:
- REFUSE when a soft-gate phase has warnings but no responses
- REFUSE when warnings_responded references warnings that didn't fire
- REFUSE when a response is not one of resolved | deferred | n-a
- REFUSE when a deferred response is missing required_by
- ACCEPT when every fired warning has a valid response
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

from shared import sign_off  # noqa: E402

pytestmark = pytest.mark.soft_gate


def _copy_fixture(tmp_path: pathlib.Path) -> pathlib.Path:
    target = tmp_path / "items"
    shutil.copytree(ITEMS_FIXTURE, target)
    return target


def _sidecar(repo: pathlib.Path) -> pathlib.Path:
    # Phase 2 (modeling) sidecar.
    return repo / "docs/specifications/_phase-2-passed.yaml"


def test_soft_gate_refuses_when_warning_has_no_response(tmp_path: pathlib.Path) -> None:
    """Items fixture's modeling gate emits one warning (User has no
    `updatedAt`). sign_off must refuse if warnings_responded is empty."""
    target = _copy_fixture(tmp_path)
    sidecar = _sidecar(target)
    sidecar.unlink()

    rc = sign_off.sign_off("modeling", target)  # no warnings_responded
    assert rc == 1, "sign_off must refuse when warnings have no response"
    assert not sidecar.exists()


def test_soft_gate_accepts_resolved_warning(tmp_path: pathlib.Path) -> None:
    """A warning marked `resolved` passes the engagement check."""
    target = _copy_fixture(tmp_path)
    sidecar = _sidecar(target)
    sidecar.unlink()

    rc = sign_off.sign_off(
        "modeling",
        target,
        warnings_responded=[
            {
                "id": "MODEL-ENTITY-HAS-ID-TIMESTAMPS",
                "response": "n-a",
                "reason": "User has no updateable fields in v1",
            }
        ],
    )
    assert rc == 0
    assert sidecar.exists()
    doc = yaml.safe_load(sidecar.read_text())
    assert len(doc["warnings_responded"]) == 1
    assert doc["warnings_responded"][0]["id"] == "MODEL-ENTITY-HAS-ID-TIMESTAMPS"


def test_soft_gate_refuses_stale_response(tmp_path: pathlib.Path) -> None:
    """A response for a warning that didn't fire is rejected."""
    target = _copy_fixture(tmp_path)
    sidecar = _sidecar(target)
    sidecar.unlink()

    rc = sign_off.sign_off(
        "modeling",
        target,
        warnings_responded=[
            {
                "id": "MODEL-ENTITY-HAS-ID-TIMESTAMPS",
                "response": "n-a",
                "reason": "User v1",
            },
            {
                "id": "MODEL-NEVER-FIRED",
                "response": "resolved",
                "reason": "stale leftover",
            },
        ],
    )
    assert rc == 1


def test_soft_gate_refuses_invalid_response_value(tmp_path: pathlib.Path) -> None:
    """`response` must be one of resolved | deferred | n-a."""
    target = _copy_fixture(tmp_path)
    sidecar = _sidecar(target)
    sidecar.unlink()

    rc = sign_off.sign_off(
        "modeling",
        target,
        warnings_responded=[
            {
                "id": "MODEL-ENTITY-HAS-ID-TIMESTAMPS",
                "response": "fixed-it",  # invalid
                "reason": "...",
            }
        ],
    )
    assert rc == 1


def test_soft_gate_refuses_deferred_without_required_by(tmp_path: pathlib.Path) -> None:
    """`deferred` responses must declare `required_by`."""
    target = _copy_fixture(tmp_path)
    sidecar = _sidecar(target)
    sidecar.unlink()

    rc = sign_off.sign_off(
        "modeling",
        target,
        warnings_responded=[
            {
                "id": "MODEL-ENTITY-HAS-ID-TIMESTAMPS",
                "response": "deferred",
                "reason": "...",
                # missing required_by
            }
        ],
    )
    assert rc == 1


def test_soft_gate_accepts_deferred_with_required_by(tmp_path: pathlib.Path) -> None:
    target = _copy_fixture(tmp_path)
    sidecar = _sidecar(target)
    sidecar.unlink()

    rc = sign_off.sign_off(
        "modeling",
        target,
        warnings_responded=[
            {
                "id": "MODEL-ENTITY-HAS-ID-TIMESTAMPS",
                "response": "deferred",
                "reason": "schema review pending",
                "required_by": "audit",
            }
        ],
    )
    assert rc == 0
