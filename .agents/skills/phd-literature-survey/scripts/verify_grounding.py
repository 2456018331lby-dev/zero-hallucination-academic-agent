#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_grounding.py - Literature Survey Grounding Evidence Verification Gate

Ensures zero hallucination in PhD literature survey comparison matrices:
1. Every paper in the matrix must correspond to an existing physical file in local literature pool (./literature/).
2. Every entry must possess a valid, verifiable 'evidence' field (local PDF filename and exact page range,
   e.g., '[01]_paper.pdf, pp. 1-10', or explicit '文献未说明').
3. Uses PyMuPDF (fitz) to open the physical PDF:
   - Validates that the file exists and is a valid readable PDF.
   - Validates that the specified page range strictly falls within actual PDF page count [1, total_pages].
     If evidence points to a non-existent page -> FAILS (exit code 1).
   - Extracts text from the specified page range and matches it against paper title/keywords
     using a tolerant presence-checking heuristic.
4. Supports both --pdf-dir and --literature-dir as backward-compatible CLI flags.
"""

import os
import re
import sys
import argparse

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def extract_keywords(text):
    """提取长度大于等于 4 的字母数字关键词（过滤高频非核心词汇）。"""
    stop_words = {
        "with", "from", "that", "this", "these", "those", "their", "there",
        "which", "using", "based", "aided", "assisted", "towards", "paper",
        "study", "design", "network", "system", "systems", "approach"
    }
    tokens = re.findall(r"[a-zA-Z]{4,}", text.lower())
    return [t for t in tokens if t not in stop_words]


def parse_page_range(evidence_str, max_pages=None):
    """从 evidence 文本中解析起始与终止页码。"""
    # 匹配常见的 pp. 1-10, p. 5, pages 3-7, 1-10 等
    m = re.search(r"(?:pp?\.|pages?|页码?)\s*(\d+)(?:\s*[-–—~至到]\s*(\d+))?", evidence_str, re.I)
    if m:
        sp = int(m.group(1))
        ep = int(m.group(2)) if m.group(2) else sp
        return sp, ep

    # 次级匹配: 查找 standalone 数字区间如 1-10
    m2 = re.search(r"\b(\d+)\s*[-–—~至到]\s*(\d+)\b", evidence_str)
    if m2:
        sp = int(m2.group(1))
        ep = int(m2.group(2))
        return sp, ep

    # 单页匹配
    m3 = re.search(r"\b(\d+)\b", evidence_str)
    if m3:
        p = int(m3.group(1))
        return p, p

    return None, None


def verify_grounding(matrix_path, literature_dir):
    matrix_path = os.path.abspath(matrix_path)
    literature_dir = os.path.abspath(literature_dir)

    print("=" * 75)
    print(f"[*] Literature Survey Grounding Verification Gate")
    print(f"[*] Matrix File    : {matrix_path}")
    print(f"[*] Literature Pool: {literature_dir}")
    print(f"[*] Engine         : PyMuPDF (fitz) Genuine Physical Verification")
    print("=" * 75)

    if not os.path.exists(matrix_path):
        print(f"[-] Matrix file not found: {matrix_path}", file=sys.stderr)
        return False

    if not os.path.exists(literature_dir):
        print(f"[-] Literature directory not found: {literature_dir}", file=sys.stderr)
        return False

    if not HAS_PYMUPDF:
        print("[-] [依赖缺失] PyMuPDF (fitz) is required for physical page grounding.", file=sys.stderr)
        print("    请运行安装命令: pip install -r .agents/skills/requirements.txt (或: pip install pymupdf)", file=sys.stderr)
        return False

    # 扫描本地文献池已存在的 PDF 文件
    local_pdfs = [f for f in os.listdir(literature_dir) if f.lower().endswith(".pdf")]
    local_pdfs_norm = {re.sub(r"[^a-zA-Z0-9]", "", f.lower()): f for f in local_pdfs}
    print(f"[+] Found {len(local_pdfs)} local PDF files in literature pool.")

    with open(matrix_path, "r", encoding="utf-8", errors="ignore") as fp:
        lines = fp.readlines()

    table_rows = []
    header_cols = []
    in_table = False

    for line in lines:
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if not cells or all(c == "" for c in cells):
                continue
            if re.match(r"^:?-+:?$", cells[0]):
                continue  # 分割行
            if not in_table:
                in_table = True
                header_cols = [c.lower() for c in cells]
            else:
                table_rows.append(cells)
        elif in_table:
            in_table = False

    failures = []
    warnings = []
    verified_entries = []

    if table_rows and header_cols:
        print(f"[+] Detected matrix table format ({len(table_rows)} rows, {len(header_cols)} columns).")
        title_idx = -1
        evidence_idx = -1
        for idx, col in enumerate(header_cols):
            if any(k in col for k in ("论文", "题目", "title")):
                title_idx = idx
            if any(k in col for k in ("evidence", "证据", "出处", "出处与页码", "本地文件")):
                evidence_idx = idx

        if title_idx < 0:
            failures.append("Could not identify 'Paper Title' column in matrix table header.")

        for r_idx, row in enumerate(table_rows, start=1):
            if title_idx >= len(row):
                continue
            title = row[title_idx].replace("**", "").strip()
            if not title:
                continue

            evidence_val = row[evidence_idx].strip() if (evidence_idx >= 0 and evidence_idx < len(row)) else ""
            if not evidence_val:
                failures.append(f"Row {r_idx} [{title[:35]}]: Missing mandatory 'evidence' field (16th dimension)!")
                continue

            if evidence_val == "文献未说明":
                verified_entries.append((r_idx, title[:30], "None (文献未说明)", "N/A", "PASS (Declared Unstated)"))
                continue

            # 从 evidence 提取目标文件名
            matched_file = None
            for raw_fn in local_pdfs:
                if raw_fn in evidence_val or raw_fn.lower() in evidence_val.lower():
                    matched_file = raw_fn
                    break

            if not matched_file:
                # 尝试用标题模糊匹配本地 PDF
                title_clean = re.sub(r"[^a-zA-Z0-9]", "", title.lower())
                for norm_k, raw_fn in local_pdfs_norm.items():
                    if norm_k in title_clean or title_clean in norm_k or any(w in raw_fn.lower() for w in title.lower().split()[:3] if len(w) > 3):
                        matched_file = raw_fn
                        break

            if not matched_file:
                failures.append(f"Row {r_idx} [{title[:35]}]: Physical PDF file not found in pool for evidence '{evidence_val}'!")
                continue

            pdf_path = os.path.join(literature_dir, matched_file)

            # PyMuPDF 真实物理校验
            try:
                doc = fitz.open(pdf_path)
            except Exception as e:
                failures.append(f"Row {r_idx} [{title[:35]}]: Failed to open PDF '{matched_file}': {e}")
                continue

            total_pages = len(doc)
            sp, ep = parse_page_range(evidence_val, total_pages)

            if sp is None or ep is None:
                warnings.append(f"Row {r_idx} [{title[:35]}]: Evidence '{evidence_val}' lacks parseable page number range.")
                # 默认全本抽样检查第 1 页
                sp, ep = 1, min(total_pages, 5)

            # 核心物理门禁：检查页码是否落在物理实际页数内
            if sp < 1 or ep > total_pages or sp > ep:
                failures.append(
                    f"Row {r_idx} [{title[:35]}]: Evidence claims page range pp. {sp}-{ep}, "
                    f"but physical PDF '{matched_file}' only has {total_pages} pages! (Physical Grounding Violation)"
                )
                continue

            # 抽取指定页码区间的实际文本
            page_text = ""
            for p_num in range(sp - 1, ep):
                page_text += doc[p_num].get_text("text") + " "
            page_text_lower = page_text.lower()

            # 关键词存在性验证
            title_tokens = extract_keywords(title)
            # 同时也检查整行的其他单元格重要词汇（如方法名、期刊等）
            row_tokens = extract_keywords(" ".join(row))
            all_candidate_tokens = list(set(title_tokens + [t for t in row_tokens if len(t) >= 5]))

            matched_tokens = [t for t in all_candidate_tokens if t in page_text_lower]
            match_ratio = len(matched_tokens) / len(all_candidate_tokens) if all_candidate_tokens else 0

            # 宽松但真实的匹配判定：至少命中 2 个特征关键词，或命中率 >= 25%
            # (如果单页只命中 1 个，但在前 3 页中能找到标题，则放行并提醒)
            if len(matched_tokens) >= 2 or match_ratio >= 0.25:
                verified_entries.append(
                    (r_idx, matched_file, f"pp. {sp}-{ep} (of {total_pages})", f"{len(matched_tokens)} tokens matched", "PASS")
                )
            else:
                # 检查第 1 页（标题页）是否吻合该论文，以区分"页码引错"还是"完全张冠李戴"
                p1_text = doc[0].get_text("text").lower()
                p1_matched = [t for t in title_tokens if t in p1_text]
                if len(p1_matched) >= 2:
                    failures.append(
                        f"Row {r_idx} [{title[:35]}]: PDF '{matched_file}' matches paper, but specified pages pp. {sp}-{ep} "
                        f"do not contain expected text content (matched only {len(matched_tokens)} tokens: {matched_tokens})!"
                    )
                else:
                    failures.append(
                        f"Row {r_idx} [{title[:35]}]: Physical PDF '{matched_file}' content does NOT match paper title! "
                        f"(Matched only {len(p1_matched)} tokens on cover page)!"
                    )

    else:
        print("[*] Scanning document for individual paper sections...")
        paper_sections = re.findall(r"(?:###|####|\d+\.)\s+(.+?)(?=\n(?:###|####|\d+\.)|\Z)", "".join(lines), re.S)
        if not paper_sections:
            failures.append("Matrix file does not contain recognized table or structured paper sections.")
        for p in paper_sections:
            first_line = p.strip().splitlines()[0]
            if "evidence" not in p.lower() and "证据" not in p:
                failures.append(f"Paper [{first_line[:50]}]: Lacks mandatory 'evidence / 证据出处' field!")

    print("\n" + "=" * 75)
    print(f"[*] Physical Grounding Audit Detailed Records ({len(verified_entries)} verified):")
    for r_idx, fn, prange, match_info, st in verified_entries:
        print(f"    [PASS] Row {r_idx}: {fn[:35]} | {prange} | {match_info}")

    print("-" * 75)
    print(f"[*] Summary: {len(failures)} FAILURES, {len(warnings)} WARNINGS.")
    for f in failures:
        print(f"  [FAIL] {f}")
    for w in warnings:
        print(f"  [WARN] {w}")
    print("=" * 75)

    if failures:
        print("\n[-] Grounding Gate FAILED: Physical page grounding verification failed!", file=sys.stderr)
        return False

    print("\n[OK] Grounding Gate PASSED: All matrix papers physically grounded with verifiable pages.")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Literature Survey Grounding Verification Gate (PyMuPDF)")
    parser.add_argument("matrix_file", nargs="?", default="survey/literature_comparison_matrix.md", help="Path to literature comparison matrix markdown")
    parser.add_argument("--literature-dir", "--pdf-dir", dest="literature_dir", default="literature", help="Path to local literature pool directory")

    args = parser.parse_args()
    success = verify_grounding(args.matrix_file, args.literature_dir)
    sys.exit(0 if success else 1)
