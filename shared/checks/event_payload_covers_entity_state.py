"""Cross-contract check: domain events publish the full state of
their affected entity at the moment of the event, and the data
contract records that state.

This is the load-bearing principle behind the data contract being a
*historic record* (per SUITE-DESIGN §5 "Events carry full domain
state"). Thin events — payloads with only identifiers — force every
consumer back to the live API, couple downstream availability to
API availability, and make the contract a record of *that an event
happened*, not *what it carried*. The contract loses its audit
value.

For every event listed in the model's `## Domain Events` table:

1. Resolve the affected entity from the channel name
   (`<domain>.<entity>.<action>` → look up the entity slug in the
   model's `## Entities` headings, case-insensitive).
2. Compute the *published* attribute set for that entity — every
   attribute in the entity's table, minus those flagged
   `[secret]` in their Description column.
3. Verify three edges:
   - **model → asyncapi**: every published attribute appears as a
     property in the matching `<EventName>` message's payload
     `data` (via `asyncapi_event_payloads`).
   - **model → datacontract**: every published attribute appears
     as a property in the matching datacontract record (matched
     via the same channel-stem candidate list `event_in_datacontract`
     uses).
   - **asyncapi ↔ datacontract**: the asyncapi payload property
     set equals the datacontract record property set, modulo two
     accepted naming conventions: `id` in asyncapi == `<entity>Id`
     in datacontract (the existing dog-walking convention), and
     vice versa.

**Removal events** (action ∈ {`removed`, `deleted`, `expired`}) are
exempt — the entity is gone, so a minimal payload (id + timestamp)
is the right shape. They still need a datacontract record for
audit purposes (enforced by `EVENT-IN-DATACONTRACT`).

**Aggregate roots.** If the affected entity is declared as an
aggregate root in the model's `## Aggregates` section, every
declared child collection is also verified:

- The asyncapi payload's `data.<collection>` is an array-of-object
  whose item properties cover the child's published attributes.
- The datacontract record's `<collection>` field is `logicalType:
  array` whose items.properties cover the same attribute set.
- The two sides' item property sets are equal (modulo the
  `id` ↔ `<entity>Id` naming convention).

The check is silent when the model has no `## Domain Events` table
(opt-in convention).
"""

from __future__ import annotations

import pathlib

from shared.check_result import CheckResult
from shared.checks.event_in_datacontract import _candidates as datacontract_candidates
from shared.spec_parsers import (
    asyncapi_array_item_properties,
    asyncapi_event_payloads,
    datacontract_array_item_properties,
    datacontract_record_fields,
    domain_model_aggregates,
    domain_model_entities,
    domain_model_events,
    domain_model_published_attributes,
    load_yaml,
)

metadata = {
    "id": "EVENT-PAYLOAD-COVERS-ENTITY-STATE",
    "category": "cross-reference",
    "phases": ["contracts", "audit"],
    "severity_by_phase": {"contracts": "error", "audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/domain-model.md"},
        {"file_exists": "docs/specifications/contracts/asyncapi.yaml"},
        {"file_exists": "docs/specifications/contracts/datacontract.yaml"},
    ],
}

REMOVAL_ACTIONS = {"removed", "deleted", "expired"}


def _resolve_entity(channel: str, entities: list[str]) -> str | None:
    """Best-effort match: channel is `<domain>.<entity-slug>.<action>`;
    find an entity in `entities` whose lowercased name == the slug."""
    parts = channel.split(".")
    if len(parts) < 3:
        return None
    slug = parts[1].lower()
    for entity in entities:
        if entity.lower() == slug:
            return entity
    return None


def _channel_action(channel: str) -> str:
    parts = channel.split(".")
    return parts[-1].lower() if parts else ""


def _equivalent_field(attr: str, entity: str, candidate: str) -> bool:
    """True if `candidate` is the asyncapi/datacontract spelling of
    the model attribute `attr` on `entity`. Accepts the existing
    convention where the model's `id` becomes `<entity>Id` in the
    payload (e.g. Dog.id → dogId)."""
    if candidate == attr:
        return True
    return attr == "id" and candidate == f"{entity[0].lower()}{entity[1:]}Id"


def _missing_from_payload(attrs: list[str], entity: str, payload_fields: set[str]) -> list[str]:
    return [a for a in attrs if not any(_equivalent_field(a, entity, f) for f in payload_fields)]


def run(repo_root: pathlib.Path) -> CheckResult:
    specs = repo_root / "docs" / "specifications"
    domain_model = specs / "domain-model.md"
    events = domain_model_events(domain_model)
    if not events:
        return CheckResult.ok()

    entities = domain_model_entities(domain_model)
    published_attrs = domain_model_published_attributes(domain_model)
    aggregates = domain_model_aggregates(domain_model)
    asyncapi = load_yaml(specs / "contracts" / "asyncapi.yaml")
    datacontract = load_yaml(specs / "contracts" / "datacontract.yaml")
    payloads = asyncapi_event_payloads(asyncapi)
    records = datacontract_record_fields(datacontract)

    problems: list[str] = []
    for event_row in events:
        event_name = event_row["event"]
        channel = event_row["channel"]
        if _channel_action(channel) in REMOVAL_ACTIONS:
            continue
        entity = _resolve_entity(channel, entities)
        if entity is None:
            problems.append(
                f"{event_name}: channel '{channel}' has no matching entity "
                f"in the model's `## Entities` section."
            )
            continue
        attrs = published_attrs.get(entity)
        if not attrs:
            # Entity has no published attributes — nothing to check.
            continue

        # model → asyncapi
        payload = payloads.get(event_name)
        if payload is None:
            problems.append(
                f"{event_name}: no AsyncAPI message named '{event_name}' "
                f"(or its payload doesn't resolve to a data envelope)."
            )
        else:
            payload_field_set = set(payload.keys())
            for missing in _missing_from_payload(attrs, entity, payload_field_set):
                problems.append(
                    f"{event_name}: model field '{entity}.{missing}' "
                    f"missing from AsyncAPI {event_name} payload."
                )

        # model → datacontract
        record_name = next((c for c in datacontract_candidates(channel) if c in records), None)
        record_fields: set[str] = set()
        if record_name is None:
            problems.append(f"{event_name}: no datacontract record matches channel '{channel}'.")
        else:
            record_fields = set(records[record_name].keys())
            for missing in _missing_from_payload(attrs, entity, record_fields):
                problems.append(
                    f"{event_name}: model field '{entity}.{missing}' "
                    f"missing from datacontract record '{record_name}'."
                )

        # asyncapi ↔ datacontract
        if payload is not None and record_name is not None:
            payload_only = set(payload.keys()) - record_fields
            record_only = record_fields - set(payload.keys())
            for f in sorted(payload_only):
                problems.append(
                    f"{event_name}: AsyncAPI payload has '{f}' but "
                    f"datacontract record '{record_name}' does not."
                )
            for f in sorted(record_only):
                problems.append(
                    f"{event_name}: datacontract record '{record_name}' "
                    f"has '{f}' but AsyncAPI payload does not."
                )

        # Aggregate-child coverage: for every child collection declared
        # on this entity, the asyncapi payload + datacontract record
        # must carry an array whose item shape covers the child's
        # published attributes.
        for agg in aggregates.get(entity, []):
            child = agg["child"]
            collection = agg["collection"]
            child_attrs = published_attrs.get(child)
            if not child_attrs:
                problems.append(
                    f"{event_name}: aggregate child '{child}' declared in "
                    f"`## Aggregates` has no attributes in `## Entities`."
                )
                continue

            # asyncapi side
            if payload is not None:
                if collection not in payload:
                    problems.append(
                        f"{event_name}: aggregate child collection "
                        f"'{collection}' missing from AsyncAPI payload "
                        f"(expected for {entity} → {child})."
                    )
                else:
                    item_props = asyncapi_array_item_properties(
                        payload[collection], asyncapi
                    )
                    if item_props is None:
                        problems.append(
                            f"{event_name}: AsyncAPI payload field "
                            f"'{collection}' is not an array of objects "
                            f"(expected for aggregate child {child})."
                        )
                    else:
                        for missing in _missing_from_payload(
                            child_attrs, child, item_props
                        ):
                            problems.append(
                                f"{event_name}: child field "
                                f"'{child}.{missing}' missing from AsyncAPI "
                                f"payload '{collection}[]' items."
                            )

            # datacontract side
            if record_name is not None:
                record_props = records[record_name]
                if collection not in record_props:
                    problems.append(
                        f"{event_name}: aggregate child collection "
                        f"'{collection}' missing from datacontract record "
                        f"'{record_name}' (expected for {entity} → {child})."
                    )
                else:
                    dc_item_props = datacontract_array_item_properties(
                        record_props[collection]
                    )
                    if dc_item_props is None:
                        problems.append(
                            f"{event_name}: datacontract record "
                            f"'{record_name}' field '{collection}' is not "
                            f"an ODCS array-of-object (expected for "
                            f"aggregate child {child})."
                        )
                    else:
                        for missing in _missing_from_payload(
                            child_attrs, child, dc_item_props
                        ):
                            problems.append(
                                f"{event_name}: child field "
                                f"'{child}.{missing}' missing from "
                                f"datacontract '{record_name}.{collection}[]' "
                                f"items."
                            )

            # asyncapi ↔ datacontract item symmetry
            if (
                payload is not None
                and record_name is not None
                and collection in payload
                and collection in records[record_name]
            ):
                a_items = asyncapi_array_item_properties(
                    payload[collection], asyncapi
                )
                d_items = datacontract_array_item_properties(
                    records[record_name][collection]
                )
                if a_items is not None and d_items is not None:
                    a_only = a_items - d_items
                    d_only = d_items - a_items
                    for f in sorted(a_only):
                        problems.append(
                            f"{event_name}: AsyncAPI '{collection}[]' has "
                            f"'{f}' but datacontract "
                            f"'{record_name}.{collection}[]' does not."
                        )
                    for f in sorted(d_only):
                        problems.append(
                            f"{event_name}: datacontract "
                            f"'{record_name}.{collection}[]' has '{f}' but "
                            f"AsyncAPI '{collection}[]' does not."
                        )

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "Domain event payloads must carry the full state of their "
        "affected entity (minus [secret]-marked fields), and the "
        "datacontract record must match. The data contract is the "
        "audit-grade historic record — thin events break it. See "
        'SUITE-DESIGN §5 "Events carry full domain state".',
        details=problems,
    )
