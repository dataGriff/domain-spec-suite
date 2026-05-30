"""Small helpers for extracting structured facts from the spec files.

These are deliberately regex-based — the spec markdown follows a known
convention from the bootstrap templates, so there's no need for a full
markdown parser. If conventions drift over time, fix the parser here
rather than scattering ad-hoc regexes across check modules.
"""

from __future__ import annotations

import pathlib
import re

import yaml

# ── markdown section + heading helpers ────────────────────────────


def _section(text: str, heading_pattern: str) -> str:
    """Return the slice of `text` under the heading matched by
    `heading_pattern` (anchored to start of line), up to the next
    same-level (## ) heading. Returns the empty string if no match."""
    start_match = re.search(heading_pattern, text, re.MULTILINE)
    if start_match is None:
        return ""
    after_heading = text[start_match.end() :]
    next_section = re.search(r"(?m)^##\s+\S", after_heading)
    return after_heading[: next_section.start()] if next_section else after_heading


def _h3_names(section_text: str) -> list[str]:
    """Extract `### Name` headings from a markdown section, returning
    just the name portion (stripped of trailing ' — qualifier' style
    suffixes)."""
    names: list[str] = []
    for match in re.finditer(r"(?m)^###\s+(\S[^\n]*)$", section_text):
        raw = match.group(1).strip()
        # Strip 'Stockroom Lead — Sam' style → 'Stockroom Lead'
        clean = re.split(r"\s*—\s*", raw, maxsplit=1)[0].strip()
        names.append(clean)
    return names


# ── domain model ─────────────────────────────────────────────────


def domain_model_entities(domain_model: pathlib.Path) -> list[str]:
    """List entity names declared under `## Entities` in domain-model.md."""
    text = domain_model.read_text(encoding="utf-8")
    return _h3_names(_section(text, r"^##\s+Entities\s*$"))


def domain_model_attributes(domain_model: pathlib.Path) -> dict[str, list[str]]:
    """{entity_name: [attribute_name, ...]} parsed from the attribute
    tables under each entity heading. Backtick-wrapped attribute names
    are unwrapped."""
    text = domain_model.read_text(encoding="utf-8")
    entities_section = _section(text, r"^##\s+Entities\s*$")
    out: dict[str, list[str]] = {}

    # Split into per-entity blocks by ### headings.
    blocks = re.split(r"(?m)(?=^###\s+\S)", entities_section)
    for block in blocks:
        heading = re.match(r"###\s+(\S[^\n]*)", block)
        if heading is None:
            continue
        name = heading.group(1).strip().split(" — ")[0].split("—")[0].strip()
        attrs: list[str] = []
        for row in re.finditer(r"^\|\s*`([^`]+)`\s*\|", block, re.MULTILINE):
            attrs.append(row.group(1))
        if attrs:
            out[name] = attrs
    return out


def domain_model_events(domain_model: pathlib.Path) -> list[dict[str, str]]:
    """List of {event, trigger, channel} dicts parsed from the
    Domain Events table."""
    text = domain_model.read_text(encoding="utf-8")
    events_section = _section(text, r"^##\s+Domain Events\s*$")
    out: list[dict[str, str]] = []
    rows = re.finditer(
        r"^\|\s*`?(?P<event>[\w]+)`?\s*\|\s*(?P<trigger>[^|]+?)\s*\|\s*`?(?P<channel>[\w.-]+)`?\s*\|",
        events_section,
        re.MULTILINE,
    )
    for row in rows:
        event = row.group("event").strip()
        if event.lower() in {"event", "---"}:
            continue
        out.append(
            {
                "event": event,
                "trigger": row.group("trigger").strip(),
                "channel": row.group("channel").strip(),
            }
        )
    return out


def domain_model_lifecycle_transitions(domain_model: pathlib.Path) -> list[tuple[str, str]]:
    """List of (from_state, to_state) tuples from the Status Lifecycle
    tables. Returns transitions from any entity's lifecycle table."""
    text = domain_model.read_text(encoding="utf-8")
    lifecycle_section = _section(text, r"^##\s+Status Lifecycle\s*$")
    transitions: list[tuple[str, str]] = []
    for row in re.finditer(
        r"^\|\s*`?(?P<frm>\w+)`?\s*\|\s*`?(?P<to>\w+)`?\s*\|",
        lifecycle_section,
        re.MULTILINE,
    ):
        frm, to = row.group("frm").strip(), row.group("to").strip()
        if frm.lower() in {"from", "---"}:
            continue
        transitions.append((frm, to))
    return transitions


# ── glossary ─────────────────────────────────────────────────────


def glossary_entities(glossary: pathlib.Path) -> list[str]:
    """List entity names declared under `## Entities` in glossary.md."""
    text = glossary.read_text(encoding="utf-8")
    return _h3_names(_section(text, r"^##\s+Entities\s*$"))


def glossary_attributes(glossary: pathlib.Path) -> dict[str, list[str]]:
    """{entity_name: [attribute_name, ...]} parsed from glossary's
    `## X attributes` sections."""
    text = glossary.read_text(encoding="utf-8")
    out: dict[str, list[str]] = {}
    for match in re.finditer(r"(?m)^##\s+(?P<ent>\S+)\s+attributes\s*$", text):
        entity = match.group("ent")
        section_text = _section(text, re.escape(match.group(0)))
        attrs = _h3_names(section_text)
        out[entity] = attrs
    return out


# ── PRD ──────────────────────────────────────────────────────────


PERSONA_HEADING = re.compile(r"(?m)^###\s+(?P<name>\S[^\n]*)$")


def prd_persona_names(prd: pathlib.Path) -> list[str]:
    """Persona names under `## Target Users / Personas` (or similar).
    Returns both the full heading and just the role part for fuzzy
    matching downstream."""
    text = prd.read_text(encoding="utf-8")
    section = _section(text, r"^##\s+Target Users(?:\s*/\s*Personas)?\s*$")
    return _h3_names(section)


def prd_user_story_blocks(prd: pathlib.Path) -> list[str]:
    """Per-story markdown blocks (raw text), each starting at a
    `#### US-` heading."""
    text = prd.read_text(encoding="utf-8")
    section = _section(text, r"^##\s+User Stories\s*$")
    blocks = re.split(r"(?m)(?=^####\s+US-)", section)
    return [b for b in blocks if b.strip().startswith("#### US-")]


# ── auth matrix ─────────────────────────────────────────────────


def auth_matrix_operations(auth_matrix: pathlib.Path) -> list[dict[str, str]]:
    """List of {operation, endpoint} dicts from the auth matrix table."""
    text = auth_matrix.read_text(encoding="utf-8")
    section = _section(text, r"^##\s+Auth Matrix\s*$")
    out: list[dict[str, str]] = []
    for row in re.finditer(
        r"^\|\s*(?P<op>[^|]+?)\s*\|\s*`(?P<endpoint>[^`]+)`\s*\|",
        section,
        re.MULTILINE,
    ):
        op = row.group("op").strip()
        if op.lower() in {"operation", "---"}:
            continue
        out.append({"operation": op, "endpoint": row.group("endpoint").strip()})
    return out


# ── error catalogue ─────────────────────────────────────────────


def error_catalogue_codes(error_catalogue: pathlib.Path) -> set[str]:
    """Set of error code identifiers declared in error-catalogue.md.
    Codes appear as backtick-wrapped SCREAMING_SNAKE_CASE in headings."""
    text = error_catalogue.read_text(encoding="utf-8")
    return set(re.findall(r"###\s+`([A-Z][A-Z0-9_]+)`", text))


def auth_matrix_error_codes(auth_matrix: pathlib.Path) -> set[str]:
    """Error codes referenced in the auth-matrix Error Responses table
    (e.g. AUTHENTICATION_REQUIRED, FORBIDDEN, ...)."""
    text = auth_matrix.read_text(encoding="utf-8")
    section = _section(text, r"^##\s+Error Responses\s*$")
    return set(re.findall(r"`([A-Z][A-Z0-9_]+)`", section))


# ── OpenAPI / AsyncAPI / data contract (YAML) ───────────────────


def load_yaml(path: pathlib.Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


# Schemas ending with these suffixes are request/response wrappers,
# not domain entities. Used by entity-coverage checks against OpenAPI.
NON_ENTITY_SUFFIXES = ("Request", "Response", "Error", "List", "Pagination", "Summary")


def openapi_entity_schemas(openapi: dict) -> dict[str, dict]:
    """Filter components.schemas to those whose name is plausibly an
    entity (not a request/response/error wrapper)."""
    schemas = openapi.get("components", {}).get("schemas", {})
    return {
        name: defn
        for name, defn in schemas.items()
        if not any(name.endswith(s) for s in NON_ENTITY_SUFFIXES)
    }


def openapi_write_operations(openapi: dict) -> list[dict[str, str]]:
    """List of {method, path, operationId, summary} for every POST/PATCH/
    PUT/DELETE operation. Excludes auth operations whose state changes
    are self-evident from the endpoint."""
    out: list[dict[str, str]] = []
    write_methods = {"post", "patch", "put", "delete"}
    for path, item in openapi.get("paths", {}).items():
        for method, op in item.items():
            if method.lower() not in write_methods:
                continue
            out.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "operationId": op.get("operationId", ""),
                    "summary": op.get("summary", ""),
                }
            )
    return out


def openapi_response_codes(openapi: dict) -> set[str]:
    """Set of response shape names (as referenced via $ref in operation
    responses). Used to map operations back to error codes."""
    out: set[str] = set()
    for item in openapi.get("paths", {}).values():
        for method, op in item.items():
            if method.lower() not in {"get", "post", "patch", "put", "delete"}:
                continue
            for code, response in op.get("responses", {}).items():
                if str(code).startswith("4") or str(code).startswith("5"):
                    ref = response.get("$ref", "")
                    if ref:
                        out.add(ref.rsplit("/", 1)[-1])
    return out


def asyncapi_channels(asyncapi: dict) -> list[str]:
    return sorted(asyncapi.get("channels", {}).keys())


def datacontract_schema_names(datacontract: dict) -> set[str]:
    """Set of schema record names in the data contract."""
    return {entry.get("name") for entry in datacontract.get("schema", []) if entry.get("name")}
