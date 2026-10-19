#!/usr/bin/env python3
"""verify_mimo_audit.py - cross-check MiMo's metadata table against the main agent's own data.

This is the "trust but verify" step of the orchestrator/subagent workflow
(see docs/01-workflow.md): MiMo's reply is a *draft*, not a conclusion.

It compares three independent sources:
  1. MiMo's markdown table      -> work/mimo_metadata_audit.md
  2. the main agent's data       -> deliverables/literature_table.json  (arXiv id, year, title)
  3. ground truth page counts    -> work/pdftext/*.txt  (max n in `<<<PAGE n>>>`)

and writes a verification report next to the MiMo reply.
"""
from __future__ import annotations

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))          # .../work
EX = os.path.normpath(os.path.join(HERE, ".."))            # .../examples/bupt-isac
MIMO = os.path.join(HERE, "mimo_metadata_audit.md")
JSON = os.path.join(EX, "deliverables", "literature_table.json")
PDFTEXT = os.path.join(HERE, "pdftext")
OUT = os.path.join(HERE, "mimo_audit_verification.md")


def load_mimo_rows():
    """Parse the 6-column markdown table from MiMo's reply, keyed by the [NN] prefix."""
    rows = {}
    if not os.path.isfile(MIMO):
        return rows
    for line in open(MIMO, encoding="utf-8"):
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 6:
            continue
        if set(cells[0]) <= set(":- ") or cells[1] in ("文件名", "filename"):
            continue                                     # header / separator
        m = re.match(r"\[(\d+)\]", cells[1])
        if not m:
            continue
        rows[str(int(m.group(1)))] = {                 # normalize [01] -> "1"
            "file": cells[1], "arxiv": cells[2], "year": cells[3],
            "title": cells[4], "pages": cells[5],
        }
    return rows


def truth():
    data = json.load(open(JSON, encoding="utf-8"))
    t = {}
    for p in data["papers"]:
        pid = str(int(str(p["id"]).strip("[]")))         # "[01]" / "[1]" -> "1"
        arxiv = re.search(r"(arXiv:\d{4}\.\d{4,5}(?:v\d+)?)", str(p.get("venue", "")))
        pat = re.compile(r"^\[0*%d\]" % int(pid))     # match [01]_... for pid "1"
        fname = next((f for f in os.listdir(PDFTEXT) if pat.match(f)), "")
        src = os.path.join(PDFTEXT, fname) if fname else ""
        pages = ""
        if os.path.isfile(src):
            nums = [int(n) for n in re.findall(r"<<<PAGE (\d+)>>>", open(src, encoding="utf-8").read())]
            pages = str(max(nums)) if nums else ""
        t[pid] = {
            "arxiv": arxiv.group(1) if arxiv else "",
            "year": str(p.get("year", "")),
            "title": re.sub(r"\s+", " ", str(p.get("title", ""))).strip(),
            "pages": pages,
        }
    return t


def norm(s: str) -> str:
    s = re.sub(r"arXiv:", "", str(s), flags=re.I)
    s = re.sub(r"[\s\-–—_.,:;()\[\]/]+", "", s)
    return s.lower()


def main() -> int:
    mimo, truthmap = load_mimo_rows(), truth()
    ids = sorted(set(mimo) | set(truthmap), key=lambda x: int(x))

    L = ["# MiMo 子代理回执 · 交叉核对报告", "",
         "> 核对对象：`work/mimo_metadata_audit.md`（MiMo 产出）",
         "> 基准：`deliverables/literature_table.json`（主代理数据）＋ `work/pdftext/*.txt`（页码真值）", ""]

    if not mimo:
        L.append("**未找到可解析的 MiMo 表格**（文件缺失或格式不符）。")
        open(OUT, "w", encoding="utf-8").write("\n".join(L))
        print("no MiMo rows parsed")
        return 1

    L += ["| 序号 | 字段 | MiMo | 基准 | 判定 |", "| :--: | :-- | :-- | :-- | :--: |"]
    ok = bad = 0
    for pid in ids:
        m, t = mimo.get(pid), truthmap.get(pid)
        if not m or not t:
            L.append(f"| [{pid}] | — | {'缺失' if not m else '—'} | {'缺失' if not t else '—'} | ⚠️ |")
            bad += 1
            continue
        for key, label in (("arxiv", "arXiv 编号"), ("year", "年份"), ("title", "标题"), ("pages", "页数")):
            same = norm(m[key]) == norm(t[key]) or (
                key == "arxiv" and norm(m[key]).rstrip("v0123456789") == norm(t[key]).rstrip("v0123456789"))
            if same:
                ok += 1
            else:
                bad += 1
            L.append(f"| [{pid}] | {label} | {m[key][:60] or '（空）'} | {t[key][:60] or '（空）'} | "
                     f"{'✅' if same else '❌'} |")

    L += ["", f"**统计**：一致 {ok} 项，不一致 {bad} 项。", ""]
    if bad == 0:
        L.append("**结论**：MiMo 回执与主代理数据完全一致，可采信。")
    else:
        L.append("**结论**：存在不一致项。以 `work/pdftext/` 原文为准修正；MiMo 产出仅作辅助。")
    open(OUT, "w", encoding="utf-8").write("\n".join(L))
    print(f"wrote {OUT}  (ok={ok}, bad={bad})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
