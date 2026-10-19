#!/usr/bin/env python3
"""apply_animations.py (OTFS-ISAC deck) - entrance animations via the local editor SDK.

Design (restrained, academic):
  * text / labels          -> FADE_IN     (anim_type 1)
  * big numerals / KPI      -> ENTER_SCALE (anim_type 18)

Only ceremony + key-number pages are animated; dense body pages stay static.
At most 3 animations per page. Shape ids were read from `slide_get_page_info`
(dump_pages.py) - never hand-built.

Usage:
    python apply_animations.py --file-id <file_id> [--dry-run] [--force]

The SDK always emits click-triggered 1000 ms fades and cannot express
"after previous", so run `retime_animations.py` afterwards.
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

# (page_index, [(shape_id, anim_type, note), ...]) -- order == playback order
PLAN = [
    (0, [("dc24751b_226a55f673d102be", FADE_IN, "封面 主标题"),
         ("a16a21a6_226a55f673d102be", FADE_IN, "封面 副标题"),
         ("694706e4_226a55f673d102be", FADE_IN, "封面 文献基础/落款")]),
    (2, [("bddbe3d4_64c8816bb173d838", ENTER_SCALE, "巨型数字 01"),
         ("0b8199d2_64c8816bb173d838", FADE_IN, "为什么难"),
         ("c2cf95fb_64c8816bb173d838", FADE_IN, "三行说明")]),
    (5, [("bddbe3d4_330ef55e9329f257", ENTER_SCALE, "巨型数字 02"),
         ("0b8199d2_330ef55e9329f257", FADE_IN, "文献格局"),
         ("c2cf95fb_330ef55e9329f257", FADE_IN, "三行说明")]),
    (8, [("203a827_b3fcf15d249a9e90", ENTER_SCALE, "KPI M 倍（[04] 无模糊距离）"),
         ("7fe84dbc_b3fcf15d249a9e90", ENTER_SCALE, "KPI 3.125%（[06] 导频开销）")]),
    (9, [("203a827_19faa054254605da", ENTER_SCALE, "KPI 1200 m/s（[37] 相对速度）"),
         ("7fe84dbc_19faa054254605da", ENTER_SCALE, "KPI 对数线性（[34] 均衡复杂度）")]),
    (10, [("203a827_ca09fdab9046fd24", ENTER_SCALE, "KPI 2-D FFT（[39] 退化）"),
          ("7fe84dbc_ca09fdab9046fd24", ENTER_SCALE, "KPI 约 20%（[25] SE 提升）")]),
    (11, [("bddbe3d4_bb30ceaffa635ed2", ENTER_SCALE, "巨型数字 03"),
          ("0b8199d2_bb30ceaffa635ed2", FADE_IN, "还缺什么"),
          ("c2cf95fb_bb30ceaffa635ed2", FADE_IN, "三行说明")]),
    (12, [("0b8199d2_45d9a7da527e04a7", FADE_IN, "左栏标题 已在文献自身设定内解决"),
          ("203a827_45d9a7da527e04a7", FADE_IN, "右栏标题 仍然没有解决")]),
    (14, [("dc24751b_6b90968ed689c7f3", FADE_IN, "标题 核心研究逻辑"),
          ("ff944461_6b90968ed689c7f3", FADE_IN, "链式说明句"),
          ("b0b1674a_6b90968ed689c7f3", FADE_IN, "结论金句")]),
]


def call(tool: str, payload: dict, dry: bool):
    if dry:
        print(f"    [dry] {tool} {json.dumps(payload, ensure_ascii=False)}")
        return None
    p = subprocess.run([sys.executable, EDSDK, "call", tool, "--json", json.dumps(payload)],
                       capture_output=True, text=True)
    out = (p.stdout or "").strip()
    print(f"    {tool} -> {out[:150]}")
    if p.returncode != 0:
        print(f"    !! rc={p.returncode} {p.stderr[:200]}", file=sys.stderr)
    return out


def page_anim_count(file_id: str, page: int) -> int:
    d = call("slide_get_page_info", {"file_id": file_id, "page_index": page}, dry=False)
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
