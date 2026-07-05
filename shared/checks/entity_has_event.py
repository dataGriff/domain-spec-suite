"""Cross-reference check: every entity appears in the Domain Events
table — nothing is born silently.

Entities created through auth or bootstrap flows (a Walker who
self-registers, a User minted at invite acceptance) tend to escape
the event stream: the write op sits on an exempt `/auth/` path, the
Domain Events table never mentions the entity, and the historic
record ends up with unresolvable foreign keys to an entity nobody
ever published (see EVENT-FK-RESOLVABLE for the downstream symptom —
this check catches the same disease at its source, the model).

Rule: every entity under `## Entities` must be mentioned by at least
one Domain Events row (event name, trigger, or channel). Aggregate
children declared in `## Aggregates` are exempt — they travel inside
their root's events.
"""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult
from shared.spec_parsers import (
    domain_model_aggregates,
    domain_model_entities,
    domain_model_events,
)

metadata = {
    "id": "ENTITY-HAS-EVENT",
    "category": "cross-reference",
    "phases": ["modeling", "audit"],
    "severity_by_phase": {"modeling": "warning", "audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/domain-model.md"},
    ],
}


def run(repo_root: pathlib.Path) -> CheckResult:
    model = repo_root / "docs" / "specifications" / "domain-model.md"

    entities = domain_model_entities(model)
    events = domain_model_events(model)
    children = {
        child["child"] for kids in domain_model_aggregates(model).values() for child in kids
    }

    # Match only against event names and channel names — trigger prose
    # is too loose ("walker declines the walk" would spuriously cover a
    # Walker entity that no event ever publishes).
    haystack = " ".join(f"{e['event']} {e['channel']}" for e in events).lower()

    uncovered: list[str] = []
    for entity in entities:
        if entity in children:
            continue
        needle = re.sub(r"\s+", "", entity).lower()
        if needle not in haystack:
            uncovered.append(entity)

    if not uncovered:
        return CheckResult.ok()

    return CheckResult.fail(
        "These entities never appear in the Domain Events table — they "
        "come into existence (and change) without the event stream "
        "ever hearing about it, so the historic record can't resolve "
        "references to them. What event marks each entity's creation "
        "(registration and invite-acceptance flows count too), or why "
        "is the entity legitimately absent from the stream?",
        details=uncovered,
    )
