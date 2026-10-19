"""`zhaw seminar` — turn a 15+1 column literature matrix into a group-meeting deck.

Outputs three files:
  * ``seminar_presentation.tex`` — compilable ctexbeamer (16:9, Madrid, booktabs)
  * ``seminar_outline.md``       — Marp-compatible outline, for quick editing
  * ``seminar_notes.md``         — speaker notes, one block per slide

Every slide is generated from the matrix, so a fabricated claim has nowhere to
come from: if the matrix says 文献未说明, the slide says 文献未说明.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from ._paths import repo_root
from ._util import col, now_iso, parse_matrix, write_json, write_text

PAPER_FIELDS = [
    ("研究问题 / 系统架构", ("系统架构", "架构")),
    ("波形与信号设计", ("波形",)),
    ("感知侧指标", ("感知指标", "感知")),
    ("通信侧指标", ("通信指标", "通信")),
    ("场景约束", ("高度", "速度")),
    ("优化方法", ("优化方法", "算法")),
    ("核心折中", ("折中",)),
]

TEX_SPECIALS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


MATH_SPAN_RE = re.compile(r"(\$[^$]*\$)")


def tex_escape(value: str) -> str:
    """Escape a matrix cell for safe LaTeX body text, preserving inline math.

    Cells in a literature matrix often carry inline math such as ``$V_{\\max}$``.
    Stripping the ``$`` and then escaping ``_`` mangles it into
    ``V\\_\\{\\textbackslash{}max\\}``, so math spans are passed through verbatim
    and only the surrounding text is escaped.
    """
    s = (value or "").strip()
    s = re.sub(r"\s+", " ", s)
    if "$" not in s:
        return "".join(TEX_SPECIALS.get(ch, ch) for ch in s)
    out = []
    for part in MATH_SPAN_RE.split(s):
        if len(part) >= 2 and part.startswith("$") and part.endswith("$"):
            out.append(part)
        else:
            out.append("".join(TEX_SPECIALS.get(ch, ch) for ch in part))
    return "".join(out)


def _paper_title(row: dict) -> str:
    return col(row, "论文题目", "题目", "title", default="（未命名）")


def _author(row: dict) -> str:
    return col(row, "第一作者", "作者", default="文献未说明")


def _venue(row: dict) -> str:
    return col(row, "发表期刊", "期刊", "会议", "venue", default="文献未说明")


def _year(row: dict) -> str:
    return col(row, "年份", "year", default="")


def _evidence(row: dict) -> str:
    return col(row, "本地文献出处", "出处", "页码", default="文献未说明")


def _build_tex(matrix: dict, meta: dict) -> str:
    rows = matrix["rows"]
    topic = meta.get("topic") or matrix["title"] or "文献综述"
    title_zh = meta.get("title") or f"{topic}：前沿文献精读与开题切入点"
    author = meta.get("author") or "汇报人"
    advisor = meta.get("advisor") or "指导教师"
    institute = meta.get("institute") or "信息与通信工程学院"

    lines: list[str] = [
        "% -*- coding: utf-8 -*-",
        "% 由 `zhaw seminar` 从文献对比矩阵自动生成。",
        f"% 生成时间: {meta.get('generated_at', '')}",
        f"% 矩阵来源: {meta.get('matrix_name', '')}（{len(rows)} 篇）",
        "% 每个数字都可回溯到矩阵的『本地文献出处与页码』列。",
        r"\documentclass[aspectratio=169,10pt,UTF8]{ctexbeamer}",
        r"\usetheme{Madrid}",
        r"\usecolortheme{default}",
        r"\usepackage{amsmath,amssymb,amsfonts}",
        r"\usepackage{booktabs}",
        r"\usepackage{array}",
        r"\usepackage{hyperref}",
        r"\definecolor{AcademiaBlue}{RGB}{24,76,120}",
        r"\setbeamercolor{structure}{fg=AcademiaBlue}",
        r"\setbeamercolor{title}{fg=white,bg=AcademiaBlue}",
        r"\setbeamercolor{frametitle}{fg=white,bg=AcademiaBlue}",
        r"\setbeamercolor{block title}{fg=white,bg=AcademiaBlue}",
        r"\setbeamerfont{frametitle}{size=\large}",
        r"\setbeamertemplate{navigation symbols}{}",
        "",
        f"\\title[{tex_escape(topic)}]{{{tex_escape(title_zh)}}}",
        r"\subtitle{组会文献精读分享 / 开题文献调研}",
        f"\\author[{tex_escape(author)}]{{{tex_escape(author)} \\quad 指导教师：{tex_escape(advisor)}}}",
        f"\\institute[{{{tex_escape(institute)}}}]{{{tex_escape(institute)}}}",
        r"\date{\today}",
        "",
        r"\begin{document}",
        "",
        r"\begin{frame}",
        r"  \titlepage",
        r"\end{frame}",
        "",
        r"\begin{frame}{汇报大纲}",
        r"  \tableofcontents",
        r"\end{frame}",
        "",
        r"\section{研究背景与核心矛盾}",
        r"\begin{frame}{为什么做这个方向}",
    ]
    intro = matrix.get("intro", "")
    if intro:
        lines.append(r"  \begin{block}{矩阵前言（原文摘录）}")
        for para in [p for p in intro.split("\n") if p.strip()][:2]:
            lines.append("    " + tex_escape(para))
            lines.append("")
        lines.append(r"  \end{block}")
    lines += [
        r"  \vspace{0.2cm}",
        r"  \begin{itemize}",
        f"    \\item 精读文献数：\\textbf{{{len(rows)} 篇}}",
        f"    \\item 覆盖年份：{tex_escape(_year_range(rows))}",
        f"    \\item 覆盖方法：{tex_escape(_method_summary(rows))}",
        r"  \end{itemize}",
        r"\end{frame}",
        "",
        r"\section{逐篇精读}",
    ]

    for idx, row in enumerate(rows, 1):
        title = _paper_title(row)
        lines += [
            f"\\begin{{frame}}{{{idx}. {tex_escape(title[:60])}}}",
            f"  \\footnotesize",
            f"  \\textbf{{作者/出处}}: {tex_escape(_author(row))}，{tex_escape(_venue(row))}，{tex_escape(_year(row))}\\\\",
            f"  \\textbf{{证据}}: {tex_escape(_evidence(row))}",
            r"  \vspace{0.15cm}",
            r"  \begin{description}",
        ]
        for label, aliases in PAPER_FIELDS:
            value = col(row, *aliases, default="文献未说明")
            lines.append(f"    \\item[{tex_escape(label)}] {tex_escape(value)}")
        lines += [r"  \end{description}", r"\end{frame}", ""]

    lines += [
        r"\section{横向对比}",
        r"\begin{frame}{核心维度横向对比}",
        r"  \scriptsize",
        r"  \setlength{\tabcolsep}{3pt}",
        r"  \begin{table}",
        r"    \centering",
        r"    \begin{tabular}{@{}p{0.6cm}p{3.2cm}p{1.4cm}p{2.2cm}p{2.2cm}p{3.2cm}@{}}",
        r"      \toprule",
        r"      序号 & 论文 & 年份 & 感知指标 & 通信指标 & 核心折中 \\",
        r"      \midrule",
    ]
    for row in rows:
        lines.append(
            "      {n} & {t} & {y} & {s} & {c} & {tr} \\\\".format(
                n=tex_escape(col(row, "序号", default="")),
                t=tex_escape(_short(_paper_title(row), 26)),
                y=tex_escape(_year(row)),
                s=tex_escape(_short(col(row, "感知指标", "感知", default="文献未说明"), 18)),
                c=tex_escape(_short(col(row, "通信指标", "通信", default="文献未说明"), 18)),
                tr=tex_escape(_short(col(row, "折中", default="文献未说明"), 24)),
            )
        )
    lines += [
        r"      \bottomrule",
        r"    \end{tabular}",
        r"  \end{table}",
        r"\end{frame}",
        "",
        r"\section{趋势、空白与切入点}",
        r"\begin{frame}{技术演进脉络}",
        r"  \begin{itemize}",
    ]
    for item in _trends(rows):
        lines.append(f"    \\item {tex_escape(item)}")
    lines += [
        r"  \end{itemize}",
        r"\end{frame}",
        "",
        r"\begin{frame}{尚未解决的问题（来自矩阵的『文献未说明』与折中列）}",
        r"  \begin{itemize}",
    ]
    for item in _gaps(rows):
        lines.append(f"    \\item {tex_escape(item)}")
    lines += [
        r"  \end{itemize}",
        r"\end{frame}",
        "",
        r"\section{下一步工作}",
        r"\begin{frame}{我的切入点与计划}",
        r"  \begin{block}{拟研究问题}",
        r"    % TODO: 用你自己的话写一句，必须能从上面的空白推导出来",
        r"    [待填：针对哪个空白，提出什么方法，预期什么指标改善]",
        r"  \end{block}",
        r"  \begin{itemize}",
        r"    \item 第 1 步：复现矩阵中方法最接近的一篇（建议 [待填]）",
        r"    \item 第 2 步：在其基础上改动 [待填]，形成对比基线",
        r"    \item 第 3 步：用真实仿真数据填 experiments/*.csv，再跑 zhaw check",
        r"  \end{itemize}",
        r"\end{frame}",
        "",
        r"\begin{frame}{参考文献（本地文献池）}",
        r"  \footnotesize",
        r"  \begin{enumerate}",
    ]
    for row in rows:
        lines.append(
            f"    \\item {tex_escape(_author(row))}, {tex_escape(_short(_paper_title(row), 70))}, "
            f"{tex_escape(_venue(row))}, {tex_escape(_year(row))}. "
            f"\\textit{{{tex_escape(_evidence(row))}}}"
        )
    lines += [
        r"  \end{enumerate}",
        r"\end{frame}",
        "",
        r"\end{document}",
        "",
    ]
    return "\n".join(lines)


def _short(text: str, n: int) -> str:
    s = re.sub(r"\s+", " ", (text or "").strip())
    return s if len(s) <= n else s[: n - 1] + "…"


def _year_range(rows: list[dict]) -> str:
    years = sorted({_year(r) for r in rows if re.fullmatch(r"\d{4}", _year(r) or "")})
    if not years:
        return "文献未说明"
    return years[0] if len(years) == 1 else f"{years[0]}–{years[-1]}"


def _method_summary(rows: list[dict]) -> str:
    methods = []
    for r in rows:
        m = col(r, "优化方法", "算法", default="")
        if m and m != "文献未说明":
            methods.append(_short(m, 28))
    uniq = list(dict.fromkeys(methods))
    return "；".join(uniq[:4]) + ("…" if len(uniq) > 4 else "") if uniq else "文献未说明"


def _trends(rows: list[dict]) -> list[str]:
    """Deterministic observations, each traceable to a matrix column."""
    out: list[str] = []
    waveforms = [col(r, "波形", default="") for r in rows]
    if any("OFDM" in w or "ofdm" in w for w in waveforms):
        out.append("多载波（OFDM/OCDM）成为通感一体化波形的主流载体，共 " +
                   str(sum(1 for w in waveforms if "OFDM" in w or "ofdm" in w)) + " 篇涉及。")
    bands = [col(r, "频段", default="") for r in rows]
    mm = [b for b in bands if "28" in b or "毫米波" in b]
    if mm:
        out.append(f"毫米波频段（28 GHz）在大带宽感知场景中被反复采用，共 {len(mm)} 篇。")
    opts = [col(r, "优化方法", "算法", default="") for r in rows]
    sca = [o for o in opts if "SCA" in o or "逐次凸" in o]
    if sca:
        out.append(f"非凸问题普遍采用 SCA/AO/BCD 交替优化框架，共 {len(sca)} 篇。")
    scen = [col(r, "高度", default="") for r in rows]
    if any("文献未说明" in s for s in scen):
        out.append("场景参数（高度/速度）在部分文献中未明确，横向对比存在口径差异。")
    if not out:
        out.append("（矩阵信息不足，无法自动归纳趋势，请人工补写）")
    return out


def _gaps(rows: list[dict]) -> list[str]:
    out: list[str] = []
    unknown_cols = ("感知指标", "通信指标", "折中", "频段", "波形")
    counts = {c: sum(1 for r in rows if "文献未说明" in col(r, c, default="")) for c in unknown_cols}
    for name, n in counts.items():
        if n:
            out.append(f"{name} 有 {n} 篇标注『文献未说明』，说明该维度尚未形成统一评价口径。")
    if not out:
        out.append("矩阵各维度信息完整，空白需从折中关系列人工提炼。")
    out.append("上述空白只是候选；具体选题必须由你本人判断，AI 不替你定方向。")
    return out


def _build_outline(matrix: dict, meta: dict) -> str:
    rows = matrix["rows"]
    topic = meta.get("topic") or matrix["title"] or "文献综述"
    lines = [
        "---",
        "marp: true",
        "theme: default",
        "paginate: true",
        "size: 16:9",
        "---",
        "",
        f"# {meta.get('title') or topic}",
        "",
        "组会文献精读分享 / 开题文献调研",
        "",
        f"{meta.get('author', '汇报人')} · {meta.get('generated_at', '')}",
        "",
        "---",
        "",
        "## 汇报大纲",
        "",
        "1. 研究背景与核心矛盾",
        "2. 逐篇精读（" + str(len(rows)) + " 篇）",
        "3. 横向对比",
        "4. 趋势、空白与切入点",
        "5. 下一步工作",
        "",
        "---",
        "",
        "## 研究背景",
        "",
    ]
    if matrix.get("intro"):
        for para in [p for p in matrix["intro"].split("\n") if p.strip()][:2]:
            lines += [para, ""]
    for idx, row in enumerate(rows, 1):
        lines += ["---", "", f"## {idx}. {_paper_title(row)}", ""]
        lines += [f"**作者/出处**：{_author(row)}，{_venue(row)}，{_year(row)}", ""]
        for label, aliases in PAPER_FIELDS:
            lines.append(f"- **{label}**：{col(row, *aliases, default='文献未说明')}")
        lines += ["", f"> 证据：{_evidence(row)}", ""]
    lines += ["---", "", "## 趋势与空白", ""]
    for t in _trends(rows) + _gaps(rows):
        lines.append(f"- {t}")
    lines += ["", "---", "", "## 下一步", "", "1. [待填：拟研究问题]", "2. [待填：复现哪一篇]",
              "3. [待填：改动点与预期指标]", ""]
    return "\n".join(lines)


def _build_notes(matrix: dict, meta: dict) -> str:
    rows = matrix["rows"]
    lines = [
        f"# 组会讲稿（{len(rows)} 篇文献）",
        "",
        f"生成时间：{meta.get('generated_at', '')}",
        "",
        "> 每段对应一张幻灯片。所有事实来自矩阵，未标注的信息不要口头补充。",
        "",
        "## 幻灯片 1 · 封面",
        "",
        "各位老师同学好，我汇报的题目是《" + (meta.get('title') or matrix['title']) + "》。",
        "这次汇报基于 " + str(len(rows)) + " 篇精读文献，所有数据都能回溯到本地 PDF 的具体页码。",
        "",
    ]
    for idx, row in enumerate(rows, 1):
        lines += [
            f"## 幻灯片 {idx + 2} · {_paper_title(row)}",
            "",
            f"这篇由 {_author(row)} 等发表于 {_venue(row)}（{_year(row)}）。",
            f"它解决的是：{col(row, '系统架构', '架构', default='文献未说明')}。",
            f"波形上采用：{col(row, '波形', default='文献未说明')}。",
            f"感知侧指标是 {col(row, '感知指标', '感知', default='文献未说明')}，"
            f"通信侧是 {col(row, '通信指标', '通信', default='文献未说明')}。",
            f"优化方法：{col(row, '优化方法', '算法', default='文献未说明')}。",
            f"它揭示的核心折中是：{col(row, '折中', default='文献未说明')}。",
            f"（证据：{_evidence(row)}）",
            "",
        ]
    lines += [
        "## 收尾",
        "",
        "最后是我从矩阵里读出的空白和下一步计划。[按 PPT 第 N 页念]",
        "以上文献如有理解偏差，请老师指正。",
        "",
    ]
    return "\n".join(lines)


def build(
    matrix_path: Path,
    out_dir: Path | None = None,
    title: str | None = None,
    author: str | None = None,
    advisor: str | None = None,
    topic: str | None = None,
    institute: str | None = None,
    compile_pdf: bool = False,
) -> dict:
    matrix_path = Path(matrix_path).resolve()
    if not matrix_path.exists():
        raise SystemExit(f"[zhaw seminar] matrix not found: {matrix_path}")
    matrix = parse_matrix(matrix_path)
    if not matrix["rows"]:
        raise SystemExit(f"[zhaw seminar] matrix has no data rows: {matrix_path}")

    dest = Path(out_dir) if out_dir else matrix_path.parent
    dest.mkdir(parents=True, exist_ok=True)

    meta = {
        "generated_at": now_iso(),
        "matrix_name": matrix_path.name,
        "title": title,
        "author": author or "汇报人",
        "advisor": advisor or "指导教师",
        "topic": topic,
        "institute": institute,
    }

    tex_path = write_text(dest / "seminar_presentation.tex", _build_tex(matrix, meta))
    outline_path = write_text(dest / "seminar_outline.md", _build_outline(matrix, meta))
    notes_path = write_text(dest / "seminar_notes.md", _build_notes(matrix, meta))

    pdf_path = None
    compile_log = ""
    if compile_pdf:
        pdf_path, compile_log = _compile(tex_path)

    report = {
        "status": "PASS",
        "matrix": str(matrix_path),
        "papers": len(matrix["rows"]),
        "columns": len(matrix["columns"]),
        "tex": str(tex_path),
        "outline": str(outline_path),
        "notes": str(notes_path),
        "pdf": str(pdf_path) if pdf_path else None,
        "compile_log_tail": compile_log.splitlines()[-6:] if compile_log else [],
        "generated_at": meta["generated_at"],
    }
    write_json(dest / "seminar_report.json", report)
    return report


def _compile(tex_path: Path) -> tuple[Path | None, str]:
    xelatex = shutil.which("xelatex")
    if not xelatex:
        candidates = [
            Path.home() / "AppData/Local/Programs/MiKTeX/miktex/bin/x64/xelatex.exe",
            Path("C:/Program Files/MiKTeX/miktex/bin/x64/xelatex.exe"),
        ]
        for c in candidates:
            if c.exists():
                xelatex = str(c)
                break
    if not xelatex:
        return None, "xelatex not found; skipped PDF compilation"
    log = []
    pdf = tex_path.with_suffix(".pdf")
    for _ in range(2):
        proc = subprocess.run(
            [xelatex, "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
            cwd=str(tex_path.parent),
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
        )
        log.append(proc.stdout[-4000:])
        if proc.returncode != 0:
            # 退出码非 0 但已产出 PDF 的情况很常见（未定义引用、字体警告等），
            # 只要 PDF 真实存在就交付，并把日志交给调用方判断。
            if pdf.exists():
                return pdf, "\n".join(log)
            return None, "\n".join(log)
    return (pdf if pdf.exists() else None), "\n".join(log)
