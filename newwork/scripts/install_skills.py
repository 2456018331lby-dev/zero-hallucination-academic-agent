#!/usr/bin/env python3
"""install_skills.py - sync the skills in this repo into the WorkBuddy skill root.

`newwork/skills/` is the SOURCE OF TRUTH for the skills used by this workflow.
WorkBuddy (and the agent) only picks a skill up if it lives under the user-level
skill root, so run this once after cloning / after editing a skill:

    python install_skills.py                # install/refresh every skill here
    python install_skills.py --only phd-literature-review
    python install_skills.py --dry-run

Target root defaults to  ~/.workbuddy/skills  (override with --root).
It copies each `skills/<name>/` folder over the installed copy; it never deletes
unrelated skills, and it never touches the source tree.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "skills"))
DEFAULT_ROOT = os.path.join(os.path.expanduser("~"), ".workbuddy", "skills")


def main() -> int:
    ap = argparse.ArgumentParser(description="Install/refresh the workflow's skills.")
    ap.add_argument("--root", default=DEFAULT_ROOT, help="skill root (default ~/.workbuddy/skills)")
    ap.add_argument("--only", default=None, help="install just this skill name")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.isdir(SRC):
        sys.exit(f"skills source not found: {SRC}")

    names = sorted(
        d for d in os.listdir(SRC)
        if os.path.isdir(os.path.join(SRC, d)) and not d.startswith(".")
    )
    if args.only:
        names = [n for n in names if n == args.only] or sys.exit(f"no such skill: {args.only}")
    if not names:
        sys.exit("no skills to install")

    os.makedirs(args.root, exist_ok=True)
    for name in names:
        src, dst = os.path.join(SRC, name), os.path.join(args.root, name)
        if not os.path.isfile(os.path.join(src, "SKILL.md")):
            print(f"  skip {name}: no SKILL.md")
            continue
        if args.dry_run:
            print(f"  would install {name} -> {dst}")
            continue
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        print(f"  installed {name} -> {dst}")
    print(f"\ndone ({'dry-run' if args.dry_run else 'installed ' + str(len(names)) + ' skill(s)'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
