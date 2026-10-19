#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_grounding.py -- thin shim (single source of truth lives in .agents).

The real implementation, including both **table mode** and **matrix mode**, is
maintained once at:

    .agents/skills/phd-literature-survey/scripts/verify_grounding.py

Keeping one copy kills the historical drift between the two skills (the same
gate used to exist here and there, and they silently diverged). This shim keeps
the documented CLI of `phd-literature-review` working unchanged.

Usage (identical to the canonical script):

    python verify_grounding.py --table-json literature_table.json --pdftext _pdftext
    python verify_grounding.py survey/matrix.md --pdf-dir literature
"""
from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
# <repo>/newwork/skills/phd-literature-review/scripts/this.py -> <repo>
REPO = HERE.parents[4]


def _canonical() -> Path:
    override = os.environ.get("ZHAW_ROOT")
    root = Path(override).resolve() if override else REPO
    return root / ".agents" / "skills" / "phd-literature-survey" / "scripts" / "verify_grounding.py"


def main() -> int:
    target = _canonical()
    if not target.is_file():
        sys.stderr.write(
            "[ERR] Canonical implementation not found: %s\n"
            "      Run from a checkout of zero-hallucination-academic-agent,\n"
            "      or set ZHAW_ROOT to the repo root.\n" % target
        )
        return 2
    # Execute the canonical script as __main__: argv and exit code pass through.
    runpy.run_path(str(target), run_name="__main__")
    return 0


if __name__ == "__main__":
    sys.exit(main())
