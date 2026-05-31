"""Audit-time post-processing: respect engagement decisions made at
prior phases.

Per SUITE-DESIGN §6 update mode + the M6.3 finding: the audit re-runs
every cross-reference check at error severity. That's correct when a
spec drifted since sign-off. It's WRONG when a check was legitimately
n-a'd or deferred at its owning phase — re-firing it at audit error
loses the engagement the user already did.

This module reads every `_phase-N-passed.yaml` in the target repo,
builds a map of `check_id → (response, phase)` for any check that was
n-a'd or deferred, and downgrades matching audit outcomes from error
to warning. For each downgraded outcome it synthesises a
`warnings_responded` entry tagged with the prior phase, so the
audit's sign-off doesn't refuse on un-engaged warnings.

The downgrade preserves audit's discoverability — the check still
appears in the audit output as a WARN with a note pointing at the
prior phase's response — without blocking sign-off.
"""

from __future__ import annotations

import pathlib

import yaml

from shared.run_phase import CheckOutcome

PRIOR_PHASES_IN_ORDER = [
    ("bootstrap", 0),
    ("discovery", 1),
    ("modeling", 2),
    ("access-control", 3),
    ("flows", 4),
    ("nfrs", 5),
    ("contracts", 6),
]

CARRY_FORWARD_RESPONSES = {"n-a", "deferred"}


def _sidecar_path(repo: pathlib.Path, phase_num: int) -> pathlib.Path:
    return repo / "docs" / "specifications" / f"_phase-{phase_num}-passed.yaml"


def read_prior_engagement(repo: pathlib.Path) -> dict[str, dict]:
    """Build {check_id: {response, reason, phase}} from every prior
    phase's warnings_responded entries with a carry-forward response."""
    engagement: dict[str, dict] = {}
    for phase_name, phase_num in PRIOR_PHASES_IN_ORDER:
        sidecar = _sidecar_path(repo, phase_num)
        if not sidecar.is_file():
            continue
        doc = yaml.safe_load(sidecar.read_text(encoding="utf-8")) or {}
        for entry in doc.get("warnings_responded") or []:
            if not isinstance(entry, dict):
                continue
            check_id = entry.get("id")
            response = entry.get("response")
            if not check_id or response not in CARRY_FORWARD_RESPONSES:
                continue
            # First phase to address a check wins; later phases would
            # typically be subsequent re-engagements but we don't want
            # to overwrite the original record.
            engagement.setdefault(
                check_id,
                {
                    "response": response,
                    "reason": entry.get("reason", ""),
                    "phase": phase_name,
                    "required_by": entry.get("required_by"),
                },
            )
    return engagement


def apply_prior_engagement(
    outcomes: list[CheckOutcome], engagement: dict[str, dict]
) -> tuple[list[CheckOutcome], list[dict]]:
    """Walk outcomes; for any failed error-severity outcome whose
    check_id is in `engagement`, downgrade to warning and append a
    note. Returns (new_outcomes, synthetic_responses).

    `synthetic_responses` is a list of warnings_responded entries
    sign_off can merge with the user-supplied responses so the
    engagement check passes."""
    new_outcomes: list[CheckOutcome] = []
    synthetic: list[dict] = []

    for outcome in outcomes:
        if (
            not outcome.passed
            and not outcome.skipped
            and outcome.severity == "error"
            and outcome.id in engagement
        ):
            prior = engagement[outcome.id]
            note = (
                f"  · carry-forward: n-a/deferred at phase '{prior['phase']}' "
                f"({prior['response']}) — reason: {prior['reason']}"
            )
            downgraded = CheckOutcome(
                id=outcome.id,
                severity="warning",
                passed=outcome.passed,
                skipped=outcome.skipped,
                message=outcome.message,
                details=list(outcome.details) + [note],
            )
            new_outcomes.append(downgraded)
            synthetic.append(
                {
                    "id": outcome.id,
                    "response": prior["response"],
                    "reason": (f"carried forward from phase '{prior['phase']}': {prior['reason']}"),
                    "required_by": prior.get("required_by"),
                }
            )
        else:
            new_outcomes.append(outcome)

    return new_outcomes, synthetic


def downgraded_exit_code(outcomes: list[CheckOutcome]) -> int:
    """Recompute exit_code after a downgrade pass. Returns 1 if any
    remaining error-severity outcome failed; 0 otherwise."""
    for outcome in outcomes:
        if not outcome.passed and not outcome.skipped and outcome.severity == "error":
            return 1
    return 0
