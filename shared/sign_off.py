"""The only path that writes `_phase-N-passed.yaml`.

Per SUITE-DESIGN §5.5, mechanical enforcement is non-negotiable:
sign-off MUST run the phase's gate, and MUST refuse to write the
sidecar if the gate exits non-zero. The single exception is
`--force-advance`, which records the bypass loudly in
`_progress.yaml` so the audit surfaces it until accepted.

Usage:

    python shared/sign_off.py <phase> [--repo <path>]
    python shared/sign_off.py <phase> --force-advance --reason '<text>'
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import pathlib
import sys

SUITE_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))

import yaml  # noqa: E402

from shared import run_phase  # noqa: E402

SUITE_VERSION = yaml.safe_load((SUITE_ROOT / "suite-version.yaml").read_text())["suite_version"]
GATE_VERSION = yaml.safe_load((SUITE_ROOT / "gate-version.yaml").read_text())["gate_version"]


# ── helpers ──────────────────────────────────────────────────────


def _now() -> str:
    return _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _sidecar_path(repo: pathlib.Path, phase: str) -> pathlib.Path:
    phase_num = {
        "bootstrap": 0,
        "discovery": 1,
        "modeling": 2,
        "access-control": 3,
        "flows": 4,
        "nfrs": 5,
        "contracts": 6,
        "audit": 7,
    }[phase]
    return repo / "docs" / "specifications" / f"_phase-{phase_num}-passed.yaml"


def _progress_path(repo: pathlib.Path) -> pathlib.Path:
    return repo / "docs" / "specifications" / "_progress.yaml"


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _files_signed(repo: pathlib.Path, gate: dict) -> list[dict]:
    """Build the files_signed block for a sign-off sidecar."""
    entries = []
    for rel in gate.get("signs_files", []):
        target = repo / rel
        if not target.is_file():
            raise FileNotFoundError(
                f"sign_off: gate.yaml lists '{rel}' under signs_files but the file doesn't exist"
            )
        entries.append(
            {
                "path": rel,
                "sha256": _sha256(target),
                "mtime": _now(),  # human-only; not consulted by SIGNOFF-SHA256-MATCHES
            }
        )
    return entries


def _stamp_ts(entries: list[dict]) -> list[dict]:
    """Fill in `ts` for any entry that doesn't carry one. The agent
    supplies the verdict and rationale; sign_off owns the timestamp so
    every entry is anchored to the sign-off moment."""
    stamped: list[dict] = []
    now = _now()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(f"sign_off: findings entry must be a mapping, got {entry!r}")
        out = dict(entry)
        out.setdefault("ts", now)
        stamped.append(out)
    return stamped


_REQUIRED_DECISION_FIELDS = ("id", "summary", "rationale")


def _validate_decisions(decisions: list[dict]) -> tuple[bool, str | None]:
    """Each decision must have id, summary, rationale. Returns
    (True, None) on pass, (False, msg) on failure."""
    problems: list[str] = []
    for entry in decisions:
        if not isinstance(entry, dict):
            return False, f"decisions entry must be a mapping, got {entry!r}"
        missing = [f for f in _REQUIRED_DECISION_FIELDS if not entry.get(f)]
        if missing:
            problems.append(
                f"  · decision {entry.get('id', '<no id>')!r} missing "
                f"required field(s): {', '.join(missing)}"
            )
    if problems:
        return False, "decisions entries are malformed:\n" + "\n".join(problems)
    return True, None


def _record_phase_passed(
    repo: pathlib.Path,
    phase: str,
    gate: dict,
    *,
    rubric_findings: list[dict] | None = None,
    warnings_responded: list[dict] | None = None,
    decisions: list[dict] | None = None,
) -> pathlib.Path:
    """Write the sidecar. Returns the path written.

    `rubric_findings` and `warnings_responded` are the agent's record of
    the rubric pass and the soft-gate engagement loop, respectively.
    Both default to an empty list — that's correct for hard-gate phases
    with no rubric (bootstrap, audit) and acceptable for hard-gate
    phases whose rubric findings are all `pass` and not surfaced to the
    user, but the agent SHOULD pass them through any time it evaluated
    a rubric (per SUITE-DESIGN §5.5).

    `decisions` is the agent-emitted Decision Log — semantic choices the
    agent made that aren't surfaced by any check or rubric (entity
    split-vs-collapse, FK-vs-copy denormalization, snapshot timing,
    etc.). Empty list for hard-gate phases is fine; soft-middle and
    contracts phases SHOULD carry decisions any time the agent chose
    between defensible alternatives. See per-skill SKILL.md §Decision
    Log for the decision-prone areas per phase.
    """
    sidecar = _sidecar_path(repo, phase)
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar_doc = {
        "phase": phase,
        "signed_off_at": _now(),
        "gate_version": GATE_VERSION,
        "checks_passed": [entry["id"] for entry in gate.get("checks", [])],
        "warnings_responded": _stamp_ts(warnings_responded or []),
        "rubric_findings": _stamp_ts(rubric_findings or []),
        "decisions": _stamp_ts(decisions or []),
        "files_signed": _files_signed(repo, gate),
    }
    sidecar.write_text(yaml.safe_dump(sidecar_doc, sort_keys=False), encoding="utf-8")
    return sidecar


def _bump_progress(repo: pathlib.Path, phase: str) -> None:
    progress_path = _progress_path(repo)
    if not progress_path.is_file():
        return  # nothing to update (test fixtures may sign without progress)
    progress = yaml.safe_load(progress_path.read_text()) or {}
    progress.setdefault("phases", {})[phase] = {
        "status": "passed",
        "signed_off_at": _now(),
        "gate_version": GATE_VERSION,
    }
    progress["last_updated"] = _now()
    progress.setdefault("session_log", []).append(
        {"timestamp": _now(), "event": "phase-passed", "phase": phase}
    )
    progress_path.write_text(yaml.safe_dump(progress, sort_keys=False), encoding="utf-8")


def _append_force_advance(repo: pathlib.Path, phase: str, reason: str) -> None:
    progress_path = _progress_path(repo)
    progress = yaml.safe_load(progress_path.read_text()) if progress_path.is_file() else {}
    if not isinstance(progress, dict):
        progress = {}
    fas = progress.get("force_advances") or []
    fas.append(
        {
            "phase": phase,
            "reason": reason,
            "forced_at": _now(),
            "operator": "sign_off.py",
            "accepted": False,
        }
    )
    progress["force_advances"] = fas
    progress["last_updated"] = _now()
    progress_path.write_text(yaml.safe_dump(progress, sort_keys=False), encoding="utf-8")


# ── main orchestration ──────────────────────────────────────────


_VALID_WARNING_RESPONSES = {"resolved", "deferred", "n-a"}


def _validate_warnings_engagement(
    outcomes: list, warnings_responded: list[dict]
) -> tuple[bool, str | None]:
    """Soft-gate engagement check: every check that fired at warning
    severity must have a corresponding entry in `warnings_responded`,
    and every responded entry must reference a real warning that fired.

    Returns (True, None) when the engagement is complete; (False, msg)
    with a multi-line interview-style refusal message otherwise.
    """
    fired_warnings = {
        o.id for o in outcomes if not o.passed and not o.skipped and o.severity == "warning"
    }
    responded_ids = {entry.get("id") for entry in warnings_responded if entry.get("id")}

    missing = fired_warnings - responded_ids
    stale = responded_ids - fired_warnings

    if not missing and not stale:
        # Check response values are valid.
        bad_responses = [
            entry
            for entry in warnings_responded
            if entry.get("response") not in _VALID_WARNING_RESPONSES
        ]
        if bad_responses:
            return False, (
                "warnings_responded entries have invalid `response` values. "
                f"Each must be one of {sorted(_VALID_WARNING_RESPONSES)}.\n  · "
                + "\n  · ".join(
                    f"{e.get('id', '<?>')}: response={e.get('response')!r}" for e in bad_responses
                )
            )
        # Check deferred entries carry required_by.
        bad_deferred = [
            entry
            for entry in warnings_responded
            if entry.get("response") == "deferred" and not entry.get("required_by")
        ]
        if bad_deferred:
            return False, (
                "deferred warnings must declare `required_by: <phase>`\n  · "
                + "\n  · ".join(f"{e.get('id', '<?>')}" for e in bad_deferred)
            )
        return True, None

    lines: list[str] = ["soft-gate engagement is incomplete:"]
    if missing:
        lines.append(
            f"  · {len(missing)} warning(s) surfaced by the gate have no "
            "response in warnings_responded:"
        )
        for wid in sorted(missing):
            lines.append(f"      - {wid}")
    if stale:
        lines.append(
            f"  · {len(stale)} response(s) in warnings_responded reference "
            "warnings that didn't fire (stale — were they cleared by a recent "
            "edit?):"
        )
        for wid in sorted(stale):
            lines.append(f"      - {wid}")
    lines.append("")
    lines.append(
        "For each surfaced warning, add an entry to warnings_responded "
        "via --findings with `response: resolved | deferred | n-a` and a "
        "`reason`. Deferred warnings additionally need `required_by: <phase>`."
    )
    return False, "\n".join(lines)


def sign_off(
    phase: str,
    repo: pathlib.Path,
    *,
    force_advance: str | None = None,
    rubric_findings: list[dict] | None = None,
    warnings_responded: list[dict] | None = None,
    decisions: list[dict] | None = None,
) -> int:
    gate = run_phase.load_gate(phase)

    if decisions:
        ok, msg = _validate_decisions(decisions)
        if not ok:
            print(f"sign-off REFUSED: {msg}", file=sys.stderr)
            return 1

    if force_advance is None:
        exit_code, outcomes = run_phase.run_phase(phase, repo)

        # Audit-phase post-processing: respect prior-phase engagement.
        # Cross-ref checks n-a'd / deferred at their owning phase get
        # downgraded from error → warning at audit, with a carry-forward
        # response auto-synthesised so the engagement check passes.
        synthetic_responses: list[dict] = []
        if phase == "audit":
            from shared import prior_engagement

            engagement = prior_engagement.read_prior_engagement(repo)
            outcomes, synthetic_responses = prior_engagement.apply_prior_engagement(
                outcomes, engagement
            )
            exit_code = prior_engagement.downgraded_exit_code(outcomes)

        if exit_code != 0:
            print(
                f"sign-off REFUSED: {phase} gate did not pass.\n"
                f"{run_phase.render(phase, repo, outcomes)}",
                file=sys.stderr,
            )
            print(
                "\nFix the failing checks and re-run sign-off, or — in a "
                "genuine emergency — run with --force-advance --reason "
                "'<text>' (the audit will surface this until cleared by "
                "task suite:accept-force).",
                file=sys.stderr,
            )
            return 1

        # Soft-gate engagement check: even when the runner exits 0,
        # any warning-severity check that fired must have an explicit
        # response in warnings_responded. Synthetic responses
        # (carry-forwards from prior phases) merge with user-supplied ones.
        combined_responses = list(warnings_responded or []) + synthetic_responses
        ok, msg = _validate_warnings_engagement(outcomes, combined_responses)
        if not ok:
            print(f"sign-off REFUSED: {msg}", file=sys.stderr)
            return 1

        # If audit synthesised carry-forwards and the user didn't override
        # them, fold them into warnings_responded so the sidecar records
        # the engagement explicitly.
        if synthetic_responses and not warnings_responded:
            warnings_responded = synthetic_responses
        elif synthetic_responses:
            user_ids = {entry.get("id") for entry in warnings_responded or []}
            warnings_responded = list(warnings_responded or []) + [
                entry for entry in synthetic_responses if entry.get("id") not in user_ids
            ]
    else:
        _append_force_advance(repo, phase, force_advance)
        print(
            f"force-advance recorded for phase '{phase}' "
            f"(reason: {force_advance}). The audit will fail until this "
            "entry is accepted via `task suite:accept-force`.",
            file=sys.stderr,
        )

    sidecar = _record_phase_passed(
        repo,
        phase,
        gate,
        rubric_findings=rubric_findings,
        warnings_responded=warnings_responded,
        decisions=decisions,
    )
    _bump_progress(repo, phase)
    print(f"sign-off written: {sidecar.relative_to(repo)}")
    return 0


def _load_findings_file(path: pathlib.Path) -> tuple[list[dict], list[dict], list[dict]]:
    """Load rubric_findings + warnings_responded + decisions from a YAML
    file the agent writes before invoking sign_off. Returns
    ([], [], []) on missing keys. Validates shape: top-level must be a
    mapping with at most those three keys."""
    if not path.is_file():
        raise FileNotFoundError(f"sign_off: --findings file does not exist: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(
            f"sign_off: --findings file must contain a YAML mapping, got {type(data).__name__}"
        )
    allowed = {"rubric_findings", "warnings_responded", "decisions"}
    extra = set(data.keys()) - allowed
    if extra:
        raise ValueError(
            f"sign_off: --findings file has unknown keys {sorted(extra)}; "
            f"only {sorted(allowed)} are accepted"
        )
    rf = data.get("rubric_findings") or []
    wr = data.get("warnings_responded") or []
    dc = data.get("decisions") or []
    if not all(isinstance(x, list) for x in (rf, wr, dc)):
        raise ValueError(
            "sign_off: rubric_findings, warnings_responded, and decisions must be YAML lists"
        )
    return rf, wr, dc


# ── CLI ──────────────────────────────────────────────────────────


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mechanically sign off a phase against a domain repo."
    )
    parser.add_argument("phase", help="Phase id (e.g. contracts).")
    parser.add_argument("--repo", default=".", help="Target domain repo. Defaults to cwd.")
    parser.add_argument(
        "--force-advance",
        action="store_true",
        help="Sign off despite a failing gate. Requires --reason.",
    )
    parser.add_argument(
        "--reason",
        help="Required when --force-advance is set; recorded on the entry.",
    )
    parser.add_argument(
        "--findings",
        help=(
            "Path to a YAML file with `rubric_findings:`, "
            "`warnings_responded:`, and/or `decisions:` keys. Written into "
            "the sidecar verbatim (sign_off only stamps `ts` if absent). "
            "Use this to record the agent's rubric verdicts, soft-gate "
            "engagement responses, and the Decision Log of semantic choices."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo = pathlib.Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"sign_off: target repo does not exist: {repo}", file=sys.stderr)
        return 2

    force_advance_reason: str | None = None
    if args.force_advance:
        if not args.reason:
            print("sign_off: --force-advance requires --reason '<text>'", file=sys.stderr)
            return 2
        force_advance_reason = args.reason

    rubric_findings: list[dict] | None = None
    warnings_responded: list[dict] | None = None
    decisions: list[dict] | None = None
    if args.findings:
        try:
            rubric_findings, warnings_responded, decisions = _load_findings_file(
                pathlib.Path(args.findings).resolve()
            )
        except (FileNotFoundError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 2

    return sign_off(
        args.phase,
        repo,
        force_advance=force_advance_reason,
        rubric_findings=rubric_findings,
        warnings_responded=warnings_responded,
        decisions=decisions,
    )


if __name__ == "__main__":
    sys.exit(main())
