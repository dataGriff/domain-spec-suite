"""Copy the blank template skeletons for an authoring phase into
their canonical `docs/specifications/` paths, *only* for files that
don't already exist.

Used by phases that produce content files (discovery, modeling,
access-control, flows, nfrs, contracts). Each phase's `gate.yaml`
declares `signs_files:` — the canonical destination paths. The
matching template lives under the suite's own `templates/` directory
with the same sub-path beneath `docs/specifications/`. So:

    docs/specifications/contracts/openapi.yaml
      ←  <suite-root>/templates/contracts/openapi.yaml

Templates live in the suite (not in each spec repo) because they're
versioned alongside the gate code that consumes their outputs, and
because a completed spec repo doesn't need its own copy of the
blanks.

Idempotent: re-running against a partially-populated repo only fills
in the missing files; never overwrites user-authored content. That's
the load-bearing safety guarantee — the agent invokes this freely
without worrying about clobbering work.

Pass `all` as the phase to lay down every authoring-phase template
in one shot (used by `task domain:init`).
"""

from __future__ import annotations

import argparse
import pathlib
import shutil
import sys

SUITE_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))

from shared import run_phase  # noqa: E402

SPECS_PREFIX = "docs/specifications/"
TEMPLATES_DIR = SUITE_ROOT / "templates"

AUTHORING_PHASES = (
    "discovery",
    "modeling",
    "access-control",
    "flows",
    "nfrs",
    "contracts",
)


def template_source_for(dest_rel: str) -> pathlib.Path | None:
    """Map a `signs_files:` entry to its template source path in the
    suite. Returns None for entries that aren't under
    docs/specifications/ (no template convention applies)."""
    if not dest_rel.startswith(SPECS_PREFIX):
        return None
    sub_path = dest_rel[len(SPECS_PREFIX) :]
    return TEMPLATES_DIR / sub_path


def init_phase(repo: pathlib.Path, phase: str) -> int:
    gate = run_phase.load_gate(phase)
    signs_files = gate.get("signs_files", [])
    if not signs_files:
        print(f"init_phase: {phase} has no signs_files — nothing to do.")
        return 0

    copied: list[str] = []
    skipped_present: list[str] = []
    missing_template: list[pathlib.Path] = []

    for dest_rel in signs_files:
        template = template_source_for(dest_rel)
        if template is None:
            # signs_files entry that isn't a docs/specifications/ path
            # — no template convention to apply.
            continue

        dest = repo / dest_rel

        if dest.is_file():
            skipped_present.append(dest_rel)
            continue
        if not template.is_file():
            missing_template.append(template)
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(template, dest)
        copied.append(dest_rel)

    for path in copied:
        print(f"  COPIED  {path}")
    for path in skipped_present:
        print(f"  SKIP    {path}  (already exists)")
    for path in missing_template:
        print(f"  MISSING {path}  (template not present in suite)", file=sys.stderr)

    print(
        f"\n{len(copied)} copied, {len(skipped_present)} skipped, "
        f"{len(missing_template)} missing template{'s' if len(missing_template) != 1 else ''}"
    )
    return 0 if not missing_template else 1


def init_all(repo: pathlib.Path) -> int:
    rc = 0
    for phase in AUTHORING_PHASES:
        print(f"== {phase} ==")
        result = init_phase(repo, phase)
        if result != 0:
            rc = result
        print()
    return rc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Copy a phase's blank template files into their docs/specifications/ "
            "destinations from the suite's templates/ directory."
        )
    )
    parser.add_argument(
        "phase",
        help="Phase id (e.g. contracts), or 'all' for every authoring phase.",
    )
    parser.add_argument("--repo", default=".", help="Target domain repo. Defaults to cwd.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo = pathlib.Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"init_phase: target repo does not exist: {repo}", file=sys.stderr)
        return 2
    if args.phase == "all":
        return init_all(repo)
    return init_phase(repo, args.phase)


if __name__ == "__main__":
    sys.exit(main())
