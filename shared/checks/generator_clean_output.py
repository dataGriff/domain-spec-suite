"""Audit check: scripts/generate_domain_overview.py produces clean output.

Per SUITE-DESIGN §8 Phase 7, "clean" means:
1. The generator exits 0.
2. The rendered domain-overview.html carries no `[Resource1]`,
   `[Domain]`, or `{{...}}` placeholder strings.
3. Every entity named in domain-model.md appears in the rendered
   overview.
4. No stderr noise (Python tracebacks / warnings).

Implementation: subprocess the generator with the target as cwd. We
deliberately do NOT use `task docs:generate` here — the generator
script is the contract; what wraps it varies per repo.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

from shared.check_result import CheckResult

metadata = {
    "id": "GENERATOR-CLEAN-OUTPUT",
    "category": "structural",
    "phases": ["audit"],
    "severity_by_phase": {"audit": "error"},
    "prerequisites": [
        {"file_exists": "scripts/generate_domain_overview.py"},
        {"file_exists": "docs/specifications/domain-model.md"},
    ],
}

PLACEHOLDER = re.compile(r"\[Resource1\]|\[Domain\]|\{\{")
ENTITY_HEADING = re.compile(r"^### (\S[^\n]*)$", re.MULTILINE)


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
    overview_path = repo_root / "docs" / "specifications" / "domain-overview.html"
    generator = repo_root / "scripts" / "generate_domain_overview.py"

    proc = subprocess.run(
        [sys.executable, str(generator)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return CheckResult.fail(
            "The domain-overview generator exited with a non-zero status. "
            "What's the underlying error? Run "
            "`python scripts/generate_domain_overview.py` from the repo "
            "root to reproduce, then fix the offending spec or contract.",
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

    if not overview_path.is_file():
        return CheckResult.fail(
            "The generator did not write docs/specifications/domain-overview.html. "
            "Check that the script's OUTPUT_FILE path matches the expected location.",
        )

    rendered = overview_path.read_text(encoding="utf-8")

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
