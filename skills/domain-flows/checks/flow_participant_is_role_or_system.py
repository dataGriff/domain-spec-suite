"""Phase 4 soft check: every `participant <name>` in a sequence
diagram is either a known role (from auth-matrix), a known persona
(from PRD), or a recognised system actor (API, EventBus, Worker,
DB, Cache, ExternalAPI, Webhook).

Warning, not error: domain-specific external systems exist that we
can't anticipate (e.g. 'PaymentProcessor', 'EmailService'); the user
can mark these n-a with a one-line reason."""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult
from shared.spec_parsers import _section, prd_persona_names

metadata = {
    "id": "FLOW-PARTICIPANT-IS-ROLE-OR-SYSTEM",
    "category": "structural",
    "phases": ["flows"],
    "severity_by_phase": {"flows": "warning"},
    "prerequisites": [
        {"file_exists": "docs/specifications/sequence-diagrams.md"},
    ],
}

PARTICIPANT_RE = re.compile(r"^\s*participant\s+(?P<name>\S+)", re.MULTILINE)
ROLE_ROW_RE = re.compile(r"^\|\s*`(?P<role>[a-z][a-z0-9_-]*)`\s*\|", re.MULTILINE)

# System actors that are universally recognised in sequence diagrams.
SYSTEM_ACTORS = {
    "api",
    "client",
    "server",
    "user",
    "eventbus",
    "worker",
    "scheduler",
    "db",
    "database",
    "cache",
    "externalapi",
    "webhook",
}


def _known_roles(auth_matrix: pathlib.Path) -> set[str]:
    if not auth_matrix.is_file():
        return set()
    text = auth_matrix.read_text(encoding="utf-8")
    section = _section(text, r"^##\s+Roles\s*$")
    return {match.group("role").lower() for match in ROLE_ROW_RE.finditer(section)}


def run(repo_root: pathlib.Path) -> CheckResult:
    flows = repo_root / "docs/specifications/sequence-diagrams.md"
    auth_matrix = repo_root / "docs/specifications/auth-matrix.md"
    prd = repo_root / "docs/specifications/prd.md"

    text = flows.read_text(encoding="utf-8")
    roles = _known_roles(auth_matrix)
    personas = {p.lower().split()[0] for p in prd_persona_names(prd)}
    accepted = SYSTEM_ACTORS | roles | personas

    problems: list[str] = []
    for match in PARTICIPANT_RE.finditer(text):
        name = match.group("name").strip().lower()
        # Permit common compounding ("APIServer", "AuthAPI") by checking substring matches.
        if any(token in name for token in accepted):
            continue
        problems.append(
            f"participant '{match.group('name')}' isn't a known role, persona, or system actor"
        )

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "Some sequence-diagram participants aren't a known role, "
        "persona, or recognised system actor. For each one below: is "
        "it a real external system the spec set should name (resolve "
        "— add a clarifying note in the flow), or domain-specific "
        "infrastructure that's fine here (mark n-a)?",
        details=problems,
    )
