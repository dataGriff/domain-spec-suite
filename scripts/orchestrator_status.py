"""Machine-readable state report the orchestrator uses on every
invocation (SUITE-DESIGN §3 + §6).

Reads a target domain repo and returns a structured snapshot:

- whether the repo has been bootstrapped at all
- per-phase status: not-started | in-progress | passed | stale
- pending force-advances awaiting acceptance
- recommended next action (start phase N, resume phase N, run update
  mode, declare complete, …)

The orchestrator SKILL.md invokes this and turns its output into
user-facing prose. Keeping the logic in Python (not in the skill
prompt) is the same mechanical-enforcement promise we apply to
sign-off: the agent can't drift on "what phase am I in".

CLI:

    python scripts/orchestrator_status.py [--repo <path>] [--json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from dataclasses import asdict, dataclass, field

SUITE_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))

import yaml  # noqa: E402

from shared import spec_paths  # noqa: E402

PHASE_ORDER = [
    "bootstrap",
    "discovery",
    "modeling",
    "access-control",
    "flows",
    "nfrs",
    "contracts",
    "audit",
]

PHASE_NUMBER = {name: i for i, name in enumerate(PHASE_ORDER)}

# Phases whose skills are implemented in the suite today. Phases not
# in this set are reported as `not_implemented` so the orchestrator
# can tell the user honestly rather than silently routing into a stub.
# Currently exhaustive (all 8 phases shipped), so the not-implemented
# routing below is unreachable — kept as the guard for any future
# phase added to PHASE_ORDER before its skill lands.
IMPLEMENTED_PHASES: set[str] = {
    "bootstrap",
    "discovery",
    "modeling",
    "access-control",
    "flows",
    "nfrs",
    "contracts",
    "audit",
}


@dataclass
class PhaseStatus:
    phase: str
    number: int
    status: str  # not-started | in-progress | passed | stale | not-implemented
    implemented: bool
    signed_off_at: str | None = None
    gate_version: str | None = None
    stale_files: list[str] = field(default_factory=list)


@dataclass
class StatusReport:
    repo: str
    bootstrapped: bool
    suite_version: str | None
    gate_version: str | None
    domain_name: str | None
    phases: list[PhaseStatus]
    pending_force_advances: list[dict]
    next_action: dict


# ── helpers ──────────────────────────────────────────────────────


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sidecar_path(repo: pathlib.Path, phase: str) -> pathlib.Path:
    return spec_paths.phase_sidecar_path(repo, phase)


def _progress(repo: pathlib.Path) -> dict | None:
    progress_path = spec_paths.progress_path(repo)
    if not progress_path.is_file():
        return None
    return yaml.safe_load(progress_path.read_text()) or {}


def _read_sidecar(repo: pathlib.Path, phase: str) -> dict | None:
    sidecar = _sidecar_path(repo, phase)
    if not sidecar.is_file():
        return None
    return yaml.safe_load(sidecar.read_text()) or {}


def _stale_files(repo: pathlib.Path, sidecar: dict) -> list[str]:
    """Files whose current sha256 differs from the recorded value."""
    drift: list[str] = []
    for entry in sidecar.get("files_signed", []):
        path_rel = entry.get("path")
        expected = entry.get("sha256")
        if not path_rel or not expected:
            continue
        target = repo / path_rel
        if not target.is_file():
            drift.append(f"{path_rel} (missing)")
            continue
        if _sha256(target) != expected:
            drift.append(path_rel)
    return drift


def _phase_status(repo: pathlib.Path, progress: dict, phase: str) -> PhaseStatus:
    implemented = phase in IMPLEMENTED_PHASES
    progress_entry = (progress.get("phases", {}) or {}).get(phase, {}) or {}
    sidecar = _read_sidecar(repo, phase)

    # If the sidecar exists, treat the phase as passed (or stale if the
    # files have drifted). The progress file's status is advisory but
    # the sidecar + sha256 is authoritative per SUITE-DESIGN §6.
    if sidecar is not None:
        drift = _stale_files(repo, sidecar)
        if drift:
            return PhaseStatus(
                phase=phase,
                number=PHASE_NUMBER[phase],
                status="stale",
                implemented=implemented,
                signed_off_at=sidecar.get("signed_off_at"),
                gate_version=sidecar.get("gate_version"),
                stale_files=drift,
            )
        return PhaseStatus(
            phase=phase,
            number=PHASE_NUMBER[phase],
            status="passed",
            implemented=implemented,
            signed_off_at=sidecar.get("signed_off_at"),
            gate_version=sidecar.get("gate_version"),
        )

    # No sidecar — defer to progress file's status if any, else
    # not-started.
    declared = progress_entry.get("status")
    if declared == "in-progress":
        return PhaseStatus(
            phase=phase,
            number=PHASE_NUMBER[phase],
            status="in-progress",
            implemented=implemented,
        )

    return PhaseStatus(
        phase=phase,
        number=PHASE_NUMBER[phase],
        status="not-started",
        implemented=implemented,
    )


def _pending_force_advances(progress: dict) -> list[dict]:
    entries = progress.get("force_advances") or []
    return [e for e in entries if not e.get("accepted")]


def _next_action(phases: list[PhaseStatus], pending_force: list[dict]) -> dict:
    """Decide what the orchestrator should propose next."""
    # Any stale phase: enter update mode.
    stale = [p for p in phases if p.status == "stale"]
    if stale:
        first_stale = stale[0]
        return {
            "action": "update-mode",
            "phase": first_stale.phase,
            "summary": (
                f"{len(stale)} phase(s) stale — {first_stale.phase} has "
                f"{len(first_stale.stale_files)} file(s) whose sha256 has drifted "
                "since sign-off. Walk the user through the three update-mode "
                "options (targeted / full / audit-only)."
            ),
            "stale_phases": [s.phase for s in stale],
        }

    # Any in-progress phase: resume it.
    in_progress = [p for p in phases if p.status == "in-progress"]
    if in_progress:
        first = in_progress[0]
        return {
            "action": "resume",
            "phase": first.phase,
            "summary": f"resume in-progress phase {first.phase} (Phase {first.number}).",
        }

    # Pending force-advances even on otherwise-passed phases: surface
    # them before declaring complete.
    if pending_force:
        return {
            "action": "accept-force-advances",
            "phase": "audit",
            "summary": (
                f"{len(pending_force)} unaccepted force-advance(s) on file. "
                "Audit will fail until they are accepted via "
                "`task suite:accept-force`."
            ),
            "pending": [fa.get("phase") for fa in pending_force],
        }

    # Find the first not-started phase in order.
    for p in phases:
        if p.status == "not-started":
            if not p.implemented:
                return {
                    "action": "not-implemented",
                    "phase": p.phase,
                    "summary": (
                        f"Phase {p.number} ({p.phase}) is next, but the suite "
                        "doesn't implement that skill yet. Tell the user honestly "
                        "rather than routing into a stub."
                    ),
                }
            return {
                "action": "start",
                "phase": p.phase,
                "summary": f"start phase {p.phase} (Phase {p.number}).",
            }

    # Every phase passed including audit.
    return {
        "action": "complete",
        "phase": "audit",
        "summary": "Spec set complete — every phase signed off and the audit is green.",
    }


def build_report(repo: pathlib.Path) -> StatusReport:
    progress = _progress(repo)
    bootstrapped = progress is not None
    if not bootstrapped:
        # Fresh / un-bootstrapped repo. Return a minimal report whose
        # next_action is "bootstrap this thing".
        return StatusReport(
            repo=str(repo),
            bootstrapped=False,
            suite_version=None,
            gate_version=None,
            domain_name=None,
            phases=[],
            pending_force_advances=[],
            next_action={
                "action": "bootstrap",
                "phase": "bootstrap",
                "summary": (
                    "No .spec-suite/progress.yaml found — this looks like a fresh domain. "
                    "Confirm with the user and route to the domain-bootstrap skill."
                ),
            },
        )

    phase_reports = [_phase_status(repo, progress, p) for p in PHASE_ORDER]
    pending = _pending_force_advances(progress)
    return StatusReport(
        repo=str(repo),
        bootstrapped=True,
        suite_version=progress.get("suite_version"),
        gate_version=progress.get("gate_version"),
        domain_name=progress.get("domain_name"),
        phases=phase_reports,
        pending_force_advances=pending,
        next_action=_next_action(phase_reports, pending),
    )


# ── rendering ────────────────────────────────────────────────────


def render_text(report: StatusReport) -> str:
    lines: list[str] = []
    lines.append(f"=== orchestrator status — {report.repo} ===")
    if not report.bootstrapped:
        lines.append("  bootstrapped: NO  (no .spec-suite/progress.yaml)")
        lines.append(f"  next: {report.next_action['summary']}")
        return "\n".join(lines)

    domain = report.domain_name or "<unnamed>"
    lines.append(f"  domain: {domain}  suite={report.suite_version}  gate={report.gate_version}")
    for p in report.phases:
        impl = "" if p.implemented else "  [skill not yet implemented]"
        marker = {
            "passed": "PASS",
            "stale": "STALE",
            "in-progress": "WIP ",
            "not-started": "TODO",
        }.get(p.status, p.status.upper())
        lines.append(f"  {marker}  Phase {p.number} {p.phase}{impl}")
        if p.stale_files:
            for f in p.stale_files:
                lines.append(f"           · drift: {f}")

    if report.pending_force_advances:
        lines.append("")
        lines.append("  pending force-advances:")
        for fa in report.pending_force_advances:
            lines.append(
                f"    · {fa.get('phase')} — {fa.get('reason')!r} (forced {fa.get('forced_at')})"
            )

    lines.append("")
    lines.append(f"  next action: {report.next_action['action']}")
    lines.append(f"               {report.next_action['summary']}")
    return "\n".join(lines)


# ── CLI ──────────────────────────────────────────────────────────


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report orchestrator-relevant state for a target domain repo."
    )
    parser.add_argument("--repo", default=".", help="Target domain repo. Defaults to cwd.")
    parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON instead of text."
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo = pathlib.Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"orchestrator_status: target repo does not exist: {repo}", file=sys.stderr)
        return 2
    report = build_report(repo)
    if args.json:
        print(json.dumps(asdict(report), indent=2))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
