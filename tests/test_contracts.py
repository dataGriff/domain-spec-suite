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

from scripts import accept_force, force_advance, init_phase  # noqa: E402
from shared import run_phase, sign_off  # noqa: E402

pytestmark = pytest.mark.contracts


# ── helpers ──────────────────────────────────────────────────────


def _copy_fixture(tmp_path: pathlib.Path) -> pathlib.Path:
    target = tmp_path / "items"
    shutil.copytree(ITEMS_FIXTURE, target)
    return target


def _progress(repo: pathlib.Path) -> dict:
    from shared import spec_paths

    return yaml.safe_load(spec_paths.progress_path(repo).read_text())


def _sidecar_path(repo: pathlib.Path, phase: str = "contracts") -> pathlib.Path:
    from shared import spec_paths

    return spec_paths.phase_sidecar_path(repo, phase)


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


def test_enum_values_consistent_catches_openapi_drift(tmp_path: pathlib.Path) -> None:
    """Adding a `## Enumerations` section to the model without a
    matching OpenAPI schema must fail ENUM-VALUES-CONSISTENT."""
    from shared.checks import enum_values_consistent

    target = _copy_fixture(tmp_path)
    model = target / "docs/specifications/domain-model.md"
    model.write_text(
        model.read_text() + "\n\n## Enumerations\n\n### Breed\n\n"
        "| Value | Notes |\n|---|---|\n| `labrador` | |\n| `poodle` | |\n",
        encoding="utf-8",
    )

    result = enum_values_consistent.run(target)
    assert not result.passed
    assert any("Breed" in d and "missing from OpenAPI" in d for d in result.details)


def test_event_payload_check_catches_thin_asyncapi(tmp_path: pathlib.Path) -> None:
    """Removing a required attribute from the AsyncAPI message
    payload makes EVENT-PAYLOAD-COVERS-ENTITY-STATE fail with a
    clear (entity, field, edge) breadcrumb."""
    from shared.checks import event_payload_covers_entity_state

    target = _copy_fixture(tmp_path)
    asyncapi_path = target / "docs/specifications/contracts/asyncapi.yaml"
    doc = yaml.safe_load(asyncapi_path.read_text())
    # Drop `description` from ItemData (Item entity has it; payload was carrying it).
    doc["components"]["schemas"]["ItemData"]["properties"].pop("description")
    asyncapi_path.write_text(yaml.safe_dump(doc, sort_keys=False))

    result = event_payload_covers_entity_state.run(target)
    assert not result.passed
    assert any("Item.description" in d and "AsyncAPI" in d for d in result.details), result.details


def test_event_payload_check_catches_thin_datacontract(tmp_path: pathlib.Path) -> None:
    """Same shape, this time the datacontract record drops a field
    the model declares."""
    from shared.checks import event_payload_covers_entity_state

    target = _copy_fixture(tmp_path)
    dc_path = target / "docs/specifications/contracts/datacontract.yaml"
    doc = yaml.safe_load(dc_path.read_text())
    items_record = next(r for r in doc["schema"] if r["name"] == "items")
    items_record["properties"] = [
        p for p in items_record["properties"] if p["name"] != "description"
    ]
    dc_path.write_text(yaml.safe_dump(doc, sort_keys=False))

    result = event_payload_covers_entity_state.run(target)
    assert not result.passed
    assert any("Item.description" in d and "datacontract" in d for d in result.details), (
        result.details
    )


def test_event_payload_check_catches_asyncapi_datacontract_divergence(
    tmp_path: pathlib.Path,
) -> None:
    """Adding a field only to the datacontract record (without
    adding it to the AsyncAPI payload) is caught by the
    asyncapi-vs-datacontract edge."""
    from shared.checks import event_payload_covers_entity_state

    target = _copy_fixture(tmp_path)
    dc_path = target / "docs/specifications/contracts/datacontract.yaml"
    doc = yaml.safe_load(dc_path.read_text())
    items_record = next(r for r in doc["schema"] if r["name"] == "items")
    items_record["properties"].append(
        {"name": "extraField", "logicalType": "string", "required": False}
    )
    dc_path.write_text(yaml.safe_dump(doc, sort_keys=False))

    result = event_payload_covers_entity_state.run(target)
    assert not result.passed
    assert any("extraField" in d and "AsyncAPI payload does not" in d for d in result.details), (
        result.details
    )


def test_event_payload_check_respects_secret_marker(tmp_path: pathlib.Path) -> None:
    """An attribute marked `[secret]` in the model's Description
    column is exempt — the check doesn't complain when it's absent
    from the AsyncAPI payload or datacontract record."""
    from shared.checks import event_payload_covers_entity_state

    target = _copy_fixture(tmp_path)
    model = target / "docs/specifications/domain-model.md"
    # Tag `Item.description` as [secret] — should be exempt from the
    # event-payload requirement.
    text = model.read_text()
    text = text.replace(
        "| `description`",
        "| `description`",  # leave name unchanged; munge the Description column
    )
    # Find the description row and inject [secret] into its description cell.
    import re

    text = re.sub(
        r"(\|\s*`description`\s*\|[^|]*\|[^|]*\|)([^|\n]*)",
        r"\1 [secret]\2",
        text,
        count=1,
    )
    model.write_text(text)

    # Now also drop `description` from both AsyncAPI + datacontract.
    asyncapi_path = target / "docs/specifications/contracts/asyncapi.yaml"
    a = yaml.safe_load(asyncapi_path.read_text())
    a["components"]["schemas"]["ItemData"]["properties"].pop("description")
    asyncapi_path.write_text(yaml.safe_dump(a, sort_keys=False))

    dc_path = target / "docs/specifications/contracts/datacontract.yaml"
    d = yaml.safe_load(dc_path.read_text())
    items_record = next(r for r in d["schema"] if r["name"] == "items")
    items_record["properties"] = [
        p for p in items_record["properties"] if p["name"] != "description"
    ]
    dc_path.write_text(yaml.safe_dump(d, sort_keys=False))

    result = event_payload_covers_entity_state.run(target)
    assert result.passed, (
        f"[secret]-marked field should not be required in events. details: {result.details}"
    )


def _add_item_tag_aggregate(target: pathlib.Path) -> None:
    """Mutate the copied Items fixture to declare an Item → ItemTag
    aggregate (collection `tags`) and add a well-formed asyncapi +
    datacontract carrying it. Used as the pass-case baseline for
    aggregate-coverage tests; failure tests further mutate from
    here."""
    model = target / "docs/specifications/domain-model.md"
    text = model.read_text()
    # Add ItemTag entity under ## Entities (before ## Relationships).
    item_tag_entity = (
        "### ItemTag\n\n"
        "A short label attached to an Item.\n\n"
        "| Attribute | Type | Required | Description |\n"
        "|-----------|------|----------|-------------|\n"
        "| `id` | UUID | Yes | Unique identifier |\n"
        "| `itemId` | UUID | Yes | FK to parent Item |\n"
        "| `label` | string | Yes | The tag text |\n\n"
        "---\n\n"
    )
    text = text.replace("## Relationships", item_tag_entity + "## Relationships", 1)
    # Append ## Aggregates section after Domain Events block.
    aggregates_section = (
        "\n## Aggregates\n\n"
        "| Root | Child | Collection |\n"
        "|------|-------|------------|\n"
        "| `Item` | `ItemTag` | `tags` |\n"
    )
    text = text + aggregates_section
    model.write_text(text, encoding="utf-8")

    # AsyncAPI: add ItemTagPayload schema; reference it via tags array
    # on ItemData.
    asyncapi_path = target / "docs/specifications/contracts/asyncapi.yaml"
    a = yaml.safe_load(asyncapi_path.read_text())
    a["components"]["schemas"]["ItemTagPayload"] = {
        "type": "object",
        "required": ["id", "itemId", "label"],
        "properties": {
            "id": {"type": "string", "format": "uuid"},
            "itemId": {"type": "string", "format": "uuid"},
            "label": {"type": "string"},
        },
    }
    a["components"]["schemas"]["ItemData"]["properties"]["tags"] = {
        "type": "array",
        "items": {"$ref": "#/components/schemas/ItemTagPayload"},
    }
    a["components"]["schemas"]["ItemData"]["required"].append("tags")
    asyncapi_path.write_text(yaml.safe_dump(a, sort_keys=False))

    # Datacontract: nested ODCS array on the `items` record.
    dc_path = target / "docs/specifications/contracts/datacontract.yaml"
    d = yaml.safe_load(dc_path.read_text())
    items_record = next(r for r in d["schema"] if r["name"] == "items")
    items_record["properties"].append(
        {
            "name": "tags",
            "description": "Tags attached to this item.",
            "logicalType": "array",
            "required": True,
            "items": {
                "logicalType": "object",
                "properties": [
                    {
                        "name": "id",
                        "logicalType": "string",
                        "physicalType": "uuid",
                        "required": True,
                    },
                    {
                        "name": "itemId",
                        "logicalType": "string",
                        "physicalType": "uuid",
                        "required": True,
                    },
                    {"name": "label", "logicalType": "string", "required": True},
                ],
            },
        }
    )
    dc_path.write_text(yaml.safe_dump(d, sort_keys=False))


def test_aggregate_parser_picks_up_aggregates_section(tmp_path: pathlib.Path) -> None:
    """domain_model_aggregates parses the new section into
    {root: [{child, collection}, ...]}."""
    from shared.spec_parsers import domain_model_aggregates

    model = tmp_path / "domain-model.md"
    model.write_text(
        "# Domain\n\n## Aggregates\n\n"
        "| Root | Child | Collection |\n"
        "|------|-------|------------|\n"
        "| `RateCard` | `RateCardEntry` | `entries` |\n"
        "| `Invoice` | `InvoiceLineItem` | `lineItems` |\n",
        encoding="utf-8",
    )
    out = domain_model_aggregates(model)
    assert out == {
        "RateCard": [{"child": "RateCardEntry", "collection": "entries"}],
        "Invoice": [{"child": "InvoiceLineItem", "collection": "lineItems"}],
    }


def test_aggregate_parser_returns_empty_when_section_absent(tmp_path: pathlib.Path) -> None:
    """domain_model_aggregates returns {} when the section is absent
    (opt-in convention — must not error)."""
    from shared.spec_parsers import domain_model_aggregates

    model = tmp_path / "domain-model.md"
    model.write_text("# Domain\n\n## Entities\n\n### Foo\n", encoding="utf-8")
    assert domain_model_aggregates(model) == {}


def test_event_payload_check_passes_with_well_formed_aggregate(
    tmp_path: pathlib.Path,
) -> None:
    """Adding an Item → ItemTag aggregate with the collection carried
    in both asyncapi and datacontract must NOT trigger any aggregate
    failures."""
    from shared.checks import event_payload_covers_entity_state

    target = _copy_fixture(tmp_path)
    _add_item_tag_aggregate(target)

    result = event_payload_covers_entity_state.run(target)
    assert result.passed, result.details


def test_event_payload_check_catches_missing_aggregate_collection(
    tmp_path: pathlib.Path,
) -> None:
    """Aggregate declared in the model but the asyncapi payload
    omits the collection → fail with a clear breadcrumb."""
    from shared.checks import event_payload_covers_entity_state

    target = _copy_fixture(tmp_path)
    _add_item_tag_aggregate(target)
    # Drop tags from the asyncapi ItemData properties.
    asyncapi_path = target / "docs/specifications/contracts/asyncapi.yaml"
    a = yaml.safe_load(asyncapi_path.read_text())
    a["components"]["schemas"]["ItemData"]["properties"].pop("tags")
    a["components"]["schemas"]["ItemData"]["required"].remove("tags")
    asyncapi_path.write_text(yaml.safe_dump(a, sort_keys=False))

    result = event_payload_covers_entity_state.run(target)
    assert not result.passed
    assert any("tags" in d and "missing from AsyncAPI payload" in d for d in result.details), (
        result.details
    )


def test_event_payload_check_catches_thin_aggregate_items(
    tmp_path: pathlib.Path,
) -> None:
    """Aggregate collection is present but the child item shape
    drops one of the child's published attributes → fail."""
    from shared.checks import event_payload_covers_entity_state

    target = _copy_fixture(tmp_path)
    _add_item_tag_aggregate(target)
    # Remove `label` from the asyncapi child item schema.
    asyncapi_path = target / "docs/specifications/contracts/asyncapi.yaml"
    a = yaml.safe_load(asyncapi_path.read_text())
    a["components"]["schemas"]["ItemTagPayload"]["properties"].pop("label")
    a["components"]["schemas"]["ItemTagPayload"]["required"].remove("label")
    asyncapi_path.write_text(yaml.safe_dump(a, sort_keys=False))

    result = event_payload_covers_entity_state.run(target)
    assert not result.passed
    assert any("ItemTag.label" in d and "AsyncAPI" in d and "items" in d for d in result.details), (
        result.details
    )


def test_event_payload_check_catches_aggregate_item_divergence(
    tmp_path: pathlib.Path,
) -> None:
    """The asyncapi child item schema and datacontract nested record
    must agree on the property set — divergence is caught."""
    from shared.checks import event_payload_covers_entity_state

    target = _copy_fixture(tmp_path)
    _add_item_tag_aggregate(target)
    # Add a field only on the datacontract side.
    dc_path = target / "docs/specifications/contracts/datacontract.yaml"
    d = yaml.safe_load(dc_path.read_text())
    items_record = next(r for r in d["schema"] if r["name"] == "items")
    tags_field = next(p for p in items_record["properties"] if p["name"] == "tags")
    tags_field["items"]["properties"].append(
        {"name": "extraTagField", "logicalType": "string", "required": False}
    )
    dc_path.write_text(yaml.safe_dump(d, sort_keys=False))

    result = event_payload_covers_entity_state.run(target)
    assert not result.passed
    assert any(
        "extraTagField" in d and "AsyncAPI 'tags[]' does not" in d for d in result.details
    ), result.details


def test_idempotency_key_check_passes_against_fixture(tmp_path: pathlib.Path) -> None:
    """The Items fixture declares `Idempotency-Key` (via $ref to
    components.parameters.IdempotencyKey) on every POST. The check
    must accept that and pass."""
    from shared.checks import idempotency_key_on_post_ops

    target = _copy_fixture(tmp_path)
    result = idempotency_key_on_post_ops.run(target)
    assert result.passed, result.details


def test_idempotency_key_check_fails_when_post_omits_header(
    tmp_path: pathlib.Path,
) -> None:
    """Dropping the Idempotency-Key $ref from one POST op must fail
    the check with a clear breadcrumb."""
    from shared.checks import idempotency_key_on_post_ops

    target = _copy_fixture(tmp_path)
    openapi_path = target / "docs/specifications/contracts/openapi.yaml"
    doc = yaml.safe_load(openapi_path.read_text())
    create_item = doc["paths"]["/v1/items"]["post"]
    create_item["parameters"] = []
    openapi_path.write_text(yaml.safe_dump(doc, sort_keys=False))

    result = idempotency_key_on_post_ops.run(target)
    assert not result.passed
    assert any("/v1/items" in d and "Idempotency-Key" in d for d in result.details), result.details


def test_idempotency_key_check_accepts_inline_declaration(
    tmp_path: pathlib.Path,
) -> None:
    """A POST op may declare the header inline (no $ref) — the check
    must accept that as long as `in: header`, name matches
    Idempotency-Key (case-insensitive), and `required: true`."""
    from shared.checks import idempotency_key_on_post_ops

    target = _copy_fixture(tmp_path)
    openapi_path = target / "docs/specifications/contracts/openapi.yaml"
    doc = yaml.safe_load(openapi_path.read_text())
    create_item = doc["paths"]["/v1/items"]["post"]
    create_item["parameters"] = [
        {
            "name": "idempotency-key",
            "in": "header",
            "required": True,
            "schema": {"type": "string", "format": "uuid"},
        }
    ]
    openapi_path.write_text(yaml.safe_dump(doc, sort_keys=False))

    result = idempotency_key_on_post_ops.run(target)
    assert result.passed, result.details


def test_idempotency_key_check_rejects_required_false(
    tmp_path: pathlib.Path,
) -> None:
    """Declaring the header with `required: false` is not enough —
    the check enforces required: true so clients can't silently skip."""
    from shared.checks import idempotency_key_on_post_ops

    target = _copy_fixture(tmp_path)
    openapi_path = target / "docs/specifications/contracts/openapi.yaml"
    doc = yaml.safe_load(openapi_path.read_text())
    create_item = doc["paths"]["/v1/items"]["post"]
    create_item["parameters"] = [
        {
            "name": "Idempotency-Key",
            "in": "header",
            "required": False,
            "schema": {"type": "string", "format": "uuid"},
        }
    ]
    openapi_path.write_text(yaml.safe_dump(doc, sort_keys=False))

    result = idempotency_key_on_post_ops.run(target)
    assert not result.passed


def test_idempotency_key_check_silent_when_no_posts(
    tmp_path: pathlib.Path,
) -> None:
    """A spec set with only GET endpoints triggers no failures —
    the check is scoped to POST."""
    from shared.checks import idempotency_key_on_post_ops

    target = _copy_fixture(tmp_path)
    openapi_path = target / "docs/specifications/contracts/openapi.yaml"
    doc = yaml.safe_load(openapi_path.read_text())
    # Strip every POST from every path.
    for path_item in doc["paths"].values():
        path_item.pop("post", None)
    openapi_path.write_text(yaml.safe_dump(doc, sort_keys=False))

    result = idempotency_key_on_post_ops.run(target)
    assert result.passed, result.details


def test_idempotency_key_check_accepts_path_level_parameter(
    tmp_path: pathlib.Path,
) -> None:
    """OpenAPI allows declaring parameters at path level (applies to
    every operation under the path). The check must walk path-level
    parameters as well as operation-level ones."""
    from shared.checks import idempotency_key_on_post_ops

    target = _copy_fixture(tmp_path)
    openapi_path = target / "docs/specifications/contracts/openapi.yaml"
    doc = yaml.safe_load(openapi_path.read_text())
    # Drop op-level params from createItem, declare at path level.
    items_path = doc["paths"]["/v1/items"]
    items_path["post"]["parameters"] = []
    items_path["parameters"] = [{"$ref": "#/components/parameters/IdempotencyKey"}]
    openapi_path.write_text(yaml.safe_dump(doc, sort_keys=False))

    result = idempotency_key_on_post_ops.run(target)
    assert result.passed, result.details


def test_enum_values_consistent_catches_value_mismatch(tmp_path: pathlib.Path) -> None:
    """When the model and OpenAPI both declare an enum but the values
    diverge, the check reports the mismatch."""
    from shared.checks import enum_values_consistent

    target = _copy_fixture(tmp_path)
    model = target / "docs/specifications/domain-model.md"
    model.write_text(
        model.read_text() + "\n\n## Enumerations\n\n### Breed\n\n"
        "| Value | Notes |\n|---|---|\n| `labrador` | |\n| `poodle` | |\n",
        encoding="utf-8",
    )
    openapi = target / "docs/specifications/contracts/openapi.yaml"
    doc = yaml.safe_load(openapi.read_text())
    doc.setdefault("components", {}).setdefault("schemas", {})["Breed"] = {
        "type": "string",
        "enum": ["labrador", "wolfhound"],  # wolfhound diverges
    }
    openapi.write_text(yaml.safe_dump(doc, sort_keys=False))

    result = enum_values_consistent.run(target)
    assert not result.passed
    assert any("OpenAPI enum" in d and "wolfhound" in d for d in result.details)


def test_enum_values_consistent_closed_perfect_match(tmp_path: pathlib.Path) -> None:
    """Closed enum (no `(open)` marker): when the openapi enum equals
    the model values exactly, the check passes (regression guard)."""
    from shared.checks import enum_values_consistent

    target = _copy_fixture(tmp_path)
    model = target / "docs/specifications/domain-model.md"
    model.write_text(
        model.read_text() + "\n\n## Enumerations\n\n### Status\n\n"
        "| Value | Notes |\n|---|---|\n| `pending` | |\n| `active` | |\n",
        encoding="utf-8",
    )
    openapi = target / "docs/specifications/contracts/openapi.yaml"
    doc = yaml.safe_load(openapi.read_text())
    doc.setdefault("components", {}).setdefault("schemas", {})["Status"] = {
        "type": "string",
        "enum": ["pending", "active"],
    }
    openapi.write_text(yaml.safe_dump(doc, sort_keys=False))

    result = enum_values_consistent.run(target)
    assert result.passed, result.details


def test_enum_values_consistent_open_accepts_contract_superset(
    tmp_path: pathlib.Path,
) -> None:
    """Open enum (`### Name (open)`): the contract MAY exceed the
    model's representative values without failing the check."""
    from shared.checks import enum_values_consistent

    target = _copy_fixture(tmp_path)
    model = target / "docs/specifications/domain-model.md"
    model.write_text(
        model.read_text() + "\n\n## Enumerations\n\n### Breed (open)\n\n"
        "| Value | Notes |\n|---|---|\n| `labrador` | |\n| `poodle` | |\n",
        encoding="utf-8",
    )
    openapi = target / "docs/specifications/contracts/openapi.yaml"
    doc = yaml.safe_load(openapi.read_text())
    doc.setdefault("components", {}).setdefault("schemas", {})["Breed"] = {
        "type": "string",
        "enum": ["labrador", "poodle", "bulldog", "dachshund", "mixed"],
    }
    openapi.write_text(yaml.safe_dump(doc, sort_keys=False))

    result = enum_values_consistent.run(target)
    assert result.passed, result.details


def test_enum_values_consistent_open_rejects_model_extra(
    tmp_path: pathlib.Path,
) -> None:
    """Open enum: a model value missing from the contract is still a
    failure — the model must be a subset of the contract, not a
    superset (otherwise an event could carry a value the contract
    refuses)."""
    from shared.checks import enum_values_consistent

    target = _copy_fixture(tmp_path)
    model = target / "docs/specifications/domain-model.md"
    model.write_text(
        model.read_text() + "\n\n## Enumerations\n\n### Breed (open)\n\n"
        "| Value | Notes |\n|---|---|\n| `labrador` | |\n| `wolfhound` | |\n",
        encoding="utf-8",
    )
    openapi = target / "docs/specifications/contracts/openapi.yaml"
    doc = yaml.safe_load(openapi.read_text())
    doc.setdefault("components", {}).setdefault("schemas", {})["Breed"] = {
        "type": "string",
        "enum": ["labrador", "poodle", "bulldog"],  # missing wolfhound
    }
    openapi.write_text(yaml.safe_dump(doc, sort_keys=False))

    result = enum_values_consistent.run(target)
    assert not result.passed
    assert any("wolfhound" in d and "missing model values" in d for d in result.details), (
        result.details
    )


def test_enum_values_consistent_open_marker_variants(tmp_path: pathlib.Path) -> None:
    """The `(open)` marker is case-insensitive and tolerates the
    bracket variant `[open]`."""
    from shared.spec_parsers import domain_model_enums

    model = tmp_path / "domain-model.md"
    model.write_text(
        "# Domain Model — Foo\n\n## Enumerations\n\n"
        "### Closed\n\n| Value |\n|---|\n| `a` |\n\n"
        "### LowerCase (open)\n\n| Value |\n|---|\n| `a` |\n\n"
        "### MixedCase (Open)\n\n| Value |\n|---|\n| `a` |\n\n"
        "### Bracketed [open]\n\n| Value |\n|---|\n| `a` |\n",
        encoding="utf-8",
    )
    enums = domain_model_enums(model)
    assert enums["Closed"]["open"] is False
    assert enums["LowerCase"]["open"] is True
    assert enums["MixedCase"]["open"] is True
    assert enums["Bracketed"]["open"] is True


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


# ── sign_off findings interface ──────────────────────────────────


def test_sign_off_accepts_rubric_findings(tmp_path: pathlib.Path) -> None:
    """sign_off(rubric_findings=...) writes them verbatim into the
    sidecar, stamping `ts` for any entry that doesn't carry one.
    Warning-engagement is covered by tests/test_soft_gate.py — contracts
    is a hard-gate phase with no warnings to address."""
    target = _copy_fixture(tmp_path)
    sidecar = _sidecar_path(target)
    sidecar.unlink()

    rc = sign_off.sign_off(
        "contracts",
        target,
        rubric_findings=[
            {
                "id": "RUBRIC-DEMO-NO-TS",
                "verdict": "warn",
                "detail": "demo finding without ts",
                "response": "resolved",
                "reason": "agent fixed it",
                # no ts — sign_off should stamp it
            },
            {
                "id": "RUBRIC-DEMO-EXPLICIT-TS",
                "verdict": "pass",
                "detail": "demo finding with explicit ts",
                "response": "resolved",
                "reason": "agent verdict accepted",
                "ts": "2026-01-01T00:00:00Z",
            },
        ],
    )
    assert rc == 0

    doc = yaml.safe_load(sidecar.read_text())
    assert len(doc["rubric_findings"]) == 2
    no_ts = next(r for r in doc["rubric_findings"] if r["id"] == "RUBRIC-DEMO-NO-TS")
    explicit_ts = next(r for r in doc["rubric_findings"] if r["id"] == "RUBRIC-DEMO-EXPLICIT-TS")
    assert no_ts["ts"], "sign_off must stamp ts when absent"
    assert explicit_ts["ts"] == "2026-01-01T00:00:00Z", "sign_off must preserve an explicit ts"


def test_sign_off_findings_yaml_round_trip(tmp_path: pathlib.Path) -> None:
    """The --findings CLI loader produces the same shape as the Python
    API. Covers the YAML round-trip the agent uses when running the
    skill end-to-end."""
    target = _copy_fixture(tmp_path)
    sidecar = _sidecar_path(target)
    sidecar.unlink()

    findings_path = tmp_path / "findings.yaml"
    findings_path.write_text(
        yaml.safe_dump(
            {
                "rubric_findings": [
                    {
                        "id": "RUBRIC-CLI",
                        "verdict": "pass",
                        "detail": "via CLI",
                        "response": "resolved",
                        "reason": "ok",
                    }
                ],
                "warnings_responded": [],
            }
        )
    )

    rc = sign_off.main(["contracts", "--repo", str(target), "--findings", str(findings_path)])
    assert rc == 0
    doc = yaml.safe_load(sidecar.read_text())
    assert doc["rubric_findings"][0]["id"] == "RUBRIC-CLI"
    assert doc["warnings_responded"] == []


def test_sign_off_rejects_malformed_findings_file(tmp_path: pathlib.Path) -> None:
    target = _copy_fixture(tmp_path)
    bad = tmp_path / "bad.yaml"
    bad.write_text("- just\n- a\n- list\n")  # top-level list, not mapping
    rc = sign_off.main(["contracts", "--repo", str(target), "--findings", str(bad)])
    assert rc == 2


# ── Decision Log (sign_off `decisions` interface) ────────────────


def test_sign_off_accepts_decisions(tmp_path: pathlib.Path) -> None:
    """sign_off(decisions=...) writes them verbatim into the sidecar,
    stamping `ts` for any entry that doesn't carry one."""
    target = _copy_fixture(tmp_path)
    sidecar = _sidecar_path(target)
    sidecar.unlink()

    rc = sign_off.sign_off(
        "contracts",
        target,
        decisions=[
            {
                "id": "RATECARD-SNAPSHOT-AT-SCHEDULED",
                "summary": "Snapshot price at scheduled, not completed.",
                "rationale": "Locks the price at the moment of agreement.",
                "affects": [
                    "docs/specifications/domain-model.md",
                    "docs/specifications/contracts/openapi.yaml",
                ],
                # no ts — sign_off stamps it
            }
        ],
    )
    assert rc == 0

    doc = yaml.safe_load(sidecar.read_text())
    assert "decisions" in doc
    assert len(doc["decisions"]) == 1
    entry = doc["decisions"][0]
    assert entry["id"] == "RATECARD-SNAPSHOT-AT-SCHEDULED"
    assert entry["ts"], "sign_off must stamp ts when absent"
    assert "domain-model.md" in entry["affects"][0]


def test_sign_off_decisions_yaml_round_trip(tmp_path: pathlib.Path) -> None:
    """`--findings <yaml>` accepts a `decisions:` key alongside
    `rubric_findings:` and `warnings_responded:`."""
    target = _copy_fixture(tmp_path)
    sidecar = _sidecar_path(target)
    sidecar.unlink()

    findings_path = tmp_path / "findings.yaml"
    findings_path.write_text(
        yaml.safe_dump(
            {
                "rubric_findings": [],
                "warnings_responded": [],
                "decisions": [
                    {
                        "id": "OPENAPI-PAGINATION-CAP-50",
                        "summary": "List endpoints cap pageSize at 50.",
                        "rationale": (
                            "Single-walker workload doesn't justify "
                            "larger pages; lower cap protects mobile bandwidth."
                        ),
                        "affects": ["docs/specifications/contracts/openapi.yaml"],
                    }
                ],
            }
        )
    )

    rc = sign_off.main(["contracts", "--repo", str(target), "--findings", str(findings_path)])
    assert rc == 0
    doc = yaml.safe_load(sidecar.read_text())
    assert doc["decisions"][0]["id"] == "OPENAPI-PAGINATION-CAP-50"


def test_sign_off_rejects_decision_missing_required_field(tmp_path: pathlib.Path) -> None:
    """Each decision must have id, summary, rationale. Missing any of
    those is rejected before sign-off proceeds."""
    target = _copy_fixture(tmp_path)
    sidecar = _sidecar_path(target)
    sidecar.unlink()

    rc = sign_off.sign_off(
        "contracts",
        target,
        decisions=[
            {
                "id": "INCOMPLETE-DECISION",
                "summary": "What was decided",
                # no rationale
            }
        ],
    )
    assert rc == 1, "sign_off must reject decisions missing required fields"
    assert not sidecar.exists()


def test_sign_off_findings_yaml_decisions_alone(tmp_path: pathlib.Path) -> None:
    """A findings file with only a `decisions:` key (no rubric or
    warnings) loads cleanly."""
    target = _copy_fixture(tmp_path)
    sidecar = _sidecar_path(target)
    sidecar.unlink()

    findings_path = tmp_path / "findings-only-decisions.yaml"
    findings_path.write_text(
        yaml.safe_dump(
            {
                "decisions": [
                    {
                        "id": "DEC-ALONE",
                        "summary": "Decisions can live alone.",
                        "rationale": "The other two keys default to empty lists.",
                    }
                ]
            }
        )
    )

    rc = sign_off.main(["contracts", "--repo", str(target), "--findings", str(findings_path)])
    assert rc == 0
    doc = yaml.safe_load(sidecar.read_text())
    assert doc["decisions"][0]["id"] == "DEC-ALONE"
    assert doc["rubric_findings"] == []
    assert doc["warnings_responded"] == []


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


# ── init_phase (authoring half) ──────────────────────────────────


def test_init_phase_copies_missing_contracts(tmp_path: pathlib.Path) -> None:
    """When contracts/ is empty, init_phase copies the three blank
    skeletons from the suite's templates/contracts/ directory."""
    target = _copy_fixture(tmp_path)
    contracts_dir = target / "docs/specifications/contracts"

    # Wipe the existing contracts so init has work to do.
    for f in ("openapi.yaml", "asyncapi.yaml", "datacontract.yaml"):
        (contracts_dir / f).unlink()

    rc = init_phase.init_phase(target, "contracts")
    assert rc == 0

    import re

    placeholder = re.compile(r"\[[A-Za-z][A-Za-z0-9 ]*\]")
    for f in ("openapi.yaml", "asyncapi.yaml", "datacontract.yaml"):
        path = contracts_dir / f
        assert path.is_file(), f"init didn't copy {f}"
        # The copied file should be the blank template (carries
        # [Resource1] / [Domain Name] / [resource1] etc. placeholders).
        assert placeholder.search(path.read_text()), (
            f"copied {f} has no placeholders — was the wrong source used?"
        )


def test_init_phase_never_overwrites_existing(tmp_path: pathlib.Path) -> None:
    """A file that already exists is left strictly alone."""
    target = _copy_fixture(tmp_path)
    openapi = target / "docs/specifications/contracts/openapi.yaml"
    original = openapi.read_text()

    rc = init_phase.init_phase(target, "contracts")
    assert rc == 0
    assert openapi.read_text() == original, "init clobbered user-authored content"


def test_init_phase_is_idempotent(tmp_path: pathlib.Path) -> None:
    """Running init twice produces the same outcome as running it once."""
    target = _copy_fixture(tmp_path)
    contracts_dir = target / "docs/specifications/contracts"
    (contracts_dir / "openapi.yaml").unlink()

    rc1 = init_phase.init_phase(target, "contracts")
    snapshot = (contracts_dir / "openapi.yaml").read_text()
    rc2 = init_phase.init_phase(target, "contracts")
    assert rc1 == rc2 == 0
    assert (contracts_dir / "openapi.yaml").read_text() == snapshot


def test_init_phase_template_path_mapping() -> None:
    """The canonical mapping converts docs/specifications/X to
    <suite>/templates/X."""
    suite_root = pathlib.Path(init_phase.SUITE_ROOT).resolve()
    assert (
        init_phase.template_source_for("docs/specifications/contracts/openapi.yaml")
        == suite_root / "templates/contracts/openapi.yaml"
    )
    assert (
        init_phase.template_source_for("docs/specifications/domain-model.md")
        == suite_root / "templates/domain-model.md"
    )
    # Paths outside docs/specifications/ have no template convention.
    assert init_phase.template_source_for("README.md") is None


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
