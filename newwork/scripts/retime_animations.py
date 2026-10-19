#!/usr/bin/env python3
"""retime_animations.py - make each slide self-build after a single click.

The local editor SDK can only produce click-triggered entrance effects
(`slide_add_anim` exposes no startType/duration), so a page with 3 effects needs
3 clicks. This script rewrites the saved <p:timing> tree directly:

  * the 1st click group of every slide is left alone  -> "on click"
  * groups 2..N get their outer <p:cond delay="indefinite"/> replaced by a
    numeric stagger and their effect nodeType clickEffect -> afterEffect
    -> "after previous"
  * fade durations are shortened 1000 ms -> 600 ms for a crisper feel
    (the scale preset is already 500 ms)

This is a deterministic zip rewrite: every part is copied verbatim except the
slide XMLs that actually change. Always run with --dry-run first.

Usage:
    python retime_animations.py <pptx> [--stagger 300] [--dry-run]
    python retime_animations.py <pptx> --check        # report only, no write
"""
from __future__ import annotations

import argparse
import re
import shutil
import zipfile
from xml.etree import ElementTree

# A click group always begins with exactly this sequence.
GROUP_HEAD = ('<p:par><p:cTn fill="hold"><p:stCondLst>'
              '<p:cond delay="indefinite"/></p:stCondLst>')
FADE_DUR = re.compile(r'(<p:animEffect[^>]*>\s*<p:cBhvr>\s*<p:cTn dur=")1000(")')


def retime_slide(xml: str, stagger: int, fade_ms: int) -> tuple[str, int, bool]:
    """Return (new_xml, groups_converted, changed)."""
    starts = [m.start() for m in re.finditer(re.escape(GROUP_HEAD), xml)]
    if len(starts) <= 1:
        groups = 0
    else:
        groups = len(starts) - 1

    out, prev = [], 0
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(xml)
        seg = xml[s:e]
        if i > 0:
            seg = seg.replace('<p:cond delay="indefinite"/>',
                              f'<p:cond delay="{stagger}"/>', 1)
            seg = seg.replace('nodeType="clickEffect"',
                              'nodeType="afterEffect"', 1)
        out.append(xml[prev:s])
        out.append(seg)
        prev = e
    out.append(xml[prev:])
    new = "".join(out)

    if fade_ms != 1000:
        new = FADE_DUR.sub(lambda m: f'{m.group(1)}{fade_ms}{m.group(2)}', new)

    # hard validation: must still be well-formed XML
    ElementTree.fromstring(new)
    return new, groups, new != xml


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pptx")
    ap.add_argument("--stagger", type=int, default=300,
                    help="ms gap between cascaded effects (default 300)")
    ap.add_argument("--fade-ms", type=int, default=600)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="report the current state, never write")
    args = ap.parse_args()

    zin = zipfile.ZipFile(args.pptx)
    names = zin.namelist()
    slides = sorted(
        (n for n in names if re.match(r"ppt/slides/slide\d+\.xml$", n)),
        key=lambda n: int(re.search(r"(\d+)", n.split("/")[-1]).group(1)),
    )

    patched: dict[str, str] = {}
    for n in slides:
        xml = zin.read(n).decode("utf-8")
        new, groups, changed = retime_slide(xml, args.stagger, args.fade_ms)
        if changed:
            patched[n] = new

        before_clicks = len(re.findall(r'<p:cond delay="indefinite"/>', xml))
        after_clicks = len(re.findall(r'<p:cond delay="indefinite"/>', new))
        after_auto = new.count('nodeType="afterEffect"')
        tag = "check" if args.check else ("dry" if args.dry_run else "wrote")
        print(f"  {n:<28} click {before_clicks} -> {after_clicks}   "
              f"auto-after 0 -> {after_auto}   groups={groups} [{tag}]")

    if args.check or args.dry_run:
        print(f"\n{len(patched)} slide(s) would change; no file written")
        return 0

    if not patched:
        print("\nnothing to do")
        return 0

    shutil.copy2(args.pptx, args.pptx + ".bak")
    tmp = args.pptx + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in names:
            data = zin.read(n)
            if n in patched:
                data = patched[n].encode("utf-8")
            zout.writestr(n, data)
    zin.close()
    shutil.move(tmp, args.pptx)
    print(f"\nrewrote {args.pptx}: {len(patched)} slide(s) retimed "
          f"(stagger={args.stagger} ms, fade={args.fade_ms} ms). "
          f"Backup at {args.pptx}.bak")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
