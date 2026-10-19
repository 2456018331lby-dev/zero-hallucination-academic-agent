"""Repository and skill-script discovery.

The gates are plain scripts under ``.agents/skills/<skill>/scripts/``. We never
hard-code an absolute path: the repository root is discovered from this file's
location, or from ``ZHAW_ROOT`` when the package is installed elsewhere
(``pip install zhaw`` + a separate checkout).
"""
from __future__ import annotations

import os
from pathlib import Path

_ENV_VAR = "ZHAW_ROOT"


def repo_root() -> Path:
    """Return the checkout root that contains ``.agents/skills``."""
    override = os.environ.get(_ENV_VAR)
    if override:
        root = Path(override).expanduser().resolve()
        if (root / ".agents" / "skills").is_dir():
            return root
        raise SystemExit(
            f"[ERR] {_ENV_VAR}={root} does not look like a checkout: "
            f"missing .agents/skills/"
        )

    here = Path(__file__).resolve()
    # In-place install (repo root contains the zhaw/ package) or any parent.
    for candidate in (here.parent.parent, *here.parents):
        if (candidate / ".agents" / "skills").is_dir():
            return candidate
    raise SystemExit(
        "[ERR] Cannot locate the repository root.\n"
        "      Expected a checkout containing .agents/skills/ next to the zhaw package,\n"
        f"      or set {_ENV_VAR} to the repository root."
    )


def skills_dir() -> Path:
    return repo_root() / ".agents" / "skills"


def script(relative: str) -> Path:
    """Resolve a gate script such as ``citation-auditor/scripts/check_citations.py``."""
    path = skills_dir() / relative
    if not path.is_file():
        raise SystemExit(
            f"[ERR] Gate script not found: {path}\n"
            "      Your checkout may be incomplete; run `zhaw doctor`."
        )
    return path
