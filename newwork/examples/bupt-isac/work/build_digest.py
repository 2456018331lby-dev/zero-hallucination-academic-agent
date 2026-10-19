#!/usr/bin/env python3
"""Build a compact per-paper digest from extracted PDF text."""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "pdftext")
OUT = os.path.join(HERE, "digest.md")


def squeeze(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def abstract_of(t: str) -> str:
    m = re.search(r"abstract\b[^\n]{0,40}?[—\-:]?\s*", t, re.I)
    if not m:
        return ""
    start = m.end()
    end = len(t)
    for pat in (r"\n\s*index\s+terms", r"\n\s*I\.\s*INTRODUCTION", r"\n\s*1\.\s*INTRODUCTION",
                r"\n\s*I\s+INTRODUCTION", r"\n\s*Keywords"):
        mm = re.search(pat, t[start:], re.I)
        if mm:
            end = min(end, start + mm.start())
    body = t[start:end]
    if len(body) > 2200:
        body = body[:2200]
    return squeeze(body)


def headings(t: str) -> list[str]:
    out = []
    for line in t.split("\n"):
        s = line.strip()
        if re.match(r"^([IVX]+|[0-9]+)\.\s+[A-Z][A-Za-z \-/]{3,60}$", s):
            out.append(s)
        elif re.match(r"^[A-Z]\.\s+[A-Z][A-Za-z \-/]{3,60}$", s) and len(s) < 70:
            out.append("  " + s)
    seen, dedup = set(), []
    for h in out:
        if h not in seen:
            seen.add(h)
            dedup.append(h)
    return dedup[:28]


def contribution(t: str) -> str:
    hits = []
    for m in re.finditer(r"contribution", t, re.I):
        a = max(0, m.start() - 300)
        hits.append(squeeze(t[a: m.start() + 1100]))
    if not hits:
        for m in re.finditer(r"(our|the)\s+(main\s+)?contributions?\s+(are|of this)", t, re.I):
            hits.append(squeeze(t[m.start(): m.start() + 1400]))
    return " || ".join(hits[:2])


def conclusion(t: str) -> str:
    m = None
    for pat in (r"\n\s*[IVX0-9]+\.\s*CONCLUSION", r"\n\s*CONCLUSION\b", r"\n\s*[IVX0-9]+\.\s*Conclusion"):
        m = re.search(pat, t, re.I)
        if m:
            break
    if not m:
        return ""
    return squeeze(t[m.end(): m.end() + 2200])


def main() -> None:
    files = sorted(f for f in os.listdir(SRC) if f.endswith(".txt"))
    with open(OUT, "w", encoding="utf-8") as fh:
        for f in files:
            t = open(os.path.join(SRC, f), encoding="utf-8").read()
            fh.write("\n\n" + "=" * 78 + "\n")
            fh.write(f"FILE: {f}\n")
            fh.write("=" * 78 + "\n")
            fh.write("\n[HEADER]\n" + squeeze(t[:700]) + "\n")
            fh.write("\n[ABSTRACT]\n" + abstract_of(t) + "\n")
            fh.write("\n[HEADINGS]\n" + "\n".join(headings(t)) + "\n")
            fh.write("\n[CONTRIBUTION]\n" + (contribution(t) or "(none found)") + "\n")
            fh.write("\n[CONCLUSION]\n" + (conclusion(t) or "(none found)") + "\n")
    print("wrote", OUT, os.path.getsize(OUT), "bytes")


main()
