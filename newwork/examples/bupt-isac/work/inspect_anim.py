#!/usr/bin/env python3
"""inspect_anim.py - dump the <p:timing> animation structure of every slide.

Reads the .pptx as a plain zip (no editor SDK, no COM), so it is deterministic
and safe to run at any time.

Note on the XML shape: in this deck's <p:cTn> elements the `id` attribute is
absent, so do NOT anchor a regex on `id="..."`. An effect node is identified by
`presetID=` plus `nodeType=`. The animation target is `<p:spTgt spid="N"/>`,
where N is the shape's numeric cNvPr id (not the SDK's hex-like string).

Usage:
    python inspect_anim.py "path/to/deck.pptx" [--xml PAGE]
"""
from __future__ import annotations

import re
import sys
import zipfile


def slide_no(name: str) -> int:
    m = re.search(r"slide(\d+)\.xml$", name)
    return int(m.group(1)) if m else 0


# one effect step: the <p:par> whose <p:cTn> carries presetID + nodeType
EFFECT = re.compile(
    r'<p:cTn\s+presetID="(\d+)"\s+presetClass="(\w+)"\s+presetSubtype="(\d+)"'
    r'[^>]*nodeType="(\w+)"'
)
# the stCondLst immediately following a nodeType (delay of that step)
TARGET = re.compile(r'<p:spTgt\s+spid="(\w+)"')
DUR = re.compile(r'<p:animEffect[^>]*>\s*<p:cBhvr>\s*<p:cTn\s+dur="(\d+)"')


def main() -> int:
    path = sys.argv[1]
    dump = None
    if "--xml" in sys.argv:
        dump = int(sys.argv[sys.argv.index("--xml") + 1])
    z = zipfile.ZipFile(path)
    slides = sorted(
        (n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)),
        key=slide_no,
    )
    grand = 0
    for n in slides:
        xml = z.read(n).decode("utf-8")
        idx = slide_no(n)
        if dump == idx - 1:
            i = xml.find("<p:timing>")
            print(xml[i:i + 4000])
            return 0
        if "<p:timing>" not in xml:
            print(f"slide{idx:>2}  (page {idx - 1:>2})  no timing")
            continue
        effects = EFFECT.findall(xml)
        targets = TARGET.findall(xml)
        durs = DUR.findall(xml)
        # playback "steps": top-level <p:par> groups under the mainSeq childTnLst
        steps = re.findall(r'<p:cond delay="(indefinite|\d+)"/>', xml)
        print(f"slide{idx:>2}  (page {idx - 1:>2})  effects={len(effects)}  "
              f"cond_delays={steps[:8]}")
        for i, (pid, pclass, psub, ntype) in enumerate(effects):
            tgt = targets[i] if i < len(targets) else "?"
            dur = durs[i] if i < len(durs) else "-"
            print(f"      #{i}  spid={tgt:<6} presetID={pid:>3} {pclass:<8} "
                  f"{ntype:<12} dur={dur}")
            grand += 1
    print(f"\ntotal effects on disk = {grand}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
