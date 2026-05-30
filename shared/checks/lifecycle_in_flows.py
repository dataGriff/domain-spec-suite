"""Cross-reference check: every state mentioned in a domain-model
lifecycle table appears at least once in sequence-diagrams.md.

This is the lenient form. The strict form (every individual transition
appears in a flow) is more useful but requires the domain to author
explicit reactivation/reversal flows even for trivial toggles. The
v1.0 audit accepts "every state is exercised somewhere" as evidence of
lifecycle coverage; future gate versions may tighten.
"""

from __future__ import annotations

import pathlib

from shared.check_result import CheckResult
from shared.spec_parsers import domain_model_lifecycle_transitions

metadata = {
    "id": "LIFECYCLE-IN-FLOWS",
    "category": "cross-reference",
    "phases": ["flows", "audit"],
    "severity_by_phase": {"flows": "warning", "audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/domain-model.md"},
        {"file_exists": "docs/specifications/sequence-diagrams.md"},
    ],
}


def run(repo_root: pathlib.Path) -> CheckResult:
    domain_model = repo_root / "docs" / "specifications" / "domain-model.md"
    flows = repo_root / "docs" / "specifications" / "sequence-diagrams.md"

    transitions = domain_model_lifecycle_transitions(domain_model)
    states = {state for frm_to in transitions for state in frm_to}
    if not states:
        return CheckResult.ok()  # No lifecycle declared = nothing to cover

    flows_text = flows.read_text(encoding="utf-8")
    missing = [s for s in sorted(states) if s not in flows_text]
    if not missing:
        return CheckResult.ok()

    return CheckResult.fail(
        "Lifecycle states declared in domain-model.md don't appear in "
        "any sequence diagram. Every state an entity can occupy should "
        "show up in at least one flow so readers can see how the system "
        "drives entities between states. Which existing flow exercises "
        "each missing state — or do new flows need to be added?",
        details=[f"state '{s}' not mentioned in sequence-diagrams.md" for s in missing],
    )
