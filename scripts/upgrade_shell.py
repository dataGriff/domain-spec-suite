"""Manifest-aware shell upgrade for an already-bootstrapped spec repo.

Wraps `scripts/bootstrap.py --force` behind the clearer name that
SUITE-DESIGN §1/§2 and the bootstrap refusal messages point at
(`task suite:upgrade-shell`). The domain name is recovered from the
target's `.spec-suite/bootstrap.yaml` (or `progress.yaml`) so the
operator doesn't have to re-supply it.

Only files listed in `template_manifest.yaml` are overwritten. Spec
content (`docs/specifications/**`) and `.spec-suite/` state are never
touched — that guarantee lives in bootstrap.py's --force path; this
script adds nothing on top of it except name recovery and a
must-already-be-bootstrapped precondition.

Usage:

    python scripts/upgrade_shell.py [--repo <path>]
        [--site-url https://...] [--repo-url https://...]
        [--repo-name owner/repo]
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import yaml

SUITE_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))

import bootstrap  # noqa: E402 — sibling script, same directory

from shared import spec_paths  # noqa: E402


def recover_domain_name(repo: pathlib.Path) -> str | None:
    """Read the domain name the original bootstrap recorded."""
    for path in (spec_paths.bootstrap_path(repo), spec_paths.progress_path(repo)):
        if not path.is_file():
            continue
        doc = yaml.safe_load(path.read_text()) or {}
        name = doc.get("domain_name")
        if name:
            return str(name)
    return None


def upgrade_shell(args: argparse.Namespace) -> int:
    repo = pathlib.Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"upgrade_shell: target repo does not exist: {repo}", file=sys.stderr)
        return 2

    domain_name = args.domain_name or recover_domain_name(repo)
    if domain_name is None:
        print(
            f"upgrade_shell: {repo} doesn't look bootstrapped — no domain_name in "
            f"{spec_paths.bootstrap_path(repo)} or {spec_paths.progress_path(repo)}. "
            "Run `task suite:bootstrap` for a first-time setup, or pass "
            "--domain-name explicitly.",
            file=sys.stderr,
        )
        return 1

    bootstrap_args = argparse.Namespace(
        target=str(repo),
        domain_name=domain_name,
        site_url=args.site_url,
        repo_url=args.repo_url,
        repo_name=args.repo_name,
        force=True,
        # The repo was accepted at original bootstrap time; an upgrade
        # must not fail on a legacy (non `spec-`-prefixed) name.
        allow_non_prefix=True,
    )
    try:
        return bootstrap.bootstrap(bootstrap_args)
    except bootstrap.BootstrapError as exc:
        print(f"upgrade_shell: {exc}", file=sys.stderr)
        return 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh a bootstrapped repo's shell files from the suite templates."
    )
    parser.add_argument("--repo", default=".", help="Target domain repo. Defaults to cwd.")
    parser.add_argument(
        "--domain-name",
        help="Override the domain name (defaults to the one recorded at bootstrap).",
    )
    parser.add_argument("--site-url", help="Optional mkdocs site_url.")
    parser.add_argument("--repo-url", help="Optional repo_url for mkdocs.")
    parser.add_argument("--repo-name", help="Optional repo_name (owner/repo) for mkdocs.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return upgrade_shell(parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
