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


def _record_phase_passed(repo: pathlib.Path, phase: str, gate: dict) -> pathlib.Path:
    """Write the sidecar. Returns the path written."""
    sidecar = _sidecar_path(repo, phase)
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar_doc = {
        "phase": phase,
        "signed_off_at": _now(),
        "gate_version": GATE_VERSION,
        "checks_passed": [entry["id"] for entry in gate.get("checks", [])],
        "warnings_responded": [],
        "rubric_findings": [],
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


def sign_off(phase: str, repo: pathlib.Path, *, force_advance: str | None = None) -> int:
    gate = run_phase.load_gate(phase)

    if force_advance is None:
        exit_code, outcomes = run_phase.run_phase(phase, repo)
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
    else:
        _append_force_advance(repo, phase, force_advance)
        print(
            f"force-advance recorded for phase '{phase}' "
            f"(reason: {force_advance}). The audit will fail until this "
            "entry is accepted via `task suite:accept-force`.",
            file=sys.stderr,
        )

    sidecar = _record_phase_passed(repo, phase, gate)
    _bump_progress(repo, phase)
    print(f"sign-off written: {sidecar.relative_to(repo)}")
    return 0


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

    return sign_off(args.phase, repo, force_advance=force_advance_reason)


if __name__ == "__main__":
    sys.exit(main())
