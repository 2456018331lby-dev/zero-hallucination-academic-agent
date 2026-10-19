#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_grounding.py - hard grounding gate for the literature-review pipeline.

Ported from `.agents/skills/phd-literature-survey/scripts/verify_grounding.py`
(the PyMuPDF physical page-range gate) and extended with a **table mode** that
matches this skill's pipeline, where the single source of truth is
`literature_table.json` and the extracted text lives in `_pdftext/*.txt`.

Why a second mode: the original gate proved that an *evidence* cell points at a
real page. This pipeline has no evidence column — instead it makes far more
aggressive claims per row (`results`, `setup`). So the table mode checks the one
thing that actually goes wrong: **a number in the table that is nowhere in the
paper**.

Two modes
---------
A. table mode (default for this skill; stdlib only)

    python verify_grounding.py --table-json literature_table.json \\
                               --pdftext _pdftext

   For every paper it locates the extracted `.txt` via the JSON `file` field and
   then:

     * `title`   -> >=60% of significant title tokens must appear on pages 1-2
     * `venue`   -> any arXiv id / DOI in the cell must appear in the text
     * `results` -> every quantitative token (percent, value+unit, high-precision
                    decimal, integer >= 100) must appear in the text
     * `setup`   -> same quantitative check

   Matching is whitespace-insensitive and normalises full-width forms and the
   whole dash family (-, -, -, -, -). A range token that fails is retried as its
   two endpoints, so "1.4-77 GHz" also passes when the paper writes
   "1.4 GHz to 77 GHz".

   FAILs if a title, an arXiv id, or a claimed number cannot be located.

B. matrix mode (backward compatible; requires PyMuPDF)

    python verify_grounding.py survey/literature_comparison_matrix.md \\
                               --literature-dir literature

   Physical page-range validation: opens each PDF with PyMuPDF and fails if the
   cited page range falls outside the real page count, or if the cited pages do
   not contain the paper's own text.

Exit code: 0 = gate passed, 1 = gate failed.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import sys
import unicodedata

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# PyMuPDF is only needed by matrix mode. It is loaded lazily so `--libs` can be
# applied first (this project keeps every dependency in an isolated --target dir
# that is never on sys.path by default). PyMuPDF renamed its module: prefer
# `pymupdf`, keep `fitz` for older installs.
fitz = None
HAS_PYMUPDF = False


def load_pymupdf(libs: str | None = None) -> bool:
    global fitz, HAS_PYMUPDF
    if libs:
        sys.path.insert(0, libs)
    if HAS_PYMUPDF:
        return True
    for mod in ("pymupdf", "fitz"):
        try:
            fitz = importlib.import_module(mod)
            HAS_PYMUPDF = True
            return True
        except ImportError:
            continue
    return False

RULE = "=" * 75

# ---------------------------------------------------------------- normalising

_DASHES = "\u2010\u2011\u2012\u2013\u2014\u2015\u2212\u2043\ufe58\ufe63\uff0d"


def norm(s: str, keep_hyphen: bool = True) -> str:
    """NFKC + unify dashes + drop ALL whitespace, so PDF spacing stops mattering.

    Also drops thousands separators that sit between digits: PDF extraction
    happily produces "10, 000" where the table says "10000", and both must
    normalise to the same string.
    """
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub("[" + _DASHES + "]", "-", s)
    s = re.sub(r"[\s\u00ad]+", "", s)
    s = re.sub(r"(?<=\d)[,，](?=\d)", "", s)
    if not keep_hyphen:
        s = s.replace("-", "")
    return s.lower()


def text_norm(s: str) -> str:
    """Hyphen-stripped form, to survive line-wrap hyphenation in two-column PDFs."""
    return norm(s, keep_hyphen=False)


STOP_WORDS = {
    "with", "from", "that", "this", "these", "those", "their", "there", "which",
    "using", "based", "aided", "assisted", "towards", "paper", "study", "design",
    "network", "system", "systems", "approach", "toward", "analysis", "review",
    "survey", "based", "under", "over", "into", "also", "such", "more", "most",
}

# quantitative tokens -----------------------------------------------------------

_UNITS = (r"dBm|dB|GHz|MHz|kHz|Hz|Gbps|Mbps|kbps|bps|cm|mm|km|ms|us|µs|ns|"
          r"kg|km/h|m/s|bit|bits|times|-fold")
_QTY = re.compile(
    r"(?<![\d.])"
    r"(\d+(?:\.\d+)?(?:\s*[" + _DASHES + r"-]\s*\d+(?:\.\d+)?)?)"
    r"\s*(%|" + _UNITS + r")(?![a-zA-Z])",
    re.I,
)
_DEC = re.compile(r"(?<![\d.])(\d+\.\d{2,})(?![\d])")
_BIG = re.compile(r"(?<![\d.])(\d{3,})(?![\d.])")

_ARXIV = re.compile(r"arXiv[:\s]*([0-9]{4}\.[0-9]{4,5})", re.I)
_DOI = re.compile(r"\b(10\.\d{4,9}/[^\s,;)）】]+)", re.I)


def quantities(field_text: str) -> list[str]:
    """Pull the distinctive quantitative claims out of one table cell."""
    out: list[str] = []
    if not field_text:
        return out
    for m in _QTY.finditer(field_text):
        out.append(m.group(1) + m.group(2))
    for m in _DEC.finditer(field_text):
        out.append(m.group(1))
    for m in _BIG.finditer(field_text):
        out.append(m.group(1))
    seen, uniq = set(), []
    for t in out:
        k = norm(t)
        if k not in seen:
            seen.add(k)
            uniq.append(t)
    return uniq


def locate_quantity(tok: str, flat: str, flat_w: str) -> bool:
    """Is this quantitative token physically present in the paper text?

    `flat` keeps hyphens, `flat_w` strips them, so "6bit" still matches a paper
    that writes "6-bit". A range whose exact spelling is absent is retried as
    its two endpoints within a short window, so "0-100km" still matches
    "distributed between 0 and 100 km/h".
    """
    needle = norm(tok)
    if needle in flat or text_norm(tok) in flat_w:
        return True

    parts = [p for p in re.split(r"-", needle) if p]
    if len(parts) == 2 and any(c.isdigit() for c in parts[0]) \
            and any(c.isdigit() for c in parts[1]):
        return locate_range(parts[0], parts[1], flat_w)
    return False


def locate_range(a: str, b: str, flat_w: str, window: int = 80) -> bool:
    """Both endpoints, each not glued to a longer number, close to each other."""
    def hits(needle: str):
        return [m.start() for m in
                re.finditer(r"(?<!\d)" + re.escape(needle) + r"(?!\d)", flat_w)]

    left, right = hits(a), hits(b)
    if not left or not right:
        return False
    return any(abs(i - j) <= window for i in left for j in right)


def split_pages(txt: str) -> list[str]:
    """Split an extract_pdfs.py output file on <<<PAGE n>>> markers."""
    if "<<<PAGE" not in txt:
        return [txt]
    return re.split(r"<<<PAGE\s+\d+(?:\s+ERROR[^>]*)?>>>", txt)


# ---------------------------------------------------------------- table mode

def verify_table(json_path: str, pdftext_dir: str, min_title_ratio: float = 0.60) -> bool:
    json_path = os.path.abspath(json_path)
    pdftext_dir = os.path.abspath(pdftext_dir)

    print(RULE)
    print("[*] Grounding Gate - table mode (literature_table.json vs extracted text)")
    print(f"[*] Table JSON : {json_path}")
    print(f"[*] PDF text   : {pdftext_dir}")
    print("[*] Engine     : stdlib (whitespace-insensitive numeric grounding)")
    print(RULE)

    if not os.path.isfile(json_path):
        print(f"[-] table json not found: {json_path}", file=sys.stderr)
        return False
    if not os.path.isdir(pdftext_dir):
        print(f"[-] pdftext dir not found: {pdftext_dir}", file=sys.stderr)
        return False

    with open(json_path, encoding="utf-8") as fh:
        data = json.load(fh)
    papers = data.get("papers") or data.get("items") or []
    if not papers:
        print("[-] no 'papers' array in the json", file=sys.stderr)
        return False

    txts = {os.path.splitext(f)[0]: os.path.join(pdftext_dir, f)
            for f in os.listdir(pdftext_dir) if f.lower().endswith(".txt")}
    print(f"[+] {len(papers)} papers in table, {len(txts)} extracted .txt files\n")

    failures: list[str] = []
    warnings: list[str] = []
    passed = 0

    for p in papers:
        pid = p.get("id", "?")
        pid_s = f"[{pid}]" if not str(pid).startswith("[") else str(pid)
        title = str(p.get("title", ""))

        src = str(p.get("file", "") or "")
        stem = os.path.splitext(os.path.basename(src))[0]
        path = txts.get(stem)
        if path is None:
            cand = [k for k in txts if norm(k) == norm(stem)]
            if not cand:
                cand = [k for k in txts if norm(stem) and norm(stem) in norm(k)]
            if cand:
                path = txts[cand[0]]
        if path is None:
            failures.append(f"{pid_s} [{title[:42]}]: no extracted text for "
                            f"file='{src}'")
            continue

        with open(path, encoding="utf-8", errors="ignore") as fh:
            raw = fh.read()
        pages = split_pages(raw)
        flat = norm(raw)
        flat_w = text_norm(raw)

        local: list[str] = []

        # (1) title must be locatable on the first two pages
        toks = [t for t in re.findall(r"[A-Za-z]{4,}", title)
                if t.lower() not in STOP_WORDS]
        if toks:
            front_w = text_norm(" ".join(pages[:2]))
            hit = [t for t in toks if t.lower() in front_w]
            ratio = len(hit) / len(toks)
            if ratio < min_title_ratio:
                local.append(f"title only {ratio:.0%} matched on pages 1-2 "
                             f"({len(hit)}/{len(toks)}: missing "
                             f"{[t for t in toks if t.lower() not in front_w][:6]})")
        else:
            warnings.append(f"{pid_s}: title has no significant tokens to check")

        # (2) venue identifiers must physically exist
        venue = str(p.get("venue", ""))
        for m in _ARXIV.finditer(venue):
            if norm(m.group(1)) not in flat:
                local.append(f"arXiv id {m.group(1)} from venue not found in text")
        for m in _DOI.finditer(venue):
            if norm(m.group(1)).rstrip(".") not in flat:
                local.append(f"DOI {m.group(1)} from venue not found in text")

        # (3) every quantitative claim in results / setup must be locatable
        for field in ("results", "setup"):
            for tok in quantities(str(p.get(field, ""))):
                if not locate_quantity(tok, flat, flat_w):
                    local.append(f"{field}: '{tok}' not found in text")

        if local:
            for msg in local:
                failures.append(f"{pid_s} [{title[:42]}]: {msg}")
        else:
            n = len(quantities(str(p.get("results", "")))) + \
                len(quantities(str(p.get("setup", ""))))
            print(f"  [PASS] {pid_s:<5} {stem[:48]:<50} {n} quantitative claim(s) grounded")
            passed += 1

    print("\n" + RULE)
    print(f"[*] Summary: {passed}/{len(papers)} papers fully grounded, "
          f"{len(failures)} FAILURES, {len(warnings)} WARNINGS.")
    for f in failures:
        print(f"  [FAIL] {f}")
    for w in warnings:
        print(f"  [WARN] {w}")
    print(RULE)

    if failures:
        print("\n[-] Grounding Gate FAILED: at least one claim has no source.",
              file=sys.stderr)
        return False
    print("\n[OK] Grounding Gate PASSED: every title, venue id and quantitative "
          "claim is physically present in the local PDF text.")
    return True


# --------------------------------------------------------------- matrix mode

def extract_keywords(text: str) -> list[str]:
    stop = STOP_WORDS | {"their", "there", "these", "those"}
    return [t for t in re.findall(r"[a-zA-Z]{4,}", text.lower()) if t not in stop]


def parse_page_range(evidence_str: str, max_pages=None):
    m = re.search(r"(?:pp?\.|pages?|页码?)\s*(\d+)(?:\s*[-–—~至到]\s*(\d+))?",
                  evidence_str, re.I)
    if m:
        sp = int(m.group(1))
        return sp, int(m.group(2)) if m.group(2) else sp
    m2 = re.search(r"\b(\d+)\s*[-–—~至到]\s*(\d+)\b", evidence_str)
    if m2:
        return int(m2.group(1)), int(m2.group(2))
    m3 = re.search(r"\b(\d+)\b", evidence_str)
    if m3:
        return int(m3.group(1)), int(m3.group(1))
    return None, None


def verify_matrix(matrix_path: str, literature_dir: str, libs: str | None = None) -> bool:
    matrix_path = os.path.abspath(matrix_path)
    literature_dir = os.path.abspath(literature_dir)

    print(RULE)
    print("[*] Grounding Gate - matrix mode (physical page-range verification)")
    print(f"[*] Matrix File    : {matrix_path}")
    print(f"[*] Literature Pool: {literature_dir}")
    print(f"[*] Engine         : PyMuPDF (fitz)")
    print(RULE)

    if not os.path.exists(matrix_path):
        print(f"[-] matrix file not found: {matrix_path}", file=sys.stderr)
        return False
    if not os.path.exists(literature_dir):
        print(f"[-] literature dir not found: {literature_dir}", file=sys.stderr)
        return False
    if not load_pymupdf(libs):
        print("[-] PyMuPDF is required for matrix mode.", file=sys.stderr)
        print("    pip install --target <LIBDIR> pymupdf", file=sys.stderr)
        print("    then re-run with --libs <LIBDIR>", file=sys.stderr)
        return False

    local_pdfs = [f for f in os.listdir(literature_dir) if f.lower().endswith(".pdf")]
    local_pdfs_norm = {re.sub(r"[^a-zA-Z0-9]", "", f.lower()): f for f in local_pdfs}
    print(f"[+] {len(local_pdfs)} local PDFs in pool.")

    with open(matrix_path, encoding="utf-8", errors="ignore") as fp:
        lines = fp.readlines()

    rows, header, in_table = [], [], False
    for line in lines:
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if not cells or all(c == "" for c in cells):
                continue
            if re.match(r"^:?-+:?$", cells[0]):
                continue
            if not in_table:
                in_table, header = True, [c.lower() for c in cells]
            else:
                rows.append(cells)
        elif in_table:
            in_table = False

    failures, warnings, verified = [], [], []
    if rows and header:
        print(f"[+] table detected: {len(rows)} rows x {len(header)} cols.")
        title_idx = evidence_idx = -1
        for i, col in enumerate(header):
            if any(k in col for k in ("论文", "题目", "title")):
                title_idx = i
            if any(k in col for k in ("evidence", "证据", "出处", "本地文件")):
                evidence_idx = i
        if title_idx < 0:
            failures.append("could not identify the 'paper title' column")

        for r_idx, row in enumerate(rows, start=1):
            if title_idx >= len(row):
                continue
            title = row[title_idx].replace("**", "").strip()
            if not title:
                continue
            ev = row[evidence_idx].strip() if 0 <= evidence_idx < len(row) else ""
            if not ev:
                failures.append(f"row {r_idx} [{title[:35]}]: missing 'evidence' field")
                continue
            if ev == "文献未说明":
                verified.append((r_idx, title[:30], "declared unstated", "PASS"))
                continue

            matched = next((f for f in local_pdfs
                            if f in ev or f.lower() in ev.lower()), None)
            if not matched:
                tc = re.sub(r"[^a-zA-Z0-9]", "", title.lower())
                for nk, raw in local_pdfs_norm.items():
                    if nk and (nk in tc or tc in nk):
                        matched = raw
                        break
            if not matched:
                failures.append(f"row {r_idx} [{title[:35]}]: no PDF for evidence "
                                f"'{ev}'")
                continue

            try:
                doc = fitz.open(os.path.join(literature_dir, matched))
            except Exception as e:  # noqa: BLE001
                failures.append(f"row {r_idx} [{title[:35]}]: cannot open "
                                f"'{matched}': {e}")
                continue

            total = len(doc)
            sp, ep = parse_page_range(ev, total)
            if sp is None:
                warnings.append(f"row {r_idx} [{title[:35]}]: evidence '{ev}' has no "
                                f"page range; sampling pp.1-{min(total, 5)}")
                sp, ep = 1, min(total, 5)
            if sp < 1 or ep > total or sp > ep:
                failures.append(f"row {r_idx} [{title[:35]}]: claims pp.{sp}-{ep} but "
                                f"'{matched}' has {total} pages "
                                f"(physical grounding violation)")
                continue

            page_text = " ".join(doc[i].get_text("text") for i in range(sp - 1, ep)).lower()
            cand = list(set(extract_keywords(title) +
                            [t for t in extract_keywords(" ".join(row)) if len(t) >= 5]))
            hit = [t for t in cand if t in page_text]
            ratio = len(hit) / len(cand) if cand else 0
            if len(hit) >= 2 or ratio >= 0.25:
                verified.append((r_idx, matched, f"pp.{sp}-{ep} of {total}",
                                 f"{len(hit)} tokens"))
            else:
                p1 = doc[0].get_text("text").lower()
                if len([t for t in extract_keywords(title) if t in p1]) >= 2:
                    failures.append(f"row {r_idx} [{title[:35]}]: PDF matches the paper "
                                    f"but pages pp.{sp}-{ep} lack its content")
                else:
                    failures.append(f"row {r_idx} [{title[:35]}]: '{matched}' does not "
                                    f"match this title at all")
    else:
        failures.append("matrix file has no recognizable table (add the 'evidence' "
                        "column) - or use --table-json mode")

    print(f"\n[*] {len(verified)} verified")
    for r_idx, fn, pr, info in verified:
        print(f"    [PASS] row {r_idx}: {str(fn)[:38]} | {pr} | {info}")
    print("-" * 75)
    print(f"[*] Summary: {len(failures)} FAILURES, {len(warnings)} WARNINGS.")
    for f in failures:
        print(f"  [FAIL] {f}")
    for w in warnings:
        print(f"  [WARN] {w}")
    print(RULE)
    if failures:
        print("\n[-] Grounding Gate FAILED.", file=sys.stderr)
        return False
    print("\n[OK] Grounding Gate PASSED.")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Grounding gate: table mode (json + extracted text) or "
                    "matrix mode (markdown + physical PDF pages).")
    ap.add_argument("matrix_file", nargs="?",
                    default="survey/literature_comparison_matrix.md",
                    help="matrix markdown (matrix mode)")
    ap.add_argument("--table-json", default=None,
                    help="literature_table.json (table mode)")
    ap.add_argument("--pdftext", default="_pdftext",
                    help="folder of extracted .txt files (table mode)")
    ap.add_argument("--literature-dir", "--pdf-dir", dest="literature_dir",
                    default="literature", help="local PDF pool (matrix mode)")
    ap.add_argument("--libs", default=None,
                    help="optional extra sys.path for isolated deps (PyMuPDF)")
    ap.add_argument("--min-title-ratio", type=float, default=0.60)
    args = ap.parse_args()

    if args.table_json:
        ok = verify_table(args.table_json, args.pdftext, args.min_title_ratio)
    else:
        ok = verify_matrix(args.matrix_file, args.literature_dir, args.libs)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

# --- Backward-compatible alias -------------------------------------------------
# Older callers (tests/test_gates.py, skill docs) use the pre-merge name and
# signature: verify_grounding(matrix_path, literature_dir) -> bool
verify_grounding = verify_matrix
