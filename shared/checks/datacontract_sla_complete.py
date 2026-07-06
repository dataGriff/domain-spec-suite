"""Structural check: the data contract declares the three
load-bearing SLA properties — availability, retention, and
latency (freshness).

The datacontract's own prose claims to serve "reporting, analytics,
downstream sync", but before gate 1.4 the only SLAs a consumer could
rely on were availability and retention. A consumer building on the
historic record needs to know how *fresh* it is — the lag between a
domain transition committing and its event being readable. Values
come from nfr.md (delivery/availability NFRs); this check enforces
presence, not specific numbers."""

from __future__ import annotations

import pathlib

from shared.check_result import CheckResult
from shared.spec_parsers import load_yaml

REQUIRED_SLA_PROPERTIES = ("availability", "retention", "latency")

metadata = {
    "id": "DATACONTRACT-SLA-COMPLETE",
    "category": "structural",
    "phases": ["contracts", "audit"],
    "severity_by_phase": {"contracts": "error", "audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/contracts/datacontract.yaml"},
    ],
}


def run(repo_root: pathlib.Path) -> CheckResult:
    datacontract = load_yaml(
        repo_root / "docs" / "specifications" / "contracts" / "datacontract.yaml"
    )

    declared = set()
    for entry in datacontract.get("slaProperties") or []:
        if isinstance(entry, dict) and entry.get("property"):
            declared.add(str(entry["property"]).strip().lower())

    missing = [p for p in REQUIRED_SLA_PROPERTIES if p not in declared]
    if not missing:
        return CheckResult.ok()

    return CheckResult.fail(
        "The data contract's slaProperties are incomplete — downstream "
        "consumers can't plan against the historic record without "
        "availability, retention, AND latency (freshness: how long "
        "after a domain transition commits is its event readable?). "
        "What is the value for each missing property below? Derive "
        "them from nfr.md's delivery and retention requirements.",
        details=[f"missing slaProperty: {p}" for p in missing],
    )
