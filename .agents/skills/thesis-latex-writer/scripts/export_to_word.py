#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_to_word.py - Publication-Grade Word (.docx) Exporter for Academic Theses & Surveys

Features:
1. GB/T 7713.1 Academic Styling:
   - Heading 1 (16pt SimHei bold, centered, page break)
   - Heading 2 (14pt SimHei bold)
   - Heading 3 (13pt SimHei bold)
   - Body text: 12pt SimSun / Times New Roman, 1.35 line spacing, 2-char first-line indent
2. Markdown table parsing: renders tables as native booktabs three-line tables (no silent drops).
3. Code / Mermaid block formatting in clean bordered callout boxes.
4. Dynamic LaTeX project ingestion: extracts chapters and sections from .tex rather than hardcoded text.
5. Scaffold mode: inserts prominent red warning banners on cover/page header and highlights
   placeholder/mock data with red alert badges: '[占位数据——禁止作为结论引用]'.
"""

import os
import re
import sys
import argparse

try:
    import docx
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml import OxmlElement, parse_xml
    from docx.oxml.ns import qn
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def set_cell_borders(cell, top=False, bottom=False, left=False, right=False, sz="12", color="000000"):
    """为单元格设置三线表边框。"""
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for side, active in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        edge = OxmlElement(f'w:{side}')
        if active:
            edge.set(qn('w:val'), 'single')
            edge.set(qn('w:sz'), str(sz))
            edge.set(qn('w:space'), '0')
            edge.set(qn('w:color'), color)
        else:
            edge.set(qn('w:val'), 'none')
        tcBorders.append(edge)
    tcPr.append(tcBorders)


def add_heading(doc, text, level):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True

    run = p.add_run(text)
    run.bold = True
    run.font.name = 'SimHei'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), 'SimHei')

    if level == 1:
        run.font.size = Pt(16)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.page_break_before = True
    elif level == 2:
        run.font.size = Pt(14)
    else:
        run.font.size = Pt(13)
    return p


def add_paragraph(doc, text, bold_prefix="", indent=True, is_placeholder=False):
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.35
    p.paragraph_format.space_after = Pt(4)
    if indent:
        p.paragraph_format.first_line_indent = Inches(0.28)  # 约 2 字符

    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.bold = True
        r_pre.font.name = 'SimHei'
        r_pre.font.size = Pt(12)
        r_pre._element.rPr.rFonts.set(qn('w:eastAsia'), 'SimHei')

    if is_placeholder:
        r_badge = p.add_run("【占位数据——禁止作为结论引用】 ")
        r_badge.bold = True
        r_badge.font.size = Pt(11)
        r_badge.font.color.rgb = RGBColor(200, 0, 0)
        r_badge.font.name = 'SimHei'
        r_badge._element.rPr.rFonts.set(qn('w:eastAsia'), 'SimHei')

    r = p.add_run(text)
    r.font.name = 'SimSun'
    r.font.size = Pt(12)
    r._element.rPr.rFonts.set(qn('w:eastAsia'), 'SimSun')
    if is_placeholder:
        r.font.color.rgb = RGBColor(160, 0, 0)
    return p


def add_markdown_table_to_doc(doc, raw_table_lines):
    """解析 Markdown 表格行并生成符合国标的三线表。"""
    clean_rows = []
    for line in raw_table_lines:
        s = line.strip()
        if not s.startswith("|"):
            continue
        # 排除分割线行 |:---|:---|
        if re.search(r"^\|(?:\s*:?[-]+:?\s*\|)+$", s):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if cells and any(cells):
            clean_rows.append(cells)

    if len(clean_rows) < 1:
        return

    num_cols = max(len(r) for r in clean_rows)
    for r in clean_rows:
        while len(r) < num_cols:
            r.append("")

    table = doc.add_table(rows=len(clean_rows), cols=num_cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True

    for r_idx, row in enumerate(table.rows):
        # 跨页断行保护
        trPr = row._tr.get_or_add_trPr()
        trPr.append(parse_xml(r'<w:cantSplit xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'))

        is_header = (r_idx == 0)
        is_bottom = (r_idx == len(table.rows) - 1)

        for c_idx, cell in enumerate(row.cells):
            # 三线表边框：顶部 1.5pt，表头底 0.75pt，底部 1.5pt，无竖线
            set_cell_borders(
                cell,
                top=is_header,
                bottom=(is_header or is_bottom),
                left=False,
                right=False,
                sz="12" if (is_header or is_bottom) else "6"
            )

            cell.text = clean_rows[r_idx][c_idx]
            for p in cell.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if is_header else WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.line_spacing = 1.15
                p.paragraph_format.space_before = Pt(3)
                p.paragraph_format.space_after = Pt(3)
                for r in p.runs:
                    r.font.size = Pt(9.5)
                    r.font.name = 'SimSun'
                    r._element.rPr.rFonts.set(qn('w:eastAsia'), 'SimSun')
                    if is_header:
                        r.bold = True
                        r.font.name = 'SimHei'
                        r._element.rPr.rFonts.set(qn('w:eastAsia'), 'SimHei')

    doc.add_paragraph()  # 表后空行


def build_survey_docx(input_md, output_docx):
    """将学术调研报告 Markdown 完整转换为格式规范的 Word 文档。"""
    if not os.path.exists(input_md):
        print(f"[-] Input markdown not found: {input_md}", file=sys.stderr)
        return False

    doc = docx.Document()
    for s in doc.sections:
        s.top_margin = Inches(1.18)
        s.bottom_margin = Inches(0.98)
        s.left_margin = Inches(1.02)
        s.right_margin = Inches(1.02)

    with open(input_md, "r", encoding="utf-8") as f:
        lines = f.readlines()

    in_table = False
    table_lines = []
    in_code_block = False
    code_block_lines = []

    for line in lines:
        stripped = line.strip()

        # 代码块处理
        if stripped.startswith("```"):
            if in_code_block:
                # 结束代码块
                in_code_block = False
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Inches(0.4)
                p.paragraph_format.space_before = Pt(4)
                p.paragraph_format.space_after = Pt(4)
                run = p.add_run("\n".join(code_block_lines))
                run.font.name = 'Consolas'
                run.font.size = Pt(9.5)
                run.font.color.rgb = RGBColor(60, 60, 60)
                code_block_lines = []
            else:
                in_code_block = True
                lang = stripped.lstrip("`").strip()
                if lang:
                    code_block_lines.append(f"[{lang.upper()}]")
            continue

        if in_code_block:
            code_block_lines.append(stripped)
            continue

        # 表格处理
        if stripped.startswith("|") and not stripped.startswith(">"):
            in_table = True
            table_lines.append(stripped)
            continue
        elif in_table:
            in_table = False
            add_markdown_table_to_doc(doc, table_lines)
            table_lines = []

        if not stripped:
            continue

        # 标题处理
        if stripped.startswith("# "):
            title_text = stripped.lstrip("#").strip()
            add_heading(doc, title_text, 1)
        elif stripped.startswith("## "):
            add_heading(doc, stripped.lstrip("#").strip(), 1)
        elif stripped.startswith("### "):
            add_heading(doc, stripped.lstrip("#").strip(), 2)
        elif stripped.startswith("#### "):
            add_heading(doc, stripped.lstrip("#").strip(), 3)
        elif stripped.startswith(">"):
            # 引用块
            quote_text = stripped.lstrip(">").strip()
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.4)
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(4)
            r = p.add_run(quote_text)
            r.italic = True
            r.font.name = 'KaiTi'
            r._element.rPr.rFonts.set(qn('w:eastAsia'), 'KaiTi')
            r.font.size = Pt(10.5)
        else:
            add_paragraph(doc, stripped)

    if in_table and table_lines:
        add_markdown_table_to_doc(doc, table_lines)

    os.makedirs(os.path.dirname(os.path.abspath(output_docx)), exist_ok=True)
    doc.save(output_docx)
    print(f"[OK] Generated Word Survey Report: {output_docx}")
    return True


def strip_latex_formatting(text):
    """去除基础 LaTeX 标记，保留纯文本。"""
    t = re.sub(r"%.*", "", text)
    t = re.sub(r"\\textbf\{([^}]+)\}", r"\1", t)
    t = re.sub(r"\\textit\{([^}]+)\}", r"\1", t)
    t = re.sub(r"\\emph\{([^}]+)\}", r"\1", t)
    t = re.sub(r"\\cite[tp]?\{[^}]+\}", "[文献]", t)
    t = re.sub(r"\\ref\{[^}]+\}", "[图表]", t)
    t = re.sub(r"\$([^$]+)\$", r"\1", t)
    t = re.sub(r"\\label\{[^}]+\}", "", t)
    return t.strip()


def parse_tex_file_sections(tex_path):
    """从 .tex 文件提取结构与段落。"""
    if not os.path.exists(tex_path):
        return []

    with open(tex_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    elements = []
    lines = content.splitlines()
    in_table = False
    table_rows = []

    for line in lines:
        line_code, _ = line.split("%", 1) if "%" in line else (line, "")
        s = line_code.strip()
        if not s:
            continue

        if r"\chapter{" in s or r"\chapter*{" in s:
            m = re.search(r"\\chapter\*?\{([^}]+)\}", s)
            if m:
                elements.append(("h1", m.group(1).strip()))
        elif r"\section{" in s or r"\section*{" in s:
            m = re.search(r"\\section\*?\{([^}]+)\}", s)
            if m:
                elements.append(("h2", m.group(1).strip()))
        elif r"\subsection{" in s or r"\subsection*{" in s:
            m = re.search(r"\\subsection\*?\{([^}]+)\}", s)
            if m:
                elements.append(("h3", m.group(1).strip()))
        elif r"\begin{tabular" in s:
            in_table = True
            table_rows = []
        elif r"\end{tabular" in s:
            in_table = False
            if table_rows:
                elements.append(("table", table_rows))
                table_rows = []
        elif in_table:
            if r"\toprule" in s or r"\midrule" in s or r"\bottomrule" in s:
                continue
            cells = [strip_latex_formatting(c) for c in s.rstrip(r"\\").split("&")]
            if any(cells):
                table_rows.append(cells)
        elif not s.startswith("\\") or s.startswith("\\noindent"):
            clean = strip_latex_formatting(s)
            if clean and len(clean) > 2:
                elements.append(("p", clean))

    return elements


def build_thesis_docx(project_dir, output_docx, scaffold=False):
    """从 LaTeX 工程动态读取章节内容并生成学位论文 Word 文档。"""
    project_dir = os.path.abspath(project_dir)
    main_tex = os.path.join(project_dir, "main.tex")
    if not os.path.exists(main_tex):
        print(f"[-] main.tex not found in: {project_dir}", file=sys.stderr)
        return False

    doc = docx.Document()
    for s in doc.sections:
        s.top_margin = Inches(1.18)
        s.bottom_margin = Inches(0.98)
        s.left_margin = Inches(1.02)
        s.right_margin = Inches(1.02)

    # 封面/横幅与页眉水印
    if scaffold:
        # 页眉红色水印
        header = doc.sections[0].header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run("【SCAFFOLD DRAFT —— 仅供草稿审阅，严禁送审】")
        hrun.bold = True
        hrun.font.size = Pt(9.5)
        hrun.font.name = 'SimHei'
        hrun._element.rPr.rFonts.set(qn('w:eastAsia'), 'SimHei')
        hrPr = hrun._r.get_or_add_rPr()
        hcolor = OxmlElement('w:color')
        hcolor.set(qn('w:val'), 'C00000')
        hrPr.append(hcolor)

        # 封面醒目红色边框警告横幅
        p_scaffold = doc.add_paragraph()
        p_scaffold.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pPr = p_scaffold._p.get_or_add_pPr()
        pBdr = OxmlElement('w:pBdr')
        for side in ('top', 'left', 'bottom', 'right'):
            border = OxmlElement(f'w:{side}')
            border.set(qn('w:val'), 'single')
            border.set(qn('w:sz'), '18')  # 2.25 pt
            border.set(qn('w:space'), '6')
            border.set(qn('w:color'), 'C00000')
            pBdr.append(border)
        pPr.append(pBdr)

        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), 'FFF5F5')
        pPr.append(shd)

        r_scaffold = p_scaffold.add_run(
            "【学术完整性脚手架警告 (SCAFFOLD DRAFT)】\n"
            "本文档处于脚手架起草阶段，第四章实验数据采用 \\TODO{} 占位符保护。\n"
            "未经真实实验仿真数据填充与人工专家签名核验，严禁用作正式学术评审与送审！"
        )
        r_scaffold.bold = True
        r_scaffold.font.size = Pt(12)
        r_scaffold.font.name = 'SimHei'
        r_scaffold._element.rPr.rFonts.set(qn('w:eastAsia'), 'SimHei')
        rPr = r_scaffold._r.get_or_add_rPr()
        color_el = OxmlElement('w:color')
        color_el.set(qn('w:val'), 'C00000')
        rPr.append(color_el)
        p_scaffold.paragraph_format.space_after = Pt(20)

    # 解析 main.tex 中引入的章节
    with open(main_tex, "r", encoding="utf-8", errors="ignore") as f:
        main_content = f.read()

    # 动态提取论文题目与学校信息
    thesis_title = "面向前沿方向的高水平学位论文"
    m_pdftitle = re.search(r"pdftitle\s*=\s*\{([^}]+)\}", main_content)
    if m_pdftitle:
        thesis_title = m_pdftitle.group(1).strip()
    else:
        m_title = re.search(r"\\title\*?\{([^}]+)\}", main_content)
        if m_title:
            thesis_title = m_title.group(1).strip()

    school_name = "硕士学位论文"
    if "北京大学" in main_content:
        school_name = "北京大学硕士学位论文"
    elif "清华大学" in main_content:
        school_name = "清华大学硕士学位论文"

    add_heading(doc, school_name, 1)
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run(f"{thesis_title}\n（学位论文草稿）")
    r_sub.font.size = Pt(16)
    r_sub.bold = True
    r_sub.font.name = 'SimHei'
    r_sub._element.rPr.rFonts.set(qn('w:eastAsia'), 'SimHei')
    p_sub.paragraph_format.space_after = Pt(30)

    # 递归提取所有 \input 或 \include 章节
    def resolve_tex_files(content, base_dir):
        files = []
        inputs = re.findall(r"\\(?:input|include)\{([^}]+)\}", content)
        for rel in inputs:
            cand = os.path.join(base_dir, rel if rel.endswith(".tex") else rel + ".tex")
            if not os.path.exists(cand):
                cand = os.path.join(base_dir, "chapters", os.path.basename(rel) if rel.endswith(".tex") else os.path.basename(rel) + ".tex")
            if os.path.exists(cand):
                files.append(cand)
                # Check nested inputs
                with open(cand, "r", encoding="utf-8", errors="ignore") as sub_fp:
                    sub_c = sub_fp.read()
                if r"\input" in sub_c or r"\include" in sub_c:
                    files.extend(resolve_tex_files(sub_c, base_dir))
        return files

    all_tex_paths = []
    seen_paths = set()
    for p in resolve_tex_files(main_content, project_dir):
        norm = os.path.normpath(p)
        if norm not in seen_paths:
            seen_paths.add(norm)
            all_tex_paths.append(p)

    for tex_path in all_tex_paths:

        elements = parse_tex_file_sections(tex_path)
        for kind, val in elements:
            if kind == "h1":
                add_heading(doc, val, 1)
            elif kind == "h2":
                add_heading(doc, val, 2)
            elif kind == "h3":
                add_heading(doc, val, 3)
            elif kind == "p":
                is_mock = scaffold and any(kw in val for kw in ("TODO", "待填", "占位", "SCAFFOLD", "待替换"))
                add_paragraph(doc, val, is_placeholder=is_mock)
            elif kind == "table":
                # 添加三线表
                if len(val) >= 2:
                    max_cols = max(len(r) for r in val) if val else 0
                    if max_cols > 0:
                        table = doc.add_table(rows=len(val), cols=max_cols)
                        table.alignment = WD_TABLE_ALIGNMENT.CENTER
                        for r_idx, row in enumerate(table.rows):
                            r_data = val[r_idx]
                            for c_idx, cell in enumerate(row.cells):
                                cell.text = r_data[c_idx] if c_idx < len(r_data) else ""
                                set_cell_borders(
                                    cell,
                                    top=(r_idx == 0),
                                    bottom=(r_idx == 0 or r_idx == len(table.rows) - 1),
                                    sz="12" if (r_idx == 0 or r_idx == len(table.rows) - 1) else "6"
                                )
                                for p in cell.paragraphs:
                                    for r in p.runs:
                                        r.font.size = Pt(9.5)
                                        r.font.name = 'SimSun'
                        doc.add_paragraph()

    os.makedirs(os.path.dirname(os.path.abspath(output_docx)), exist_ok=True)
    doc.save(output_docx)
    print(f"[OK] Generated Word Thesis: {output_docx}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export academic documents to Word (.docx)")
    parser.add_argument("--survey", help="Input survey markdown path")
    parser.add_argument("--output-survey", help="Output survey docx path")
    parser.add_argument("--thesis", help="LaTeX thesis project directory")
    parser.add_argument("--output-thesis", help="Output thesis docx path")
    parser.add_argument("--scaffold", action="store_true", help="Scaffold mode: add red warning banners")

    args = parser.parse_args()

    if not HAS_DOCX:
        print("[-] [依赖缺失] python-docx 未安装，无法生成 Word (.docx) 文档。", file=sys.stderr)
        print("    请运行安装命令: pip install -r .agents/skills/requirements.txt (或: pip install python-docx)", file=sys.stderr)
        sys.exit(1)

    # 默认行为（向后兼容）
    if not args.survey and not args.thesis:
        cur_dir = os.path.abspath(os.path.dirname(__file__))
        if os.path.basename(cur_dir) == "pku_thesis_workflow":
            base_dir = cur_dir
        else:
            cand1 = os.path.abspath(os.path.join(cur_dir, "..", "..", "..", "pku_thesis_workflow"))
            cand2 = os.path.abspath(os.path.join(cur_dir, "pku_thesis_workflow"))
            if os.path.exists(cand1):
                base_dir = cand1
            elif os.path.exists(cand2):
                base_dir = cand2
            else:
                base_dir = cur_dir
        survey_md = os.path.join(base_dir, "survey", "research_direction_survey_report.md")
        survey_docx = os.path.join(base_dir, "survey", "Research_Direction_Survey_Report.docx")
        thesis_dir = os.path.join(base_dir, "pku_thesis_project")
        thesis_docx = os.path.join(base_dir, "pku_thesis_project", "Peking_University_Thesis_085402.docx")

        if os.path.exists(survey_md):
            build_survey_docx(survey_md, survey_docx)
        if os.path.exists(thesis_dir):
            build_thesis_docx(thesis_dir, thesis_docx, scaffold=True)
    else:
        if args.survey and args.output_survey:
            build_survey_docx(args.survey, args.output_survey)
        if args.thesis and args.output_thesis:
            build_thesis_docx(args.thesis, args.output_thesis, scaffold=args.scaffold)
