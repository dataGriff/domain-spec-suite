"""Migrate an existing spec repo from the old layout (underscore-
prefixed bookkeeping mixed into `docs/specifications/`) to the new
`.spec-suite/` layout.

Moves the following:

    docs/specifications/_progress.yaml         → .spec-suite/progress.yaml
    docs/specifications/_bootstrap.yaml        → .spec-suite/bootstrap.yaml
    docs/specifications/_ambiguities.md        → .spec-suite/ambiguities.md
    docs/specifications/_template_manifest.yaml → .spec-suite/template-manifest.yaml
    docs/specifications/_phase-N-passed.yaml   → .spec-suite/phases/phase-N-passed.yaml
    docs/specifications/_review-<ts>.md        → .spec-suite/reviews/<ts>.md
    docs/specifications/_template/             → .spec-suite/templates/

`docs/specifications/` is left with only spec content
(prd.md, domain-model.md, ... contracts/, generated HTML).

Idempotent: refuses to overwrite an existing populated `.spec-suite/`
unless `--force` is set. Re-runs on an already-migrated repo report
"already migrated" and exit 0.

Usage:

    python scripts/migrate_to_spec_suite_dir.py --repo <target>
    python scripts/migrate_to_spec_suite_dir.py --repo <target> --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import shutil
import sys

import yaml

SUITE_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))

from shared import spec_paths  # noqa: E402

# Old → new files_signed path translations. Any sidecar whose
# files_signed references an old path gets rewritten to the new one
# (and the sha256 is recomputed from the new file location).
PATH_TRANSLATIONS = {
    "docs/specifications/_progress.yaml": ".spec-suite/progress.yaml",
    "docs/specifications/_bootstrap.yaml": ".spec-suite/bootstrap.yaml",
    "docs/specifications/_ambiguities.md": ".spec-suite/ambiguities.md",
    "docs/specifications/_template_manifest.yaml": ".spec-suite/template-manifest.yaml",
}


# (source-rel-to-repo, dest-fn-on-spec_paths) for simple file moves.
FILE_MOVES = [
    ("docs/specifications/_progress.yaml", spec_paths.progress_path),
    ("docs/specifications/_bootstrap.yaml", spec_paths.bootstrap_path),
    ("docs/specifications/_ambiguities.md", spec_paths.ambiguities_path),
    ("docs/specifications/_template_manifest.yaml", spec_paths.template_manifest_path),
]

PHASE_SIDECAR_PREFIX = "docs/specifications/_phase-"
PHASE_SIDECAR_SUFFIX = "-passed.yaml"

REVIEW_PREFIX = "docs/specifications/_review-"
REVIEW_SUFFIX = ".md"

TEMPLATE_DIR = "docs/specifications/_template"


def _move(src: pathlib.Path, dst: pathlib.Path, dry_run: bool) -> str:
    if dry_run:
        return f"  WOULD MOVE  {src} → {dst}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return f"  MOVED       {src} → {dst}"


def _sources_still_present(repo: pathlib.Path) -> bool:
    """True if any old-layout file is still in docs/specifications/."""
    if any((repo / rel).exists() for rel, _ in FILE_MOVES):
        return True
    specs = repo / "docs" / "specifications"
    if not specs.is_dir():
        return False
    return (
        any(p.name.startswith("_phase-") for p in specs.iterdir())
        or any(p.name.startswith("_review-") for p in specs.iterdir())
        or (specs / "_template").is_dir()
    )


def migrate(repo: pathlib.Path, force: bool, dry_run: bool) -> int:
    state = spec_paths.state_dir(repo)
    sources_left = _sources_still_present(repo)
    if state.exists() and any(state.iterdir()) and sources_left and not force:
        print(
            f"migrate: {state.relative_to(repo)} already exists and is "
            "non-empty BUT old-layout sources are still present in "
            "docs/specifications/. Re-run with --force to merge.",
            file=sys.stderr,
        )
        return 1

    if not dry_run:
        spec_paths.ensure_state_skeleton(repo)
    moves: list[str] = []

    # Simple file moves.
    for src_rel, dst_fn in FILE_MOVES:
        src = repo / src_rel
        if not src.is_file():
            continue
        moves.append(_move(src, dst_fn(repo), dry_run))

    # Phase sidecars (varies by number).
    specs = repo / "docs" / "specifications"
    if specs.is_dir():
        for src in sorted(specs.glob("_phase-*-passed.yaml")):
            # Strip the leading underscore; .spec-suite/phases/phase-N-passed.yaml
            new_name = src.name.lstrip("_")
            dst = spec_paths.phases_dir(repo) / new_name
            moves.append(_move(src, dst, dry_run))

        # Review reports.
        for src in sorted(specs.glob("_review-*.md")):
            # Strip the "_review-" prefix → leaves "<timestamp>.md"
            new_name = src.name[len("_review-") :]
            dst = spec_paths.reviews_dir(repo) / new_name
            moves.append(_move(src, dst, dry_run))

        # Template dir.
        templates_src = specs / "_template"
        if templates_src.is_dir():
            templates_dst = spec_paths.templates_dir(repo)
            if dry_run:
                moves.append(f"  WOULD MOVE  {templates_src} → {templates_dst}/  (entire tree)")
            else:
                if templates_dst.exists():
                    shutil.rmtree(templates_dst)
                shutil.move(str(templates_src), str(templates_dst))
                moves.append(f"  MOVED       {templates_src} → {templates_dst}/  (entire tree)")

    # Sidecar files_signed path translation: any sidecar that still
    # references docs/specifications/_X paths gets rewritten to .spec-suite/X
    # with recomputed sha256 from the new location.
    if not dry_run and spec_paths.phases_dir(repo).is_dir():
        rewrites: list[str] = []
        for sidecar in spec_paths.all_phase_sidecars(repo):
            doc = yaml.safe_load(sidecar.read_text(encoding="utf-8")) or {}
            files_signed = doc.get("files_signed") or []
            changed = False
            for entry in files_signed:
                if not isinstance(entry, dict):
                    continue
                old_path = entry.get("path")
                if old_path in PATH_TRANSLATIONS:
                    new_path = PATH_TRANSLATIONS[old_path]
                    new_file = repo / new_path
                    if new_file.is_file():
                        entry["path"] = new_path
                        entry["sha256"] = hashlib.sha256(new_file.read_bytes()).hexdigest()
                        changed = True
            if changed:
                sidecar.write_text(yaml.safe_dump(doc, sort_keys=False))
                rewrites.append(f"  REWROTE     {sidecar.relative_to(repo)} (files_signed paths)")
        moves.extend(rewrites)

    if not moves:
        print("migrate: nothing to do (no old-layout files found).")
        return 0

    for line in moves:
        print(line)
    print()
    label = "would migrate" if dry_run else "migrated"
    print(f"{label} {len(moves)} item(s) into {state.relative_to(repo)}/")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Move suite bookkeeping from docs/specifications/ to .spec-suite/."
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Target spec repo to migrate. Defaults to cwd.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite a non-empty .spec-suite/ directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the moves without executing them.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo = pathlib.Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"migrate: target repo does not exist: {repo}", file=sys.stderr)
        return 2
    return migrate(repo, force=args.force, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
