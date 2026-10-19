# -*- coding: utf-8 -*-
"""Patch deliverables/文献阅读对比表格.xlsx so it matches the JSON (add [30]).

We patch (insert one row, copy the neighbour's style) instead of regenerating, so
every existing cell style / width / freeze pane is preserved byte-for-byte.
"""
from __future__ import annotations

import json
import os
from copy import copy

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
JSON_PATH = os.path.join(ROOT, "deliverables", "literature_table.json")
XLSX = os.path.join(ROOT, "deliverables", "文献阅读对比表格.xlsx")

COLS = ["id", "title", "authors", "year", "venue", "problem", "method", "innovation",
        "setup", "results", "pros", "cons", "relation", "recommend", "why"]


def main() -> None:
    with open(JSON_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    row = next(p for p in data["papers"] if p["id"] == "[30]")

    wb = openpyxl.load_workbook(XLSX)
    ws = wb["文献阅读对比表"]

    # locate the [20] row (we insert right after it)
    target = None
    for r in range(2, ws.max_row + 1):
        if ws.cell(r, 1).value == "[20]":
            target = r
            break
    if target is None:
        raise SystemExit("[20] row not found")
    if any(ws.cell(r, 1).value == "[30]" for r in range(2, ws.max_row + 1)):
        print("already present")
        return

    ins = target + 1
    ws.insert_rows(ins)
    # copy style from the row above (the [20] row)
    for c in range(1, len(COLS) + 1):
        src = ws.cell(target, c)
        dst = ws.cell(ins, c)
        dst._style = copy(src._style)
    ws.row_dimensions[ins].height = ws.row_dimensions[target].height or 130.0

    for c, key in enumerate(COLS, start=1):
        ws.cell(ins, c, row[key])

    # keep the 取材说明 sheet's counts in sync
    ws2 = wb["取材说明"]
    for r in range(1, ws2.max_row + 1):
        v = ws2.cell(r, 2).value
        if isinstance(v, str):
            nv = v.replace("深读 11 篇", "深读 12 篇") \
                  .replace("深读名单为 11 篇，其余 28 篇作为背景",
                           "深读名单为 12 篇，其余 27 篇作为背景")
            if nv != v:
                ws2.cell(r, 2, nv)

    wb.save(XLSX)
    print("patched xlsx: inserted [30] at row", ins, "| sheet1 rows now", ws.max_row)


if __name__ == "__main__":
    main()
