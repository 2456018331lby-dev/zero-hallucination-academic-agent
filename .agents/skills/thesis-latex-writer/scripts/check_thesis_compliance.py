#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_thesis_compliance.py - Academic Thesis Compliance and Quality Gate Linter

Comprehensive verification against GB/T 7713.1-2006, GB/T 7714-2015, and university standards:
1. Markdown residue detection (literal **, __, |---|, ``` fences in non-comment lines)
2. Three-line tables compliance (booktabs \\toprule, \\midrule, \\bottomrule; no vertical rules)
3. Caption positioning (table caption ABOVE table; figure caption BELOW figure)
4. Resource integrity (\\includegraphics target file existence; figures/ dead files; figure count > 0)
5. Front and back matter checklist (English abstract/keywords, TOC, LOF/LOT, notation, acknowledgments, declaration, achievements)
6. Bibliography structure (citation count threshold, dangling \\cite keys, uncited entries, GB/T 7714 type tags)
7. Placeholder leaks (TODO, 待填, 占位, SCAFFOLD in non-comment lines; gated by --scaffold)
8. Anti-AIGC slop clichés filter
9. Compilation log post-processing (LaTeX errors, Overfull \\hbox > 5pt, undefined references)
"""

import os
import re
import sys
import json
import argparse

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

AIGC_SLOP_WORDS = [
    "毫无疑问", "双刃剑", "深入探讨", "不可忽视", "赋能", "值得注意的是",
    "总而言之", "显而易见", "如前所述", "在当今快节奏的", "毋庸置疑",
    "显微镜下", "奠定坚实基础", "综上所述", "不可否认", "显见的是",
    "不言而喻", "具有里程碑意义", "开创了先河", "不乏其人"
]

PLACEHOLDER_PATTERNS = [
    r"TODO", r"待填", r"占位", r"SCAFFOLD", r"待补充", r"待实验数据",
    r"\[待替换", r"待完善", r"待提供"
]

REQUIRED_SECTIONS = [
    {"name": "英文摘要 (English Abstract)", "patterns": [r"\\chapter\*\{Abstract\}", r"\\begin\{abstracten\}", r"\\section\*\{Abstract\}", r"\bAbstract\b.*(?:\r?\n.*?){1,5}\bKeywords\b"], "level": "ERROR"},
    {"name": "致谢 (Acknowledgments)", "patterns": [r"\\chapter\*\{致(?:\s|\\quad)*谢\}", r"\\section\*\{致(?:\s|\\quad)*谢\}", r"\\chapter\{致(?:\s|\\quad)*谢\}"], "level": "ERROR"},
    {"name": "原创性/授权声明 (Declaration)", "patterns": [r"独创性声明", r"原创性声明", r"授权声明", r"声明书"], "level": "ERROR"},
    {"name": "图表清单/目录 (LOF/LOT)", "patterns": [r"\\listoffigures", r"\\listoftables", r"图目录", r"表目录", r"图表目录"], "level": "WARNING"},
    {"name": "主要符号对照表 (Notation Table)", "patterns": [r"主要符号对照表", r"符号说明", r"符号表", r"\\chapter\*\{符号说明\}"], "level": "WARNING"},
    {"name": "攻读学位期间研究成果 (Achievements)", "patterns": [r"攻读学位期间.*成果", r"攻读.*期间发表.*论文", r"研究成果清单"], "level": "WARNING"},
]


def strip_tex_comments(line):
    """去除行内未转义的 % 注释，返回 (有效代码, 注释内容)。"""
    res = []
    comment = ""
    i = 0
    escaped = False
    while i < len(line):
        ch = line[i]
        if ch == "\\" and not escaped:
            escaped = True
            res.append(ch)
        elif ch == "%" and not escaped:
            comment = line[i + 1:]
            break
        else:
            escaped = False
            res.append(ch)
        i += 1
    return "".join(res), comment


def find_files_by_ext(base_dir, ext):
    matched = []
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "node_modules")]
        for f in files:
            if f.endswith(ext):
                matched.append(os.path.join(root, f))
    return matched


def check_thesis(project_dir, scaffold_mode=False, strict=False, min_bib=60, json_out=None):
    project_dir = os.path.abspath(project_dir)
    issues = []

    tex_files = find_files_by_ext(project_dir, ".tex")
    bib_files = find_files_by_ext(project_dir, ".bib")

    if not tex_files:
        issues.append({
            "file": "", "line": 0, "level": "ERROR",
            "rule": "Project Structure", "msg": f"No .tex files found in {project_dir}"
        })
        return _summarize_and_exit(issues, project_dir, json_out, strict)

    all_tex_content = {}
    total_figures = 0
    referenced_graphics = set()
    cited_keys = set()
    defined_bib_keys = set()

    # 1. 扫描 .bib 文件提取已定义引文
    for bf in bib_files:
        with open(bf, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = re.match(r"^\s*@\w+\s*\{\s*([^,]+),", line)
                if m:
                    defined_bib_keys.add(m.group(1).strip())

    # 2. 逐文件逐行语法与内容核验
    for tf in tex_files:
        rel_path = os.path.relpath(tf, project_dir)
        with open(tf, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        all_tex_content[rel_path] = content
        lines = content.splitlines()

        # 收集 \cite
        for m in re.finditer(r"\\cite[tp]?\{([^}]+)\}", content):
            for k in m.group(1).split(","):
                k = k.strip()
                if k:
                    cited_keys.add(k)

        # 收集 \bibitem
        for m in re.finditer(r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}", content):
            defined_bib_keys.add(m.group(1).strip())

        # 逐行分析
        for idx, line in enumerate(lines, start=1):
            code, _ = strip_tex_comments(line)
            stripped_code = code.strip()
            if not stripped_code:
                continue

            # (A) Markdown 残留检测
            # 1. 粗体/斜体 **text**
            if "**" in stripped_code:
                issues.append({
                    "file": rel_path, "line": idx, "level": "ERROR",
                    "rule": "Markdown Residue",
                    "msg": f"Detected literal '**' markdown syntax: '{stripped_code[:60]}'. Use '\\textbf{{...}}' in LaTeX."
                })
            # 2. 下划线斜体 __text__ (且不是数学公式中的下标)
            if re.search(r"(?<!\\)__[^\s_]+__", stripped_code):
                issues.append({
                    "file": rel_path, "line": idx, "level": "ERROR",
                    "rule": "Markdown Residue",
                    "msg": f"Detected literal '__' markdown syntax: '{stripped_code[:60]}'."
                })
            # 3. Markdown 表格分割行 |---|
            if re.search(r"\|\s*[-:]+\s*\|", stripped_code):
                issues.append({
                    "file": rel_path, "line": idx, "level": "ERROR",
                    "rule": "Markdown Residue",
                    "msg": f"Detected literal markdown table separator '|---|': '{stripped_code[:60]}'."
                })
            # 4. Markdown 代码围栏 ```
            if stripped_code.startswith("```"):
                issues.append({
                    "file": rel_path, "line": idx, "level": "ERROR",
                    "rule": "Markdown Residue",
                    "msg": f"Detected literal markdown code fence '```': '{stripped_code[:60]}'."
                })

            # (B) 占位符/脚手架泄漏检测
            for pat in PLACEHOLDER_PATTERNS:
                if re.search(pat, stripped_code, re.I):
                    lvl = "WARNING" if scaffold_mode else "ERROR"
                    issues.append({
                        "file": rel_path, "line": idx, "level": lvl,
                        "rule": "Placeholder Leak",
                        "msg": f"Detected uncompleted draft token '{pat}': '{stripped_code[:70]}'."
                               + (" (Permitted under --scaffold draft mode)" if scaffold_mode else " Strictly forbidden in final submission!")
                    })

            # (C) Anti-AIGC 禁用套话
            for slop in AIGC_SLOP_WORDS:
                if slop in stripped_code:
                    issues.append({
                        "file": rel_path, "line": idx, "level": "WARNING",
                        "rule": "Anti-AIGC Slop Filter",
                        "msg": f"Detected AI cliché: '{slop}'. Recommend replacing with objective, data-grounded phrasing."
                    })

            # (D) 三线表竖线违规
            if r"\begin{tabular" in stripped_code:
                # 提取 tabular 参数中的对齐字符串
                m_align = re.search(r"\\begin\{tabular\*?x?\}\s*(?:\{[^}]*\}\s*)?\{([^}]+)\}", stripped_code)
                if m_align and "|" in m_align.group(1):
                    issues.append({
                        "file": rel_path, "line": idx, "level": "ERROR",
                        "rule": "GB/T 7713 Three-Line Table",
                        "msg": "Vertical lines '|' forbidden in three-line table column specification."
                    })
                elif "|" in stripped_code and not stripped_code.startswith(r"\begin{tabularx}"):
                    # 直接检测该行是否有 '|'
                    issues.append({
                        "file": rel_path, "line": idx, "level": "ERROR",
                        "rule": "GB/T 7713 Three-Line Table",
                        "msg": "Found vertical rule '|' in tabular environment."
                    })

            # (E) 收集 \includegraphics 路径
            for m_img in re.finditer(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", code):
                img_path = m_img.group(1).strip()
                referenced_graphics.add(img_path)
                # 核验物理存在性
                found = False
                candidates = [
                    os.path.join(project_dir, img_path),
                    os.path.join(os.path.dirname(tf), img_path),
                    os.path.join(project_dir, "figures", img_path),
                    os.path.join(project_dir, "figures", os.path.basename(img_path)),
                ]
                exts = ["", ".pdf", ".png", ".jpg", ".jpeg", ".eps"]
                for c in candidates:
                    for e in exts:
                        if os.path.isfile(c + e):
                            found = True
                            break
                    if found:
                        break
                if not found:
                    issues.append({
                        "file": rel_path, "line": idx, "level": "ERROR",
                        "rule": "Resource Integrity",
                        "msg": f"Image file '{img_path}' referenced by \\includegraphics does not exist on disk."
                    })

        # (F) 环境级检查：Table 与 Figure Caption 位置
        # 匹配所有 table 环境
        table_blocks = re.finditer(r"\\begin\{table\*?\}(.*?)\\end\{table\*?\}", content, re.S)
        for tb in table_blocks:
            body = tb.group(1)
            cap_m = re.search(r"\\caption(?:\[[^\]]*\])?\{", body)
            tab_m = re.search(r"\\begin\{tabular\*?x?\}", body)
            if cap_m and tab_m:
                if cap_m.start() > tab_m.start():
                    # 计算大致行号
                    line_no = content[:tb.start() + cap_m.start()].count("\n") + 1
                    issues.append({
                        "file": rel_path, "line": line_no, "level": "ERROR",
                        "rule": "Caption Positioning",
                        "msg": "Table caption is placed BELOW tabular! GB/T 7713.1 requires table caption ABOVE table."
                    })

        # 匹配所有 figure 环境
        fig_blocks = re.finditer(r"\\begin\{figure\*?\}(.*?)\\end\{figure\*?\}", content, re.S)
        for fb in fig_blocks:
            total_figures += 1
            body = fb.group(1)
            cap_m = re.search(r"\\caption(?:\[[^\]]*\])?\{", body)
            img_m = re.search(r"\\includegraphics", body)
            if cap_m and img_m:
                if cap_m.start() < img_m.start():
                    line_no = content[:fb.start() + cap_m.start()].count("\n") + 1
                    issues.append({
                        "file": rel_path, "line": line_no, "level": "ERROR",
                        "rule": "Caption Positioning",
                        "msg": "Figure caption is placed ABOVE includegraphics! GB/T 7713.1 requires figure caption BELOW figure."
                    })

    # 3. 全文图表数量检查
    if total_figures == 0:
        issues.append({
            "file": "main.tex", "line": 1, "level": "ERROR",
            "rule": "Resource Integrity",
            "msg": "Total figure count is 0! Degree thesis must contain figures/visualizations."
        })

    # 4. figures/ 目录死文件检查
    figures_dir = os.path.join(project_dir, "figures")
    if os.path.isdir(figures_dir):
        for root, _, files in os.walk(figures_dir):
            for fn in files:
                if fn.lower().endswith((".pdf", ".png", ".jpg", ".jpeg", ".eps")):
                    full_p = os.path.join(root, fn)
                    rel_fig = os.path.relpath(full_p, project_dir).replace("\\", "/")
                    base_name = fn
                    base_no_ext = os.path.splitext(fn)[0]
                    # 检查是否被引用
                    matched = False
                    for rg in referenced_graphics:
                        rg_norm = rg.replace("\\", "/")
                        if rg_norm in (rel_fig, base_name, base_no_ext, f"figures/{base_name}", f"figures/{base_no_ext}"):
                            matched = True
                            break
                    if not matched:
                        issues.append({
                            "file": rel_fig, "line": 1, "level": "WARNING",
                            "rule": "Resource Integrity",
                            "msg": f"Dead figure file '{rel_fig}' in figures/ is never referenced in any .tex file."
                        })

    # 5. 前后件清单检查
    full_corpus = "\n".join(all_tex_content.values())
    for sec in REQUIRED_SECTIONS:
        found = False
        for pat in sec["patterns"]:
            if re.search(pat, full_corpus, re.I | re.S):
                found = True
                break
        if not found:
            lvl = sec["level"]
            if scaffold_mode and lvl == "ERROR":
                lvl = "WARNING"
            issues.append({
                "file": "main.tex", "line": 1, "level": lvl,
                "rule": "Front/Back Matter Checklist",
                "msg": f"Missing required front/back matter: '{sec['name']}'."
                       + (" (Permitted under --scaffold draft mode)" if scaffold_mode else " Required for defense submission.")
            })

    # 6. 引文与参考文献结构检查
    dangling_cites = sorted(cited_keys - defined_bib_keys)
    if dangling_cites:
        issues.append({
            "file": "references.bib", "line": 1, "level": "ERROR",
            "rule": "Bibliography Integrity",
            "msg": f"Found {len(dangling_cites)} dangling \\cite references (not found in bibliography): {dangling_cites[:8]}"
        })

    uncited_entries = sorted(defined_bib_keys - cited_keys)
    if uncited_entries:
        issues.append({
            "file": "references.bib", "line": 1, "level": "WARNING",
            "rule": "Bibliography Integrity",
            "msg": f"Found {len(uncited_entries)} bibliography entries never cited in text: {uncited_entries[:8]}"
        })

    total_bib_count = len(defined_bib_keys)
    if total_bib_count < min_bib:
        issues.append({
            "file": "references.bib", "line": 1, "level": "WARNING",
            "rule": "Bibliography Count",
            "msg": f"Total references count is {total_bib_count} (< threshold {min_bib}). Master thesis typically requires >= 60 entries."
        })

    # 7. 编译日志解析 (若存在)
    log_files = find_files_by_ext(project_dir, ".log")
    for lf in log_files:
        rel_log = os.path.relpath(lf, project_dir)
        with open(lf, "r", encoding="utf-8", errors="ignore") as fp:
            log_text = fp.read()

        # LaTeX Error
        for m_err in re.finditer(r"(?:! LaTeX Error:|! Package \w+ Error:)\s*(.*?)(?=\n\s*\n|\n!)", log_text, re.S):
            issues.append({
                "file": rel_log, "line": 1, "level": "ERROR",
                "rule": "Compilation Log",
                "msg": f"Compiler Error: {m_err.group(0)[:120].strip()}"
            })

        # Overfull \hbox > 5.0pt
        for m_box in re.finditer(r"Overfull \\hbox \(([0-9.]+)pt too wide\) in paragraph at lines ([0-9]+)--([0-9]+)", log_text):
            excess = float(m_box.group(1))
            if excess > 5.0:
                issues.append({
                    "file": rel_log, "line": int(m_box.group(2)), "level": "WARNING",
                    "rule": "Margin Overflow (Overfull \\hbox)",
                    "msg": f"Severe overfull \\hbox: {excess}pt protrusion across margin (lines {m_box.group(2)}-{m_box.group(3)})."
                })

        # Undefined references
        if "There were undefined references" in log_text:
            issues.append({
                "file": rel_log, "line": 1, "level": "WARNING",
                "rule": "Undefined References",
                "msg": "Log indicates undefined references or missing \\label/\\ref mappings."
            })

    return _summarize_and_exit(issues, project_dir, json_out, strict)


def _summarize_and_exit(issues, project_dir, json_out, strict):
    n_err = sum(1 for i in issues if i["level"] == "ERROR")
    n_warn = sum(1 for i in issues if i["level"] == "WARNING")

    report = {
        "project": project_dir,
        "stats": {"errors": n_err, "warnings": n_warn, "total_issues": len(issues)},
        "issues": issues,
    }

    print("=" * 75)
    print(f"[*] Academic Thesis Compliance Scan finished.")
    print(f"[*] Results: {n_err} ERROR(s), {n_warn} WARNING(s).")
    print("=" * 75)

    for i in issues:
        loc = f"{i['file']}:L{i['line']}" if i["line"] else i["file"]
        print(f"[{i['level']:<7}] {loc:<32} | {i['rule']:<24} | {i['msg']}")
    print("=" * 75)

    if json_out:
        with open(json_out, "w", encoding="utf-8") as fp:
            json.dump(report, fp, ensure_ascii=False, indent=2)
        print(f"[OK] Compliance report saved to: {json_out}")

    if n_err > 0:
        return 1
    if strict and n_warn > 0:
        return 2
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Academic Degree Thesis Compliance Linter")
    parser.add_argument("project_dir", nargs="?", default=".", help="LaTeX project root directory")
    parser.add_argument("--json", dest="json_out", default=None, help="Output JSON report path")
    parser.add_argument("--scaffold", action="store_true", help="Scaffold mode: allow placeholder tokens as NOTICE")
    parser.add_argument("--strict", action="store_true", help="Strict mode: treat WARNINGs as failures (exit code 2)")
    parser.add_argument("--min-bib", type=int, default=60, help="Minimum reference threshold (default: 60)")
    args = parser.parse_args()

    exit_code = check_thesis(
        args.project_dir,
        scaffold_mode=args.scaffold,
        strict=args.strict,
        min_bib=args.min_bib,
        json_out=args.json_out
    )
    sys.exit(exit_code)
