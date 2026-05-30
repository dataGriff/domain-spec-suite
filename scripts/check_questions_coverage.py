"""Build-time guard: every gate-check id listed in any phase's
`gate.yaml` must have a matching entry in that phase's `questions.md`
(per SUITE-DESIGN §7.5 authoring rule 1).

Phases that don't have a `questions.md` yet (un-built phases) are
allowed to skip — the check only fires when the file exists. The same
phase's `gate.yaml` may carry extra-check ids that don't surface
user-facing prompts (e.g. tool-only lint checks like
`SPECTRAL-OPENAPI`) — those are listed in `NO_QUESTION_NEEDED` below
so the coverage check ignores them.

Exits 0 on full coverage, 1 otherwise. Wired into `task lint` via
Taskfile so it runs on every CI / pre-push check.
"""

from __future__ import annotations

import pathlib
import sys

import yaml

SUITE_ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS_DIR = SUITE_ROOT / "skills"

# Check ids that are mechanical-tool-only — they don't surface
# user-facing interview questions because the failure is "the binary
# returned non-zero", which has no useful conversational form.
NO_QUESTION_NEEDED: set[str] = {
    "SPECTRAL-OPENAPI",
    "SPECTRAL-ASYNCAPI",
    "DATACONTRACT-LINT",
    # Audit-only integrity checks — their "questions" would be
    # operator advice, not interview prose.
    "NO-TEMPLATE-PLACEHOLDERS",
    "SIGNOFF-SHA256-MATCHES",
    "FORCE-ADVANCES-ALL-ACCEPTED",
    "AMBIGUITIES-NO-AUDIT-REQUIRED",
    "GENERATOR-CLEAN-OUTPUT",
}


def load_questions(questions_path: pathlib.Path) -> list[dict]:
    text = questions_path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, list):
        raise ValueError(f"{questions_path}: top-level must be a YAML list")
    return data


def check_phase(skill_dir: pathlib.Path) -> list[str]:
    """Return a list of coverage problems for one skill directory."""
    problems: list[str] = []
    gate_path = skill_dir / "gate.yaml"
    questions_path = skill_dir / "questions.md"

    if not gate_path.is_file():
        return []  # un-built phase
    if not questions_path.is_file():
        # Phase is mechanical-only by design (audit, contracts) and
        # has opted out of an interview-style question bank. Nothing
        # to enforce. Phases that should have one are caught when
        # someone adds the questions.md file but forgets entries.
        return problems

    gate = yaml.safe_load(gate_path.read_text())
    questions = load_questions(questions_path)
    by_bind = {q.get("binds_to_check"): q for q in questions}

    seen_ids: set[str] = set()
    for entry in gate.get("checks", []):
        check_id = entry["id"]
        if check_id in NO_QUESTION_NEEDED:
            continue
        seen_ids.add(check_id)
        if check_id not in by_bind:
            problems.append(
                f"{skill_dir.name}: {check_id} is in gate.yaml but has no "
                "matching questions.md entry"
            )

    # Surplus questions are a hint of stale entries — surface them.
    for binding, entry in by_bind.items():
        if binding is None:
            problems.append(
                f"{skill_dir.name}: questions.md entry {entry.get('id', '<?>')!r} "
                "is missing a binds_to_check field"
            )
        elif binding not in seen_ids and binding not in NO_QUESTION_NEEDED:
            problems.append(
                f"{skill_dir.name}: questions.md entry binds to {binding!r} "
                "but no such check id is in gate.yaml"
            )

    return problems


def main() -> int:
    all_problems: list[str] = []
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        all_problems.extend(check_phase(skill_dir))

    if not all_problems:
        print("question-bank coverage: OK")
        return 0

    print("question-bank coverage: FAIL", file=sys.stderr)
    for problem in all_problems:
        print(f"  · {problem}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
