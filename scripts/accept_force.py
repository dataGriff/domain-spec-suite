"""Mark the most recent unaccepted force-advance entry for a given
phase as accepted, so the audit can pass.

Per SUITE-DESIGN §5/§9: the audit's FORCE-ADVANCES-ALL-ACCEPTED check
fires on any entry with `accepted: false`. Acceptance is an explicit
acknowledgement that the bypass is intentional and reviewed; the
reason is recorded alongside the original.

Usage:

    python scripts/accept_force.py <phase> --reason '<text>' [--repo <path>]
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


def accept_force(repo: pathlib.Path, phase: str, reason: str) -> int:
    progress_path = spec_paths.progress_path(repo)
    if not progress_path.is_file():
        print(f"accept_force: {progress_path} does not exist", file=sys.stderr)
        return 1

    progress = yaml.safe_load(progress_path.read_text()) or {}
    entries = progress.get("force_advances") or []
    pending = [
        (i, e) for i, e in enumerate(entries) if e.get("phase") == phase and not e.get("accepted")
    ]
    if not pending:
        print(
            f"accept_force: no unaccepted force-advance entry found for phase '{phase}'",
            file=sys.stderr,
        )
        return 1

    # Most recent unaccepted entry wins.
    idx, _entry = pending[-1]
    entries[idx]["accepted"] = True
    entries[idx]["accepted_reason"] = reason
    entries[idx]["accepted_at"] = _now()

    progress["force_advances"] = entries
    progress["last_updated"] = _now()
    progress_path.write_text(yaml.safe_dump(progress, sort_keys=False), encoding="utf-8")

    print(
        f"force-advance accepted: phase={phase}, reason={reason!r}. "
        "Audit will now pass over this entry."
    )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mark a force-advance entry as accepted so the audit can pass."
    )
    parser.add_argument("phase", help="Phase id whose unaccepted entry to mark.")
    parser.add_argument("--reason", required=True, help="Why the bypass is accepted.")
    parser.add_argument("--repo", default=".", help="Target domain repo. Defaults to cwd.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo = pathlib.Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"accept_force: target repo does not exist: {repo}", file=sys.stderr)
        return 2
    return accept_force(repo, args.phase, args.reason)


if __name__ == "__main__":
    sys.exit(main())
