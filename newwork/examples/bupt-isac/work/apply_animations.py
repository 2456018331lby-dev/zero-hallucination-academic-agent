#!/usr/bin/env python3
"""apply_animations.py - add the ISAC deck's entrance animations via the local editor SDK.

Design (deliberately restrained, academic):
  * text            -> FADE_IN        (anim_type 1)
  * numbers / large glyphs -> ENTER_SCALE (anim_type 18)

Only "ceremony" and "key-number" pages are animated; dense body pages are left
static so the pacing does not drag. At most 3 animations per page.

The shape ids below were read from `slide_get_page_info`. Run with --dry-run first.

Usage:
    python apply_animations.py --file-id <file_id> [--dry-run]

NOTE: the SDK cannot express "after previous", so every node lands as a click
trigger with a 1000 ms fade. Run `retime_animations.py` afterwards to convert
nodes 2..N to after-previous and shorten the fade.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

FADE_IN, ENTER_SCALE = 1, 18

EDSDK = os.path.join(
    os.path.expanduser("~"),
    ".workbuddy", "plugins", "cache", "workbuddy-builtin",
    "skill-tencent-local-office-edit", "5.5.4-wb.38151288.g1ca4889a.h1a8f7c37fe76", "edsdk.py",
)

# (page_index, [(shape_id, anim_type, note), ...])  -- order == playback order
# Page 0 is NOT here: it already ships with 3 FADE_IN nodes (title / subtitle /
# footer) written by the deck builder, which read well for a cover. Leave it.
PLAN = [
    (2, [("000055", ENTER_SCALE, "巨型数字 01"),
         ("000058", FADE_IN, "为什么难"),
         ("00005a", FADE_IN, "三行说明")]),
    (5, [("000089", ENTER_SCALE, "巨型数字 02"),
         ("00008c", FADE_IN, "别人怎么做"),
         ("00008e", FADE_IN, "三行说明")]),
    (8, [("0000e9", ENTER_SCALE, "KPI 0%（[8] 专用感知时频开销）"),
         ("0000f4", ENTER_SCALE, "KPI cm 级（[4] 测距精度）")]),
    (9, [("00010a", ENTER_SCALE, "KPI 4 重（[6] UW-OCDM）"),
         ("000115", ENTER_SCALE, "KPI <1%（[10] RAA 成本）")]),
    (10, [("00012b", ENTER_SCALE, "KPI −10 dB（[12] 数字孪生）"),
          ("000136", ENTER_SCALE, "KPI 5%（[7] LAMBDA 样本比例）")]),
    (11, [("000143", ENTER_SCALE, "巨型数字 03"),
          ("000146", FADE_IN, "还缺什么"),
          ("000148", FADE_IN, "三行说明")]),
    (12, [("000151", FADE_IN, "左栏标题 已经解决 · 5 项"),
          ("000163", FADE_IN, "右栏标题 仍然没有解决 · 7 项")]),
    (14, [("0001ac", FADE_IN, "标题 核心研究逻辑"),
          ("0001b8", FADE_IN, "链式说明句"),
          ("0001bc", FADE_IN, "结论金句")]),
]

# Idempotence guard: refuse to run if any target page already has animations, so
# a careless second invocation cannot double the sequences (this happened once).
RUN_IF_ANY_ANIMATED = False


def call(tool: str, payload: dict, dry: bool):
    if dry:
        print(f"    [dry] {tool} {json.dumps(payload, ensure_ascii=False)}")
        return None
    p = subprocess.run([sys.executable, EDSDK, "call", tool, "--json", json.dumps(payload)],
                       capture_output=True, text=True)
    out = (p.stdout or "").strip()
    print(f"    {tool} -> {out[:160]}")
    if p.returncode != 0:
        print(f"    !! rc={p.returncode} {p.stderr[:200]}", file=sys.stderr)
    return out


def page_anim_count(file_id: str, page: int) -> int:
    d = call("slide_get_page_info",
             {"file_id": file_id, "page_index": page}, dry=False)
    try:
        return int(json.loads(d).get("anim_count", 0))
    except Exception:
        return -1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file-id", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="apply even if target pages already carry animations")
    args = ap.parse_args()

    if not args.dry_run and not args.force:
        dirty = [(p, page_anim_count(args.file_id, p)) for p, _ in PLAN]
        dirty = [(p, n) for p, n in dirty if n > 0]
        if dirty:
            print("REFUSING: these target pages already have animations "
                  f"{dirty}\n           (re-run with --force if that is intended)",
                  file=sys.stderr)
            return 2

    total = 0
    for page, items in PLAN:
        print(f"  page_index={page}  ({len(items)} anims)")
        for shape, atype, note in items:
            print(f"    - {shape} type={atype}  # {note}")
            call("slide_add_anim",
                 {"file_id": args.file_id, "page_index": page,
                  "shape_id": shape, "anim_type": atype},
                 args.dry_run)
            total += 1
    print(f"\n{total} animations across {len(PLAN)} pages"
          f"{' (dry-run)' if args.dry_run else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
