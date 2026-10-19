# -*- coding: utf-8 -*-
"""Bump the deep-read count 11 -> 12 in the OTFS deck's four count runs.

The deck's category tables already list [30] (e.g. slide 8 "[30] [38]"), so only
the stated *count* was stale. Edits are surgical: exact-run replacement, zip
rewritten entry-for-entry so animations / media are untouched.
"""
from __future__ import annotations

import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
PPTX = os.path.join(ROOT, "deliverables", "OTFS-ISAC方向汇报", "OTFS-ISAC方向汇报.pptx")
BAK = os.path.join(HERE, "backup", "_pptx_before_count.pptx")

# slide -> ordered list of (old_run_text, new_run_text) applied to <a:t>..</a:t>
EDITS = {
    "ppt/slides/slide1.xml": [("<a:t> 11 </a:t>", "<a:t> 12 </a:t>"),
                              ("<a:t>11/11 </a:t>", "<a:t>12/12 </a:t>")],
    "ppt/slides/slide13.xml": [("<a:t> 11 </a:t>", "<a:t> 12 </a:t>")],
    "ppt/slides/slide15.xml": [("<a:t> 11 </a:t>", "<a:t> 12 </a:t>")],
}


def main() -> None:
    if not os.path.exists(BAK):
        os.makedirs(os.path.dirname(BAK), exist_ok=True)
        with open(PPTX, "rb") as s, open(BAK, "wb") as d:
            d.write(s.read())

    zin = zipfile.ZipFile(PPTX, "r")
    items = zin.infolist()
    payload = {}
    for n in EDITS:
        xml = zin.read(n).decode("utf-8")
        for old, new in EDITS[n]:
            cnt = xml.count(old)
            if cnt != 1:
                print(f"ABORT: {n}: expected 1 of {old!r}, found {cnt}", file=sys.stderr)
                zin.close()
                return
            xml = xml.replace(old, new)
        payload[n] = xml.encode("utf-8")
    zin.close()

    tmp = PPTX + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for it in items:
            data = payload.get(it.filename)
            if data is None:
                data = zipfile.ZipFile(PPTX).read(it.filename)
            zout.writestr(it, data)
    os.replace(tmp, PPTX)

    # verify
    z = zipfile.ZipFile(PPTX)
    ok = True
    for n, edits in EDITS.items():
        x = z.read(n).decode("utf-8")
        for _, new in edits:
            if new not in x:
                ok = False
                print("MISSING after edit:", n, new, file=sys.stderr)
    print("count bump done; verify:", "OK" if ok else "FAILED")
    print("slides:", len([m for m in z.namelist() if re.match(r'ppt/slides/slide\d+\.xml$', m)]))


if __name__ == "__main__":
    main()
