# -*- coding: utf-8 -*-
"""Render deliverables/文献阅读对比表格.md from the single source of truth
(deliverables/literature_table.json). Keeps md <-> json from drifting apart.
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
JSON_PATH = os.path.join(ROOT, "deliverables", "literature_table.json")
MD_PATH = os.path.join(ROOT, "deliverables", "文献阅读对比表格.md")


def cell(v) -> str:
    """Markdown-table-safe text: escape literal pipes (e.g. |vk| -> \\|vk\\|)."""
    return str(v).replace("|", "\\|")


def main() -> None:
    with open(JSON_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    meta = data["meta"]
    papers = data["papers"]

    L: list[str] = []
    L.append(f"# 文献阅读对比表格 · {meta['direction']}")
    L.append("")
    L.append(f"**子方向**：{meta['subtitle']}")
    L.append("")
    L.append(f"> **数据来源**：{meta['source_note']}")
    L.append("> ")
    L.append(f"> **取材原则**：{meta['rules']}")
    L.append("")
    L.append(f"共 **{len(papers)}** 篇。生成日期：{meta['generated']}")
    L.append("")

    # 表 1 · 书目信息总览
    L.append("## 表 1 · 书目信息总览")
    L.append("")
    L.append("| 序号 | 论文题目 | 作者 | 年份 | 会议/期刊 | 是否建议重点汇报 |")
    L.append("| :---: | :--- | :--- | :---: | :--- | :--- |")
    for p in papers:
        L.append(f"| {p['id']} | {cell(p['title'])} | {cell(p['authors'])} | {p['year']} | {cell(p['venue'])} | {p['recommend']} |")
    L.append("")

    # 表 2 · 研究内容对比
    L.append("## 表 2 · 研究内容对比")
    L.append("")
    L.append("| 序号 | 研究问题 | 核心方法 | 主要创新点 |")
    L.append("| :---: | :--- | :--- | :--- |")
    for p in papers:
        L.append(f"| {p['id']} | {cell(p['problem'])} | {cell(p['method'])} | {cell(p['innovation'])} |")
    L.append("")

    # 表 3 · 实验设置与关键结果
    L.append("## 表 3 · 实验设置与关键结果")
    L.append("")
    L.append("| 序号 | 数据集/实验设置 | 关键实验结果 |")
    L.append("| :---: | :--- | :--- |")
    for p in papers:
        L.append(f"| {p['id']} | {cell(p['setup'])} | {cell(p['results'])} |")
    L.append("")

    # 表 4 · 评价、定位与汇报建议
    L.append("## 表 4 · 评价、定位与汇报建议")
    L.append("")
    L.append("| 序号 | 方法优点 | 方法局限 | 与本研究方向的关系 | 是否建议重点汇报 | 推荐汇报理由 |")
    L.append("| :---: | :--- | :--- | :--- | :--- | :--- |")
    for p in papers:
        L.append(f"| {p['id']} | {cell(p['pros'])} | {cell(p['cons'])} | {cell(p['relation'])} | {p['recommend']} | {cell(p['why'])} |")
    L.append("")
    L.append("---")
    L.append("")

    # 附录 · 逐篇完整 15 字段卡片
    L.append("## 附录 · 逐篇完整 15 字段卡片")
    L.append("")
    for p in papers:
        L.append(f"### [{p['id']}] {p['title']}")
        L.append("")
        L.append(f"- **本地文件**：`{p['file']}`")
        L.append(f"- **论文题目**：{cell(p['title'])}")
        L.append(f"- **作者**：{cell(p['authors'])}")
        L.append(f"- **年份**：{p['year']}")
        venue = cell(p["venue"])
        if p.get("venue_note"):
            venue += f"（{p['venue_note']}）"
        L.append(f"- **会议/期刊**：{venue}")
        L.append(f"- **研究问题**：{cell(p['problem'])}")
        L.append(f"- **核心方法**：{cell(p['method'])}")
        L.append(f"- **主要创新点**：{cell(p['innovation'])}")
        L.append(f"- **数据集/实验设置**：{cell(p['setup'])}")
        L.append(f"- **关键实验结果**：{cell(p['results'])}")
        L.append(f"- **方法优点**：{cell(p['pros'])}")
        L.append(f"- **方法局限**：{cell(p['cons'])}")
        L.append(f"- **与本研究方向的关系**：{cell(p['relation'])}")
        L.append(f"- **是否建议重点汇报**：{p['recommend']}")
        L.append(f"- **推荐汇报理由**：{cell(p['why'])}")
        L.append("")

    out = "\n".join(L).rstrip("\n") + "\n"
    with open(MD_PATH, "w", encoding="utf-8") as fh:
        fh.write(out)
    print("wrote", MD_PATH, "papers =", len(papers))


if __name__ == "__main__":
    main()
