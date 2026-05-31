"""Copy the blank template skeletons for an authoring phase into
their canonical `docs/specifications/` paths, *only* for files that
don't already exist.

Used by phases that produce content files (discovery, modeling,
access-control, flows, nfrs, contracts). Each phase's `gate.yaml`
declares `signs_files:` — the canonical destination paths. The
matching template lives under `.spec-suite/templates/` with the
same sub-path beneath `docs/specifications/`. So:

    docs/specifications/contracts/openapi.yaml
      ←  .spec-suite/templates/contracts/openapi.yaml

Idempotent: re-running against a partially-populated repo only fills
in the missing files; never overwrites user-authored content. That's
the load-bearing safety guarantee — the agent invokes this freely
without worrying about clobbering work.
"""

from __future__ import annotations

import argparse
import pathlib
import shutil
import sys

SUITE_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))

from shared import run_phase, spec_paths  # noqa: E402

SPECS_PREFIX = "docs/specifications/"


def template_path_for(dest_rel: str) -> str | None:
    """Map a `signs_files:` entry to its template source. Returns None
    for entries that aren't under docs/specifications/ (no template
    convention applies)."""
    if not dest_rel.startswith(SPECS_PREFIX):
        return None
    # Templates live in .spec-suite/templates/ with the same sub-path
    # beneath docs/specifications/ stripped.
    return f"{spec_paths.STATE_DIRNAME}/templates/" + dest_rel[len(SPECS_PREFIX) :]


def init_phase(repo: pathlib.Path, phase: str) -> int:
    gate = run_phase.load_gate(phase)
    signs_files = gate.get("signs_files", [])
    if not signs_files:
        print(f"init_phase: {phase} has no signs_files — nothing to do.")
        return 0

    copied: list[str] = []
    skipped_present: list[str] = []
    missing_template: list[str] = []

    for dest_rel in signs_files:
        template_rel = template_path_for(dest_rel)
        if template_rel is None:
            # signs_files entry that isn't a docs/specifications/ path
            # — no template convention to apply.
            continue

        dest = repo / dest_rel
        template = repo / template_rel

        if dest.is_file():
            skipped_present.append(dest_rel)
            continue
        if not template.is_file():
            missing_template.append(template_rel)
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(template, dest)
        copied.append(dest_rel)

    for path in copied:
        print(f"  COPIED  {path}")
    for path in skipped_present:
        print(f"  SKIP    {path}  (already exists)")
    for path in missing_template:
        print(f"  MISSING {path}  (template not present in this repo)", file=sys.stderr)

    print(
        f"\n{len(copied)} copied, {len(skipped_present)} skipped, "
        f"{len(missing_template)} missing template{'s' if len(missing_template) != 1 else ''}"
    )
    return 0 if not missing_template else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy a phase's _template/ files into their docs/specifications/ destinations."
    )
    parser.add_argument("phase", help="Phase id (e.g. contracts).")
    parser.add_argument("--repo", default=".", help="Target domain repo. Defaults to cwd.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo = pathlib.Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"init_phase: target repo does not exist: {repo}", file=sys.stderr)
        return 2
    return init_phase(repo, args.phase)


if __name__ == "__main__":
    sys.exit(main())
