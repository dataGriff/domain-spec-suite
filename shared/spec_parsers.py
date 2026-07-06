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


def domain_model_published_attributes(domain_model: pathlib.Path) -> dict[str, list[str]]:
    """Like `domain_model_attributes` but strips attributes whose
    Description column is prefixed with the `[secret]` marker.

    Used by `EVENT-PAYLOAD-COVERS-ENTITY-STATE` to compute the set
    of attributes that MUST appear in event payloads + datacontract
    records. Sensitive fields (password hashes, time-limited URLs)
    carry the marker so they are intentionally excluded from the
    historic record.

    Example row that's excluded:
        | `passwordHash` | string | Yes | [secret] bcrypt hash, never published |
    """
    text = domain_model.read_text(encoding="utf-8")
    entities_section = _section(text, r"^##\s+Entities\s*$")
    out: dict[str, list[str]] = {}

    blocks = re.split(r"(?m)(?=^###\s+\S)", entities_section)
    for block in blocks:
        heading = re.match(r"###\s+(\S[^\n]*)", block)
        if heading is None:
            continue
        name = heading.group(1).strip().split(" — ")[0].split("—")[0].strip()
        attrs: list[str] = []
        # Match the whole row so we can inspect the Description column
        # and skip [secret]-marked entries.
        for row in re.finditer(
            r"^\|\s*`([^`]+)`\s*\|[^|]*\|[^|]*\|([^|\n]*)\|",
            block,
            re.MULTILINE,
        ):
            attr_name = row.group(1)
            description = row.group(2)
            if "[secret]" in description:
                continue
            attrs.append(attr_name)
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


def domain_model_enums(domain_model: pathlib.Path) -> dict[str, dict]:
    """Parse the `## Enumerations` section.

    Each `### Name` heading declares one enum; the table beneath it
    has a `Value` column whose backticked values are the enum
    members.

    The heading MAY carry an `(open)` (or `[open]`) suffix to mark
    the enum as **expandable**: the model lists a representative
    subset; the contract's enum schema may extend the list with
    additional values. Without the marker, the enum is **closed**
    (the default — `ENUM-VALUES-CONSISTENT` enforces strict
    equality between model and contract values).

    Returns `{name: {"values": [...], "open": bool}}`. Empty dict if
    the section is absent (opt-in)."""
    text = domain_model.read_text(encoding="utf-8")
    section = _section(text, r"^##\s+Enumerations\s*$")
    if not section:
        return {}
    out: dict[str, dict] = {}
    blocks = re.split(r"(?m)(?=^###\s+\S)", section)
    for block in blocks:
        heading = re.match(r"###\s+(\S[^\n]*)", block)
        if heading is None:
            continue
        raw_name = heading.group(1).strip()
        # Detect (open) or [open] suffix; case-insensitive; tolerate
        # surrounding whitespace.
        is_open = bool(re.search(r"[\(\[]\s*open\s*[\)\]]\s*$", raw_name, re.IGNORECASE))
        # Strip the marker (and any trailing whitespace) from the name.
        name = re.sub(r"\s*[\(\[]\s*open\s*[\)\]]\s*$", "", raw_name, flags=re.IGNORECASE).strip()
        values: list[str] = []
        for row in re.finditer(r"^\|\s*`([^`]+)`\s*\|", block, re.MULTILINE):
            values.append(row.group(1))
        if values:
            out[name] = {"values": values, "open": is_open}
    return out


def domain_model_aggregates(domain_model: pathlib.Path) -> dict[str, list[dict[str, str]]]:
    """Parse the `## Aggregates` section.

    Aggregate roots MAY declare their child collections so the
    contracts phase can verify aggregate-event payloads carry the
    children too (per SUITE-DESIGN §4.5).

    Expected table format:

        | Root | Child | Collection |
        |------|-------|------------|
        | `RateCard` | `RateCardEntry` | `entries` |

    Returns `{root_entity: [{"child": ..., "collection": ...}, ...]}`.
    Empty dict if the section is absent (opt-in)."""
    text = domain_model.read_text(encoding="utf-8")
    section = _section(text, r"^##\s+Aggregates\s*$")
    if not section:
        return {}
    out: dict[str, list[dict[str, str]]] = {}
    for row in re.finditer(
        r"^\|\s*`(?P<root>[^`]+)`\s*\|\s*`(?P<child>[^`]+)`\s*\|\s*`(?P<collection>[^`]+)`\s*\|",
        section,
        re.MULTILINE,
    ):
        root = row.group("root").strip()
        child = row.group("child").strip()
        collection = row.group("collection").strip()
        out.setdefault(root, []).append({"child": child, "collection": collection})
    return out


# ── glossary ─────────────────────────────────────────────────────


def glossary_entities(glossary: pathlib.Path) -> list[str]:
    """List entity names declared under `## Entities` in glossary.md."""
    text = glossary.read_text(encoding="utf-8")
    return _h3_names(_section(text, r"^##\s+Entities\s*$"))


def glossary_term_names(glossary: pathlib.Path) -> set[str]:
    """Every `### Name` heading anywhere in glossary.md, cleaned of
    trailing ' — qualifier' suffixes. The glossary is a lexicon —
    entities, roles, domain events, enumerations, other terms — and
    this returns the full set of defined terms regardless of which
    section they sit under."""
    text = glossary.read_text(encoding="utf-8")
    return set(_h3_names(text))


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


def error_catalogue_code_statuses(error_catalogue: pathlib.Path) -> dict[str, int]:
    """{code: http_status} from error-catalogue.md. Each `### \\`CODE\\``
    heading is followed by an `**HTTP status:** NNN ...` line; the first
    such line after the heading wins."""
    text = error_catalogue.read_text(encoding="utf-8")
    out: dict[str, int] = {}
    blocks = re.split(r"(?m)(?=^###\s+`)", text)
    for block in blocks:
        heading = re.match(r"###\s+`([A-Z][A-Z0-9_]+)`", block)
        if heading is None:
            continue
        status = re.search(r"\*\*HTTP status:\*\*\s*(\d{3})", block)
        if status is not None:
            out[heading.group(1)] = int(status.group(1))
    return out


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


HTTP_METHODS = {"get", "post", "patch", "put", "delete"}


def openapi_operations(openapi: dict) -> list[dict[str, str]]:
    """List of {method, path, operationId} for every operation."""
    out: list[dict[str, str]] = []
    for path, item in (openapi.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for method, op in item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(op, dict):
                continue
            out.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "operationId": op.get("operationId", ""),
                }
            )
    return out


def endpoint_path_matches(mention: str, template: str) -> bool:
    """True when a path mentioned in prose (possibly with concrete ids,
    e.g. `/v1/items/123`) matches an OpenAPI path template
    (`/v1/items/{itemId}`). Segment-wise: a `{param}` template segment
    matches anything; other segments must match exactly. Query strings
    on the mention are ignored."""
    mention_segs = [s for s in mention.split("?", 1)[0].split("/") if s]
    template_segs = [s for s in template.split("/") if s]
    if len(mention_segs) != len(template_segs):
        return False
    for m_seg, t_seg in zip(mention_segs, template_segs, strict=True):
        if t_seg.startswith("{") and t_seg.endswith("}"):
            continue
        # Prose often keeps the placeholder too ({itemId} vs {id}) —
        # treat any braced mention segment as matching a braced template
        # segment only (handled above) or failing against a literal.
        if m_seg != t_seg:
            return False
    return True


ENDPOINT_MENTION = re.compile(r"\b(GET|POST|PATCH|PUT|DELETE)\s+(/[A-Za-z0-9_\-/{}.]+)")


def endpoint_mentions(text: str) -> list[tuple[str, str]]:
    """Every `METHOD /path` mention in a prose/markdown string,
    as (method, path) tuples. Query strings are stripped."""
    return [(m.group(1), m.group(2).split("?", 1)[0]) for m in ENDPOINT_MENTION.finditer(text)]


def acceptance_scenario_blocks(scenarios: pathlib.Path) -> list[dict[str, str]]:
    """Per-scenario blocks from acceptance-scenarios.md. Each dict is
    {heading, text} where text runs from the `### Scenario` heading to
    the next `###`/`##` heading."""
    text = scenarios.read_text(encoding="utf-8")
    out: list[dict[str, str]] = []
    blocks = re.split(r"(?m)(?=^###\s+Scenario\b)", text)
    for block in blocks:
        heading = re.match(r"###\s+(Scenario\s+\S[^\n]*)", block)
        if heading is None:
            continue
        body = re.split(r"(?m)^##\s", block, maxsplit=1)[0]
        out.append({"heading": heading.group(1).strip(), "text": body})
    return out


def _iter_operation_responses(openapi: dict):
    """Yield (method, path, status_str, resolved_response_dict) for
    every declared response on every operation, resolving
    `$ref: '#/components/responses/...'` indirection."""
    responses_components = (openapi.get("components") or {}).get("responses") or {}
    for path, item in (openapi.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for method, op in item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(op, dict):
                continue
            for status, response in (op.get("responses") or {}).items():
                if not isinstance(response, dict):
                    continue
                ref = response.get("$ref")
                if isinstance(ref, str):
                    response = responses_components.get(ref.rsplit("/", 1)[-1], {})
                yield method.upper(), path, str(status), response


def _schema_code_enum(schema: dict, schemas: dict) -> list[str]:
    """Extract the `code` property's enum from a response schema,
    resolving one level of `$ref` and walking `allOf` branches."""
    schema = _resolve_local_ref(schema, schemas)
    if not isinstance(schema, dict):
        return []
    branches = [schema] + [_resolve_local_ref(b, schemas) for b in schema.get("allOf", [])]
    for branch in branches:
        if not isinstance(branch, dict):
            continue
        code = (branch.get("properties") or {}).get("code")
        code = _resolve_local_ref(code, schemas) if isinstance(code, dict) else None
        if isinstance(code, dict) and isinstance(code.get("enum"), list):
            return [str(v) for v in code["enum"]]
    return []


def openapi_error_code_bindings(openapi: dict) -> tuple[set[int], dict[int, set[str]]]:
    """(declared_error_statuses, {status: union of `code` enum values
    admitted by response schemas bound at that status}). Statuses cover
    every 4xx/5xx declared on any operation; the enum map only carries
    entries where a response schema actually enumerates codes."""
    schemas = (openapi.get("components") or {}).get("schemas") or {}
    declared: set[int] = set()
    enums_by_status: dict[int, set[str]] = {}
    for _method, _path, status, response in _iter_operation_responses(openapi):
        if not status.isdigit() or int(status) < 400:
            continue
        status_int = int(status)
        declared.add(status_int)
        content = (response.get("content") or {}).get("application/json") or {}
        schema = content.get("schema")
        if isinstance(schema, dict):
            codes = _schema_code_enum(schema, schemas)
            if codes:
                enums_by_status.setdefault(status_int, set()).update(codes)
    return declared, enums_by_status


def openapi_enum_properties(openapi: dict) -> dict[str, set[str]]:
    """{property_name: union of string enum values} across every
    `components.schemas` object schema. A property maps its `$ref` to
    a named enum schema when present. Used to validate literals quoted
    in prose (acceptance scenarios) against the contract."""
    schemas = (openapi.get("components") or {}).get("schemas") or {}
    out: dict[str, set[str]] = {}
    for defn in schemas.values():
        if not isinstance(defn, dict):
            continue
        branches = [defn] + [_resolve_local_ref(b, schemas) for b in defn.get("allOf", [])]
        for branch in branches:
            if not isinstance(branch, dict):
                continue
            for prop_name, prop in (branch.get("properties") or {}).items():
                prop = _resolve_local_ref(prop, schemas) if isinstance(prop, dict) else None
                if not isinstance(prop, dict):
                    continue
                values = prop.get("enum")
                if isinstance(values, list) and values:
                    out.setdefault(prop_name, set()).update(str(v) for v in values)
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


def contract_named_enums(doc: dict) -> dict[str, list[str]]:
    """Extract `{name: enum_values}` from a contract document's
    `components.schemas`. Returns only schemas that declare a top-level
    `enum:` list with `type: string`. OpenAPI and AsyncAPI both use this
    shape under `components.schemas.<Name>`."""
    schemas = (doc.get("components") or {}).get("schemas") or {}
    out: dict[str, list[str]] = {}
    for name, defn in schemas.items():
        if not isinstance(defn, dict):
            continue
        values = defn.get("enum")
        if isinstance(values, list) and values:
            out[name] = [str(v) for v in values]
    return out


def _resolve_local_ref(node: dict, schemas: dict) -> dict:
    """If `node` is a single-key `$ref` dict pointing to
    `#/components/schemas/<Name>`, return the referenced schema.
    Otherwise return `node` unchanged."""
    if not isinstance(node, dict):
        return node
    ref = node.get("$ref")
    if not isinstance(ref, str):
        return node
    # Only handle local refs into components/schemas
    name = ref.rsplit("/", 1)[-1]
    return schemas.get(name, node)


def _find_data_property(envelope: dict, schemas: dict) -> dict | None:
    """Given an AsyncAPI envelope schema, locate the `data` property
    schema. Handles both shapes:
      - allOf: [<CloudEvents base>, {properties: {data: {...}}}]
      - {properties: {data: {...}}}  (envelope inlines data directly)

    Resolves a `$ref` on the `data` value if present. Returns None if
    no data property can be found."""
    if not isinstance(envelope, dict):
        return None
    # allOf shape: walk each branch looking for properties.data
    for branch in envelope.get("allOf", []):
        resolved = _resolve_local_ref(branch, schemas)
        data = (resolved.get("properties") or {}).get("data")
        if data is not None:
            return _resolve_local_ref(data, schemas)
    # Direct shape: properties.data
    data = (envelope.get("properties") or {}).get("data")
    if data is not None:
        return _resolve_local_ref(data, schemas)
    return None


def asyncapi_event_payloads(asyncapi: dict) -> dict[str, dict[str, dict]]:
    """{message_name: {data_field_name: schema_dict}} parsed from the
    AsyncAPI document.

    Resolves each `components.messages.<Name>` to its payload
    envelope (via `$ref` or inline), then locates the envelope's
    `data` property schema (in `allOf` per CloudEvents convention, or
    inline). Returns the `data` schema's `properties` dict.

    Messages whose payload can't be resolved (e.g. payload is purely
    a `$ref` to an external file) are silently omitted.
    """
    schemas = (asyncapi.get("components") or {}).get("schemas") or {}
    messages = (asyncapi.get("components") or {}).get("messages") or {}

    out: dict[str, dict[str, dict]] = {}
    for msg_name, msg in messages.items():
        if not isinstance(msg, dict):
            continue
        payload = msg.get("payload")
        if not isinstance(payload, dict):
            continue
        envelope = _resolve_local_ref(payload, schemas)
        data_schema = _find_data_property(envelope, schemas)
        if not isinstance(data_schema, dict):
            continue
        props = data_schema.get("properties") or {}
        if isinstance(props, dict):
            out[msg_name] = dict(props)
    return out


def datacontract_record_fields(datacontract: dict) -> dict[str, dict[str, dict]]:
    """{record_name: {field_name: property_dict}} parsed from
    `schema[*].properties[*]` per ODCS convention."""
    out: dict[str, dict[str, dict]] = {}
    for record in datacontract.get("schema") or []:
        if not isinstance(record, dict):
            continue
        name = record.get("name")
        if not name:
            continue
        fields: dict[str, dict] = {}
        for prop in record.get("properties") or []:
            if isinstance(prop, dict) and prop.get("name"):
                fields[prop["name"]] = prop
        out[name] = fields
    return out


def asyncapi_array_item_properties(field_schema: dict, asyncapi: dict) -> set[str] | None:
    """If `field_schema` is an array-of-object schema, return the set
    of property names declared on its items (resolving a `$ref`).

    Returns None if the schema is not `type: array`, or if its items
    cannot be resolved to a property-bearing object schema. Used by
    `EVENT-PAYLOAD-COVERS-ENTITY-STATE` to walk aggregate-child
    collections in an asyncapi event payload."""
    if not isinstance(field_schema, dict):
        return None
    if field_schema.get("type") != "array":
        return None
    items = field_schema.get("items")
    if not isinstance(items, dict):
        return None
    schemas = (asyncapi.get("components") or {}).get("schemas") or {}
    items = _resolve_local_ref(items, schemas)
    props = items.get("properties") or {}
    if not isinstance(props, dict):
        return None
    return set(props.keys())


def datacontract_array_item_properties(field_prop: dict) -> set[str] | None:
    """If `field_prop` is an ODCS array property, return the set of
    item property names. ODCS shape:

        - name: entries
          logicalType: array
          items:
            logicalType: object
            properties:
              - {name: ..., logicalType: ...}

    Returns None if the field isn't an array, or its items don't carry
    a properties list."""
    if not isinstance(field_prop, dict):
        return None
    if field_prop.get("logicalType") != "array":
        return None
    items = field_prop.get("items")
    if not isinstance(items, dict):
        return None
    props = items.get("properties") or []
    if not isinstance(props, list):
        return None
    names: set[str] = set()
    for p in props:
        if isinstance(p, dict) and p.get("name"):
            names.add(p["name"])
    return names if names else None


def datacontract_named_enums(datacontract: dict) -> dict[str, list[str]]:
    """Datacontract field-level enums keyed by enum schema name. Walks
    every record's `properties` list (per ODCS); a property with an
    `enum:` list contributes `{<record-or-schema-name>: [values]}`
    keyed by the property's `$ref` target if one is declared, else
    by the property name. Returns empty dict if no enum-typed
    properties exist."""
    out: dict[str, list[str]] = {}
    for record in datacontract.get("schema") or []:
        if not isinstance(record, dict):
            continue
        for prop in record.get("properties") or []:
            if not isinstance(prop, dict):
                continue
            values = prop.get("enum")
            if isinstance(values, list) and values:
                ref = prop.get("$ref") or prop.get("ref")
                key = ref.rsplit("/", 1)[-1] if isinstance(ref, str) else prop.get("name")
                if key:
                    out[key] = [str(v) for v in values]
    return out
