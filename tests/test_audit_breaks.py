"""M2.4: deliberate-break tests for the audit skill.

For each break below, the test:
  1. Copies the clean Items fixture to a tmp directory
  2. Applies one specific mutation
  3. Re-seeds sign-off sha256s (unless the break is about staleness)
  4. Runs the audit
  5. Asserts the audit fails with the expected check id
  6. Asserts the failure message reads like an interview question
     (substring + style heuristics)

The point isn't exhaustive coverage of every conceivable break — it's
*proof* that the audit catches the realistic break shapes BUILD-PLAN
Task 2.4 enumerated, and that the failure messages remain actionable.
"""

from __future__ import annotations

import hashlib
import pathlib
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent
ITEMS_FIXTURE = REPO / "tests" / "fixtures" / "items"

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from shared import run_phase, spec_paths  # noqa: E402

pytestmark = pytest.mark.audit


# ── helpers ──────────────────────────────────────────────────────


def _reseed_signoffs(repo: pathlib.Path) -> None:
    """Regenerate sha256 values across every sign-off sidecar so the
    SIGNOFF-SHA256-MATCHES check sees a clean state. Used by breaks
    that mutate signed spec files for purposes other than testing
    staleness."""
    for sidecar in spec_paths.all_phase_sidecars(repo):
        doc = yaml.safe_load(sidecar.read_text(encoding="utf-8")) or {}
        files_signed = doc.get("files_signed") or []
        changed = False
        for entry in files_signed:
            if not isinstance(entry, dict):
                continue
            path = entry.get("path")
            if not path:
                continue
            target = repo / path
            if not target.is_file():
                continue
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            if entry.get("sha256") != actual:
                entry["sha256"] = actual
                changed = True
        if changed:
            sidecar.write_text(yaml.safe_dump(doc, sort_keys=False))


def _insert_into_entities_section(repo: pathlib.Path, content: str) -> None:
    """Insert markdown content at the end of the `## Entities` section
    of domain-model.md, before the next `## ` heading."""
    p = repo / "docs" / "specifications" / "domain-model.md"
    text = p.read_text(encoding="utf-8")
    entities_idx = text.find("## Entities")
    assert entities_idx >= 0, "fixture: no '## Entities' heading"
    next_section = text.find("\n## ", entities_idx + len("## Entities"))
    if next_section < 0:
        p.write_text(text + "\n" + content, encoding="utf-8")
    else:
        p.write_text(text[:next_section] + "\n" + content + text[next_section:], encoding="utf-8")


# ── break shape ──────────────────────────────────────────────────


@dataclass
class Break:
    name: str
    apply: Callable[[pathlib.Path], None]
    expected_failing_check: str
    expected_message_substring: str
    reseed_after_mutate: bool = True


# ── break implementations ────────────────────────────────────────


def _rename_field_in_domain_model(repo: pathlib.Path) -> None:
    p = repo / "docs/specifications/domain-model.md"
    p.write_text(p.read_text().replace("| `description`", "| `descriptionRenamed`", 1))


def _remove_asyncapi_channel(repo: pathlib.Path) -> None:
    p = repo / "docs/specifications/contracts/asyncapi.yaml"
    asyncapi = yaml.safe_load(p.read_text())
    asyncapi["channels"].pop("items.item.added")
    p.write_text(yaml.safe_dump(asyncapi, sort_keys=False))


def _auth_matrix_nonexistent_op(repo: pathlib.Path) -> None:
    p = repo / "docs/specifications/auth-matrix.md"
    text = p.read_text()
    last_row = "| Remove item | `DELETE /v1/items/{itemId}` | ❌ | 🔒 own | ❌ |"
    assert last_row in text, "fixture: last auth-matrix row not where expected"
    bogus = "| Bogus | `POST /v1/bogus` | ❌ | ✅ | ❌ |"
    p.write_text(text.replace(last_row, last_row + "\n" + bogus))


def _unreplaced_placeholder(repo: pathlib.Path) -> None:
    p = repo / "docs/specifications/glossary.md"
    p.write_text(p.read_text() + "\n\nFollow-up: handle [Resource1] downstream.\n")


def _user_story_nonexistent_persona(repo: pathlib.Path) -> None:
    """Insert a US-999 story with an unknown persona INSIDE the
    `## User Stories` section (appending at end-of-file would land
    after `## Constraints` and the parser wouldn't see it)."""
    p = repo / "docs/specifications/prd.md"
    text = p.read_text()
    # Insert the new story before the next `## ` heading after `## User Stories`.
    stories_idx = text.find("## User Stories")
    assert stories_idx >= 0, "fixture: no '## User Stories' heading"
    next_section = text.find("\n## ", stories_idx + len("## User Stories"))
    assert next_section >= 0, "fixture: '## User Stories' is the last section"
    new_story = (
        "\n#### US-999: Cast a spell\n\n"
        "**As a** Wizard,\n"
        "**I want to** invoke arcane forces,\n"
        "**So that** the catalogue gains magical properties.\n\n"
        "**Acceptance Criteria:**\n- [ ] Spells resolve in p99 < 100 ms\n"
    )
    p.write_text(text[:next_section] + new_story + text[next_section:])


def _modify_prd_no_resign(repo: pathlib.Path) -> None:
    p = repo / "docs/specifications/prd.md"
    p.write_text(p.read_text() + "\n<!-- silent tweak, no re-sign -->\n")


def _remove_datacontract_record(repo: pathlib.Path) -> None:
    p = repo / "docs/specifications/contracts/datacontract.yaml"
    dc = yaml.safe_load(p.read_text())
    dc["schema"] = [s for s in dc["schema"] if s.get("name") != "items"]
    p.write_text(yaml.safe_dump(dc, sort_keys=False))


def _entity_without_glossary(repo: pathlib.Path) -> None:
    _insert_into_entities_section(
        repo,
        "### Widget\n\n"
        "Represents an undocumented gadget.\n\n"
        "| Attribute | Type | Required | Description |\n"
        "|-----------|------|----------|-------------|\n"
        "| `id` | UUID | Yes | Unique identifier |\n"
        "| `createdAt` | ISO 8601 | Yes | Creation timestamp |\n"
        "| `updatedAt` | ISO 8601 | Yes | Last update timestamp |\n\n"
        "**Business Rules:**\n- Widgets are mysterious.\n\n",
    )


def _entity_without_openapi_schema(repo: pathlib.Path) -> None:
    # Add Widget to BOTH domain-model and glossary so ENTITY-IN-GLOSSARY
    # passes — leaving ENTITY-IN-OPENAPI-SCHEMA as the lone failure.
    _entity_without_glossary(repo)
    g = repo / "docs/specifications/glossary.md"
    text = g.read_text()
    text = text.replace(
        "## Entities\n\n### Item",
        "## Entities\n\n### Widget\n\nAn undocumented gadget.\n\n### Item",
    )
    g.write_text(text)


def _unaccepted_force_advance(repo: pathlib.Path) -> None:
    p = spec_paths.progress_path(repo)
    progress = yaml.safe_load(p.read_text())
    progress["force_advances"] = [
        {
            "phase": "contracts",
            "reason": "Spectral upstream bug",
            "forced_at": "2026-05-30T00:00:00Z",
            "operator": "test",
            "accepted": False,
        }
    ]
    p.write_text(yaml.safe_dump(progress, sort_keys=False))


def _unresolved_audit_ambiguity(repo: pathlib.Path) -> None:
    p = spec_paths.ambiguities_path(repo)
    text = p.read_text()
    assert "## Deferred to: audit\n\n_None._\n\n" in text, (
        "fixture: ambiguities.md structure changed"
    )
    p.write_text(
        text.replace(
            "## Deferred to: audit\n\n_None._\n\n",
            "## Deferred to: audit\n\n"
            "### ITEM-101: Performance target TBD\n"
            "- Recorded in phase: nfrs\n"
            "- Reason: pending performance bake-off\n"
            "- Resolution required before: audit phase\n\n",
        )
    )


def _auth_matrix_error_code_missing(repo: pathlib.Path) -> None:
    p = repo / "docs/specifications/auth-matrix.md"
    p.write_text(
        p.read_text()
        + "\n### Bonus error response\n\n"
        + "| Scenario | HTTP Status | Error Code |\n"
        + "|----------|-------------|------------|\n"
        + "| Test break | `451` | `UNAVAILABLE_FOR_LEGAL_REASONS` |\n"
    )


def _event_without_glossary_entry(repo: pathlib.Path) -> None:
    """Add a Domain Events row whose event name has no glossary entry."""
    p = repo / "docs/specifications/domain-model.md"
    anchor = "| `ItemRemoved` | DELETE /v1/items/{itemId} → 204 | `items.item.removed` |"
    text = p.read_text()
    assert anchor in text, "fixture: Domain Events table changed"
    p.write_text(
        text.replace(
            anchor,
            anchor
            + "\n| `ItemArchived` | PATCH /v1/items/{itemId} → 200 | `items.item.archived` |",
            1,
        )
    )


def _enum_missing_from_openapi(repo: pathlib.Path) -> None:
    """Declare a named enum in the model that no contract materializes.
    The convention is opt-in — Items ships without an `## Enumerations`
    section, so adding one activates ENUM-VALUES-CONSISTENT."""
    p = repo / "docs/specifications/domain-model.md"
    p.write_text(
        p.read_text()
        + "\n---\n\n## Enumerations\n\n### ItemStatus\n\n"
        + "| Value | Notes |\n|-------|-------|\n"
        + "| `active` | Default on creation |\n"
        + "| `archived` | Reversible archival |\n"
    )


def _thin_event_payload(repo: pathlib.Path) -> None:
    """Strip a published attribute from the shared ItemData payload so
    ItemAdded/ItemEdited events no longer carry full entity state."""
    p = repo / "docs/specifications/contracts/asyncapi.yaml"
    asyncapi = yaml.safe_load(p.read_text())
    item_data = asyncapi["components"]["schemas"]["ItemData"]
    item_data["properties"].pop("description")
    item_data["required"] = [f for f in item_data["required"] if f != "description"]
    p.write_text(yaml.safe_dump(asyncapi, sort_keys=False))


def _role_without_persona(repo: pathlib.Path) -> None:
    p = repo / "docs/specifications/auth-matrix.md"
    anchor = "| `viewer` | Read-only access to items | Operations Analyst (PRD §Target Users) |"
    text = p.read_text()
    assert anchor in text, "fixture: auth-matrix Roles table changed"
    bogus = "| `auditor` | Reviews catalogue changes for compliance | Compliance Team |"
    p.write_text(text.replace(anchor, anchor + "\n" + bogus, 1))


def _post_without_idempotency_key(repo: pathlib.Path) -> None:
    p = repo / "docs/specifications/contracts/openapi.yaml"
    openapi = yaml.safe_load(p.read_text())
    register = openapi["paths"]["/v1/auth/register"]["post"]
    register["parameters"] = [
        param
        for param in register.get("parameters", [])
        if param.get("$ref") != "#/components/parameters/IdempotencyKey"
    ]
    if not register["parameters"]:
        del register["parameters"]
    p.write_text(yaml.safe_dump(openapi, sort_keys=False))


def _story_group_without_flow(repo: pathlib.Path) -> None:
    """New story group with no matching flow title and no US-id
    referenced by any flow body. Uses an existing persona so
    PRD-STORY-PERSONA-LINK stays green."""
    p = repo / "docs/specifications/prd.md"
    text = p.read_text()
    stories_idx = text.find("## User Stories")
    assert stories_idx >= 0, "fixture: no '## User Stories' heading"
    next_section = text.find("\n## ", stories_idx + len("## User Stories"))
    assert next_section >= 0, "fixture: '## User Stories' is the last section"
    new_group = (
        "\n### Reporting\n\n"
        "#### US-050: Export the catalogue\n\n"
        "**As a** Operations Analyst,\n"
        "**I want to** export the item list as CSV,\n"
        "**So that** I can analyse it offline.\n\n"
        "**Acceptance Criteria:**\n- [ ] Export completes for 10k items in < 5 s\n"
    )
    p.write_text(text[:next_section] + new_group + text[next_section:])


def _lifecycle_state_not_in_flows(repo: pathlib.Path) -> None:
    p = repo / "docs/specifications/domain-model.md"
    anchor = '| `archived` | `active` | PATCH /v1/items/{itemId} with `status: "active"` |'
    text = p.read_text()
    assert anchor in text, "fixture: Item Status lifecycle table changed"
    purge_row = "| `archived` | `purged` | DELETE /v1/items/{itemId} after 90 days archived |"
    p.write_text(text.replace(anchor, anchor + "\n" + purge_row, 1))


def _entity_missing_from_rendered_overview(repo: pathlib.Path) -> None:
    """An entity the model declares but the generator can't render
    (its source is the OpenAPI schemas). Reuses the Widget break and
    patches the glossary so ENTITY-IN-GLOSSARY isn't the failure."""
    _entity_without_openapi_schema(repo)


# ── break manifest ───────────────────────────────────────────────


# For each break, expected_message_substring is matched against the
# concatenated message + details (the runner shows both). Substrings
# are chosen to be tight enough to verify the right path fired, loose
# enough to survive small wording tweaks to the on_fail copy.
BREAKS = [
    Break(
        "rename_field_in_domain_model",
        _rename_field_in_domain_model,
        "FIELD-MATCH-DOMAIN-OPENAPI",
        "missing from openapi",
    ),
    Break(
        "remove_asyncapi_channel_for_write_op",
        _remove_asyncapi_channel,
        "WRITE-OP-HAS-ASYNCAPI-CHANNEL",
        "no corresponding asyncapi",
    ),
    Break(
        "auth_matrix_references_nonexistent_op",
        _auth_matrix_nonexistent_op,
        "AUTH-MATRIX-OPENAPI-MATCH",
        "doesn't expose",
    ),
    Break(
        "unreplaced_placeholder_in_glossary",
        _unreplaced_placeholder,
        "NO-TEMPLATE-PLACEHOLDERS",
        "markers are still",
    ),
    Break(
        "user_story_with_nonexistent_persona",
        _user_story_nonexistent_persona,
        "PRD-STORY-PERSONA-LINK",
        "wizard",
    ),
    Break(
        "modify_prd_without_re_sign",
        _modify_prd_no_resign,
        "SIGNOFF-SHA256-MATCHES",
        "out of sync",
        reseed_after_mutate=False,
    ),
    Break(
        "remove_datacontract_record",
        _remove_datacontract_record,
        "EVENT-IN-DATACONTRACT",
        "no matching record",
    ),
    Break(
        "entity_without_glossary_entry",
        _entity_without_glossary,
        "ENTITY-IN-GLOSSARY",
        "don't appear in glossary",
    ),
    Break(
        "entity_without_openapi_schema",
        _entity_without_openapi_schema,
        "ENTITY-IN-OPENAPI-SCHEMA",
        "don't have a matching schema",
    ),
    Break(
        "unaccepted_force_advance",
        _unaccepted_force_advance,
        "FORCE-ADVANCES-ALL-ACCEPTED",
        "force-advance entries remain unaccepted",
        reseed_after_mutate=False,
    ),
    Break(
        "unresolved_audit_ambiguity",
        _unresolved_audit_ambiguity,
        "AMBIGUITIES-NO-AUDIT-REQUIRED",
        "audit phase",
    ),
    Break(
        "auth_matrix_error_code_missing",
        _auth_matrix_error_code_missing,
        "ERROR-CODE-IN-CATALOGUE",
        "aren't defined",
    ),
    Break(
        "event_without_glossary_entry",
        _event_without_glossary_entry,
        "GLOSSARY-COVERS-DOMAIN-TERMS",
        "not in glossary",
    ),
    Break(
        "enum_missing_from_openapi",
        _enum_missing_from_openapi,
        "ENUM-VALUES-CONSISTENT",
        "missing from openapi components.schemas",
    ),
    Break(
        "thin_event_payload",
        _thin_event_payload,
        "EVENT-PAYLOAD-COVERS-ENTITY-STATE",
        "full state",
    ),
    Break(
        "role_without_persona",
        _role_without_persona,
        "AUTH-ROLE-TRACES-TO-PERSONA",
        "doesn't match any prd persona",
    ),
    Break(
        "post_without_idempotency_key",
        _post_without_idempotency_key,
        "IDEMPOTENCY-KEY-ON-POST-OPS",
        "idempotency-key",
    ),
    Break(
        "story_group_without_flow",
        _story_group_without_flow,
        "STORY-HAS-FLOW",
        "no matching flow",
    ),
    Break(
        "lifecycle_state_not_in_flows",
        _lifecycle_state_not_in_flows,
        "LIFECYCLE-IN-FLOWS",
        "purged",
    ),
    Break(
        "entity_missing_from_rendered_overview",
        _entity_missing_from_rendered_overview,
        "GENERATOR-CLEAN-OUTPUT",
        "missing entities",
    ),
]


# ── parametrised test ────────────────────────────────────────────


INTERVIEW_TOKENS = ("?", "re-run", "fix ", "remove ", "either ", "what ", "which ", "how ", "add ")


@pytest.mark.parametrize("brk", BREAKS, ids=lambda b: b.name)
def test_audit_catches_deliberate_break(brk: Break, tmp_path: pathlib.Path) -> None:
    target = tmp_path / "items"
    shutil.copytree(ITEMS_FIXTURE, target)
    brk.apply(target)
    if brk.reseed_after_mutate:
        _reseed_signoffs(target)

    exit_code, outcomes = run_phase.run_phase("audit", target)

    assert exit_code != 0, f"break '{brk.name}' did not fail the audit. Outcomes:\n" + "\n".join(
        f"  {o.id}: {'PASS' if o.passed else 'FAIL'}" for o in outcomes
    )

    failing = [o for o in outcomes if not o.passed and not o.skipped]
    failing_ids = [o.id for o in failing]
    assert brk.expected_failing_check in failing_ids, (
        f"break '{brk.name}': expected '{brk.expected_failing_check}' to fail; got: {failing_ids}"
    )

    target_outcome = next(o for o in failing if o.id == brk.expected_failing_check)
    haystack = (target_outcome.message + "\n" + "\n".join(target_outcome.details)).lower()
    assert brk.expected_message_substring.lower() in haystack, (
        f"break '{brk.name}': expected message+details to contain "
        f"'{brk.expected_message_substring}'; got:\n"
        f"  message: {target_outcome.message}\n"
        f"  details: {target_outcome.details}"
    )

    # Interview-style sanity (§7 Hard Rule 10). Quick proxy: the
    # message either asks a question or names a concrete action.
    msg_lower = target_outcome.message.lower()
    assert any(token in msg_lower for token in INTERVIEW_TOKENS), (
        f"break '{brk.name}': message doesn't read like an interview "
        f"question or actionable directive:\n  {target_outcome.message}"
    )
