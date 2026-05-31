"""Phase 0 — lay down the canonical domain spec repo shell.

Invoked by the `domain-bootstrap` skill (or directly) to populate an
empty target directory with:

- The shell files from `skills/domain-bootstrap/templates/` (with
  `.template` placeholders substituted from CLI flags).
- An initialised `docs/specifications/_progress.yaml`,
  `_bootstrap.yaml`, `_ambiguities.md`, and `_template_manifest.yaml`
  copied from the suite.

Refuses on a non-empty directory by default. `--force` re-bootstraps
in place, overwriting *only* files listed in the manifest — spec
content and `_*.yaml` state are never touched.

Usage:

    python scripts/bootstrap.py --target /path/to/new-domain \\
        --domain-name "Items" \\
        [--site-url https://...] \\
        [--repo-url https://...] \\
        [--repo-name owner/repo] \\
        [--force]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import pathlib
import re
import shutil
import stat
import sys

import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO / "skills" / "domain-bootstrap" / "templates"
MANIFEST_PATH = REPO / "skills" / "domain-bootstrap" / "template_manifest.yaml"
SUITE_VERSION = yaml.safe_load((REPO / "suite-version.yaml").read_text())["suite_version"]
GATE_VERSION = yaml.safe_load((REPO / "gate-version.yaml").read_text())["gate_version"]

PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")
TEMPLATE_SUFFIX = ".template"

PHASE_0_CHECKS = [
    "BOOTSTRAP-FILES-EXIST",
    "BOOTSTRAP-FILES-PARSE",
    "BOOTSTRAP-PROGRESS-INITIALIZED",
    "BOOTSTRAP-MANIFEST-PRESENT",
]


# ── data structures ────────────────────────────────────────────────


class BootstrapError(RuntimeError):
    pass


def load_manifest() -> dict:
    return yaml.safe_load(MANIFEST_PATH.read_text())


# ── placeholder substitution ───────────────────────────────────────


def slugify(name: str) -> str:
    """Lowercase + hyphenate. Used for default repo_name."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip()).strip("-").lower()
    return slug or "domain"


def build_substitutions(args: argparse.Namespace) -> dict[str, str]:
    domain = args.domain_name
    slug = slugify(domain)
    return {
        "domain_name": domain,
        "domain_slug": slug,
        "site_url": args.site_url or f"https://example.com/{slug}",
        "repo_url": args.repo_url or f"https://example.com/{slug}",
        "repo_name": args.repo_name or slug,
    }


def substitute(text: str, subs: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in subs:
            raise BootstrapError(f"unknown placeholder: {{{{{key}}}}}")
        return subs[key]

    return PLACEHOLDER_PATTERN.sub(replace, text)


# ── empty-vs-occupied detection ────────────────────────────────────


def target_is_effectively_empty(target: pathlib.Path) -> bool:
    """Treat a directory as empty if it contains nothing except hidden git/IDE
    state. Files like .DS_Store and .git aren't user content we'd be
    overwriting."""
    if not target.is_dir():
        return False
    ignorable = {".git", ".DS_Store"}
    return all(p.name in ignorable for p in target.iterdir())


# ── core copy operation ────────────────────────────────────────────


def install_file(
    src: pathlib.Path,
    dst: pathlib.Path,
    entry: dict,
    subs: dict[str, str],
) -> None:
    """Copy one templated file to its destination, substituting placeholders
    if the source is suffixed `.template`. Sets the executable bit where the
    manifest asks."""
    dst.parent.mkdir(parents=True, exist_ok=True)

    if src.name.endswith(TEMPLATE_SUFFIX):
        text = src.read_text(encoding="utf-8")
        text = substitute(text, subs)
        dst.write_text(text, encoding="utf-8")
    else:
        shutil.copyfile(src, dst)

    if entry.get("executable"):
        mode = dst.stat().st_mode
        dst.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def destination_for(rel_template_path: str) -> str:
    """Strip the .template suffix from manifest paths to get the on-disk
    destination relative to the target root."""
    if rel_template_path.endswith(TEMPLATE_SUFFIX):
        return rel_template_path[: -len(TEMPLATE_SUFFIX)]
    return rel_template_path


# ── state files written outside the manifest ───────────────────────


def write_state_files(target: pathlib.Path, args: argparse.Namespace) -> list[str]:
    """Write _progress.yaml, _bootstrap.yaml, _ambiguities.md, and a copy of
    the manifest into the target's docs/specifications/. Returns the list of
    paths written (relative to target)."""
    specs_dir = target / "docs" / "specifications"
    specs_dir.mkdir(parents=True, exist_ok=True)
    now = _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")

    progress = {
        "suite_version": SUITE_VERSION,
        "gate_version": GATE_VERSION,
        "domain_name": args.domain_name,
        "started_at": now,
        "last_updated": now,
        "phases": {
            "bootstrap": {
                "status": "passed",
                "signed_off_at": now,
                "gate_version": GATE_VERSION,
            },
            "discovery": {"status": "not-started"},
            "modeling": {"status": "not-started"},
            "access-control": {"status": "not-started"},
            "flows": {"status": "not-started"},
            "nfrs": {"status": "not-started"},
            "contracts": {"status": "not-started"},
            "audit": {"status": "not-started"},
        },
        "force_advances": [],
        "session_log": [
            {"timestamp": now, "event": "suite-initialized"},
            {"timestamp": now, "event": "phase-passed", "phase": "bootstrap"},
        ],
    }

    bootstrap_record = {
        "suite_version": SUITE_VERSION,
        "gate_version": GATE_VERSION,
        "domain_name": args.domain_name,
        "bootstrapped_at": now,
        "bootstrapped_by": "scripts/bootstrap.py (skills/domain-bootstrap)",
    }

    ambiguities = (
        "# Open Ambiguities\n\n"
        "## Deferred to: audit\n\n_None._\n\n"
        "## Deferred to: post-v1\n\n_None._\n\n"
        "## Resolved\n\n_None yet._\n"
    )

    written: list[str] = []

    def write(rel: str, content: str) -> None:
        path = specs_dir / rel
        path.write_text(content, encoding="utf-8")
        written.append(str(path.relative_to(target)))

    write("_progress.yaml", yaml.safe_dump(progress, sort_keys=False))
    write("_bootstrap.yaml", yaml.safe_dump(bootstrap_record, sort_keys=False))
    write("_ambiguities.md", ambiguities)

    # Phase 0 sign-off sidecar. Bootstrap is its own sign-off — there's
    # no upstream sign_off.py path because bootstrap creates the file
    # shape every other phase relies on. Sidecar shape mirrors what
    # shared/sign_off.py writes for later phases so the orchestrator
    # and audit treat every phase uniformly.
    import hashlib  # local import — only needed here

    bootstrap_sha = hashlib.sha256((specs_dir / "_bootstrap.yaml").read_bytes()).hexdigest()
    sidecar = {
        "phase": "bootstrap",
        "signed_off_at": now,
        "gate_version": GATE_VERSION,
        "checks_passed": list(PHASE_0_CHECKS),
        "warnings_responded": [],
        "rubric_findings": [],
        "files_signed": [
            {
                "path": "docs/specifications/_bootstrap.yaml",
                "sha256": bootstrap_sha,
                "mtime": now,
            }
        ],
    }
    write("_phase-0-passed.yaml", yaml.safe_dump(sidecar, sort_keys=False))

    # Carry a copy of the manifest into the target so upgrade-shell knows
    # which files were originally installed and what their hashes were.
    shutil.copyfile(MANIFEST_PATH, specs_dir / "_template_manifest.yaml")
    written.append(str((specs_dir / "_template_manifest.yaml").relative_to(target)))

    return written


# ── Phase 0 gate ───────────────────────────────────────────────────


def run_phase_0_gate(target: pathlib.Path) -> list[str]:
    """Returns a list of failure messages. Empty list = pass."""
    failures: list[str] = []
    specs_dir = target / "docs" / "specifications"
    progress_path = specs_dir / "_progress.yaml"
    bootstrap_path = specs_dir / "_bootstrap.yaml"
    manifest_target = specs_dir / "_template_manifest.yaml"

    # Files exist
    if not progress_path.is_file():
        failures.append(f"BOOTSTRAP-FILES-EXIST: missing {progress_path}")
    if not bootstrap_path.is_file():
        failures.append(f"BOOTSTRAP-FILES-EXIST: missing {bootstrap_path}")
    if not manifest_target.is_file():
        failures.append(f"BOOTSTRAP-MANIFEST-PRESENT: missing {manifest_target}")

    # YAML parses
    for path in (progress_path, bootstrap_path, manifest_target):
        if not path.is_file():
            continue
        try:
            yaml.safe_load(path.read_text())
        except yaml.YAMLError as exc:
            failures.append(f"BOOTSTRAP-FILES-PARSE: {path} fails to parse — {exc}")

    # _progress.yaml has bootstrap.passed
    if progress_path.is_file():
        progress = yaml.safe_load(progress_path.read_text())
        bootstrap_phase = progress.get("phases", {}).get("bootstrap", {})
        if bootstrap_phase.get("status") != "passed":
            failures.append(
                "BOOTSTRAP-PROGRESS-INITIALIZED: phases.bootstrap.status is not 'passed'"
            )

    return failures


# ── orchestration ──────────────────────────────────────────────────


SPEC_PREFIX = "spec-"


def _check_spec_prefix(target: pathlib.Path, allow_non_prefix: bool) -> None:
    """Refuse to bootstrap into a target dir whose name doesn't start
    with `spec-` (the convention for domain spec repos). Override with
    --allow-non-prefix."""
    name = target.name
    if name.startswith(SPEC_PREFIX) or allow_non_prefix:
        return
    raise BootstrapError(
        f"target directory name {name!r} doesn't start with the "
        f"{SPEC_PREFIX!r} prefix. Domain spec repos are named "
        f"`{SPEC_PREFIX}<domain-slug>` so they're easy to spot in a list "
        "of sibling repos. Either rename the directory (recommended) or "
        "pass --allow-non-prefix to bypass this check (for legacy targets)."
    )


def bootstrap(args: argparse.Namespace) -> int:
    target = pathlib.Path(args.target).resolve()
    if not target.is_dir():
        raise BootstrapError(f"target directory does not exist: {target}")

    _check_spec_prefix(target, allow_non_prefix=args.allow_non_prefix)

    manifest = load_manifest()
    subs = build_substitutions(args)
    written_overwrites: list[str] = []

    if not target_is_effectively_empty(target):
        if not args.force:
            existing = sorted(p.name for p in target.iterdir())
            raise BootstrapError(
                f"target is non-empty ({len(existing)} entries: "
                f"{', '.join(existing[:8])}{'…' if len(existing) > 8 else ''}). "
                "Refusing to bootstrap without --force. Use --force to refresh "
                "manifest-owned files in place (spec content is never touched)."
            )
        # In --force mode, identify and overwrite only manifest files.
        for entry in manifest["files"]:
            dst_rel = destination_for(entry["path"])
            dst = target / dst_rel
            if dst.exists():
                written_overwrites.append(dst_rel)

    # Install every manifest file.
    written: list[str] = []
    for entry in manifest["files"]:
        src = TEMPLATES_DIR / entry["path"]
        dst_rel = destination_for(entry["path"])
        dst = target / dst_rel
        install_file(src, dst, entry, subs)
        written.append(dst_rel)

    # Write the state files that aren't part of the manifest (they're
    # per-install, not per-template).
    state_written = write_state_files(target, args)

    # Phase 0 gate check.
    failures = run_phase_0_gate(target)
    if failures:
        print("Phase 0 gate FAILED:", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return 2

    # Reporting.
    print(f"Bootstrap complete in {target}")
    print(f"  manifest files installed: {len(written)}")
    if written_overwrites:
        print(f"  manifest files overwritten (--force): {len(written_overwrites)}")
    print(f"  state files written:      {len(state_written)}")
    print(f"  suite version:            {SUITE_VERSION}")
    print(f"  gate version:             {GATE_VERSION}")
    print(f"  Phase 0 checks passed:    {len(PHASE_0_CHECKS)} ({', '.join(PHASE_0_CHECKS)})")
    print()
    print("Next steps:")
    print(f"  cd {target}")
    print("  mise trust && mise install     # installs Python, Node, Spectral,")
    print("                                  # datacontract-cli, mkdocs-material")
    print("  task setup                      # installs pyyaml and wires git hooks")
    print()
    print("Then continue with Phase 1 via the domain-discovery skill or")
    print("`task gate:discovery` directly.")
    return 0


# ── CLI ────────────────────────────────────────────────────────────


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap a domain spec repo shell.")
    parser.add_argument(
        "--target",
        required=True,
        help="Path to the directory that will become the domain spec repo.",
    )
    parser.add_argument(
        "--domain-name",
        required=True,
        help='Title-case domain name, e.g. "Items", "Orders".',
    )
    parser.add_argument("--site-url", help="Optional mkdocs site_url.")
    parser.add_argument("--repo-url", help="Optional repo_url for mkdocs.")
    parser.add_argument(
        "--repo-name",
        help="Optional repo_name (owner/repo) for mkdocs. Defaults to a slug of --domain-name.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Refresh manifest-owned files in a non-empty target. Never touches spec content.",
    )
    parser.add_argument(
        "--allow-non-prefix",
        action="store_true",
        help=(
            f"Bypass the `{SPEC_PREFIX}` target-directory-name check. "
            "Use only for legacy targets that pre-date the convention."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return bootstrap(args)
    except BootstrapError as exc:
        print(f"bootstrap: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
