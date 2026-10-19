"""Literature intake: PDF folder -> verifiable reading cards -> survey skeleton.

This is the "老师给了一堆 PDF，帮我读完做总结" layer. It deliberately stops at
the point where judgement begins:

* It extracts what is *on the page* (title, venue, year, DOI/arXiv, abstract,
  section headings, numbers) and records the page number for every field.
* It never writes "该文提出了一种创新方法" — that sentence is your job.
* The comparison matrix ships with the four judgement columns left blank, and
  ``gaps.md`` says exactly which cells are still empty.

Anything the PDF does not state is written as ``文献未说明`` — never guessed.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ._util import now_iso, write_json, write_text

# --------------------------------------------------------------------------- #
# PDF text access
# --------------------------------------------------------------------------- #
def _open_pdf(path: Path):
    try:
        import pymupdf as fitz  # noqa: PLC0415
    except ImportError:  # pragma: no cover
        try:
            import fitz  # noqa: PLC0415
        except ImportError:
            raise SystemExit(
                "pymupdf is required: py -3.12 -m pip install pymupdf"
            ) from None
    return fitz.open(str(path))


def _pages(path: Path) -> list[tuple[int, str]]:
    doc = _open_pdf(path)
    try:
        return [(i + 1, doc[i].get_text("text") or "") for i in range(doc.page_count)]
    finally:
        doc.close()


def _page_count(path: Path) -> int:
    doc = _open_pdf(path)
    try:
        return doc.page_count
    finally:
        doc.close()


# --------------------------------------------------------------------------- #
# Field extraction (regex only — no model, no guessing)
# --------------------------------------------------------------------------- #
_DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b")
_ARXIV_RE = re.compile(r"arXiv:\s*(\d{4}\.\d{4,5}(?:v\d+)?)", re.I)
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
_VENUE_HINTS = (
    "IEEE Transactions",
    "IEEE Journal",
    "IEEE Communications",
    "IEEE Wireless",
    "IEEE Vehicular",
    "IEEE Internet of Things",
    "IEEE Network",
    "IEEE Access",
    "IEEE Sensors",
    "Proceedings of",
    "Conference on",
    "Symposium",
    "Workshop",
    "ACM",
    "Springer",
    "Elsevier",
    "arXiv preprint",
)
_NUM_RE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(dB|dBm|bps/Hz|bit/s/Hz|%|倍|km|m/s|MHz|GHz)", re.I)
_LIMIT_WORDS = ("however", "limitation", "future work", "remains", "challenge", "yet")
_SELF_LIMIT_WORDS = (
    "left for future",
    "future work",
    "future research",
    "beyond the scope",
    "we leave",
    "not considered",
    "not addressed",
    "remains an open",
    "open problem",
    "limitation of",
    "our limitation",
)
_META_SENTENCE_RE = re.compile(
    r"^(?:In (?:this|the) (?:section|paper|article)|In Section|Section\s+[IVXLC0-9]|"
    r"This (?:paper|article|section|work)|Finally, we (?:outline|summarize|conclude)|"
    r"The (?:paper|article|remainder) (?:is|are)|We (?:outline|summarize|conclude)\b)",
    re.IGNORECASE,
)
_TRAILING_STOPWORDS = (
    " on",
    " of",
    " for",
    " and",
    " the",
    " with",
    " to",
    " in",
    " by",
    " from",
    " under",
    " over",
    " based",
    " via",
    " a",
    " an",
    " at",
)
_BODY_WORDS = frozenset(
    {
        "evaluate",
        "evaluated",
        "achieve",
        "achieved",
        "obtain",
        "obtained",
        "consider",
        "considered",
        "denote",
        "denoted",
        "show",
        "shows",
        "shown",
        "respectively",
        "whereas",
        "assume",
        "assumed",
        "define",
        "defined",
        "represent",
        "represents",
        "correspond",
        "corresponds",
        "measured",
        "computed",
        "derived",
        "applied",
        "based",
        "proposed",
        "investigate",
        "investigated",
        "demonstrate",
        "demonstrated",
    }
)
_SINGLE_WORD_HEADINGS = frozenset(
    {"abstract", "introduction", "references", "conclusion", "conclusions", "appendix", "summary"}
)

_GENERIC_TITLES = (
    "untitled",
    "no title",
    "microsoft word",
    "document",
    "pdf",
    "title",
    "manuscript",
    "main",
)

# Headings that are safe to treat as section boundaries even without a number.
_HEADING_WORDS = (
    "abstract",
    "index terms",
    "introduction",
    "related work",
    "literature review",
    "background",
    "motivation",
    "contributions",
    "preliminaries",
    "system model",
    "signal model",
    "problem formulation",
    "proposed",
    "method",
    "algorithm",
    "performance analysis",
    "simulation",
    "numerical results",
    "results",
    "discussion",
    "experimental",
    "evaluation",
    "conclusion",
    "summary",
    "future work",
    "references",
    "appendix",
)
_HEADING_NUM_RE = re.compile(r"^(?:\d+(?:\.\d+)*|[IVXLC]+)[.)]?\s+\S")
_STOPWORDS = frozenset(
    {
        "of",
        "for",
        "and",
        "the",
        "in",
        "on",
        "with",
        "to",
        "a",
        "an",
        "via",
        "under",
        "over",
        "from",
        "by",
        "using",
        "based",
        "toward",
        "towards",
    }
)


def _first_page_lines(pages: list[tuple[int, str]], n: int = 40) -> list[str]:
    if not pages:
        return []
    text = pages[0][1]
    lines = [ln.strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln][:n]


def _guess_title(pdf: Path, lines: list[str]) -> tuple[str, int]:
    """Title: trust the PDF metadata first, fall back to the biggest early line.

    Real-world lesson: the flattened text of a two-column paper starts with the
    *abstract* tail on some pages, and the biggest font is often a decorative
    drop-cap (``T``, ``R``).  PDF metadata (set by arXiv/IEEE) is far more
    reliable, so it wins whenever it is present and not a placeholder.
    """
    meta = _metadata_title(pdf)
    if meta:
        return meta, 1

    best, best_idx = "", 1
    for idx, line in enumerate(lines[:15], 1):
        clean = line.strip()
        if len(clean) < 12 or len(clean) > 200:
            continue
        if clean.lower().startswith(("abstract", "arxiv", "ieee", "doi", "http", "keywords", "index terms")):
            continue
        # a wrapped line is not a title
        if clean.endswith(("-", ",", ";", "and", "of", "the", "for")):
            continue
        if clean[0].islower():
            continue
        if len(clean) > len(best):
            best, best_idx = clean, idx
    return (best or "文献未说明"), best_idx


def _metadata_title(pdf: Path) -> str:
    try:
        doc = _open_pdf(pdf)
        try:
            raw = ((doc.metadata or {}).get("title") or "").strip()
        finally:
            doc.close()
    except Exception:  # noqa: BLE001 — metadata is a bonus, never a hard failure
        return ""
    if not raw or len(raw) < 8 or len(raw) > 300:
        return ""
    low = raw.lower()
    if low in _GENERIC_TITLES or low.startswith("untitled"):
        return ""
    if low == pdf.stem.lower():
        return ""
    if re.search(r"\.(?:tex|dvi|docx?|pdf|indd)$", raw, re.I):
        return ""
    return re.sub(r"\s+", " ", raw)



def _guess_venue(pages: list[tuple[int, str]]) -> tuple[str, int]:
    for page_no, text in pages[:2]:
        for line in text.splitlines():
            line = line.strip()
            if any(h.lower() in line.lower() for h in _VENUE_HINTS):
                return line[:160], page_no
    return "文献未说明", 0


def _guess_year(pages: list[tuple[int, str]]) -> tuple[str, int]:
    for page_no, text in pages[:2]:
        years = [m.group(0) for m in _YEAR_RE.finditer(text)]
        if years:
            # prefer the largest plausible year (avoids "19" style noise)
            return max(years), page_no
    return "文献未说明", 0


def _guess_abstract(pages: list[tuple[int, str]]) -> tuple[str, int]:
    for page_no, text in pages[:2]:
        low = text.lower()
        idx = low.find("abstract")
        if idx < 0:
            continue
        chunk = text[idx + len("abstract") : idx + 1800]
        chunk = re.split(r"\b(?:index terms|keywords|i\.\s*introduction|1\.\s*introduction)\b", chunk, flags=re.I)[0]
        chunk = re.sub(r"\s+", " ", chunk).strip(" :.—-")
        if len(chunk) > 40:
            return chunk[:1200], page_no
    return "文献未说明", 0


def _heading_ok(rest: str) -> bool:
    """A heading's tail is Title Case-ish, short, and has no sentence break.

    Rejects body lines that merely begin with a numeral or a Roman numeral:
    ``18) of 5G-Advanced in 2024, the global evolution of wireless``,
    ``V concludes the article. To the authors' knowledge, this is the``,
    ``3) Sensing Performance Metric: To evaluate the sensing``, ``1 +``,
    ``0.1 W``, ``20 MHz``.
    """
    rest = rest.strip()
    if len(rest) < 4 or len(rest) > 70:
        return False
    if not any(c.isalpha() for c in rest):
        return False
    if ". " in rest or rest.endswith("."):
        return False
    if rest.lower().endswith(_TRAILING_STOPWORDS):
        return False
    if re.search(r":\s+(?:The|A|An|This|These|We|It|In|To)\b", rest):
        return False
    words = rest.split()
    if len(words) > 10:
        return False
    low_words = [w for w in words if w[:1].islower()]
    if any(w.lower().strip(",.;:") in _BODY_WORDS for w in low_words):
        return False
    cap = sum(1 for w in words if w[:1].isupper() or w[:1].isdigit())
    low = sum(1 for w in low_words if w.lower() not in _STOPWORDS)
    return low == 0 or cap >= low * 2


def _guess_sections(pages: list[tuple[int, str]]) -> list[dict]:
    """Real section headings only — a wrapped body line is not a heading.

    Old behaviour accepted any line that *started with* a heading word after
    stripping digits, so ``Abstract—The dense concentration of ...`` and
    ``algorithms suffer from cumulative spatiotemporal registra-`` both slipped
    in.  Now a heading must either carry a number (``I.``/``2.3``) or be a short
    standalone line that *is* the heading, with no em-dash continuation and no
    trailing hyphen; and its tail must pass :func:`_heading_ok`.
    """
    found: list[dict] = []
    seen: list[str] = []
    for page_no, text in pages:
        for raw in text.splitlines():
            line = raw.strip()
            if not (3 <= len(line) <= 90):
                continue
            if line.endswith(("-", ",", ";", ":")) or "—" in line:
                continue
            low = line.lower()
            if _HEADING_NUM_RE.match(line):
                rest = re.sub(r"^(?:\d+(?:\.\d+)*|[IVXLC]+)[.)]?\s*", "", line)
                if not _heading_ok(rest):
                    continue
            else:
                bare = low.lstrip("0123456789. ")
                if not any(bare.startswith(h) for h in _HEADING_WORDS):
                    continue
                if len(line.split()) == 1 and low not in _SINGLE_WORD_HEADINGS:
                    continue
                if not _heading_ok(line):
                    continue
            key = re.sub(r"^[\dIVXLC.\s]+", "", low)[:40].strip()
            if not key:
                continue
            if any(key.startswith(k) or k.startswith(key) for k in seen):
                continue
            seen.append(key)
            found.append({"heading": line[:90], "page": page_no})
    return found


def _guess_numbers(pages: list[tuple[int, str]]) -> list[dict]:
    out: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for page_no, text in pages:
        for m in _NUM_RE.finditer(text):
            key = (m.group(1), m.group(2).lower())
            if key in seen:
                continue
            seen.add(key)
            out.append({"value": m.group(1), "unit": m.group(2), "page": page_no})
            if len(out) >= 12:
                return out
    return out


def _sentences(flat: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", flat) if s.strip()]


def _guess_limitations(pages: list[tuple[int, str]]) -> list[dict]:
    """What the paper itself admits it does *not* do.

    Old behaviour matched a cue word anywhere in a ±200-char window, so a
    sentence merely *citing* prior work (``[8] introduced a hybrid ... however
    ...``) was reported as this paper's own limitation.  Now:
      1. prefer the Limitations / Future Work / Conclusion section verbatim;
      2. otherwise accept only sentences that *start* with a cue phrase.
    """
    out: list[dict] = []
    seen: set[str] = set()

    def push(text: str, page_no: int) -> bool:
        text = re.sub(r"\s+", " ", text).strip(" .,")
        if not (40 <= len(text) <= 320):
            return False
        if not (text[:1].isupper() or text[:1].isdigit()):
            return False  # a mid-sentence fragment is not a citable admission
        if _META_SENTENCE_RE.match(text):
            return False  # "Section IV discusses ..." describes the paper, not a gap
        key = text[:60].lower()
        if key in seen:
            return False
        seen.add(key)
        out.append({"text": text[:300], "page": page_no})
        return len(out) >= 4

    def heading_line_ok(text: str, start: int, end: int) -> bool:
        """The match must sit on a real heading line, not in running prose."""
        line_start = text.rfind("\n", 0, start) + 1
        line_end = text.find("\n", end)
        line = text[line_start : line_end if line_end != -1 else len(text)].strip()
        if len(line) > 90 or ". " in line:
            return False
        return _heading_ok(re.sub(r"^(?:\d+(?:\.\d+)*|[IVXLC]+)[.)]?\s*", "", line))

    # 1a) section-scoped: a real Limitations / Future Work / Open Problems heading
    strict_re = re.compile(
        r"(?im)^\s*(?:\d+(?:\.\d+)*|[IVXLC]+)?[.)]?\s*(limitations?|future work|open problems?|challenges?)\b"
    )
    for page_no, text in pages:
        for m in strict_re.finditer(text):
            if not heading_line_ok(text, m.start(), m.end()):
                continue
            tail = text[m.end() : m.end() + 1200]
            for sent in _sentences(re.sub(r"\s+", " ", tail)):
                if sent.startswith("[") or "arXiv:" in sent:
                    continue  # a reference entry is not a limitation
                if push(sent, page_no):
                    return out
            if out:
                return out[:4]

    # 1b) Conclusion is a *fallback*: only sentences that actually admit a gap,
    #     otherwise a contribution summary would be misreported as a limitation.
    conclusion_re = re.compile(r"(?im)^\s*(?:\d+(?:\.\d+)*|[IVXLC]+)?[.)]?\s*conclusions?\b")
    for page_no, text in pages:
        for m in conclusion_re.finditer(text):
            if not heading_line_ok(text, m.start(), m.end()):
                continue
            tail = text[m.end() : m.end() + 1500]
            for sent in _sentences(re.sub(r"\s+", " ", tail)):
                if sent.startswith("[") or "arXiv:" in sent:
                    continue
                low = sent.lower()
                if not any(w in low for w in _LIMIT_WORDS):
                    continue
                if push(sent, page_no):
                    return out
            if out:
                return out[:4]

    # 2) fallback: only *self-admissions* ("left for future work", "beyond the
    #    scope").  A bare "However, ..." is a critique of prior work, not this
    #    paper's own limitation, so it is deliberately NOT accepted here — the
    #    honest answer is 「文献未说明」 rather than a plausible-looking sentence.
    for page_no, text in pages:
        for sent in _sentences(re.sub(r"\s+", " ", text)):
            if sent.startswith("[") or "arXiv:" in sent:
                continue
            low = sent.lower()
            if not any(w in low for w in _SELF_LIMIT_WORDS):
                continue
            if low.startswith(("however", "but", "yet", "although")):
                continue
            if push(sent, page_no):
                return out
    return out


# --------------------------------------------------------------------------- #
# Card
# --------------------------------------------------------------------------- #
def extract_one(pdf: Path) -> dict:
    pages = _pages(pdf)
    lines = _first_page_lines(pages)
    title, title_pg = _guess_title(pdf, lines)
    arxiv = next((m.group(1) for _, t in pages[:2] for m in _ARXIV_RE.finditer(t)), "文献未说明")
    doi = next((m.group(0).rstrip(".,;)") for _, t in pages[:2] for m in _DOI_RE.finditer(t)), "文献未说明")
    venue, venue_pg = _guess_venue(pages)
    if venue == "文献未说明" and arxiv != "文献未说明":
        # honest label: an arXiv preprint is a venue, "not stated" is not
        venue, venue_pg = "arXiv preprint", 1
    year, year_pg = _guess_year(pages)
    abstract, abs_pg = _guess_abstract(pages)
    return {
        "file": pdf.name,
        "pages": len(pages),
        "title": {"value": title, "page": title_pg},
        "venue": {"value": venue, "page": venue_pg},
        "year": {"value": year, "page": year_pg},
        "doi": {"value": doi, "page": 1 if doi != "文献未说明" else 0},
        "arxiv": {"value": arxiv, "page": 1 if arxiv != "文献未说明" else 0},
        "abstract": {"value": abstract, "page": abs_pg},
        "sections": _guess_sections(pages),
        "numbers": _guess_numbers(pages),
        "limitations": _guess_limitations(pages),
    }


def _card_md(card: dict, idx: int) -> str:
    def ev(field: str) -> str:
        d = card[field]
        return f"（p.{d['page']}）" if d["page"] else ""

    lines = [
        f"# [{idx:02d}] {card['title']['value']}",
        "",
        f"- **文件**：`{card['file']}`（{card['pages']} 页）",
        f"- **标题**：{card['title']['value']} {ev('title')}",
        f"- **期刊/会议**：{card['venue']['value']} {ev('venue')}",
        f"- **年份**：{card['year']['value']} {ev('year')}",
        f"- **DOI**：{card['doi']['value']} {ev('doi')}",
        f"- **arXiv**：{card['arxiv']['value']} {ev('arxiv')}",
        "",
        f"## 摘要（原文截取）{ev('abstract')}",
        "",
        card["abstract"]["value"],
        "",
        "## 章节结构",
        "",
    ]
    if card["sections"]:
        for s in card["sections"]:
            lines.append(f"- {s['heading']}（p.{s['page']}）")
    else:
        lines.append("- 文献未说明")
    lines += ["", "## 正文出现的关键数值（供你核对，不代表结论）", ""]
    if card["numbers"]:
        for n in card["numbers"]:
            lines.append(f"- {n['value']} {n['unit']}（p.{n['page']}）")
    else:
        lines.append("- 文献未说明")
    lines += ["", "## 作者自己承认的局限 / 未来工作（原文摘录）", ""]
    if card["limitations"]:
        for lim in card["limitations"]:
            lines.append(f"- {lim['text']}（p.{lim['page']}）")
    else:
        lines.append("- 文献未说明")
    lines += [
        "",
        "## 需要你填的四项（机器不猜）",
        "",
        "- **研究问题**：",
        "- **方法/模型**：",
        "- **关键指标与数值**：",
        "- **主要结论**：",
        "- **和我的课题的关系**：",
        "",
        "---",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Batch
# --------------------------------------------------------------------------- #
def _matrix_md(cards: list[dict]) -> str:
    head = (
        "| # | 文献 | 年份 | 期刊/会议 | 研究问题 | 方法/模型 | 关键指标 | 主要结论 | 与我的课题关系 | 本地 PDF 页码 |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
    )
    rows = []
    for idx, card in enumerate(cards, 1):
        title = card["title"]["value"].replace("|", "/")
        if len(title) > 48:
            title = title[:46] + "…"
        rows.append(
            f"| {idx} | {title} | {card['year']['value']} | {card['venue']['value'][:28].replace('|', '/')} "
            f"| 待填 | 待填 | 待填 | 待填 | 待填 | `{card['file']}` p.1-{card['pages']} |"
        )
    return head + "\n".join(rows) + "\n"


def _gaps_md(cards: list[dict]) -> str:
    lines = [
        "# 缺口清单（机器能看见的空白）",
        "",
        f"共 {len(cards)} 篇。下面每一行都是「这里还空着」，不是「这里有问题」。",
        "",
        "| 文献 | 摘要 | 章节 | 数值 | 局限 | 四列判断 |",
        "|---|---|---|---|---|---|",
    ]
    for card in cards:
        mark = lambda ok: "有" if ok else "**缺**"  # noqa: E731
        lines.append(
            f"| `{card['file']}` | {mark(card['abstract']['value'] != '文献未说明')} "
            f"| {mark(bool(card['sections']))} | {mark(bool(card['numbers']))} "
            f"| {mark(bool(card['limitations']))} | 待填 |"
        )
    lines += [
        "",
        "## 怎么用这份清单",
        "",
        "1. 「缺」的格子先回原文确认——大概率是 PDF 是扫描件或双栏排版，`zhaw read` 抽不到。",
        "2. 四列判断全空是正常的：那是你的工作，不是工具的。",
        "3. 数值列只是「正文出现过这个数」，**不代表它可信**，结论要靠实验复现。",
        "",
    ]
    return "\n".join(lines)


def _survey_draft_md(cards: list[dict]) -> str:
    lines = [
        "# 综述骨架（结构给你，正文你写）",
        "",
        "> 这份草稿只做两件事：按主题给文献分组、给每篇一句可核验的事实描述。",
        "> **不要直接提交**——综述的价值在于你的比较与判断，不在罗列。",
        "",
        "## 1. 研究背景与动机",
        "",
        "- 待填：这个方向为什么现在重要（引用 2-3 篇最新文献）",
        "",
        "## 2. 已有工作分类",
        "",
    ]
    groups: dict[str, list[dict]] = {}
    for card in cards:
        key = card["venue"]["value"].split()[0] if card["venue"]["value"] != "文献未说明" else "未分类"
        groups.setdefault(key, []).append(card)
    for key, items in groups.items():
        lines.append(f"### 2.x {key}")
        lines.append("")
        for card in items:
            year = card["year"]["value"]
            title = card["title"]["value"]
            lines.append(f"- **{title}**（{year}，p.1-{card['pages']}）：待填一句话概括 + 它的局限。")
        lines.append("")
    lines += [
        "## 3. 共性方法与差异",
        "",
        "- 待填：这些工作共享什么假设？分歧在哪？",
        "",
        "## 4. 尚未解决的问题（你的切入点）",
        "",
    ]
    for card in cards:
        if card["limitations"]:
            lines.append(
                f"- 来自 `{card['file']}` p.{card['limitations'][0]['page']}："
                f"{card['limitations'][0]['text'][:180]}"
            )
    lines += [
        "",
        "## 5. 本文的定位",
        "",
        "- 待填：我要解决上面哪一个问题，为什么现在能做。",
        "",
    ]
    return "\n".join(lines)


def read_literature(
    pdf_dir: Path,
    out_dir: Path,
    limit: int | None = None,
    digest: bool = False,
) -> dict:
    pdf_dir = Path(pdf_dir)
    out_dir = Path(out_dir)
    if not pdf_dir.is_dir():
        raise SystemExit(f"not a directory: {pdf_dir}")
    pdfs = sorted(p for p in pdf_dir.rglob("*.pdf"))
    if limit:
        pdfs = pdfs[:limit]
    if not pdfs:
        raise SystemExit(f"no PDF found under {pdf_dir}")

    cards_dir = out_dir / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)
    cards: list[dict] = []
    failures: list[dict] = []
    for idx, pdf in enumerate(pdfs, 1):
        try:
            card = extract_one(pdf)
        except SystemExit:
            raise
        except Exception as exc:  # noqa: BLE001 — one bad PDF must not kill the batch
            failures.append({"file": pdf.name, "error": f"{type(exc).__name__}: {exc}"})
            continue
        cards.append(card)
        write_text(cards_dir / f"{idx:02d}_{pdf.stem[:40]}.md", _card_md(card, idx))

    write_json(
        out_dir / "index.json",
        {"generated_at": now_iso(), "source_dir": str(pdf_dir), "cards": cards, "failures": failures},
    )
    write_text(out_dir / "comparison_matrix.md", _matrix_md(cards))
    write_text(out_dir / "gaps.md", _gaps_md(cards))
    if digest:
        write_text(out_dir / "survey_draft.md", _survey_draft_md(cards))

    return {
        "status": "PASS" if cards else "FAIL",
        "papers": len(cards),
        "failures": failures,
        "out_dir": str(out_dir),
        "cards": str(cards_dir),
        "matrix": str(out_dir / "comparison_matrix.md"),
        "gaps": str(out_dir / "gaps.md"),
        "survey_draft": str(out_dir / "survey_draft.md") if digest else "",
    }


def summary(result: dict) -> str:
    lines = [
        f"[+] 读完 {result['papers']} 篇 PDF -> {result['out_dir']}",
        f"    阅读卡：{result['cards']}",
        f"    对比矩阵：{result['matrix']}（四列判断留空，等你自己填）",
        f"    缺口清单：{result['gaps']}",
    ]
    if result["survey_draft"]:
        lines.append(f"    综述骨架：{result['survey_draft']}")
    if result["failures"]:
        lines.append(f"[!] {len(result['failures'])} 篇抽取失败（扫描件/加密）：")
        for f in result["failures"]:
            lines.append(f"    - {f['file']}: {f['error']}")
    lines += [
        "",
        "下一步：",
        "  1. 打开 gaps.md，把「缺」的格子回原文确认",
        "  2. 填 comparison_matrix.md 的四列判断",
        "  3. zhaw grounding <矩阵> --pdf-dir <文献目录>    # 页码级核验",
        "  4. zhaw seminar <矩阵> --compile                 # 出组会 PPT",
    ]
    return "\n".join(lines)


def load_index(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
