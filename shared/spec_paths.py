"""Central path resolution for the `.spec-suite/` bookkeeping
directory in a spec repo.

Every site that reads or writes suite-managed state (sidecars,
progress, ambiguities, templates, review reports) routes through
this module. Hardcoding paths in callers would make the layout
change in v1.0.3 unmaintainable; one helper means one place to
fix when the convention evolves.

Layout:

    <repo>/.spec-suite/
        progress.yaml            # live phase progression state
        bootstrap.yaml            # record of bootstrap event
        ambiguities.md            # open / deferred / resolved log
        template-manifest.yaml    # snapshot of suite's manifest
        phases/
            phase-0-passed.yaml   # ... through phase-7-passed.yaml
        reviews/
            <ISO-timestamp>.md    # qualitative review reports

The `.spec-suite/` directory is intentionally hidden (dot-prefixed)
so it sits alongside `.git/`, `.github/`, `.claude/` etc. and
doesn't clutter `docs/specifications/`, which is reserved for the
publishable spec content.

Blank spec templates do NOT live here; they're suite-versioned and
sit in `<suite>/templates/`. `task init:<phase>` resolves them from
the suite at authoring time.
"""

from __future__ import annotations

import pathlib

STATE_DIRNAME = ".spec-suite"

PHASE_NUMBER = {
    "bootstrap": 0,
    "discovery": 1,
    "modeling": 2,
    "access-control": 3,
    "flows": 4,
    "nfrs": 5,
    "contracts": 6,
    "audit": 7,
}


# ── directory helpers ────────────────────────────────────────────


def state_dir(repo: pathlib.Path) -> pathlib.Path:
    """Path to `<repo>/.spec-suite/`. Caller's responsibility to
    create if writing; callers that only read may want to check
    `.exists()` first."""
    return repo / STATE_DIRNAME


def phases_dir(repo: pathlib.Path) -> pathlib.Path:
    return state_dir(repo) / "phases"


def reviews_dir(repo: pathlib.Path) -> pathlib.Path:
    return state_dir(repo) / "reviews"


# ── file helpers ─────────────────────────────────────────────────


def progress_path(repo: pathlib.Path) -> pathlib.Path:
    return state_dir(repo) / "progress.yaml"


def bootstrap_path(repo: pathlib.Path) -> pathlib.Path:
    return state_dir(repo) / "bootstrap.yaml"


def ambiguities_path(repo: pathlib.Path) -> pathlib.Path:
    return state_dir(repo) / "ambiguities.md"


def template_manifest_path(repo: pathlib.Path) -> pathlib.Path:
    return state_dir(repo) / "template-manifest.yaml"


def phase_sidecar_path(repo: pathlib.Path, phase: str) -> pathlib.Path:
    if phase not in PHASE_NUMBER:
        raise ValueError(f"unknown phase '{phase}'. Expected one of: {sorted(PHASE_NUMBER)}")
    return phases_dir(repo) / f"phase-{PHASE_NUMBER[phase]}-passed.yaml"


def all_phase_sidecars(repo: pathlib.Path) -> list[pathlib.Path]:
    """Every existing phase sidecar in numeric order. Used by
    audit-time scanners (sha256, prior engagement, review)."""
    pdir = phases_dir(repo)
    if not pdir.is_dir():
        return []
    return sorted(pdir.glob("phase-*-passed.yaml"))


def review_report_path(repo: pathlib.Path, filename: str) -> pathlib.Path:
    """For a given report filename (e.g. '2026-05-31T13-45-31Z.md')
    return the absolute path under .spec-suite/reviews/."""
    return reviews_dir(repo) / filename


def ensure_state_skeleton(repo: pathlib.Path) -> None:
    """Create `.spec-suite/`, `.spec-suite/phases/`, `.spec-suite/reviews/`
    if absent. Idempotent. Called by bootstrap and by anything that
    writes a sidecar before `.spec-suite/` is guaranteed to exist."""
    state_dir(repo).mkdir(parents=True, exist_ok=True)
    phases_dir(repo).mkdir(parents=True, exist_ok=True)
    reviews_dir(repo).mkdir(parents=True, exist_ok=True)
