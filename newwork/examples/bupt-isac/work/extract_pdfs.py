#!/usr/bin/env python3
"""Extract text (and first-page metadata) from the BUPT ISAC literature PDFs."""
import os
import re
import sys

# Paths are derived from this file's location so the example stays portable:
#   <newwork>/examples/bupt-isac/work/  ->  <newwork>  ->  newwork/libs/site-packages
HERE = os.path.dirname(os.path.abspath(__file__))
NW = os.path.normpath(os.path.join(HERE, "..", "..", ".."))

_LIBDIR = os.path.join(NW, "libs", "site-packages")
if os.path.isdir(_LIBDIR):  # optional vendored deps; fall back to installed packages
    sys.path.insert(0, _LIBDIR)
from pypdf import PdfReader  # noqa: E402

SRC = os.path.join(NW, "examples", "bupt-isac", "input", "literature")
OUT = os.path.join(HERE, "pdftext")
os.makedirs(OUT, exist_ok=True)


def clean(t: str) -> str:
    t = t.replace("\u00ad", "")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def main() -> None:
    pdfs = sorted(f for f in os.listdir(SRC) if f.lower().endswith(".pdf"))
    print(f"{len(pdfs)} PDFs\n")
    for name in pdfs:
        path = os.path.join(SRC, name)
        base = os.path.splitext(name)[0]
        try:
            reader = PdfReader(path)
            pages = len(reader.pages)
            chunks = []
            for i, page in enumerate(reader.pages):
                try:
                    chunks.append(f"\n<<<PAGE {i + 1}>>>\n" + (page.extract_text() or ""))
                except Exception as e:
                    chunks.append(f"\n<<<PAGE {i + 1} ERROR {e}>>>\n")
            text = clean("\n".join(chunks))
        except Exception as e:
            print(f"  FAIL {name}: {e}")
            continue
        dest = os.path.join(OUT, base + ".txt")
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(text)
        head = clean((reader.pages[0].extract_text() or ""))[:220].replace("\n", " \\ ")
        print(f"  {pages:>3}p {len(text):>7}ch  {name[:58]}")
        print(f"        head: {head}")


main()
