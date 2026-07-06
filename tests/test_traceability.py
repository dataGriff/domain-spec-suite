"""Tests for scripts/generate_traceability.py (6.23C)."""

from __future__ import annotations

import pathlib
import shutil
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
ITEMS_FIXTURE = REPO / "tests" / "fixtures" / "items"

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts import generate_traceability  # noqa: E402


def test_items_fixture_renders_fully_covered(tmp_path: pathlib.Path) -> None:
    out = tmp_path / "traceability.html"
    exit_code = generate_traceability.main(["--repo", str(ITEMS_FIXTURE), "--output", str(out)])
    assert exit_code == 0
    html = out.read_text(encoding="utf-8")
    for sid in ("US-001", "US-002", "US-003", "US-004", "US-005", "US-006", "US-007"):
        assert sid in html, f"story {sid} missing from matrix"
    # Items is fully covered — no flags, nothing unexercised.
    assert "0</span> coverage flags" in html
    assert "0</span> unexercised surfaces" in html
    assert "Every operation and event channel" in html
    # Operations and events made it into the matrix.
    assert "POST /v1/items" in html
    assert "items.item.added" in html
    # Purpose banner + nav.
    assert "coverage dashboard" in html
    assert '<a href="../">&larr; Back to Docs</a>' in html


def test_reverse_coverage_flags_unexercised_surface(tmp_path: pathlib.Path) -> None:
    """An operation and a channel no scenario mentions land in the
    reverse-coverage section (informational — exit stays 0)."""
    import yaml

    target = tmp_path / "items"
    shutil.copytree(ITEMS_FIXTURE, target)

    openapi_path = target / "docs/specifications/contracts/openapi.yaml"
    doc = yaml.safe_load(openapi_path.read_text(encoding="utf-8"))
    doc["paths"]["/v1/items/export"] = {
        "get": {
            "operationId": "exportItems",
            "summary": "Export items",
            "responses": {"200": {"description": "ok"}},
        }
    }
    openapi_path.write_text(yaml.safe_dump(doc, sort_keys=False))

    asyncapi_path = target / "docs/specifications/contracts/asyncapi.yaml"
    adoc = yaml.safe_load(asyncapi_path.read_text(encoding="utf-8"))
    adoc["channels"]["items.item.exported"] = {"publish": {"message": {}}}
    asyncapi_path.write_text(yaml.safe_dump(adoc, sort_keys=False))

    out = tmp_path / "traceability.html"
    assert generate_traceability.main(["--repo", str(target), "--output", str(out)]) == 0
    html = out.read_text(encoding="utf-8")
    assert "GET /v1/items/export" in html
    assert "items.item.exported" in html
    assert "2</span> unexercised surfaces" in html


def test_uncovered_ac_status_is_flagged(tmp_path: pathlib.Path) -> None:
    """An AC that names a status code no scenario asserts produces an
    informational flag (not a failure — exit stays 0)."""
    target = tmp_path / "items"
    shutil.copytree(ITEMS_FIXTURE, target)

    prd = target / "docs/specifications/prd.md"
    text = prd.read_text()
    anchor = "#### US-007"
    assert anchor in text
    idx = text.find("**Acceptance Criteria:**", text.find(anchor))
    assert idx > 0
    text = (
        text[:idx]
        + "**Acceptance Criteria:**\n- [ ] Returns 418 when the item is a teapot\n"
        + text[idx + len("**Acceptance Criteria:**") :]
    )
    prd.write_text(text)

    out = tmp_path / "traceability.html"
    exit_code = generate_traceability.main(["--repo", str(target), "--output", str(out)])
    assert exit_code == 0
    html = out.read_text(encoding="utf-8")
    assert "AC mentions 418" in html


def test_story_with_no_scenarios_is_flagged(tmp_path: pathlib.Path) -> None:
    target = tmp_path / "items"
    shutil.copytree(ITEMS_FIXTURE, target)

    prd = target / "docs/specifications/prd.md"
    text = prd.read_text()
    stories_idx = text.find("## User Stories")
    next_section = text.find("\n## ", stories_idx + len("## User Stories"))
    new_story = (
        "\n#### US-997: Bulk import\n\n"
        "**As a** Stockroom Lead,\n"
        "**I want to** import items in bulk,\n"
        "**So that** onboarding is fast.\n\n"
        "**Acceptance Criteria:**\n- [ ] Import completes\n"
    )
    prd.write_text(text[:next_section] + new_story + text[next_section:])

    out = tmp_path / "traceability.html"
    assert generate_traceability.main(["--repo", str(target), "--output", str(out)]) == 0
    assert "no scenarios" in out.read_text(encoding="utf-8")
