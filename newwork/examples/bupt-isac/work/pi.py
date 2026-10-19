#!/usr/bin/env python3
"""pi.py - compact slide shape dump for the editor SDK.

Prints, per requested page, every shape that carries text (or is a large
glyph), sorted by font size desc, so we can pick animation targets without
hardcoding stale ids.

Usage:
    python pi.py <file_id> 2 5 8 9 10 11 12 14
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

EDSDK = os.path.join(
    os.path.expanduser("~"),
    ".workbuddy", "plugins", "cache", "workbuddy-builtin",
    "skill-tencent-local-office-edit", "5.5.4-wb.38151288.g1ca4889a.h1a8f7c37fe76", "edsdk.py",
)


def call(tool: str, payload: dict) -> dict:
    p = subprocess.run([sys.executable, EDSDK, "call", tool, "--json", json.dumps(payload)],
                       capture_output=True, text=True)
    out = (p.stdout or "").strip()
    try:
        return json.loads(out)
    except Exception:
        return {"_raw": out, "_err": (p.stderr or "")[:300]}


def main() -> int:
    file_id = sys.argv[1]
    pages = [int(a) for a in sys.argv[2:]]
    for pg in pages:
        d = call("slide_get_page_info", {"file_id": file_id, "page_index": pg})
        if "_raw" in d:
            print(f"page {pg}: ERROR {d['_raw'][:200]} {d.get('_err','')}")
            continue
        anims = d.get("animations", [])
        print(f"=== page {pg}  anim_count={d.get('anim_count')} "
              f"shapes={d.get('shape_count')} page_id={d.get('page_id')}")
        if anims:
            for a in anims:
                print(f"    anim#{a['index']} spid={a['shape_id']} preset={a['preset_id']}")
        rows = []
        for s in d.get("shapes", []):
            txt = (s.get("text") or "").replace("\r", " ").strip()
            fs = s.get("font_size") or 0
            if txt or fs >= 36:
                rows.append((fs, s.get("id"), s.get("w"), s.get("h"), txt[:40]))
        rows.sort(key=lambda r: -r[0])
        for fs, sid, w, h, txt in rows:
            print(f"    {sid}  fs={fs:<5} {w}x{h}  {txt!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
