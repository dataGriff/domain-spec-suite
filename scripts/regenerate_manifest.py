"""Regenerate skills/domain-bootstrap/template_manifest.yaml from the
current contents of skills/domain-bootstrap/templates/.

Run after any change to the templates directory so the bootstrap
script and `task suite:upgrade-shell` stay in sync with what's
actually shipped.

Reads the live suite-version.yaml and gate-version.yaml so the
manifest carries the same versions the suite is currently at.
"""

from __future__ import annotations

import hashlib
import pathlib
import sys

import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent
TEMPLATES = REPO / "skills" / "domain-bootstrap" / "templates"
MANIFEST = REPO / "skills" / "domain-bootstrap" / "template_manifest.yaml"
SUITE_VERSION = REPO / "suite-version.yaml"
GATE_VERSION = REPO / "gate-version.yaml"


def is_executable(rel_path: str) -> bool:
    """Files that must be chmod +x on copy. Currently just the git hooks."""
    return rel_path.startswith(".githooks/")


def main() -> int:
    if not TEMPLATES.is_dir():
        print(f"ERROR: {TEMPLATES} does not exist", file=sys.stderr)
        return 1

    suite_version = yaml.safe_load(SUITE_VERSION.read_text())["suite_version"]
    gate_version = yaml.safe_load(GATE_VERSION.read_text())["gate_version"]

    files = sorted(p for p in TEMPLATES.rglob("*") if p.is_file() and p.name != ".gitkeep")

    lines = [
        "# Manifest of files owned by the domain-bootstrap skill. Generated from",
        "# the templates/ directory. Used by bootstrap --force and by",
        "# task suite:upgrade-shell to decide which files may be overwritten on",
        "# an existing target. Regenerate with `python scripts/regenerate_manifest.py`.",
        "",
        'manifest_version: "1.0"',
        f'suite_version: "{suite_version}"',
        f'gate_version: "{gate_version}"',
        "",
        "# Each file:",
        "#   path:     location relative to the bootstrap target root (the .template",
        "#             suffix is stripped on copy if present)",
        "#   sha256:   hash of the source template content (not of the placeholder-",
        "#             substituted destination — that varies per domain)",
        "#   executable: true only for files that must be chmod +x on copy",
        "files:",
    ]

    for path in files:
        rel = path.relative_to(TEMPLATES).as_posix()
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f'  - path: "{rel}"')
        lines.append(f'    sha256: "{sha}"')
        if is_executable(rel):
            lines.append("    executable: true")

    new_text = "\n".join(lines) + "\n"
    old_text = MANIFEST.read_text() if MANIFEST.exists() else ""

    if new_text == old_text:
        print(f"✓ manifest already current ({len(files)} files)")
        return 0

    MANIFEST.write_text(new_text)
    print(f"✓ regenerated {MANIFEST.relative_to(REPO)} ({len(files)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
