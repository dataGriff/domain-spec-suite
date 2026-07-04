"""Phase-level check runner.

Loads a phase's `gate.yaml`, imports each referenced check module,
evaluates prerequisites, runs every applicable check at the
phase-appropriate severity, and prints a structured report. Exits 0
only if every applicable check passes at error severity.

CLI:

    python shared/run_phase.py <phase> [--repo <path>]

`<phase>` is one of: discovery, modeling, access-control, flows,
nfrs, contracts, audit. `--repo` defaults to the current working
directory. Bootstrap has no gate here — it is mechanical file
copying, validated end-to-end by `scripts/bootstrap.py` itself.

This is the single mechanical-enforcement path referenced from
SUITE-DESIGN §5.5. Sign-off (`shared/sign_off.py`, future) calls into
it; the audit skill's `task audit` calls into it.
"""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import sys
from collections.abc import Iterable
from dataclasses import dataclass

# Ensure the suite root is on sys.path so dynamically-loaded check
# modules can `from shared.check_result import CheckResult` etc.
# regardless of how run_phase.py is invoked.
SUITE_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))

import yaml  # noqa: E402

from shared.check_result import CheckResult  # noqa: E402

SHARED_CHECKS_DIR = SUITE_ROOT / "shared" / "checks"
SKILLS_DIR = SUITE_ROOT / "skills"

# Gate-bearing phases only. Bootstrap is deliberately absent: it has
# no gate.yaml (mechanical file copying, validated by
# scripts/bootstrap.py), so listing it would advertise a phase that
# can only end in FileNotFoundError.
PHASE_TO_SKILL = {
    "discovery": "domain-discovery",
    "modeling": "domain-modeling",
    "access-control": "domain-access-control",
    "flows": "domain-flows",
    "nfrs": "domain-nfrs",
    "contracts": "domain-contracts",
    "audit": "domain-conformance-audit",
}


# ── module discovery ──────────────────────────────────────────────


@dataclass
class CheckModule:
    metadata: dict
    run: callable  # type: ignore[type-arg]
    source: pathlib.Path

    @property
    def id(self) -> str:
        return self.metadata["id"]


def _load_module(path: pathlib.Path) -> CheckModule | None:
    """Import a check module from a path. Returns None for modules
    missing the required surface (so dotfiles, __init__, helpers etc.
    are silently ignored)."""
    spec = importlib.util.spec_from_file_location(f"_check_{path.stem}", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "metadata") or not hasattr(module, "run"):
        return None
    return CheckModule(metadata=module.metadata, run=module.run, source=path)


def discover_checks(phase: str) -> dict[str, CheckModule]:
    """Build {check_id: CheckModule} by scanning shared/checks/ and the
    phase's own checks/ directory. Phase-local checks override shared
    checks of the same id (defence in depth — never expected in
    practice)."""
    found: dict[str, CheckModule] = {}

    def scan(directory: pathlib.Path) -> None:
        if not directory.is_dir():
            return
        for path in sorted(directory.glob("*.py")):
            if path.name.startswith("_"):
                continue
            module = _load_module(path)
            if module is None:
                continue
            found[module.id] = module

    scan(SHARED_CHECKS_DIR)
    skill_dir = SKILLS_DIR / PHASE_TO_SKILL.get(phase, "")
    scan(skill_dir / "checks")
    return found


# ── prerequisite evaluation ──────────────────────────────────────


def prerequisites_met(metadata: dict, repo: pathlib.Path) -> bool:
    """Returns True if every prerequisite passes (or there are none).
    A failing prerequisite is *not* a check failure — it means the
    check is no-op'd at this phase."""
    import shutil  # local import — only needed when binary_exists is used

    for prereq in metadata.get("prerequisites", []):
        if "file_exists" in prereq:
            if not (repo / prereq["file_exists"]).is_file():
                return False
        elif "binary_exists" in prereq:
            if shutil.which(prereq["binary_exists"]) is None:
                return False
        else:
            raise ValueError(f"unknown prerequisite shape: {prereq}")
    return True


# ── runner ────────────────────────────────────────────────────────


@dataclass
class CheckOutcome:
    id: str
    severity: str
    passed: bool
    skipped: bool
    message: str
    details: list[str]


def severity_for(metadata: dict, phase: str) -> str:
    by_phase = metadata.get("severity_by_phase", {})
    if phase in by_phase:
        return by_phase[phase]
    return metadata.get("default_severity", "error")


def load_gate(phase: str) -> dict:
    skill_dir = SKILLS_DIR / PHASE_TO_SKILL[phase]
    gate_path = skill_dir / "gate.yaml"
    if not gate_path.is_file():
        raise FileNotFoundError(f"missing gate definition: {gate_path}")
    return yaml.safe_load(gate_path.read_text())


def run_phase(
    phase: str,
    repo: pathlib.Path,
    *,
    exclude: set[str] | None = None,
) -> tuple[int, list[CheckOutcome]]:
    """Run every check listed in the phase's gate against `repo`.
    Returns (exit_code, outcomes). exit_code is 0 only if every
    error-severity check that actually ran passed.

    `exclude` is an optional set of check ids to skip. Excluded checks
    don't appear in outcomes at all (different from `skipped` which
    indicates the check ran but a prerequisite wasn't met). Used by
    the spec-repo `task audit:cross-file` to skip placeholder, sha256,
    force-advance, ambiguity, and generator checks for a faster
    pre-push variant.
    """
    if phase not in PHASE_TO_SKILL:
        raise ValueError(f"unknown phase '{phase}'. Expected one of: {', '.join(PHASE_TO_SKILL)}")

    exclude = exclude or set()

    gate = load_gate(phase)
    checks_by_id = discover_checks(phase)
    outcomes: list[CheckOutcome] = []
    errored = False

    for entry in gate.get("checks", []):
        check_id = entry["id"]
        if check_id in exclude:
            continue
        if check_id not in checks_by_id:
            outcomes.append(
                CheckOutcome(
                    id=check_id,
                    severity="error",
                    passed=False,
                    skipped=False,
                    message=(
                        f"check '{check_id}' is listed in {phase}/gate.yaml "
                        "but no module implements it"
                    ),
                    details=[],
                )
            )
            errored = True
            continue

        module = checks_by_id[check_id]
        if phase not in module.metadata.get("phases", []):
            outcomes.append(
                CheckOutcome(
                    id=check_id,
                    severity="error",
                    passed=False,
                    skipped=False,
                    message=(
                        f"check '{check_id}' is listed in {phase}/gate.yaml but its "
                        f"metadata does not include '{phase}' in phases"
                    ),
                    details=[],
                )
            )
            errored = True
            continue

        if not prerequisites_met(module.metadata, repo):
            outcomes.append(
                CheckOutcome(
                    id=check_id,
                    severity="skipped",
                    passed=True,
                    skipped=True,
                    message="prerequisites not met",
                    details=[],
                )
            )
            continue

        severity = severity_for(module.metadata, phase)
        result: CheckResult = module.run(repo)
        outcomes.append(
            CheckOutcome(
                id=check_id,
                severity=severity,
                passed=result.passed,
                skipped=False,
                message=result.message,
                details=result.details,
            )
        )
        if not result.passed and severity == "error":
            errored = True

    return (1 if errored else 0), outcomes


# ── reporting ────────────────────────────────────────────────────


def render(phase: str, repo: pathlib.Path, outcomes: Iterable[CheckOutcome]) -> str:
    lines: list[str] = []
    lines.append(f"=== {phase} gate — target {repo} ===")
    passed = sum(1 for o in outcomes if o.passed and not o.skipped)
    skipped = sum(1 for o in outcomes if o.skipped)
    failed = sum(1 for o in outcomes if not o.passed)
    for outcome in outcomes:
        if outcome.skipped:
            lines.append(f"  SKIP  {outcome.id} — {outcome.message}")
            continue
        if outcome.passed:
            lines.append(f"  PASS  {outcome.id}")
            continue
        marker = "FAIL" if outcome.severity == "error" else "WARN"
        lines.append(f"  {marker}  {outcome.id}")
        if outcome.message:
            for line in outcome.message.splitlines():
                lines.append(f"        {line}")
        for detail in outcome.details:
            lines.append(f"          · {detail}")
    lines.append("")
    lines.append(f"summary: {passed} passed, {failed} failed, {skipped} skipped")
    return "\n".join(lines)


# ── CLI ──────────────────────────────────────────────────────────


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a phase's gate against a domain repo.")
    parser.add_argument("phase", help="Phase id (e.g. audit, contracts).")
    parser.add_argument(
        "--repo",
        default=".",
        help="Path to the target domain repo. Defaults to the current directory.",
    )
    parser.add_argument(
        "--exclude",
        default="",
        help=(
            "Comma-separated check ids to skip. Used by `task audit:cross-file` "
            "to skip placeholder / sha256 / force-advance / ambiguity / generator "
            "checks for a faster pre-push variant."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo = pathlib.Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"run_phase: target repo does not exist: {repo}", file=sys.stderr)
        return 2
    exclude = {x.strip() for x in args.exclude.split(",") if x.strip()}
    exit_code, outcomes = run_phase(args.phase, repo, exclude=exclude)

    # Audit-phase post-processing: respect prior-phase engagement.
    # Mirrors sign_off.py so `task audit` and `task sign-off:audit` show
    # the same downgraded view.
    if args.phase == "audit":
        from shared import prior_engagement

        engagement = prior_engagement.read_prior_engagement(repo)
        outcomes, _ = prior_engagement.apply_prior_engagement(outcomes, engagement)
        exit_code = prior_engagement.downgraded_exit_code(outcomes)

    print(render(args.phase, repo, outcomes))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
