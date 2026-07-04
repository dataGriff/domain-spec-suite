"""Dev-only: reset a phase so it can be re-run from scratch.

Per SUITE-DESIGN §11 (open question 1): while iterating on a phase
skill, you need a way to delete the phase's sign-off sidecar and the
output files it signed, and mark the phase not-started again.

What gets deleted:

- every file listed in the sidecar's `files_signed` (falling back to
  the phase gate's `signs_files` when no sidecar exists);
- the `.spec-suite/phases/phase-N-passed.yaml` sidecar itself.

What gets updated:

- `.spec-suite/progress.yaml`: the phase's status becomes
  `not-started` and a `phase-reset` event is appended to the
  session log.

Dry-run by default — prints what would happen. Pass `--yes` to
actually delete. Bootstrap can't be reset here (that's a re-bootstrap:
`task suite:upgrade-shell` or `bootstrap.py --force`).

Usage:

    python scripts/reset_phase.py <phase> [--repo <path>] [--yes]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import pathlib
import sys

import yaml

SUITE_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))

from shared import spec_paths  # noqa: E402
from shared.run_phase import PHASE_TO_SKILL, SKILLS_DIR  # noqa: E402


def _now() -> str:
    return _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def files_to_delete(repo: pathlib.Path, phase: str) -> tuple[list[pathlib.Path], pathlib.Path]:
    """Return ([signed output files that exist], sidecar_path)."""
    sidecar_path = spec_paths.phase_sidecar_path(repo, phase)

    signed_rel: list[str] = []
    if sidecar_path.is_file():
        sidecar = yaml.safe_load(sidecar_path.read_text()) or {}
        signed_rel = [entry["path"] for entry in sidecar.get("files_signed", [])]
    else:
        gate_path = SKILLS_DIR / PHASE_TO_SKILL[phase] / "gate.yaml"
        gate = yaml.safe_load(gate_path.read_text()) or {}
        signed_rel = list(gate.get("signs_files", []))

    outputs = [repo / rel for rel in signed_rel if (repo / rel).is_file()]
    return outputs, sidecar_path


def reset_phase(repo: pathlib.Path, phase: str, *, apply: bool) -> int:
    if phase == "bootstrap":
        print(
            "reset_phase: bootstrap can't be reset — re-run the shell instead "
            "(`task suite:upgrade-shell` or `bootstrap.py --force`).",
            file=sys.stderr,
        )
        return 1
    if phase not in PHASE_TO_SKILL:
        print(
            f"reset_phase: unknown phase {phase!r}. Expected one of: {', '.join(PHASE_TO_SKILL)}",
            file=sys.stderr,
        )
        return 1

    outputs, sidecar_path = files_to_delete(repo, phase)
    verb = "deleting" if apply else "would delete"

    for path in outputs:
        print(f"  {verb} {path.relative_to(repo)}")
        if apply:
            path.unlink()
    if sidecar_path.is_file():
        print(f"  {verb} {sidecar_path.relative_to(repo)}")
        if apply:
            sidecar_path.unlink()

    progress_path = spec_paths.progress_path(repo)
    if progress_path.is_file():
        print(f"  {'marking' if apply else 'would mark'} {phase} not-started in progress.yaml")
        if apply:
            progress = yaml.safe_load(progress_path.read_text()) or {}
            progress.setdefault("phases", {})[phase] = {"status": "not-started"}
            progress["last_updated"] = _now()
            progress.setdefault("session_log", []).append(
                {"timestamp": _now(), "event": "phase-reset", "phase": phase}
            )
            progress_path.write_text(yaml.safe_dump(progress, sort_keys=False), encoding="utf-8")

    if not apply:
        print("\ndry run — nothing changed. Re-run with --yes to apply.")
    else:
        print(f"\nphase {phase!r} reset. Re-run it via the orchestrator or task gate:{phase}.")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reset a phase for from-scratch re-run (dev).")
    parser.add_argument("phase", help="Phase id to reset (e.g. modeling).")
    parser.add_argument("--repo", default=".", help="Target domain repo. Defaults to cwd.")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Actually delete. Without this flag the script only prints what it would do.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo = pathlib.Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"reset_phase: target repo does not exist: {repo}", file=sys.stderr)
        return 2
    return reset_phase(repo, args.phase, apply=args.yes)


if __name__ == "__main__":
    sys.exit(main())
