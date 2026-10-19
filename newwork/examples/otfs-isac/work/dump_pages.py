#!/usr/bin/env python3
"""Dump (page_index, shape_id, text, anim_count) for the OTFS deck's target pages.

Read-only: calls slide_get_page_info via edsk.py and prints a table so the
animation PLAN can be written with real shape ids (never hand-built).
"""
from __future__ import annotations
import json
import os
import subprocess
import sys

EDS = os.path.join(
    os.path.expanduser("~"),
    ".workbuddy", "plugins", "cache", "workbuddy-builtin",
    "skill-tencent-local-office-edit", "5.5.4-wb.38151288.g1ca4889a.h1a8f7c37fe76", "edsdk.py",
)
FID = sys.argv[1]
pages = [int(x) for x in sys.argv[2:]] or [0, 2, 5, 8, 9, 10, 11, 12, 14]

for p in pages:
    out = subprocess.run(
        [sys.executable, EDS, "call", "slide_get_page_info",
         "--json", json.dumps({"file_id": FID, "page_index": p})],
        capture_output=True, text=True,
    ).stdout.strip()
    try:
        d = json.loads(out)
    except Exception:
        print(f"===== page {p} :: UNPARSEABLE =====")
        print(out[:300])
        continue
    print(f"===== page {p}  anim_count={d.get('anim_count')}  shapes={d.get('shape_count')} =====")
    for s in d.get("shapes", []):
        t = (s.get("text") or "").replace("\n", " ").replace("\r", " ").strip()
        if t:
            print(f"  {s.get('id')}  |  {t[:44]}")
