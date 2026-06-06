"""Audit check: the suite's domain-overview generator produces clean output.

Per SUITE-DESIGN §8 Phase 7, "clean" means:
1. The generator exits 0.
2. The rendered domain-overview.html carries no `[Resource1]`,
   `[Domain]`, or `{{...}}` placeholder strings.
3. Every entity named in domain-model.md appears in the rendered
   overview.
4. No stderr noise (Python tracebacks / warnings).

The generator lives in the suite at `scripts/generate_domain_overview.py`
(promoted out of consumer repos in v1.0.13). The check subprocesses it
with `--repo <repo_root>`, redirecting output to a tmp file via
DOMAIN_OVERVIEW_OUTPUT so re-running the audit doesn't churn the spec
repo's on-disk domain-overview.html.
"""

from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys
import tempfile

from shared.check_result import CheckResult

metadata = {
    "id": "GENERATOR-CLEAN-OUTPUT",
    "category": "structural",
    "phases": ["audit"],
    "severity_by_phase": {"audit": "error"},
    "prerequisites": [
        {"file_exists": "docs/specifications/contracts/openapi.yaml"},
        {"file_exists": "docs/specifications/domain-model.md"},
    ],
}

PLACEHOLDER = re.compile(r"\[Resource1\]|\[Domain\]|\{\{")
ENTITY_HEADING = re.compile(r"^### (\S[^\n]*)$", re.MULTILINE)

# Suite layout: this file is at shared/checks/<id>.py, so the suite root
# is two parents up, and the generator lives at <suite>/scripts/.
_SUITE_ROOT = pathlib.Path(__file__).resolve().parents[2]
_GENERATOR = _SUITE_ROOT / "scripts" / "generate_domain_overview.py"


def _domain_entities(domain_model: pathlib.Path) -> list[str]:
    """Extract entity names by scanning `### Heading` lines under the
    Entities section. Skips headings inside code fences."""
    text = domain_model.read_text(encoding="utf-8")
    # Restrict to the Entities section if present
    entities_section = re.split(r"(?m)^##\s+Entities\s*$", text)
    if len(entities_section) > 1:
        text = entities_section[1]
        # Stop at the next ## heading
        next_section = re.search(r"(?m)^##\s+\S", text)
        if next_section:
            text = text[: next_section.start()]
    names = []
    for match in ENTITY_HEADING.finditer(text):
        name = match.group(1).strip()
        # Trim trailing punctuation like ' — Sam'
        names.append(name.split(" — ")[0].split("—")[0].strip())
    return names


def run(repo_root: pathlib.Path) -> CheckResult:
    # Render into a tmp file rather than the canonical on-disk path,
    # so re-running the audit (e.g. inside `task check`) doesn't churn
    # the repo's domain-overview.html on every run.
    with tempfile.NamedTemporaryFile(
        prefix="domain-overview-", suffix=".html", delete=False
    ) as tmp:
        tmp_output = pathlib.Path(tmp.name)

    try:
        env = os.environ.copy()
        env["DOMAIN_OVERVIEW_OUTPUT"] = str(tmp_output)
        proc = subprocess.run(
            [sys.executable, str(_GENERATOR), "--repo", str(repo_root)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        if proc.returncode != 0:
            return CheckResult.fail(
                "The domain-overview generator exited with a non-zero status. "
                "What's the underlying error? Run "
                "`task docs:generate` (or invoke the suite-side generator "
                "directly with `--repo .`) to reproduce, then fix the "
                "offending spec or contract.",
                details=[
                    f"exit code: {proc.returncode}",
                    *[f"stderr: {line}" for line in proc.stderr.splitlines()],
                    *[f"stdout: {line}" for line in proc.stdout.splitlines()],
                ],
            )

        if proc.stderr.strip():
            return CheckResult.fail(
                "The generator produced stderr noise (warnings / tracebacks). "
                "The audit treats stderr as a soft failure even on a zero "
                "exit code — clean output means clean output. What's the "
                "underlying warning?",
                details=[f"stderr: {line}" for line in proc.stderr.splitlines()],
            )

        if not tmp_output.is_file():
            return CheckResult.fail(
                "The generator did not write to the DOMAIN_OVERVIEW_OUTPUT "
                "path. Check that the script honours the "
                "DOMAIN_OVERVIEW_OUTPUT env variable when set.",
            )

        rendered = tmp_output.read_text(encoding="utf-8")
    finally:
        tmp_output.unlink(missing_ok=True)

    placeholders = [
        f"line {i}: {line.strip()[:80]}"
        for i, line in enumerate(rendered.splitlines(), start=1)
        if PLACEHOLDER.search(line)
    ]
    if placeholders:
        return CheckResult.fail(
            "The rendered domain-overview.html still contains template "
            "placeholders. Either an upstream spec carries them (re-run "
            "the audit's NO-TEMPLATE-PLACEHOLDERS check to confirm), or "
            "the generator template itself does. Which value belongs in "
            "each of these positions?",
            details=placeholders,
        )

    entities = _domain_entities(repo_root / "docs" / "specifications" / "domain-model.md")
    missing = [e for e in entities if e not in rendered]
    if missing:
        return CheckResult.fail(
            "The rendered domain overview is missing entities that "
            "domain-model.md defines. Either the generator's entity "
            "extraction is failing for these names, or they're declared "
            "in the domain model but absent from contracts/openapi.yaml "
            "schemas (the generator's source). Which is it for each?",
            details=missing,
        )

    return CheckResult.ok()
