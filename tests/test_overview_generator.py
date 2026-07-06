"""Tests for the gate-1.4 overview-generator fidelity improvements:
correlation from the domain model's Domain Events triggers, ERD edges
from declared aggregates."""

from __future__ import annotations

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
ITEMS_FIXTURE = REPO / "tests" / "fixtures" / "items"

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.generate_domain_overview import (  # noqa: E402
    build_enumerations_section,
    build_erd_section,
    build_event_operation_correlation,
    build_page,
    load_yaml,
)
from shared.spec_parsers import domain_model_events  # noqa: E402


def _contracts():
    contracts = ITEMS_FIXTURE / "docs" / "specifications" / "contracts"
    return load_yaml(contracts / "openapi.yaml"), load_yaml(contracts / "asyncapi.yaml")


def test_correlation_uses_model_triggers_for_non_crud_channels() -> None:
    """items.user.registered has no added/edited/removed suffix, so the
    old heuristic left it unmapped; the model's trigger column maps it."""
    openapi, asyncapi = _contracts()
    events = domain_model_events(ITEMS_FIXTURE / "docs" / "specifications" / "domain-model.md")

    with_model = build_event_operation_correlation(openapi, asyncapi, events)
    assert "/v1/auth/register" in with_model

    heuristic_only = build_event_operation_correlation(openapi, asyncapi, None)
    assert "/v1/auth/register" not in heuristic_only
    # CRUD-suffixed channels still map without the model.
    assert "/v1/items" in heuristic_only


def test_page_has_purpose_banner_and_fixed_nav() -> None:
    openapi, asyncapi = _contracts()
    contracts = ITEMS_FIXTURE / "docs" / "specifications" / "contracts"
    page = build_page(openapi, asyncapi, load_yaml(contracts / "datacontract.yaml"))
    # Back link goes to the site root, not a nonexistent sibling index.html.
    assert '<a href="../">&larr; Back to Docs</a>' in page
    assert "./index.html" not in page
    # Sibling generated views are reachable from the nav.
    assert "./traceability.html" in page
    assert "./datacontract-reference.html" in page
    # Purpose banner states the derived-never-authoritative contract.
    assert "never\n  authoritative" in page or "never authoritative" in page.replace("\n  ", " ")


def test_enumerations_use_model_open_flag_and_authority_notes() -> None:
    openapi = {
        "components": {
            "schemas": {
                # Small value count — the old heuristic would call this closed.
                "Breed": {"type": "string", "enum": ["labrador", "mixed", "unknown"]},
                "Status": {"type": "string", "enum": ["active", "archived"]},
            }
        }
    }
    model_enums = {"Breed": {"values": ["labrador"], "open": True}}
    section = build_enumerations_section(openapi, model_enums)
    # Declared open beats the value-count heuristic.
    assert section.count("enum-open") == 1
    assert "full list is\nauthoritative".replace("\n", " ") in section.replace("\n", " ")
    # Undeclared enum falls back to heuristic → closed, with the match note.
    assert "matches the domain\nmodel exactly".replace("\n", " ") in section.replace("\n", " ")


def test_erd_declares_aggregate_containment_edges_and_dedupes_heuristic() -> None:
    # Synthetic contract: Walk.walkerId means the heuristic would emit
    # Walker→Walk "owns"; the declared aggregate emits Walker→Walk
    # "contains" first and the heuristic edge is deduplicated.
    openapi = {
        "components": {
            "schemas": {
                "Walker": {"properties": {"id": {"type": "string"}}},
                "Walk": {
                    "properties": {
                        "id": {"type": "string"},
                        "walkerId": {"type": "string"},
                    }
                },
            }
        }
    }
    aggregates = {"Walker": [{"child": "Walk", "collection": "walks"}]}

    section = build_erd_section(openapi, aggregates)
    assert 'Walker ||--o{ Walk : "contains"' in section
    assert section.count("Walker ||--o{ Walk") == 1

    # Without the declaration, the heuristic edge appears instead.
    heuristic = build_erd_section(openapi, None)
    assert 'Walker ||--o{ Walk : "owns"' in heuristic

    # A declared aggregate whose entities lack schemas emits nothing.
    ghost = build_erd_section(openapi, {"Ghost": [{"child": "Walk", "collection": "x"}]})
    assert "Ghost" not in ghost
