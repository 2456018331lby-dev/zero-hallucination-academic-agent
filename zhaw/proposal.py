"""`zhaw proposal` — 开题报告（研一刚需，13 阶段里唯一完全空白且最紧迫的一环）.

开题报告 ≠ 学位论文：章节结构、字数配额、进度安排表都不一样，所以这里给出
独立的 LaTeX 脚手架 + 独立的机检，而不是复用论文模板。

产物:
    <dest>/main.tex                  ctexrep 主文件（含封面 + 目录 + 七个章节）
    <dest>/chapters/sec01..sec07.tex 研究背景与意义 / 国内外研究现状 / 研究内容与目标
                                     / 技术路线与研究方法 / 创新点 / 进度安排 / 参考文献
    <dest>/references.bib            参考文献库（GB/T 7714 友好，配合 citation-auditor）
    <dest>/experiments/              数据目录约定（与 `zhaw figures` / Gate 2 对齐）
    <dest>/PROJECT.md                人类可读的检查清单
    <dest>/.gitignore

机检 (``check_proposal``) 覆盖: 七章齐全、每章字数下限、总字数下限、
参考文献条数、创新点条数、进度安排表存在、未替换占位符。
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from ._util import hanzi_count, now_iso, write_json, write_text

# 章节: (文件名, 中文标题, 建议汉字下限, 建议上限)
SECTIONS: list[tuple[str, str, int, int]] = [
    ("sec01_background.tex", "一、研究背景与意义", 1500, 3000),
    ("sec02_related.tex", "二、国内外研究现状", 3000, 6000),
    ("sec03_content.tex", "三、研究内容与目标", 1200, 2500),
    ("sec04_route.tex", "四、技术路线与研究方法", 1500, 3000),
    ("sec05_innovation.tex", "五、拟解决的关键问题与创新点", 800, 2000),
    ("sec06_schedule.tex", "六、进度安排", 200, 800),
]

SECTION_BODY: dict[str, str] = {
    "sec01_background.tex": """本章回答"为什么要做这件事"。写作要求：
\\begin{enumerate}
  \\item 从国家/行业需求切入，引用真实政策或标准文件（须有可核验出处，禁止凭记忆写编号）；
  \\item 收敛到具体的科学问题，而不是停留在"某某很重要"；
  \\item 明确本研究与已有工作的差别。
\\end{enumerate}

% \\TODO{补充国家需求段落，并给出可核验的政策文件出处}
""",
    "sec02_related.tex": """本章回答"别人做到哪一步了"。写作要求：
\\begin{enumerate}
  \\item 按技术路线分组（不是按论文逐篇罗列），每组结尾写"共同局限"；
  \\item 每个数字、每个结论都要能回到本地 PDF 的物理页码；
  \\item 建议先用 \\texttt{zhaw survey} 建文献池、\\texttt{zhaw grounding} 核验矩阵。
\\end{enumerate}

% \\TODO{从 literature_comparison_matrix.md 抽取 3-5 个技术流派}
""",
    "sec03_content.tex": """本章回答"我具体做什么"。写作要求：研究内容 3--4 条，每条可独立验收；
每条都要能对应到后文的一章。

% \\TODO{列出 3--4 条研究内容，每条一句可验收的判据}
""",
    "sec04_route.tex": """本章回答"我怎么做"。写作要求：给出技术路线图（TikZ 或外部 PDF），
说明每一步的输入/输出、用什么工具、失败时的备选方案。

% \\TODO{画技术路线图；说明仿真平台与关键指标定义}
""",
    "sec05_innovation.tex": """本章回答"凭什么算创新"。写作要求：创新点 2--3 条，每条必须写成
"与 X 相比，本文首次/改进了 Y，从而 Z"的句式，禁止"提出了一种新的……"式空话。

% \\TODO{写 2--3 条创新点，每条给出对比基线}
""",
    "sec06_schedule.tex": """本章回答"什么时候做完"。下表按学期/月拆解，交付物一列必须可验证。

\\begin{table}[htbp]
  \\centering
  \\caption{研究进度安排}
  \\label{tab:schedule}
  \\begin{tabular}{@{}llp{6.2cm}@{}}
    \\toprule
    时间 & 阶段 & 交付物（可验收） \\\\
    \\midrule
    第 1 学期 & 文献调研与选题 & 文献池 + 16 维矩阵 + 调研报告 \\\\
    第 2 学期 & 系统建模 & 符号表 + 系统模型章节 + 数学门禁通过 \\\\
    第 3 学期 & 算法设计与仿真 & experiments/*.csv + 收敛曲线 + 对比表 \\\\
    第 4 学期 & 论文撰写 & 三线表 + 章节初稿 + 引文审计通过 \\\\
    第 5 学期 & 送审与答辩 & 匿名版 PDF + 答辩 PPT + 签字页 \\\\
    \\bottomrule
  \\end{tabular}
\\end{table}
""",
}

MAIN_TEX = r"""% !TeX program = xelatex
% 开题报告 —— 由 `zhaw proposal new` 生成
% 编译: xelatex main.tex && xelatex main.tex   （或 `zhaw compile . main.tex`）
\documentclass[12pt,a4paper,openany,UTF8]{ctexrep}

\usepackage{geometry}
\geometry{left=2.8cm,right=2.8cm,top=2.5cm,bottom=2.5cm}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{booktabs,longtable,multirow,array}
\usepackage{tikz}
\usepackage[hidelinks]{hyperref}
% GB/T 7714 参考文献：必须同时具备 gbt7714 宏包与 gbt7714-numeric.bst。
% 只写 \bibliographystyle 而不引入宏包，\cite 会退化成打印 bst 的作者-年标签，
% 渲染成「[Liu et al.(2022)Liu，Cui，…]」并造成严重溢出行。
% MiKTeX: mpm --install=gbt7714    TeX Live: tlmgr install gbt7714
\usepackage[super]{gbt7714}
\usepackage{caption}
\captionsetup{font=small,labelsep=quad}
\graphicspath{{figures/}}

\title{__TITLE__}
\author{__AUTHOR__}
\date{__DATE__}

\begin{document}

\begin{titlepage}
  \centering
  \vspace*{2cm}
  {\zihao{2}\bfseries 硕士学位论文开题报告\par}
  \vspace{1.5cm}
  {\zihao{3}\bfseries __TITLE__\par}
  \vspace{2.5cm}
  {\zihao{4}
  \begin{tabular}{rl}
    学\qquad 院 & __INSTITUTE__ \\[0.6em]
    专\qquad 业 & __MAJOR__ \\[0.6em]
    研究方向 & __TOPIC__ \\[0.6em]
    研\ 究\ 生 & __AUTHOR__ \\[0.6em]
    学\qquad 号 & __STUDENT_ID__ \\[0.6em]
    指导教师 & __ADVISOR__ \\
  \end{tabular}\par}
  \vfill
  {\zihao{4} __DATE__\par}
\end{titlepage}

\pagenumbering{Roman}
\tableofcontents
\clearpage
\pagenumbering{arabic}

\chapter*{一、研究背景与意义}
\addcontentsline{toc}{chapter}{一、研究背景与意义}
\input{chapters/sec01_background.tex}

\chapter*{二、国内外研究现状}
\addcontentsline{toc}{chapter}{二、国内外研究现状}
\input{chapters/sec02_related.tex}

\chapter*{三、研究内容与目标}
\addcontentsline{toc}{chapter}{三、研究内容与目标}
\input{chapters/sec03_content.tex}

\chapter*{四、技术路线与研究方法}
\addcontentsline{toc}{chapter}{四、技术路线与研究方法}
\input{chapters/sec04_route.tex}

\chapter*{五、拟解决的关键问题与创新点}
\addcontentsline{toc}{chapter}{五、拟解决的关键问题与创新点}
\input{chapters/sec05_innovation.tex}

\chapter*{六、进度安排}
\addcontentsline{toc}{chapter}{六、进度安排}
\input{chapters/sec06_schedule.tex}

\clearpage
\bibliographystyle{gbt7714-numeric}
\bibliography{references}

\end{document}
"""

GITIGNORE = """*.aux
*.log
*.out
*.toc
*.bbl
*.blg
*.synctex.gz
*.fls
*.fdb_latexmk
__pycache__/
"""

PROJECT_MD = """# 开题报告工程：__TITLE__

由 `zhaw proposal new` 生成（__DATE__）。

## 七章结构（机检项）

| 章节 | 文件 | 建议汉字数 |
|---|---|---|
""" + "\n".join(f"| {title} | `chapters/{name}` | {lo}–{hi} |" for name, title, lo, hi in SECTIONS) + """

## 日常命令

```bash
zhaw proposal check .              # 章节完整性 / 字数 / 参考文献 / 创新点 / 进度表
zhaw bib . --apply                 # 用 Crossref 重建 references.bib（禁止凭记忆写 author）
zhaw gate1 . --offline             # 引文逐字段审计
zhaw compile . main.tex --strict   # 严格编译
zhaw docx . --output 开题报告.docx   # 导师要 Word 批注
```

## 红线

- 参考文献 author 字段**禁止凭记忆手写**，一律 `zhaw bib --apply` 回填。
- 每个量化断言必须有出处（政策文件 / 本地 PDF 页码）。
- 创新点必须写成"与 X 相比，本文……"，不接受"提出了一种新的"。
"""


def _render(main_tex: str, meta: dict) -> str:
    values = {
        "TITLE": meta.get("title") or "面向[待填方向]的[待填问题]研究",
        "AUTHOR": meta.get("author") or "[待填姓名]",
        "INSTITUTE": meta.get("institute") or "[待填学院]",
        "MAJOR": meta.get("major") or "[待填专业]",
        "TOPIC": meta.get("topic") or "[待填研究方向]",
        "STUDENT_ID": meta.get("student_id") or "[待填学号]",
        "ADVISOR": meta.get("advisor") or "[待填导师]",
        "DATE": meta.get("date") or now_iso()[:10],
    }
    for key, value in values.items():
        main_tex = main_tex.replace(f"__{key}__", value)
    return main_tex


def new_proposal(dest: Path, meta: dict | None = None, force: bool = False) -> dict:
    dest = Path(dest).resolve()
    meta = dict(meta or {})
    if dest.exists() and any(dest.iterdir()) and not force:
        raise SystemExit(f"[zhaw proposal] destination not empty: {dest} (use --force to overwrite)")
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "chapters").mkdir(exist_ok=True)
    (dest / "figures").mkdir(exist_ok=True)
    (dest / "experiments").mkdir(exist_ok=True)

    write_text(dest / "main.tex", _render(MAIN_TEX, meta))
    for name, title, _lo, _hi in SECTIONS:
        body = SECTION_BODY[name]
        write_text(dest / "chapters" / name, f"% {title}\n\n{body}\n")
    write_text(dest / "chapters" / "sec07_references.tex", "% 参考文献由 references.bib + \\bibliography 生成\n")
    write_text(dest / "references.bib", "% 由 `zhaw bib . --apply` 从 DOI 回填，禁止凭记忆手写 author\n")
    write_text(dest / "experiments" / "README.md", "# 实验数据\n\n放 `*.csv`（首行列名），`zhaw figures .` 自动出三线表与曲线。\n")
    write_text(dest / ".gitignore", GITIGNORE)
    write_text(dest / "PROJECT.md", _render(PROJECT_MD, meta))

    report = {
        "generated_at": now_iso(),
        "dest": str(dest),
        "sections": [name for name, *_ in SECTIONS],
        "title": meta.get("title"),
    }
    write_json(dest / "proposal_report.json", report)
    return report


_TODO_RE = re.compile(r"\\TODO\{|待填|TBD|TODO", re.IGNORECASE)


def check_proposal(project: Path, min_total: int = 9000, min_refs: int = 20) -> dict:
    project = Path(project).resolve()
    chap_dir = project / "chapters"
    issues: list[str] = []
    sections: list[dict] = []
    total = 0

    for name, title, lo, hi in SECTIONS:
        path = chap_dir / name
        if not path.exists():
            issues.append(f"缺少章节文件 chapters/{name}（{title}）")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        chars = hanzi_count(text)
        total += chars
        todos = len(_TODO_RE.findall(text))
        state = "PASS"
        if chars < lo:
            state = "SHORT"
            issues.append(f"{title}: {chars} 汉字 < 下限 {lo}")
        elif chars > hi:
            state = "LONG"
            issues.append(f"{title}: {chars} 汉字 > 上限 {hi}（建议拆分）")
        if todos:
            issues.append(f"{title}: {todos} 处占位符未替换")
            state = "TODO" if state == "PASS" else state
        sections.append({"file": name, "title": title, "hanzi": chars, "min": lo, "max": hi,
                         "todos": todos, "state": state})

    if total < min_total:
        issues.append(f"总汉字数 {total} < 下限 {min_total}（开题报告通常 1--2 万字）")

    bib = project / "references.bib"
    refs = 0
    if bib.exists():
        refs = len(re.findall(r"^@\w+\{", bib.read_text(encoding="utf-8", errors="replace"), re.MULTILINE))
    if refs < min_refs:
        issues.append(f"参考文献 {refs} 条 < 下限 {min_refs}")

    innovation = chap_dir / "sec05_innovation.tex"
    innovation_count = 0
    if innovation.exists():
        text = innovation.read_text(encoding="utf-8", errors="replace")
        innovation_count = len(re.findall(r"\\item", text))
        if innovation_count < 2:
            issues.append(f"创新点只有 {innovation_count} 条，至少 2 条")
        if "提出了一种新的" in text:
            issues.append("创新点使用了空话句式「提出了一种新的」，应改成「与 X 相比，本文……」")

    schedule = chap_dir / "sec06_schedule.tex"
    if not schedule.exists() or "tabular" not in schedule.read_text(encoding="utf-8", errors="replace"):
        issues.append("进度安排章节缺少表格（tabular）")

    # ---- 交付链路硬检查（冷启动实测暴露的三类漏报）----
    # 1) 封面字段仍是模板默认值/占位符 —— 开题报告最容易被跳过的一步。
    # 2) \cite 的 key 在 references.bib 里不存在 —— 编译后是「?」不是报错。
    # 3) \includegraphics 指向的图件不存在 —— 开题要求技术路线图，空 figures/ 也能过。
    tex_sources: list[tuple[str, str]] = []
    main_tex = project / "main.tex"
    if main_tex.exists():
        tex_sources.append(("main.tex", main_tex.read_text(encoding="utf-8", errors="replace")))
    if chap_dir.exists():
        for path in sorted(chap_dir.glob("*.tex")):
            tex_sources.append((f"chapters/{path.name}", path.read_text(encoding="utf-8", errors="replace")))

    if main_tex.exists():
        mt = tex_sources[0][1]
        for label, pattern in (
            ("标题", r"\\title\{([^}]*)\}"),
            ("作者", r"\\author\{([^}]*)\}"),
        ):
            m = re.search(pattern, mt)
            value = (m.group(1) if m else "").strip()
            if not value or "待填" in value:
                issues.append(f"封面{label}仍是占位符（{value or '空'}）")
        for stale in ("北京大学", "清华大学", "PEKING UNIVERSITY"):
            if stale in mt:
                issues.append(f"封面/页眉残留模板校名「{stale}」")

    if bib.exists():
        bib_keys = set(re.findall(r"^@\w+\{([^,]+),", bib.read_text(encoding="utf-8", errors="replace"), re.MULTILINE))
        cite_keys: list[str] = []
        for _, text in tex_sources:
            for group in re.findall(r"\\cite[a-zA-Z]*\{([^}]*)\}", text):
                cite_keys.extend(k.strip() for k in group.split(",") if k.strip())
        missing = sorted({k for k in cite_keys if k not in bib_keys})
        if missing:
            issues.append("引用了参考文献里不存在的 key：" + ", ".join(missing[:8]))
        if bib_keys and not cite_keys:
            issues.append(f"references.bib 有 {len(bib_keys)} 条，但正文一次都没 \\cite")

    for where, text in tex_sources:
        for graphic in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]*)\}", text):
            rel = graphic.strip()
            if not rel:
                continue
            if (project / rel).exists() or (project / "figures" / rel).exists():
                continue
            issues.append(f"{where}: \\includegraphics 指向的图件不存在：{rel}")

    status = "PASS" if not issues else "FAIL"
    return {
        "status": status,
        "project": str(project),
        "total_hanzi": total,
        "min_total": min_total,
        "references": refs,
        "min_refs": min_refs,
        "innovation_points": innovation_count,
        "sections": sections,
        "issues": issues,
    }


def render_report(result: dict) -> str:
    lines = [
        "# 开题报告机检报告",
        "",
        f"- 工程: `{result['project']}`",
        f"- 结论: **{result['status']}**",
        f"- 正文汉字: {result['total_hanzi']} / 下限 {result['min_total']}",
        f"- 参考文献: {result['references']} / 下限 {result['min_refs']}",
        f"- 创新点: {result['innovation_points']} 条",
        "",
        "## 章节明细",
        "",
        "| 章节 | 文件 | 汉字 | 区间 | 占位符 | 状态 |",
        "|---|---|---|---|---|---|",
    ]
    for sec in result["sections"]:
        lines.append(
            f"| {sec['title']} | `{sec['file']}` | {sec['hanzi']} | {sec['min']}–{sec['max']} | "
            f"{sec['todos']} | {sec['state']} |"
        )
    lines += ["", "## 待处理", ""]
    lines += [f"- {issue}" for issue in result["issues"]] or ["- 无"]
    return "\n".join(lines) + "\n"


def copy_figures(src: Path, dest: Path) -> None:
    src, dest = Path(src), Path(dest)
    if src.is_dir():
        shutil.copytree(src, dest, dirs_exist_ok=True)
