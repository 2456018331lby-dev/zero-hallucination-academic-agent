#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""academic_extractor.py - academic PDF / LaTeX clean extractor.

Ported from `.agents/skills/phd-literature-survey/scripts/academic_extractor.py`
with two changes to fit this skill's conventions:
  * `--libs <DIR>` is accepted for isolated dependencies (`sys.path` prepend),
    matching `extract_pdfs.py` / `build_table.py`.
  * missing-dependency messages say exactly how to install into the isolated
    lib dir, and the module stays importable without PyMuPDF.

Designed for IEEE, ACM, Springer, arXiv and university theses: it resolves
two-column interleaving, strips running headers/footers, repairs line-wrap
hyphenation and preserves formulas, so an LLM reads the paper in human order.

Engines, in order of preference:
  1. `pymupdf4llm`  -> markdown with layout analysis (best; optional)
  2. coordinate-based de-interleaving on PyMuPDF blocks (always available
     when `fitz` is installed)
  3. refuse, telling the caller to fall back to `extract_pdfs.py` (pypdf)

Single file:
    python academic_extractor.py paper.pdf -o out.txt
Batch, same output layout as extract_pdfs.py (<<<PAGE n>>> markers):
    python academic_extractor.py --src <PDF_DIR> --out <TXT_DIR> --libs <DIR>
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import List, Optional

try:  # PyMuPDF renamed its import: prefer `pymupdf`, keep `fitz` for old installs
    import pymupdf as fitz  # type: ignore
    HAS_FITZ = True
except ImportError:
    try:
        import fitz  # type: ignore
        HAS_FITZ = True
    except ImportError:
        HAS_FITZ = False


def _reload_fitz() -> bool:
    """Retry the PyMuPDF import after `--libs` extended sys.path."""
    global fitz, HAS_FITZ
    if HAS_FITZ:
        return True
    for mod in ("pymupdf", "fitz"):
        try:
            fitz = __import__(mod)
            HAS_FITZ = True
            return True
        except ImportError:
            continue
    return False


def deinterleave_page_blocks(page, mid_tolerance: float = 15.0) -> str:
    """Return one page's text in true reading order.

    Spanning top blocks (title/authors/abstract) -> left column ->
    right column -> spanning bottom blocks. Also drops running headers and
    footers (top/bottom 35 pt) and repairs hyphenated line wraps.
    """
    rect = page.rect
    width, height = rect.width, rect.height
    mid_x = width / 2.0

    raw_blocks = page.get_text("blocks")
    if not raw_blocks:
        return ""

    text_blocks = [b for b in raw_blocks if b[6] == 0 and b[4].strip()]
    if not text_blocks:
        return ""

    content_blocks = []
    for b in text_blocks:
        _x0, y0, _x1, y1, _text, _bno, _ = b
        if y1 < 35 or y0 > (height - 35):
            continue
        content_blocks.append(b)
    if not content_blocks:
        content_blocks = text_blocks

    left_count = sum(1 for b in content_blocks if b[2] <= mid_x + mid_tolerance)
    right_count = sum(1 for b in content_blocks if b[0] >= mid_x - mid_tolerance)
    is_two_column = (left_count >= 2 and right_count >= 2)

    if not is_two_column:
        ordered = sorted(content_blocks, key=lambda b: (b[1], b[0]))
        return "\n\n".join(b[4].strip() for b in ordered)

    spanning_top, left_col, right_col, spanning_bottom = [], [], [], []
    for b in content_blocks:
        x0, y0, x1, y1, _text, _bno, _ = b
        if x0 < (mid_x - mid_tolerance) and x1 > (mid_x + mid_tolerance):
            (spanning_top if y1 < height * 0.4 else spanning_bottom).append(b)
        elif x1 <= mid_x + mid_tolerance:
            left_col.append(b)
        else:
            right_col.append(b)

    for zone in (spanning_top, left_col, right_col, spanning_bottom):
        zone.sort(key=lambda b: b[1])

    raw_text = "\n\n".join(b[4].strip() for b in
                           spanning_top + left_col + right_col + spanning_bottom)
    return re.sub(r"(\b\w+)-\s*\n\s*(\w+\b)", r"\1\2", raw_text)


def extract_pdf(pdf_path: str, max_pages: Optional[int] = None) -> str:
    """Clean markdown from an academic PDF. pymupdf4llm first, else fitz blocks."""
    try:
        import pymupdf4llm
        pages_arg = list(range(max_pages)) if max_pages is not None else None
        md = pymupdf4llm.to_markdown(pdf_path, pages=pages_arg)
        if md and len(md.strip()) > 50:
            return md
    except Exception:  # noqa: BLE001 - optional engine, any failure -> fall back
        pass

    if not HAS_FITZ:
        raise RuntimeError(
            "PyMuPDF is not importable. Install it isolated and pass --libs:\n"
            "  pip install --target <LIBDIR> pymupdf\n"
            "  python academic_extractor.py ... --libs <LIBDIR>"
        )

    doc = fitz.open(pdf_path)
    total = len(doc)
    limit = total if max_pages is None else min(total, max_pages)
    chunks: List[str] = []
    for i in range(limit):
        page_text = deinterleave_page_blocks(doc[i])
        if page_text:
            chunks.append(f"<<<PAGE {i + 1}>>>\n{page_text}")
    doc.close()
    return "\n\n".join(chunks)


def extract_latex(tex_path: str) -> str:
    """Readable text/equations from LaTeX source, comments stripped."""
    with open(tex_path, encoding="utf-8", errors="ignore") as f:
        content = f.read()

    clean_lines = []
    for line in content.splitlines():
        line_clean = re.sub(r"(?<!\\)%.*$", "", line)
        if line_clean.strip():
            clean_lines.append(line_clean)
    text = "\n".join(clean_lines)

    title_m = re.search(r"\\title\{([^}]+)\}", text)
    abstract_m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, re.DOTALL)

    header = []
    if title_m:
        header.append(f"# {title_m.group(1).strip()}\n")
    if abstract_m:
        header.append(f"## Abstract\n{re.sub(r'\s+', ' ', abstract_m.group(1).strip())}\n")

    text = re.sub(r"\\section\*?\{([^}]+)\}", r"\n\n## \1\n", text)
    text = re.sub(r"\\subsection\*?\{([^}]+)\}", r"\n\n### \1\n", text)
    text = re.sub(r"\\subsubsection\*?\{([^}]+)\}", r"\n\n#### \1\n", text)
    text = re.sub(
        r"\\begin\{(?:equation|align|gather)\*?\}(.*?)\\end\{(?:equation|align|gather)\*?\}",
        r"\n\n$$\n\1\n$$\n", text, flags=re.DOTALL)
    text = re.sub(r"\\textbf\{([^}]+)\}", r"**\1**", text)
    text = re.sub(r"\\textit\{([^}]+)\}", r"*\1*", text)
    text = re.sub(r"\\cite\{([^}]+)\}", r"[\1]", text)
    text = re.sub(r"\\ref\{([^}]+)\}", r"[\1]", text)
    for pat in (r"\\begin\{document\}", r"\\end\{document\}",
                r"\\documentclass\[.*?\]\{.*?\}", r"\\usepackage(\[.*?\])?\{.*?\}"):
        text = re.sub(pat, "", text)

    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return "".join(header) + "\n" + text


def main() -> int:
    ap = argparse.ArgumentParser(description="Academic PDF/LaTeX clean extractor")
    ap.add_argument("input_path", nargs="?", help="path to a PDF or TeX file")
    ap.add_argument("--src", default=None, help="batch mode: folder of PDFs")
    ap.add_argument("--out", "-o", default=None, help="output file or directory")
    ap.add_argument("--max-pages", "-p", type=int, default=None)
    ap.add_argument("--libs", default=None, help="optional extra sys.path (isolated deps)")
    args = ap.parse_args()

    if args.libs:
        sys.path.insert(0, args.libs)
        _reload_fitz()

    if args.src:
        if not os.path.isdir(args.src):
            print(f"Error: not a directory: {args.src}", file=sys.stderr)
            return 1
        out_dir = args.out or "."
        os.makedirs(out_dir, exist_ok=True)
        pdfs = sorted(f for f in os.listdir(args.src) if f.lower().endswith(".pdf"))
        if not pdfs:
            print(f"Error: no PDFs in {args.src}", file=sys.stderr)
            return 1
        ok = 0
        for name in pdfs:
            base = os.path.splitext(name)[0]
            try:
                res = extract_pdf(os.path.join(args.src, name), args.max_pages)
            except Exception as e:  # noqa: BLE001
                print(f"  FAIL {name}: {e}", file=sys.stderr)
                continue
            with open(os.path.join(out_dir, base + ".txt"), "w",
                      encoding="utf-8") as fh:
                fh.write(res)
            print(f"  {len(res):>7}ch  {name[:58]}")
            ok += 1
        print(f"\nwrote {ok}/{len(pdfs)} -> {out_dir}")
        return 0 if ok else 1

    if not args.input_path:
        print("Error: give a file path, or use --src for batch mode.", file=sys.stderr)
        return 1
    if not os.path.exists(args.input_path):
        print(f"Error: file not found {args.input_path}", file=sys.stderr)
        return 1

    ext = os.path.splitext(args.input_path)[1].lower()
    if ext == ".pdf":
        try:
            result = extract_pdf(args.input_path, args.max_pages)
        except Exception as e:  # noqa: BLE001
            print(f"Error: {e}", file=sys.stderr)
            return 1
    elif ext in (".tex", ".latex"):
        result = extract_latex(args.input_path)
    else:
        print(f"Error: unsupported format {ext} (want .pdf/.tex)", file=sys.stderr)
        return 1

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(result)
        print(f"Extracted {len(result)} chars -> {args.out}")
    else:
        print(result[:2000])
        if len(result) > 2000:
            print(f"\n... [Total length: {len(result)} characters]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
