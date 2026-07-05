"""Regenerate sha256 values inside every fixture's
`.spec-suite/phases/phase-N-passed.yaml` sidecar against the current file contents.

Idempotent: if every recorded sha256 already matches the file, no
sidecar is rewritten. Used whenever a fixture's spec files change, so
the staleness check (SUITE-DESIGN §6) keeps passing.

Invoked via `task fixtures:seed-signoffs`.
"""

from __future__ import annotations

import hashlib
import pathlib
import re
import sys

FIXTURES = pathlib.Path("tests/fixtures")

# Matches the YAML pattern produced by the suite's sign-off writer:
#
#   - path: docs/specifications/prd.md
#     sha256: "abc123..."
#
# Allows any whitespace indent before `- path:` so the regex is robust
# to varying formatting.
SIGNOFF_LINE = re.compile(
    r"(?P<prefix>(?:^|\n)\s*-\s*path:\s*)(?P<path>\S+)"
    r'(?P<between>\s*\n\s*sha256:\s*"?)'
    r"(?P<sha>[0-9a-f]+)"
    r'(?P<suffix>"?)',
    re.MULTILINE,
)


def regenerate(sidecar: pathlib.Path, repo_root: pathlib.Path) -> int:
    """Rewrite the sidecar's sha256s. Returns the number of values changed."""
    text = sidecar.read_text(encoding="utf-8")
    changed = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal changed
        path = match.group("path")
        recorded = match.group("sha")
        target = repo_root / path
        if not target.exists():
            print(
                f"  WARN  referenced file missing: {path} (in {sidecar.name})",
                file=sys.stderr,
            )
            return match.group(0)
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != recorded:
            changed += 1
            return (
                f"{match.group('prefix')}{path}"
                f"{match.group('between')}{actual}{match.group('suffix')}"
            )
        return match.group(0)

    new_text = SIGNOFF_LINE.sub(replace, text)
    if new_text != text:
        sidecar.write_text(new_text, encoding="utf-8")
    return changed


def main() -> int:
    if not FIXTURES.exists():
        print(f"{FIXTURES} does not exist yet — nothing to seed.")
        return 0

    sidecars = sorted(FIXTURES.glob("*/.spec-suite/phases/phase-*-passed.yaml"))
    if not sidecars:
        print(f"no phase-*-passed.yaml sidecars under {FIXTURES} — nothing to seed.")
        return 0

    total_changed = 0
    for sidecar in sidecars:
        # Repo root for sha256 path resolution: tests/fixtures/<domain>/
        # (sidecar sits at <repo>/.spec-suite/phases/phase-N-passed.yaml)
        repo_root = sidecar.parents[2]
        changed = regenerate(sidecar, repo_root)
        if changed:
            print(
                f"  updated {changed:2d} hash(es) in {sidecar.relative_to(FIXTURES.parent.parent)}"
            )
        total_changed += changed

    if total_changed == 0:
        print(f"✓ all sha256s already current across {len(sidecars)} sidecars")
    else:
        print(f"✓ rewrote {total_changed} hash(es) across {len(sidecars)} sidecars")
    return 0


if __name__ == "__main__":
    sys.exit(main())
