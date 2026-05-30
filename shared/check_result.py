"""Shared `CheckResult` shape used by every gate check across the suite.

Each `shared/checks/<id>.py` and `skills/<phase>/checks/<id>.py` module
exposes a `metadata` dict (per SUITE-DESIGN §5.5) and a
`run(repo_root: Path) -> CheckResult` function. The runner
(`shared/run_phase.py`) aggregates these into a phase-level pass/fail.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Severity = Literal["error", "warning", "info"]


@dataclass
class CheckResult:
    """Result of running a single check against a target repo.

    `passed` is the load-bearing attribute. `message` is the
    interview-style failure question shown to the user when the check
    fails (per SUITE-DESIGN §7 Hard Rule 10 — never a lint diagnostic).
    `details` is an optional list of supporting facts (line numbers,
    file paths, etc.) the runner can render under the message.
    """

    passed: bool
    message: str = ""
    details: list[str] = field(default_factory=list)

    @classmethod
    def ok(cls) -> CheckResult:
        return cls(passed=True)

    @classmethod
    def fail(cls, message: str, details: list[str] | None = None) -> CheckResult:
        return cls(passed=False, message=message, details=details or [])
