"""Regenerate sha256 values inside every fixture's
`.spec-suite/phases/phase-N-passed.yaml` sidecar against the current
file contents.

Idempotent: if every recorded sha256 already matches the file, no
sidecar is rewritten. Used whenever a fixture's spec files change, so
the staleness check (SUITE-DESIGN §6) keeps passing.

Uses the YAML parser (not regex line edits) — the regex approach was
the source of the M6.6 sha256 bug and silently mismatched the bare
(unquoted) format `yaml.safe_dump` emits.

Invoked via `task fixtures:seed-signoffs`.
"""

from __future__ import annotations

import hashlib
import pathlib
import sys

import yaml

SUITE_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))

from shared import spec_paths  # noqa: E402

FIXTURES = SUITE_ROOT / "tests" / "fixtures"


def regenerate(sidecar: pathlib.Path, repo_root: pathlib.Path) -> int:
    """Rewrite the sidecar's sha256s. Returns the number of values changed."""
    doc = yaml.safe_load(sidecar.read_text(encoding="utf-8")) or {}
    changed = 0
    for entry in doc.get("files_signed") or []:
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        if not path:
            continue
        target = repo_root / path
        if not target.is_file():
            print(
                f"  WARN  referenced file missing: {path} (in {sidecar.name})",
                file=sys.stderr,
            )
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if entry.get("sha256") != actual:
            entry["sha256"] = actual
            changed += 1
    if changed:
        sidecar.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return changed


def main() -> int:
    if not FIXTURES.exists():
        print(f"{FIXTURES} does not exist yet — nothing to seed.")
        return 0

    sidecars = [
        sidecar
        for fixture in sorted(p for p in FIXTURES.iterdir() if p.is_dir())
        for sidecar in spec_paths.all_phase_sidecars(fixture)
    ]
    if not sidecars:
        print(f"no phase-*-passed.yaml sidecars under {FIXTURES} — nothing to seed.")
        return 1

    total_changed = 0
    for sidecar in sidecars:
        # Repo root for sha256 path resolution: tests/fixtures/<domain>/
        repo_root = sidecar.parents[2]
        changed = regenerate(sidecar, repo_root)
        if changed:
            print(f"  updated {changed:2d} hash(es) in {sidecar.relative_to(SUITE_ROOT)}")
        total_changed += changed

    if total_changed == 0:
        print(f"✓ all sha256s already current across {len(sidecars)} sidecars")
    else:
        print(f"✓ rewrote {total_changed} hash(es) across {len(sidecars)} sidecars")
    return 0


if __name__ == "__main__":
    sys.exit(main())
