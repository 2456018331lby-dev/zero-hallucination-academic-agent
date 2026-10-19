#!/usr/bin/env python3
"""Verify arXiv IDs in the PDFs and pull simulation/result evidence."""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "pdftext")
OUT = os.path.join(HERE, "evidence.md")


def squeeze(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def arxiv_ids(t: str) -> list[str]:
    ids = re.findall(r"arXiv:\s*([0-9]{4}\.[0-9]{4,5})(v[0-9]+)?", t)
    out, seen = [], set()
    for a, b in ids:
        k = a + (b or "")
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def sim_section(t: str) -> str:
    """Text from the simulation-results heading to the conclusion."""
    m = None
    for pat in (r"\n\s*[IVX0-9]+\.?\s*SIMULATION\s+RESULTS", r"\n\s*[IVX0-9]+\.?\s*NUMERICAL\s+RESULTS",
                r"\n\s*[IVX0-9]+\.?\s*Simulation\s+Results", r"\n\s*[IVX0-9]+\.?\s*EXPERIMENT"):
        m = re.search(pat, t, re.I)
        if m:
            break
    if not m:
        return "(no simulation section heading found)"
    tail = t[m.end():]
    end = re.search(r"\n\s*[IVX0-9]+\.?\s*(CONCLUSION|C ONCLUSION)", tail, re.I)
    body = tail[: end.start()] if end else tail[:14000]
    return squeeze(body)[:9000]


def numbers(t: str) -> list[str]:
    """Sentences carrying quantitative claims."""
    sents = re.split(r"(?<=[.!?])\s+", t)
    keep = []
    key = re.compile(r"(\d+(\.\d+)?\s*(dB|%|dBm|MHz|GHz|m/s|ms|bits|bps|times|×)|outperform|improv|gain of|"
                     r"reduc\w+ by|increase\w* by|exceed\w*|superior to|compared (with|to) (the )?benchmark)", re.I)
    for s in sents:
        s = squeeze(s)
        if 40 < len(s) < 400 and key.search(s):
            keep.append(s)
    return keep[:14]


def main() -> None:
    files = sorted(f for f in os.listdir(SRC) if f.endswith(".txt"))
    with open(OUT, "w", encoding="utf-8") as fh:
        for f in files:
            t = open(os.path.join(SRC, f), encoding="utf-8").read()
            fh.write("\n\n" + "#" * 78 + "\n" + f"FILE: {f}\n" + "#" * 78 + "\n")
            fh.write("\n[ARXIV IDS IN PDF]\n" + (", ".join(arxiv_ids(t)) or "(none)") + "\n")
            fh.write("\n[WEBSITE / VENUE CLUES]\n")
            for pat in (r"arXiv:\s*[0-9]{4}\.[0-9]{4,5}v?[0-9]*\s*\[[a-z.]+\]\s*[0-9]{1,2}\s+[A-Z][a-z]{2}\s+[0-9]{4}",
                        r"(?:submitted to|to appear in|accepted (?:by|for)|published in|©\s*20\d\d\s*IEEE)[^.]{0,120}"):
                for mm in list(re.finditer(pat, t))[:4]:
                    fh.write("  - " + squeeze(mm.group(0))[:160] + "\n")
            fh.write("\n[SIMULATION / EXPERIMENT SECTION]\n" + sim_section(t) + "\n")
            fh.write("\n[QUANTITATIVE CLAIMS]\n")
            for s in numbers(t):
                fh.write("  * " + s + "\n")
    print("wrote", OUT, os.path.getsize(OUT), "bytes")


main()
