"""Cross-reference check: every user story in prd.md names a known
persona, a known role, or a recognised pre-onboarding actor.

Personas are taken from the PRD itself (`### Heading` lines under
`## Target Users / Personas`). Roles are extracted from the role enum
in `domain-model.md`. A small allow-list of pre-onboarding actors
("new team member", "registered user", etc.) is also permitted —
these cover authentication stories where the user has no role yet.
"""

from __future__ import annotations

import pathlib
import re

from shared.check_result import CheckResult
from shared.spec_parsers import (
    prd_persona_names,
    prd_user_story_blocks,
)

metadata = {
    "id": "STORY-PERSONA-EXISTS",
    "category": "cross-reference",
    "phases": ["discovery", "audit"],
    "severity_by_phase": {"discovery": "error", "audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/prd.md"},
    ],
}

# "As a <noun phrase>," / "As an <noun phrase>,"
AS_A = re.compile(r"\*\*As an?\*\*\s+([^,\n]+?)\s*,", re.IGNORECASE)

# Pre-onboarding actors that are legitimate for auth/registration stories
# even when no persona/role yet applies.
GENERIC_ACTORS = {
    "new user",
    "new team member",
    "anonymous user",
    "guest",
    "guest user",
    "unauthenticated user",
    "registered user",
    "registered team member",
    "team member",
    "user",
}


def _roles_from_domain_model(domain_model: pathlib.Path) -> set[str]:
    """Best-effort extraction of role enum values from domain-model.md.
    Looks for `role` rows in attribute tables whose Description column
    mentions an enum-style list."""
    if not domain_model.is_file():
        return set()
    text = domain_model.read_text(encoding="utf-8")
    roles: set[str] = set()
    # Match: `role` ... | enum | ... | `contributor` or `viewer` |
    for match in re.finditer(r"`role`[^\n]*\n(?:[^\n]*\n){0,3}", text):
        for code in re.findall(r"`([a-z][a-z0-9_-]+)`", match.group(0)):
            if code != "role":
                roles.add(code)
    # Also try the auth-matrix style "| `contributor` | Can ..." in domain-model
    for match in re.finditer(r"^\|\s*`([a-z][a-z0-9_-]+)`\s*\|", text, re.MULTILINE):
        # Filter for short role-like codes
        code = match.group(1)
        if len(code) < 30 and "-" not in code and code.islower():
            roles.add(code)
    # Strip out obviously-attribute names
    roles.discard("id")
    roles.discard("name")
    roles.discard("status")
    roles.discard("description")
    return roles


def run(repo_root: pathlib.Path) -> CheckResult:
    prd = repo_root / "docs" / "specifications" / "prd.md"
    domain_model = repo_root / "docs" / "specifications" / "domain-model.md"

    personas = {p.lower() for p in prd_persona_names(prd)}
    roles = {r.lower() for r in _roles_from_domain_model(domain_model)}
    accepted = personas | roles | GENERIC_ACTORS

    problems: list[str] = []
    for block in prd_user_story_blocks(prd):
        story_id_match = re.match(r"####\s+(US-\d+)", block)
        story_id = story_id_match.group(1) if story_id_match else "<unknown>"
        actor_match = AS_A.search(block)
        if actor_match is None:
            problems.append(f"{story_id}: no '**As a** <persona>,' line found")
            continue
        actor = actor_match.group(1).strip().lower()
        # Pass if any accepted token appears in the actor phrase
        if any(token in actor for token in accepted):
            continue
        problems.append(
            f"{story_id}: actor '{actor}' isn't a defined persona, role, or pre-onboarding actor"
        )

    if not problems:
        return CheckResult.ok()

    return CheckResult.fail(
        "User stories name actors that aren't defined as personas in "
        "prd.md, roles in domain-model.md, or recognised pre-onboarding "
        "actors. For each story below, what persona is performing the "
        "action — and is it one that's already declared in the PRD?",
        details=problems,
    )
