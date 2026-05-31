"""Runner for the domain-review skill.

Verifies audit is green, enumerates the files the agent will read,
emits the file list + category checklist as a context bundle, and
(when the agent passes back a report body) writes the timestamped
report to docs/specifications/.

The qualitative work — actually reading the files and producing
findings — is the AGENT's job (this is a markdown-driven skill,
not a Python check). This script is the mechanical wrapping:
pre-flight, context gathering, report write.

Usage modes:

    # Mode 1: pre-flight + context bundle for the agent
    python scripts/domain_review.py --repo <target>

    # Mode 2: write a report body the agent produced
    python scripts/domain_review.py --repo <target> --write-report <path-to-md>

    # Mode 3: write report from stdin (for piping)
    python scripts/domain_review.py --repo <target> --write-report -
"""

from __future__ import annotations

import argparse
import datetime as _dt
import pathlib
import sys

SUITE_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))

from shared import prior_engagement, run_phase, spec_paths  # noqa: E402

REVIEW_FILES = [
    "docs/specifications/prd.md",
    "docs/specifications/domain-model.md",
    "docs/specifications/glossary.md",
    "docs/specifications/auth-matrix.md",
    "docs/specifications/error-catalogue.md",
    "docs/specifications/sequence-diagrams.md",
    "docs/specifications/nfr.md",
    "docs/specifications/acceptance-scenarios.md",
    "docs/specifications/contracts/openapi.yaml",
    "docs/specifications/contracts/asyncapi.yaml",
    "docs/specifications/contracts/datacontract.yaml",
    ".spec-suite/ambiguities.md",
]

CATEGORIES = [
    ("CROSS-DOC-TYPE-SHAPE", "Cross-document type / shape inconsistencies"),
    ("COVERAGE-GAP", "Coverage gaps between docs"),
    ("LOGICAL-CONTRADICTION", "Logical / semantic contradictions"),
    ("MISSING-CASE", "Missing-case gaps"),
    ("DECISION-LOG-DRIFT", "Decision Log drift"),
]


def _iso_now() -> str:
    return _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _file_safe_ts() -> str:
    """Filesystem-safe timestamp (no colons)."""
    return _iso_now().replace(":", "-")


def verify_audit_green(repo: pathlib.Path) -> tuple[bool, str]:
    """Return (passed, summary). Reuses the audit runner + prior
    engagement downgrade so the verdict matches what the user sees
    from `task audit`."""
    exit_code, outcomes = run_phase.run_phase("audit", repo)
    engagement = prior_engagement.read_prior_engagement(repo)
    outcomes, _ = prior_engagement.apply_prior_engagement(outcomes, engagement)
    exit_code = prior_engagement.downgraded_exit_code(outcomes)

    passed = exit_code == 0
    passed_count = sum(1 for o in outcomes if o.passed and not o.skipped)
    failed_count = sum(1 for o in outcomes if not o.passed and not o.skipped)
    summary = f"{passed_count} passed, {failed_count} failed"
    return passed, summary


def list_files_for_review(repo: pathlib.Path) -> tuple[list[pathlib.Path], list[pathlib.Path]]:
    """Return (spec_files, sidecars) that exist in the target."""
    spec_files = [repo / rel for rel in REVIEW_FILES if (repo / rel).is_file()]
    sidecars = spec_paths.all_phase_sidecars(repo)
    return spec_files, sidecars


def render_context_bundle(
    repo: pathlib.Path,
    audit_summary: str,
    spec_files: list[pathlib.Path],
    sidecars: list[pathlib.Path],
) -> str:
    """Markdown bundle the agent reads to do the review. Lists every
    file + the category checklist + the expected report shape."""
    lines: list[str] = []
    lines.append(f"# domain-review context bundle — {repo}")
    lines.append("")
    lines.append(f"**Reviewed:** {_iso_now()}")
    lines.append(f"**Audit state at review:** {audit_summary}")
    lines.append("")
    lines.append("## Files to read (all of them)")
    lines.append("")
    for f in spec_files:
        lines.append(f"- `{f.relative_to(repo)}`")
    lines.append("")
    lines.append("## Sidecars (for Decision Log entries)")
    lines.append("")
    for s in sidecars:
        lines.append(f"- `{s.relative_to(repo)}`")
    lines.append("")
    lines.append("## Categories to walk")
    lines.append("")
    for cat_id, cat_name in CATEGORIES:
        lines.append(f"- **{cat_id}** — {cat_name}")
    lines.append("")
    lines.append("## Output")
    lines.append("")
    lines.append(
        "Produce a markdown report with sections: Critical findings, "
        "Important findings, Minor findings, Things checked and OK, "
        "Decision Log review, Summary. Each finding has an id, file + "
        "location, problem, and recommended fix. See "
        "`skills/domain-review/SKILL.md` for the full report template."
    )
    lines.append("")
    lines.append(
        "Once the report body is ready, write it to "
        f"`.spec-suite/reviews/{_file_safe_ts()}.md` via "
        f"`python scripts/domain_review.py --repo <target> "
        f"--write-report <path-or-->`."
    )
    return "\n".join(lines)


def write_report(repo: pathlib.Path, body: str) -> pathlib.Path:
    """Write the agent-produced report body to a timestamped file
    under .spec-suite/reviews/. Returns the path written."""
    reviews = spec_paths.reviews_dir(repo)
    reviews.mkdir(parents=True, exist_ok=True)
    out = reviews / f"{_file_safe_ts()}.md"
    out.write_text(body, encoding="utf-8")
    return out


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a qualitative domain-review against a target spec repo."
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Target domain spec repo. Defaults to cwd.",
    )
    parser.add_argument(
        "--write-report",
        metavar="PATH",
        help=(
            "Path to a markdown file containing the report body (or '-' for "
            "stdin). When set, writes the report to "
            ".spec-suite/reviews/<timestamp>.md and exits. When "
            "absent, runs pre-flight + emits the context bundle to stdout."
        ),
    )
    parser.add_argument(
        "--skip-audit-check",
        action="store_true",
        help=(
            "Skip the 'audit must be green' precondition. Use only when "
            "deliberately reviewing a known-broken spec set (e.g. mid-update)."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo = pathlib.Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"domain_review: target repo does not exist: {repo}", file=sys.stderr)
        return 2

    # Write-report mode: skip everything else, just save the body.
    if args.write_report:
        if args.write_report == "-":
            body = sys.stdin.read()
        else:
            path = pathlib.Path(args.write_report)
            if not path.is_file():
                print(
                    f"domain_review: report body file does not exist: {path}",
                    file=sys.stderr,
                )
                return 2
            body = path.read_text(encoding="utf-8")
        written = write_report(repo, body)
        print(f"review report written: {written.relative_to(repo)}")
        return 0

    # Pre-flight + context bundle mode.
    if not args.skip_audit_check:
        passed, summary = verify_audit_green(repo)
        if not passed:
            print(
                f"domain_review: audit is NOT green ({summary}). "
                "Fix mechanical issues first, or pass --skip-audit-check to "
                "review a deliberately-broken spec set.",
                file=sys.stderr,
            )
            return 1
    else:
        summary = "skipped (per --skip-audit-check)"

    spec_files, sidecars = list_files_for_review(repo)
    bundle = render_context_bundle(repo, summary, spec_files, sidecars)
    print(bundle)
    return 0


if __name__ == "__main__":
    sys.exit(main())
