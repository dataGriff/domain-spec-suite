#!/usr/bin/env python3
# ruff: noqa: E501
# E501 disabled: embedded HTML/CSS in f-strings, matching
# generate_domain_overview.py's convention.
"""
generate_traceability.py

Reads the spec set (PRD, acceptance scenarios, contracts, error
catalogue) and generates a static HTML traceability matrix at:
  <repo>/docs/specifications/traceability.html

One row per PRD user story: its acceptance scenarios, the operations
and event channels those scenarios exercise, the error codes they
assert — plus informational coverage flags where a story's PRD
acceptance criteria mention a status code or catalogued error code
that none of its scenarios exercises.

The flags are deliberately informational (the page is a view, not a
gate): `US-HAS-SCENARIO` and `OPERATION-HAS-SCENARIO` are the
mechanical checks; this page is where a human sees the shape of the
coverage at a glance.

Run from a spec repo via:  task docs:generate
Run from the suite via:    python scripts/generate_traceability.py --repo <path>
"""

import argparse
import pathlib
import re
import sys
from datetime import UTC, datetime

SUITE_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))

from shared.spec_parsers import (  # noqa: E402
    acceptance_scenario_blocks,
    asyncapi_channels,
    endpoint_mentions,
    error_catalogue_codes,
    load_yaml,
    openapi_operations,
    prd_user_story_blocks,
)


def h(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


STATUS_RE = re.compile(r"\b([245]\d\d)\b")


def parse_stories(prd_path):
    """[(story_id, title, block_text), ...]"""
    out = []
    for block in prd_user_story_blocks(prd_path):
        match = re.match(r"####\s+(US-\d+)(?::\s*(.*))?", block.strip())
        if not match:
            continue
        out.append((match.group(1), (match.group(2) or "").strip(), block))
    return out


def group_scenarios(scenarios_path):
    """{story_id: [(scenario_label, text), ...]} keyed off `Scenario US-xxx-Y` headings.
    Blocks whose heading doesn't carry a US id are grouped under '(cross-cutting)'."""
    grouped = {}
    for block in acceptance_scenario_blocks(scenarios_path):
        heading = block["heading"]
        match = re.match(r"Scenario\s+((US-\d+)-\w+)", heading)
        if match:
            grouped.setdefault(match.group(2), []).append((match.group(1), block["text"]))
        else:
            label = re.sub(r"^Scenario\s+", "", heading).split(":")[0].strip()
            grouped.setdefault("(cross-cutting)", []).append((label, block["text"]))
    return grouped


def operations_in(text, operations):
    """Operations (from openapi) that the text exercises, by operationId or METHOD /path."""
    mentions = endpoint_mentions(text)
    found = []
    for op in operations:
        op_id = op.get("operationId")
        if op_id and op_id in text:
            found.append(f"{op['method']} {op['path']}")
            continue
        if any(m == op["method"] and p == op["path"] for m, p in mentions):
            found.append(f"{op['method']} {op['path']}")
    # Also keep raw mentions that didn't match a declared operation —
    # SCENARIO-REFS-VALID polices these; the matrix just shows them.
    declared = {(op["method"], op["path"]) for op in operations}
    for m, p in mentions:
        if (m, p) not in declared and f"{m} {p}" not in found:
            found.append(f"{m} {p} ⚠")
    seen = set()
    return [x for x in found if not (x in seen or seen.add(x))]


def codes_in(text, catalogue):
    return sorted({code for code in catalogue if code in text})


def channels_in(text, channels):
    return sorted({c for c in channels if c in text})


def build_rows(repo):
    specs = repo / "docs" / "specifications"
    prd = specs / "prd.md"
    scenarios_path = specs / "acceptance-scenarios.md"
    openapi = load_yaml(specs / "contracts" / "openapi.yaml")
    asyncapi_path = specs / "contracts" / "asyncapi.yaml"
    catalogue = error_catalogue_codes(specs / "error-catalogue.md")
    channels = asyncapi_channels(load_yaml(asyncapi_path)) if asyncapi_path.is_file() else []
    operations = openapi_operations(openapi)

    grouped = group_scenarios(scenarios_path)
    rows = []
    for story_id, title, block in parse_stories(prd):
        story_scenarios = grouped.get(story_id, [])
        scenario_text = "\n".join(text for _, text in story_scenarios)

        ac_statuses = set(STATUS_RE.findall(block))
        ac_codes = set(codes_in(block, catalogue))
        covered_statuses = set(STATUS_RE.findall(scenario_text))
        covered_codes = set(codes_in(scenario_text, catalogue))

        flags = []
        if not story_scenarios:
            flags.append("no scenarios")
        else:
            flags.extend(
                f"AC mentions {s} — no scenario asserts it"
                for s in sorted(ac_statuses - covered_statuses)
            )
            flags.extend(
                f"AC mentions {c} — no scenario asserts it"
                for c in sorted(ac_codes - covered_codes)
            )

        rows.append(
            {
                "id": story_id,
                "title": title,
                "scenarios": [label for label, _ in story_scenarios],
                "operations": operations_in(scenario_text, operations),
                "events": channels_in(scenario_text, channels),
                "codes": sorted(covered_codes),
                "flags": flags,
            }
        )
    cross = grouped.get("(cross-cutting)", [])
    return rows, cross


def render(rows, cross, domain_title):
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    total = len(rows)
    with_scenarios = sum(1 for r in rows if r["scenarios"])
    flag_count = sum(len(r["flags"]) for r in rows)

    def cell_list(items, formatter=None):
        if not items:
            return '<span class="none">—</span>'
        formatter = formatter or (lambda x: f"<li>{h(x)}</li>")
        return "<ul>" + "".join(formatter(i) for i in items) + "</ul>"

    body_rows = []
    for r in rows:
        flag_html = (
            '<span class="ok">✓</span>'
            if not r["flags"]
            else "<ul class='flags'>" + "".join(f"<li>{h(f)}</li>" for f in r["flags"]) + "</ul>"
        )
        body_rows.append(
            f"<tr><td class='story'><strong>{h(r['id'])}</strong><br><span class='title'>{h(r['title'])}</span></td>"
            f"<td>{cell_list(r['scenarios'])}</td>"
            f"<td class='mono'>{cell_list(r['operations'])}</td>"
            f"<td class='mono'>{cell_list(r['events'])}</td>"
            f"<td class='mono'>{cell_list(r['codes'])}</td>"
            f"<td>{flag_html}</td></tr>"
        )

    cross_html = ""
    if cross:
        items = "".join(f"<li>{h(label)}</li>" for label, _ in cross)
        cross_html = (
            "<h2>Cross-cutting scenarios</h2>"
            "<p>Scenario sections not tied to a single user story "
            "(authentication failures, rate limiting, idempotency, …):</p>"
            f"<ul class='cross'>{items}</ul>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Traceability — {h(domain_title)}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         background: #0f1419; color: #d6dbe1; margin: 0; padding: 2rem; }}
  h1 {{ color: #fff; margin-top: 0; }}
  .meta {{ color: #7a8794; margin-bottom: 1.5rem; }}
  .summary {{ display: flex; gap: 2rem; margin-bottom: 1.5rem; }}
  .summary div {{ background: #1a2027; border: 1px solid #2b333c; border-radius: 8px;
                  padding: .8rem 1.2rem; }}
  .summary .n {{ font-size: 1.5rem; font-weight: 700; color: #fff; display: block; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #2b333c; padding: .6rem .8rem; text-align: left;
            vertical-align: top; }}
  th {{ background: #1a2027; color: #fff; position: sticky; top: 0; }}
  tr:nth-child(even) {{ background: #131920; }}
  ul {{ margin: 0; padding-left: 1.1rem; }}
  .mono ul, .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
                     font-size: .85rem; }}
  .title {{ color: #9aa7b3; font-size: .85rem; }}
  .none {{ color: #57606a; }}
  .ok {{ color: #49cc90; font-weight: 700; }}
  .flags li {{ color: #fca130; }}
  .cross li {{ color: #9aa7b3; }}
  h2 {{ color: #fff; margin-top: 2rem; }}
</style>
</head>
<body>
<h1>Traceability Matrix — {h(domain_title)}</h1>
<p class="meta">Generated {generated} · story → scenarios → operations → events → error codes.
Flags are informational: they mark status/error codes a story's PRD acceptance criteria
mention that none of its scenarios asserts.</p>
<div class="summary">
  <div><span class="n">{total}</span> user stories</div>
  <div><span class="n">{with_scenarios}</span> with scenarios</div>
  <div><span class="n">{flag_count}</span> coverage flags</div>
</div>
<table>
<thead><tr><th>Story</th><th>Scenarios</th><th>Operations</th><th>Events</th><th>Error codes</th><th>Coverage flags</th></tr></thead>
<tbody>
{"".join(body_rows)}
</tbody>
</table>
{cross_html}
</body>
</html>
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate the traceability matrix HTML page.")
    parser.add_argument("--repo", default=".", help="Spec repo root (default: cwd)")
    parser.add_argument(
        "--output",
        default=None,
        help="Output path (default: <repo>/docs/specifications/traceability.html)",
    )
    args = parser.parse_args(argv)

    repo = pathlib.Path(args.repo).resolve()
    specs = repo / "docs" / "specifications"
    for required in (
        "prd.md",
        "acceptance-scenarios.md",
        "contracts/openapi.yaml",
        "error-catalogue.md",
    ):
        if not (specs / required).is_file():
            print(f"generate_traceability: {specs / required} not found", file=sys.stderr)
            return 1

    rows, cross = build_rows(repo)
    if not rows:
        print("generate_traceability: no user stories found in prd.md", file=sys.stderr)
        return 1

    openapi = load_yaml(specs / "contracts" / "openapi.yaml")
    domain_title = (openapi.get("info") or {}).get("title") or repo.name

    out_path = pathlib.Path(args.output) if args.output else specs / "traceability.html"
    out_path.write_text(render(rows, cross, domain_title), encoding="utf-8")
    flag_count = sum(len(r["flags"]) for r in rows)
    print(f"Wrote {out_path}: {len(rows)} stories, {flag_count} coverage flag(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
