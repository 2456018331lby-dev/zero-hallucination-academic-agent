#!/usr/bin/env python3
"""Extract text (page-delimited) from every PDF in a source folder.

Read-only on the source PDFs; writes one .txt per PDF into --out.

Two engines:
  * `academic` - `academic_extractor.py`, which de-interleaves two-column
    academic layouts (IEEE/ACM/Springer/arXiv) and strips running
    headers/footers. Needs PyMuPDF, so it must be installed into --libs.
  * `pypdf`    - plain per-page extraction. Always available, but scrambles
    two-column papers into left/right interleaving.

`--engine auto` (default) picks `academic` when PyMuPDF is importable and
silently falls back to `pypdf` otherwise, printing which engine each file used.

Output form: pages marked `<<<PAGE n>>>`. `verify_grounding.py --table-json`
relies on those markers for its page-scoped title check, so do not change them.

Usage:
    python extract_pdfs.py --src <PDF_DIR> --out <TXT_DIR> [--libs <SITE_DIR>]
                           [--engine auto|academic|pypdf]
"""
from __future__ import annotations

import argparse
import os
import re
import sys


def clean(t: str) -> str:
    t = t.replace("\u00ad", "")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def head_of(txt: str, n: int = 220) -> str:
    body = re.sub(r"^<<<PAGE \d+>>>\s*", "", txt.strip())
    return clean(body)[:n].replace("\n", " / ")


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract text from PDFs into .txt files.")
    ap.add_argument("--src", required=True, help="folder containing PDFs")
    ap.add_argument("--out", required=True, help="folder to write .txt files into")
    ap.add_argument("--libs", default=None, help="optional extra sys.path for pypdf / PyMuPDF")
    ap.add_argument("--engine", choices=("auto", "academic", "pypdf"), default="auto",
                    help="auto = academic when PyMuPDF is available, else pypdf")
    args = ap.parse_args()

    if args.libs:
        sys.path.insert(0, args.libs)

    # --- pick the engine -----------------------------------------------------
    print(f"engine requested: {args.engine}")
    if args.engine == "auto":
        try:
            try:
                import pymupdf  # noqa: F401,E402
            except ImportError:
                import fitz  # noqa: F401,E402
            engine = "academic"
            print("  PyMuPDF found -> academic engine (two-column de-interleaving)")
        except ImportError:
            engine = "pypdf"
            print("  PyMuPDF not importable -> pypdf engine")
            print("  (two-column papers will interleave; for better fidelity run:")
            print("     pip install --target <LIBDIR> pymupdf   then pass --libs <LIBDIR>)")
    else:
        engine = args.engine

    reader_cls = None
    if engine == "academic":
        try:
            import academic_extractor  # noqa: E402
            if not academic_extractor.HAS_FITZ:
                raise ImportError("PyMuPDF missing")
        except ImportError as e:
            if args.engine == "academic":
                print(f"academic engine unavailable ({e}). Install isolated:\n"
                      f"  pip install --target <LIBDIR> pymupdf\n"
                      f"or re-run with --engine pypdf", file=sys.stderr)
                return 2
            engine = "pypdf"
            print(f"  fallback -> pypdf ({e})")

    if engine == "pypdf":
        try:
            from pypdf import PdfReader  # noqa: E402
            reader_cls = PdfReader
        except ImportError:
            print(
                "pypdf not importable. Install it isolated first:\n"
                "  pip install --target <dir> pypdf\n"
                "then re-run with --libs <dir>",
                file=sys.stderr,
            )
            return 2

    src, out = args.src, args.out
    if not os.path.isdir(src):
        print(f"source folder not found: {src}", file=sys.stderr)
        return 1
    os.makedirs(out, exist_ok=True)

    pdfs = sorted(f for f in os.listdir(src) if f.lower().endswith(".pdf"))
    if not pdfs:
        print(f"no PDFs in {src}", file=sys.stderr)
        return 1
    print(f"{len(pdfs)} PDFs via {engine}\n")

    ok = 0
    for name in pdfs:
        path = os.path.join(src, name)
        base = os.path.splitext(name)[0]
        pages = "?"
        try:
            if engine == "academic":
                text = clean(academic_extractor.extract_pdf(path))
                if not text:
                    raise RuntimeError("academic engine returned nothing")
            else:
                reader = reader_cls(path)
                pages = len(reader.pages)
                chunks = []
                for i, page in enumerate(reader.pages):
                    try:
                        chunks.append(f"\n<<<PAGE {i + 1}>>>\n" + (page.extract_text() or ""))
                    except Exception as e:  # noqa: BLE001
                        chunks.append(f"\n<<<PAGE {i + 1} ERROR {e}>>>\n")
                text = clean("\n".join(chunks))
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL {name}: {e}")
            continue

        n_pages = len(re.findall(r"<<<PAGE \d+>>>", text)) or pages
        with open(os.path.join(out, base + ".txt"), "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"  {str(n_pages):>3}p {len(text):>7}ch  {name[:58]}")
        print(f"        head: {head_of(text)}")
        ok += 1
    print(f"\nwrote {ok}/{len(pdfs)} -> {out}  [engine={engine}]")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
