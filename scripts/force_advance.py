"""Append a force-advance entry to a domain repo's _progress.yaml.

Per SUITE-DESIGN §11 / Decision 5, this is the honesty mechanism for
bypassing a failing hard gate: the bypass gets recorded in
`_progress.yaml`'s `force_advances:` array with `accepted: false`,
and the audit surfaces it until cleared by `task suite:accept-force`.

Usage:

    python scripts/force_advance.py <phase> --reason '<text>' [--repo <path>]
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


def _now() -> str:
    return _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def force_advance(repo: pathlib.Path, phase: str, reason: str) -> int:
    progress_path = spec_paths.progress_path(repo)
    if not progress_path.is_file():
        print(f"force_advance: {progress_path} does not exist", file=sys.stderr)
        return 1

    progress = yaml.safe_load(progress_path.read_text()) or {}
    entries = progress.get("force_advances") or []
    entries.append(
        {
            "phase": phase,
            "reason": reason,
            "forced_at": _now(),
            "operator": "force_advance.py",
            "accepted": False,
        }
    )
    progress["force_advances"] = entries
    progress["last_updated"] = _now()
    progress_path.write_text(yaml.safe_dump(progress, sort_keys=False), encoding="utf-8")

    print(
        f"force-advance recorded: phase={phase}, reason={reason!r}. "
        "The audit will surface this entry until it's accepted via "
        "`task suite:accept-force` or the underlying check is resolved."
    )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record a force-advance entry in _progress.yaml.")
    parser.add_argument("phase", help="Phase id being force-advanced.")
    parser.add_argument("--reason", required=True, help="Why the gate is being bypassed.")
    parser.add_argument("--repo", default=".", help="Target domain repo. Defaults to cwd.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo = pathlib.Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"force_advance: target repo does not exist: {repo}", file=sys.stderr)
        return 2
    return force_advance(repo, args.phase, args.reason)


if __name__ == "__main__":
    sys.exit(main())
