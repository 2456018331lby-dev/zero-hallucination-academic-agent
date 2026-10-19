#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
academic_extractor.py - Academic Two-Column PDF & LaTeX Clean Extractor
Designed for IEEE, ACM, Springer, arXiv, and university theses.
Resolves column interleaving, preserves formulas, and extracts clean text for LLMs.
"""

import os
import sys
import re
import argparse
from typing import List, Dict, Any, Optional

def deinterleave_page_blocks(page, mid_tolerance: float = 15.0) -> str:
    """
    Extracts text from a single page by sorting blocks into proper reading order:
    1. Spanning Top Blocks (Title, Authors, Abstract)
    2. Left Column Blocks (top-to-bottom)
    3. Right Column Blocks (top-to-bottom)
    4. Spanning Bottom Blocks (Footers, spanning tables/figures)
    """
    rect = page.rect
    width, height = rect.width, rect.height
    mid_x = width / 2.0
    
    # Extract blocks: (x0, y0, x1, y1, text, block_no, block_type)
    # block_type == 0 indicates text; 1 indicates image
    raw_blocks = page.get_text("blocks")
    if not raw_blocks:
        return ""
        
    text_blocks = [b for b in raw_blocks if b[6] == 0 and b[4].strip()]
    if not text_blocks:
        return ""
        
    # Margin filters: remove running headers (top 35pt) and footers (bottom 35pt)
    content_blocks = []
    for b in text_blocks:
        x0, y0, x1, y1, text, bno, _ = b
        # Skip repetitive running header / page number noise
        if y1 < 35 or y0 > (height - 35):
            continue
        content_blocks.append(b)
        
    if not content_blocks:
        content_blocks = text_blocks

    # Analyze if the page is single-column or two-column
    # If most blocks stay entirely on the left or right of mid_x, it is two-column
    left_count = sum(1 for b in content_blocks if b[2] <= mid_x + mid_tolerance)
    right_count = sum(1 for b in content_blocks if b[0] >= mid_x - mid_tolerance)
    is_two_column = (left_count >= 2 and right_count >= 2)

    if not is_two_column:
        # Sort purely top-to-bottom
        sorted_blocks = sorted(content_blocks, key=lambda b: (b[1], b[0]))
        return "\n\n".join(b[4].strip() for b in sorted_blocks)

    # For two-column pages:
    spanning_top = []
    left_col = []
    right_col = []
    spanning_bottom = []
    
    for b in content_blocks:
        x0, y0, x1, y1, text, _, _ = b
        is_spanning = (x0 < (mid_x - mid_tolerance) and x1 > (mid_x + mid_tolerance))
        
        if is_spanning:
            if y1 < height * 0.4:
                spanning_top.append(b)
            else:
                spanning_bottom.append(b)
        elif x1 <= mid_x + mid_tolerance:
            left_col.append(b)
        else:
            right_col.append(b)
            
    # Sort within each zone
    spanning_top.sort(key=lambda b: b[1])
    left_col.sort(key=lambda b: b[1])
    right_col.sort(key=lambda b: b[1])
    spanning_bottom.sort(key=lambda b: b[1])
    
    ordered_blocks = spanning_top + left_col + right_col + spanning_bottom
    raw_text = "\n\n".join(b[4].strip() for b in ordered_blocks)
    
    # Fix broken hyphenated words at line wraps (e.g. "com- \n munication" -> "communication")
    clean_text = re.sub(r'(\b\w+)-\s*\n\s*(\w+\b)', r'\1\2', raw_text)
    return clean_text

def extract_pdf(pdf_path: str, max_pages: Optional[int] = None) -> str:
    """
    Extracts clean Markdown from an academic PDF.
    Primary Engine: pymupdf4llm with deep multi-column layout analysis.
    Fallback Engine: deinterleave_page_blocks coordinate analysis.
    """
    try:
        import pymupdf4llm
        pages_arg = list(range(max_pages)) if max_pages is not None else None
        md_text = pymupdf4llm.to_markdown(pdf_path, pages=pages_arg)
        if md_text and len(md_text.strip()) > 50:
            return md_text
    except Exception:
        pass

    try:
        import pymupdf as fitz
    except ImportError:  # pragma: no cover - legacy PyMuPDF
        import fitz
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    pages_to_read = total_pages if max_pages is None else min(total_pages, max_pages)
    
    page_texts = []
    for i in range(pages_to_read):
        page = doc[i]
        p_text = deinterleave_page_blocks(page)
        if p_text:
            page_texts.append(f"--- [Page {i + 1}/{total_pages}] ---\n{p_text}")
            
    doc.close()
    return "\n\n".join(page_texts)

def extract_latex(tex_path: str) -> str:
    """Extracts and cleans LaTeX source, removing comments and extracting readable text & equations."""
    with open(tex_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        
    # 1. Remove comments (% to end of line, but not \%)
    clean_lines = []
    for line in content.splitlines():
        # Match % preceded by non-backslash
        line_clean = re.sub(r'(?<!\\)%.*$', '', line)
        if line_clean.strip():
            clean_lines.append(line_clean)
    text = "\n".join(clean_lines)
    
    # 2. Extract Title and Abstract if present
    title_m = re.search(r'\\title\{([^}]+)\}', text)
    abstract_m = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', text, re.DOTALL)
    
    meta_header = []
    if title_m:
        meta_header.append(f"# {title_m.group(1).strip()}\n")
    if abstract_m:
        abs_text = re.sub(r'\s+', ' ', abstract_m.group(1).strip())
        meta_header.append(f"## Abstract\n{abs_text}\n")
        
    # 3. Clean section commands into markdown headers
    text = re.sub(r'\\section\*?\{([^}]+)\}', r'\n\n## \1\n', text)
    text = re.sub(r'\\subsection\*?\{([^}]+)\}', r'\n\n### \1\n', text)
    text = re.sub(r'\\subsubsection\*?\{([^}]+)\}', r'\n\n#### \1\n', text)
    
    # 4. Standardize equations (keep content, mark cleanly)
    text = re.sub(r'\\begin\{(?:equation|align|gather)\*?\}(.*?)\\end\{(?:equation|align|gather)\*?\}', 
                  r'\n\n$$\n\1\n$$\n', text, flags=re.DOTALL)
                  
    # 5. Clean common formatting commands
    text = re.sub(r'\\textbf\{([^}]+)\}', r'**\1**', text)
    text = re.sub(r'\\textit\{([^}]+)\}', r'*\1*', text)
    text = re.sub(r'\\cite\{([^}]+)\}', r'[\1]', text)
    text = re.sub(r'\\ref\{([^}]+)\}', r'[\1]', text)
    
    # 6. Remove document boilerplate
    text = re.sub(r'\\begin\{document\}', '', text)
    text = re.sub(r'\\end\{document\}', '', text)
    text = re.sub(r'\\documentclass\[.*?\]\{.*?\}', '', text)
    text = re.sub(r'\\usepackage(\[.*?\])?\{.*?\}', '', text)
    
    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return "".join(meta_header) + "\n" + text

def main():
    parser = argparse.ArgumentParser(description="Academic PDF/LaTeX Clean Extractor")
    parser.add_argument("input_path", help="Path to PDF or TeX file")
    parser.add_argument("--output", "-o", help="Output text/markdown file path", default=None)
    parser.add_argument("--max-pages", "-p", type=int, help="Maximum pages to extract for PDF", default=None)
    
    args = parser.parse_args()
    input_file = args.input_path
    
    if not os.path.exists(input_file):
        print(f"Error: File not found {input_file}", file=sys.stderr)
        sys.exit(1)
        
    ext = os.path.splitext(input_file)[1].lower()
    if ext == ".pdf":
        result = extract_pdf(input_file, args.max_pages)
    elif ext in [".tex", ".latex"]:
        result = extract_latex(input_file)
    else:
        print(f"Error: Unsupported file format {ext}. Please provide a .pdf or .tex file.", file=sys.stderr)
        sys.exit(1)
        
    if args.output:
        with open(args.output, "w", encoding="utf-8") as out_f:
            out_f.write(result)
        print(f"Extracted {len(result)} chars -> {args.output}")
    else:
        # Print snippet or full text
        print(result[:2000])
        if len(result) > 2000:
            print(f"\n... [Total length: {len(result)} characters]")

if __name__ == "__main__":
    main()
