"""`zhaw defense` — 答辩 PPT + 逐字讲稿 + 预答辩问题库.

答辩与组会汇报的目标不同：组会讲"我读了什么"，答辩讲"我做了什么、凭什么算贡献"。
所以这里不复用 seminar.py，而是从**学位论文工程本身**抽结构：

  章节标题   ← chapters/*.tex 的 \\chapter / \\section
  创新点     ← 结论章的 \\item 或"创新"小节
  实验证据   ← figures/ 下的 PDF + experiments/*.csv 列名
  讲稿       ← 每页一段（按页标题 + 证据提示生成，人再改写成口语）

产物（默认写到 <project>/defense/）:
    defense_presentation.tex   ctexbeamer 16:9，20 页正文 + 备份页
    defense_notes.md           逐页讲稿（Markdown，可直接念/改）
    defense_qa.md              预答辩问题库（按章节+创新点+实验设计出题）
    defense_report.json        结构摘要，便于二次加工
"""
from __future__ import annotations

import re
from pathlib import Path

from ._util import chapter_files, hanzi_count, now_iso, strip_latex, write_json, write_text

DEFAULT_PAGES = 20


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _title_of(project: Path) -> str:
    main = _read(project / "main.tex")
    match = re.search(r"\\title(?:\[[^\]]*\])?\{(.+?)\}", main, re.DOTALL)
    if match:
        return strip_latex(match.group(1)).strip() or "学位论文答辩"
    return project.name


def _author_of(project: Path) -> str:
    main = _read(project / "main.tex")
    match = re.search(r"\\author(?:\[[^\]]*\])?\{(.+?)\}", main, re.DOTALL)
    return strip_latex(match.group(1)).strip() if match else "[待填姓名]"


def _sections(project: Path) -> list[dict]:
    """按文件顺序抽出每章的标题与其下 \\section 标题。"""
    out = []
    for path in chapter_files(project):
        text = _read(path)
        if not text.strip():
            continue
        chapter = re.search(r"\\chapter\*?\{(.+?)\}", text)
        title = strip_latex(chapter.group(1)).strip() if chapter else path.stem
        secs = [strip_latex(s).strip() for s in re.findall(r"\\section\*?\{(.+?)\}", text)]
        out.append({
            "file": path.name,
            "title": title,
            "sections": [s for s in secs if s],
            "hanzi": hanzi_count(text),
            "todos": len(re.findall(r"\\TODO\{", text)),
        })
    return out


def _innovations(chapters: list[dict], project: Path) -> list[str]:
    """优先取结论/创新章节里的 \\item，其次取任意章的 \\item。"""
    candidates = [c for c in chapters if any(k in c["title"] for k in ("结论", "创新", "总结"))]
    pool = candidates or chapters
    found: list[str] = []
    for chap in pool:
        text = _read(project / "chapters" / chap["file"]) if (project / "chapters" / chap["file"]).exists() else ""
        if not text:
            for path in chapter_files(project):
                if path.name == chap["file"]:
                    text = _read(path)
                    break
        for item in re.findall(r"\\item\s+(.+?)(?=\\item|\\end\{)", text, re.DOTALL):
            clean = strip_latex(item).strip().replace("\n", " ")
            clean = re.sub(r"\s+", " ", clean)
            if 6 <= len(clean) <= 160 and not clean.startswith("待填"):
                found.append(clean)
    return found[:5]


def _figures(project: Path) -> list[str]:
    fig_dir = project / "figures"
    if not fig_dir.is_dir():
        return []
    return [p.stem for p in sorted(fig_dir.glob("*.pdf"))]


def _experiments(project: Path) -> list[dict]:
    out = []
    exp = project / "experiments"
    if not exp.is_dir():
        return out
    for csv_path in sorted(exp.glob("*.csv")):
        header = _read(csv_path).splitlines()
        cols = [c.strip() for c in header[0].split(",")] if header else []
        out.append({"file": csv_path.name, "columns": cols, "rows": max(0, len(header) - 1)})
    return out


def _tex_escape(text: str) -> str:
    text = text.replace("\\", "").replace("&", r"\&").replace("%", r"\%")
    text = text.replace("#", r"\#").replace("_", r"\_")
    text = text.replace("$", "").replace("{", "").replace("}", "")
    # 方括号会截断 \title[...]/\author[...] 的可选参数，必须包起来
    return text.replace("[", "{[}").replace("]", "{]}")


def build(
    project: Path,
    out_dir: Path | None = None,
    title: str | None = None,
    author: str | None = None,
    advisor: str | None = None,
    institute: str | None = None,
    compile: bool = False,
) -> dict:
    project = Path(project).resolve()
    out = Path(out_dir) if out_dir else project / "defense"
    out.mkdir(parents=True, exist_ok=True)

    chapters = _sections(project)
    innovations = _innovations(chapters, project)
    figs = _figures(project)
    exps = _experiments(project)
    thesis_title = title or _title_of(project)
    thesis_author = author or _author_of(project)

    # ---------------- beamer ----------------
    frames: list[str] = []

    def frame(ftitle: str, body: str, note: str = "") -> None:
        note_block = f"\n  \\note{{{_tex_escape(note)}}}" if note else ""
        frames.append(
            f"\\begin{{frame}}{{{_tex_escape(ftitle)}}}\n{body}\n{note_block}\\end{{frame}}\n"
        )

    frame("研究背景与意义", r"""\begin{itemize}
  \item 需求牵引：[待填国家/行业需求，须有可核验出处]
  \item 科学问题：[待填一句话科学问题]
  \item 本文定位：[待填本文与该问题的关系]
\end{itemize}""", "开场 40 秒内说清三件事：为什么做、问题是什么、你做了什么。")

    if chapters:
        overview = "\\begin{itemize}\n" + "\n".join(
            f"  \\item {_tex_escape(c['title'])}" for c in chapters[:6]
        ) + "\n\\end{itemize}"
        frame("论文结构", overview, "用一张图说明章节之间的逻辑关系，不要逐章念标题。")

    related = next((c for c in chapters if any(k in c["title"] for k in ("绪论", "引言", "背景", "综述"))), None)
    if related and related["sections"]:
        body = "\\begin{itemize}\n" + "\n".join(
            f"  \\item {_tex_escape(s)}" for s in related["sections"][:6]
        ) + "\n\\end{itemize}"
        frame("国内外研究现状", body, "按技术流派讲，每组结尾点出共同局限，为你的工作铺路。")
    else:
        frame("国内外研究现状", r"""\begin{itemize}
  \item 流派 A：[待填] —— 共同局限：[待填]
  \item 流派 B：[待填] —— 共同局限：[待填]
\end{itemize}""")

    frame("现有工作的局限", r"""\begin{itemize}
  \item 局限 1：[待填，必须能被你的实验直接回应]
  \item 局限 2：[待填]
  \item $\Rightarrow$ 本文的三个切入点
\end{itemize}""", "这一页是全场最关键的转折：把别人的局限精确翻译成你的贡献。")

    method_chapters = [c for c in chapters if c["sections"] and c is not related][:3]
    for chap in method_chapters:
        body = "\\begin{itemize}\n" + "\n".join(
            f"  \\item {_tex_escape(s)}" for s in chap["sections"][:5]
        ) + "\n\\end{itemize}"
        frame(chap["title"], body, f"{chap['title']}：只讲主线，公式留在备份页。")

    if figs:
        fig = figs[0]
        frame("实验结果（一）", (
            "\\begin{figure}\n  \\centering\n"
            f"  \\includegraphics[width=0.8\\linewidth]{{../figures/{fig}.pdf}}\n"
            "\\end{figure}"
        ), "指着曲线讲三句话：趋势是什么、拐点在哪、和基线差多少。")

    if exps:
        exp = exps[0]
        cols = exp["columns"][:6]
        frame("实验结果（二）", (
            "\\begin{table}\n  \\centering\n  \\small\n"
            "  \\begin{tabular}{" + "l" + "c" * (len(cols) - 1) + "}\n    \\toprule\n    "
            + " & ".join(_tex_escape(c) for c in cols) + " \\\\\n    \\midrule\n    "
            + " & ".join("..." for _ in cols) + " \\\\\n    \\bottomrule\n"
            "  \\end{tabular}\n\\end{table}"
        ), f"数据源：experiments/{exp['file']}（{exp['rows']} 行），表格由 `zhaw figures` 生成。")

    if innovations:
        body = "\\begin{enumerate}\n" + "\n".join(
            f"  \\item {_tex_escape(x)}" for x in innovations[:4]
        ) + "\n\\end{enumerate}"
    else:
        body = r"""\begin{enumerate}
  \item 与 [基线 X] 相比，本文首次 [做了什么]，从而 [带来什么]
  \item 与 [基线 Y] 相比，本文改进了 [什么]，从而 [带来什么]
\end{enumerate}"""
    frame("主要创新点", body, "创新点必须念成「与 X 相比，本文……」，禁止「提出了一种新的」。")

    frame("结论与展望", r"""\begin{itemize}
  \item 结论：[待填，与创新点一一对应]
  \item 不足：[待填，诚实列出 1--2 条]
  \item 展望：[待填，给出可执行的下一步]
\end{itemize}""", "不足要主动讲，评委最反感的是把不足藏起来。")

    frame("致谢", r"""\centering
感谢导师的指导、课题组同学的支持，请各位老师批评指正。""", "致谢 15 秒内结束。")

    # 备份页
    backup = "\\appendix\n"
    backup += "\\begin{frame}{备份：关键公式}\n\\begin{itemize}\n  \\item [待填公式 1]\n  \\item [待填公式 2]\n\\end{itemize}\n\\end{frame}\n"
    if figs[1:]:
        for extra in figs[1:3]:
            backup += (
                "\\begin{frame}{备份：" + _tex_escape(extra) + "}\n"
                "\\begin{figure}\n  \\centering\n"
                f"  \\includegraphics[width=0.75\\linewidth]{{../figures/{extra}.pdf}}\n"
                "\\end{figure}\n\\end{frame}\n"
            )

    tex = f"""% !TeX program = xelatex
% 答辩 PPT —— 由 `zhaw defense` 生成
% 编译: cd {out.name} && xelatex defense_presentation.tex （两遍）
\\documentclass[aspectratio=169,11pt]{{ctexbeamer}}
\\usetheme{{Madrid}}
\\usecolortheme{{beaver}}
\\setbeamertemplate{{navigation symbols}}{{}}
\\setbeamertemplate{{caption}}{{\\small}}
\\usepackage{{booktabs}}
\\usepackage{{graphicx}}
\\usepackage{{amsmath,amssymb}}
\\graphicspath{{{{../figures/}}{{figures/}}}}

\\title[{_tex_escape(thesis_title[:22])}]{{{_tex_escape(thesis_title)}}}
\\author[{_tex_escape(thesis_author)}]{{{_tex_escape(thesis_author)}}}
\\institute{{{_tex_escape(institute or '[待填学院]')}}}
\\date{{{now_iso()[:10]}}}

\\begin{{document}}

\\begin{{frame}}
  \\titlepage
\\end{{frame}}

\\begin{{frame}}{{汇报大纲}}
  \\tableofcontents
\\end{{frame}}

""" + "\n".join(frames) + "\n" + backup + "\n\\end{document}\n"

    write_text(out / "defense_presentation.tex", tex)

    # ---------------- 讲稿 ----------------
    notes = [f"# 答辩讲稿：{thesis_title}", "", f"- 汇报人：{thesis_author}", f"- 生成时间：{now_iso()}", "",
             "> 每页控制在 40--70 秒；讲稿是脚手架，务必改写成你自己的口语。", ""]
    notes.append("## 第 1 页 封面\n\n各位老师上午好，我是" + thesis_author + "，导师是[待填]。我的论文题目是《" + thesis_title + "》。下面我用 15 分钟汇报我的工作。\n")
    notes.append("## 第 2 页 论文结构\n\n论文共 " + str(len(chapters)) + " 章，逻辑是：[待填一句话主线]。\n")
    for idx, chap in enumerate(chapters, start=3):
        notes.append(f"## 第 {idx} 页 {chap['title']}\n\n本章回答：[待填]。要点："
                     + ("、".join(chap["sections"][:4]) if chap["sections"] else "[待填]") + "。\n")
    if innovations:
        notes.append("## 创新点\n\n" + "\n".join(f"{i}. {x}" for i, x in enumerate(innovations, 1)) + "\n")
    notes.append("## 结尾\n\n以上就是我的汇报，请各位老师批评指正。\n")
    write_text(out / "defense_notes.md", "\n".join(notes))

    # ---------------- 预答辩问题库 ----------------
    qa = [f"# 预答辩问题库：{thesis_title}", "", f"生成时间：{now_iso()}", "",
          "> 每题给出「评委想听什么」，答案必须是你自己的，不要照抄。", ""]
    qa += ["## 一、选题与动机", "",
           "1. **这个课题的必要性是什么？** 想听：真实需求 + 已有工作做不到的具体点。",
           "2. **你的工作与最接近的那篇论文差在哪？** 想听：一句话说清差别，不能含糊。",
           "3. **如果换一个应用场景，你的方法还成立吗？** 想听：假设边界在哪里。", ""]
    qa += ["## 二、方法与理论", "",
           "4. **系统模型的关键假设是否合理？放宽会怎样？** 想听：你知道假设的代价。",
           "5. **收敛性/最优性证明的关键步骤是什么？** 想听：能指着备份页讲。",
           "6. **复杂度是多少？和基线比代价增加了多少？** 想听：有具体数字。", ""]
    qa += ["## 三、实验与数据", "",
           "7. **仿真参数怎么定的？换一组参数结论会翻吗？** 想听：敏感性分析。",
           "8. **基线是怎么实现的？公平吗？** 想听：基线不是你自己调弱的。",
           "9. **提升的百分比是在什么条件下测的？** 想听：能回到 CSV 的哪一行。", ""]
    qa += ["## 四、创新点与贡献", ""]
    for i, item in enumerate(innovations, 1):
        qa.append(f"{9 + i}. **「{item[:50]}」的创新性体现在哪？** 想听：与哪篇工作对比、差别多大。")
    qa += ["", "## 五、不足与展望", "",
           "10. **你这篇最大的不足是什么？** 想听：诚实 + 有改进思路。",
           "11. **下一步打算怎么做？** 想听：具体到可执行动作。", ""]
    qa += ["## 六、论文规范", "",
           "12. **参考文献都是你读过的吗？** 想听：能说出其中 3 篇的核心结论。",
           "13. **图表都是自己画的吗？数据可复现吗？** 想听：`zhaw figures` 能重跑出来。", ""]
    write_text(out / "defense_qa.md", "\n".join(qa))

    report = {
        "generated_at": now_iso(),
        "project": str(project),
        "title": thesis_title,
        "author": thesis_author,
        "chapters": chapters,
        "innovations": innovations,
        "figures": figs,
        "experiments": exps,
        "outputs": {
            "tex": str(out / "defense_presentation.tex"),
            "notes": str(out / "defense_notes.md"),
            "qa": str(out / "defense_qa.md"),
        },
    }

    if compile:
        # 复用 seminar 的 xelatex 探测（含 MiKTeX 兜底路径），避免两处重复且行为不一致
        from .seminar import _compile

        pdf, log = _compile(out / "defense_presentation.tex")
        report["outputs"]["pdf"] = str(pdf) if pdf else None
        report["compile_log_tail"] = log.splitlines()[-6:] if log else []
        if not pdf:
            report["compile_error"] = "xelatex not found or compilation failed"

    write_json(out / "defense_report.json", report)
    return report
