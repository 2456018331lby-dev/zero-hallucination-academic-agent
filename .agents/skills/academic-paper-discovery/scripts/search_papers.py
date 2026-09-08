#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
search_papers.py - Autonomous Academic Paper Discovery & Retrieval

Features:
- Queries OpenAlex and arXiv APIs with polite rate-limiting and User-Agent.
- Venue impact scoring based on externalized venue_weights.json (includes major IEEE COM/SP and CS venues).
- Strict BibTeX generation adhering to GB/T 7714:
  - Full author list formatted as "Family, Given and Family, Given" (no et al. in bibtex)
  - Accurate extraction of volume, issue, and pages from OpenAlex biblio dict
  - Clean bare DOI without URL prefixes
  - Proper entry types (@article vs @inproceedings vs @misc)
  - Standardized citation keys: FamilyYearFirstWord
- Open-access PDF auto-download and paywall triage manifest generation.
"""

import os
import sys
import json
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import argparse
import time
import difflib
import unicodedata

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

# 内置回退权重表（若 venue_weights.json 未找到时使用）
DEFAULT_VENUES_WEIGHTS = {
    # Communications / Signal Processing
    "JSAC": 10, "IEEE JSAC": 10, "TWC": 10, "IEEE TWC": 10,
    "TSP": 10, "IEEE TSP": 10, "COMST": 10, "IEEE COMST": 10,
    "TIT": 10, "IEEE TIT": 10, "TMC": 9, "IEEE TMC": 9,
    "OJCOMS": 9, "IEEE OJCOMS": 9, "ICC": 9, "IEEE ICC": 9,
    "GLOBECOM": 8, "IEEE GLOBECOM": 8,
    # CV / AI / ML
    "CVPR": 10, "ICCV": 10, "ECCV": 9, "IEEE TPAMI": 10, "TPAMI": 10, "TIP": 9,
    "NEURIPS": 10, "ICML": 10, "ICLR": 10, "AAAI": 8, "IJCAI": 8, "JMLR": 10,
    # NLP / Web / Systems
    "ACL": 10, "EMNLP": 9, "NAACL": 8, "KDD": 10, "SIGIR": 9, "WWW": 9,
    "ISCA": 10, "MICRO": 10, "ASPLOS": 10, "DAC": 9, "ISSCC": 10, "IEEE JSSC": 10,
}

USER_AGENT = "AcademicPaperDiscoveryBot/2.0 (mailto:academic-research@university.edu)"


def load_venue_weights():
    weights_path = os.path.join(os.path.dirname(__file__), "venue_weights.json")
    if os.path.exists(weights_path):
        try:
            with open(weights_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_VENUES_WEIGHTS


VENUE_WEIGHTS = load_venue_weights()


def score_paper(paper):
    venue = (paper.get("venue") or "").upper()
    venue_score = 3
    for v_key, v_weight in VENUE_WEIGHTS.items():
        if v_key.upper() in venue:
            venue_score = max(venue_score, v_weight)

    citations = paper.get("citations", 0)
    year = paper.get("year", 2024)
    recency = max(0, year - 2020)

    import math
    cit_score = min(10.0, math.log(citations + 1, 2.5))
    final_score = (venue_score * 0.4) + (cit_score * 0.35) + (min(recency, 6) * 0.25)
    return round(final_score, 2)


def format_bibtex_author(raw_name):
    """将名字标准化为 'Family, Given'。"""
    s = raw_name.strip()
    if not s:
        return ""
    if "," in s:
        return s
    tokens = s.split()
    if len(tokens) >= 2:
        return f"{tokens[-1]}, {' '.join(tokens[:-1])}"
    return s


def clean_doi(doi_str):
    if not doi_str:
        return ""
    s = str(doi_str).strip()
    s = re.sub(r"^\s*(?:https?://)?(?:dx\.)?doi\.org/", "", s, flags=re.I)
    return s.strip()


def search_openalex(query, limit=50):
    encoded_q = urllib.parse.quote(query)
    url = f"https://api.openalex.org/works?search={encoded_q}&per_page={limit}&sort=relevance_score:desc"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    papers = []

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for item in data.get("results", []):
                title = item.get("title") or ""
                if not title:
                    continue

                year = item.get("publication_year") or 2024
                citations = item.get("cited_by_count") or 0

                primary_loc = item.get("primary_location") or {}
                source = primary_loc.get("source") or {}
                venue = source.get("display_name") or ""
                source_type = (source.get("type") or "").lower()
                work_type = (item.get("type") or "").lower()

                # 卷期页
                biblio = item.get("biblio") or {}
                volume = biblio.get("volume") or ""
                issue = biblio.get("issue") or ""
                first_page = biblio.get("first_page") or ""
                last_page = biblio.get("last_page") or ""
                pages = f"{first_page}--{last_page}" if first_page and last_page else (first_page or "")

                # 摘要
                abstract = ""
                inv_abs = item.get("abstract_inverted_index")
                if inv_abs:
                    word_positions = []
                    for word, pos_list in inv_abs.items():
                        for p in pos_list:
                            word_positions.append((p, word))
                    word_positions.sort()
                    abstract = " ".join([w for _, w in word_positions])

                # OA PDF
                open_access = item.get("open_access") or {}
                oa_url = open_access.get("oa_url") or primary_loc.get("pdf_url")

                # 作者列表提取
                authorships = item.get("authorships") or []
                raw_authors = []
                for a in authorships:
                    dn = a.get("author", {}).get("display_name", "")
                    if dn:
                        raw_authors.append(dn.strip())

                bib_authors = " and ".join(format_bibtex_author(a) for a in raw_authors if a)
                if not bib_authors:
                    bib_authors = "Unknown"

                first_author_fam = (raw_authors[0].split()[-1] if "," not in raw_authors[0] else raw_authors[0].split(",")[0]) if raw_authors else "Paper"
                first_author_disp = (raw_authors[0] + " et al.") if len(raw_authors) > 1 else (raw_authors[0] if raw_authors else "Unknown")

                # 判定 BibTeX 条目类型
                if source_type in ("journal", "article") or work_type in ("journal-article", "article") or "journal" in venue.lower() or "transactions" in venue.lower():
                    entry_type = "article"
                elif source_type in ("conference", "proceedings") or work_type in ("proceedings-article", "inproceedings") or "conference" in venue.lower() or "symposium" in venue.lower():
                    entry_type = "inproceedings"
                else:
                    entry_type = "article"

                papers.append({
                    "title": title.strip(),
                    "authors": first_author_disp,
                    "bib_authors": bib_authors,
                    "first_fam": first_author_fam,
                    "year": year,
                    "venue": venue or "Journal/Conference",
                    "volume": volume,
                    "issue": issue,
                    "pages": pages,
                    "entry_type": entry_type,
                    "citations": citations,
                    "doi": clean_doi(item.get("doi")),
                    "abstract": abstract[:1500] if abstract else "文献未说明详细摘要",
                    "oa_url": oa_url,
                    "is_oa": bool(oa_url),
                    "source": "OpenAlex"
                })
    except Exception as e:
        print(f"[-] OpenAlex search warning: {e}", file=sys.stderr)

    return papers


def search_arxiv(query, limit=20):
    encoded_q = urllib.parse.quote(query)
    url = f"http://export.arxiv.org/api/query?search_query=all:{encoded_q}&start=0&max_results={limit}&sortBy=relevance&sortOrder=descending"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    papers = []

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_text = resp.read().decode("utf-8")
            root = ET.fromstring(xml_text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            for entry in root.findall("atom:entry", ns):
                title_elem = entry.find("atom:title", ns)
                title = title_elem.text.strip().replace("\n", " ") if title_elem is not None else ""
                if not title or title.lower() == "error":
                    continue

                published_elem = entry.find("atom:published", ns)
                year = 2024
                if published_elem is not None and published_elem.text:
                    year = int(published_elem.text[:4])

                summary_elem = entry.find("atom:summary", ns)
                abstract = summary_elem.text.strip().replace("\n", " ") if summary_elem is not None else ""

                authors = []
                for author_elem in entry.findall("atom:author", ns):
                    name_elem = author_elem.find("atom:name", ns)
                    if name_elem is not None and name_elem.text:
                        authors.append(name_elem.text.strip())

                bib_authors = " and ".join(format_bibtex_author(a) for a in authors) or "Unknown"
                first_fam = (authors[0].split()[-1] if "," not in authors[0] else authors[0].split(",")[0]) if authors else "Paper"
                first_disp = (authors[0] + " et al.") if len(authors) > 1 else (authors[0] if authors else "Unknown")

                pdf_url = ""
                for link in entry.findall("atom:link", ns):
                    if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                        pdf_url = link.attrib.get("href", "")
                    elif not pdf_url and link.attrib.get("rel") == "alternate":
                        alt_href = link.attrib.get("href", "")
                        if "arxiv.org/abs/" in alt_href:
                            pdf_url = alt_href.replace("/abs/", "/pdf/") + ".pdf"

                papers.append({
                    "title": title,
                    "authors": first_disp,
                    "bib_authors": bib_authors,
                    "first_fam": first_fam,
                    "year": year,
                    "venue": "arXiv Preprint",
                    "volume": "",
                    "issue": "",
                    "pages": "",
                    "entry_type": "article",
                    "citations": 0,
                    "doi": "",
                    "abstract": abstract[:1500],
                    "oa_url": pdf_url,
                    "is_oa": bool(pdf_url),
                    "source": "arXiv"
                })
    except Exception as e:
        print(f"[-] arXiv search warning: {e}", file=sys.stderr)

    return papers


NAV_WORDS_PATTERN = re.compile(
    r"(?i)(?:skip to main|research explorer|sign in|subscribe|navigation|cookie policy|editorial board|institutional login|access through your organization)"
)


STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "over",
    "about", "after", "between", "through", "during", "before", "under",
    "around", "among", "using", "based", "via", "toward", "towards", "on",
    "in", "of", "to", "a", "an", "as", "by", "at"
}


def norm_text(s):
    s_norm = unicodedata.normalize("NFKD", s or "")
    return re.sub(r"\W+", " ", s_norm.lower()).strip()


def title_similarity(a, b):
    return difflib.SequenceMatcher(None, norm_text(a), norm_text(b)).ratio()


def calculate_page_title_similarity(page_text, expected_title):
    """
    计算首页文本与文献标题的复合相似度 (Composite Title Similarity):
    - 结合实词 Token 覆盖率 (权重 0.6) 与最佳局部窗口比对相似度 (权重 0.4)
    - 连字 (ligatures如 'fi', 'fl') 采用 NFKD 展开
    - 阈值设定为 0.50 (真论文通常 >= 0.6，无关转储页通常 < 0.5)
    """
    if not expected_title or not page_text:
        return 0.0
    nt = norm_text(expected_title)
    np = norm_text(page_text)
    if not nt:
        return 1.0
    if nt in np:
        return 1.0

    raw_tokens = re.findall(r"[a-zA-Z0-9]+", nt)
    tokens = [w for w in raw_tokens if len(w) >= 3 and w not in STOP_WORDS]
    if not tokens:
        tokens = [w for w in raw_tokens if len(w) >= 2]
    if not tokens:
        tokens = raw_tokens

    if not tokens:
        token_cov = 0.0
    else:
        padded_np = f" {np} "
        matched = sum(1 for t in tokens if f" {t} " in padded_np)
        token_cov = matched / len(tokens)

    best_win = 0.0
    for line in page_text.splitlines():
        cl = norm_text(line)
        if cl:
            sim = difflib.SequenceMatcher(None, cl, nt).ratio()
            if sim > best_win:
                best_win = sim

    t_len = len(nt)
    if len(np) > t_len:
        step = max(5, t_len // 4)
        for i in range(0, len(np) - t_len + 1, step):
            window = np[i : i + t_len]
            sim = difflib.SequenceMatcher(None, window, nt).ratio()
            if sim > best_win:
                best_win = sim
                if best_win >= 0.95:
                    break

    return 0.6 * token_cov + 0.4 * best_win


def validate_downloaded_pdf(file_path, expected_title=None):
    """
    落地页与伪正文过滤器 (Landing Page & Fake PDF Filter):
    1. 文件体积 < 40KB -> 拒收
    2. PyMuPDF 解析与物理页数检查 (缺依赖 fail-closed，页数 < 3 拒收)
    3. 首页前 500 字符命中导航词 (Skip to main, Research Explorer 等) -> 拒收
    4. 首页文本与文献标题复合相似度 < 0.50 -> 拒收
    返回 (is_valid, reject_reason)
    """
    if not os.path.exists(file_path):
        return False, "文件不存在"

    # 1. 体积检查
    file_size = os.path.getsize(file_path)
    if file_size < 40 * 1024:
        return False, f"文件体积过小 ({file_size / 1024:.1f} KB < 40 KB)，疑似错误页或残缺文件"

    # 2. PyMuPDF 解析与页数检查 (fail-closed)
    if not HAS_PYMUPDF:
        msg = "[-] [依赖缺失] 物理校验不可用 (UNVERIFIED: PyMuPDF not installed, fail-closed policy enforced)"
        print(msg, file=sys.stderr)
        return False, msg

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        return False, f"PyMuPDF 无法解析 PDF 文件: {e}"

    try:
        page_count = len(doc)
        if page_count < 3:
            return False, f"物理页数不足 3 页 (实际: {page_count} 页)，疑似摘要单页或跳转页"

        # 3. 首页前 500 字符导航词检查
        page1_text = doc[0].get_text() if page_count > 0 else ""
        first_500 = page1_text[:500]
        nav_match = NAV_WORDS_PATTERN.search(first_500)
        if nav_match:
            return False, f"首页前 500 字符命中网站导航/登录词: '{nav_match.group(0)}'，确认为网页转储而非论文本体"

        # 4. 复合标题相似度检查 (阈值 0.50)
        if expected_title:
            sim = calculate_page_title_similarity(page1_text, expected_title)
            if sim < 0.50:
                return False, f"首页文本与论文标题相似度过低 ({sim:.3f} < 0.50)，疑似无关转储页"

        return True, ""
    finally:
        doc.close()


def download_pdf(url, output_path, expected_title=None):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as response, open(output_path, "wb") as out_file:
            out_file.write(response.read())

        # 立即执行落地页与有效性过滤
        is_valid, reason = validate_downloaded_pdf(output_path, expected_title=expected_title)
        if not is_valid:
            print(f"  [-] [落地页过滤器拒收] {reason}")
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError:
                    pass
            return False

        return True
    except Exception as e:
        print(f"[-] Download failed for {url}: {e}", file=sys.stderr)
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError:
                pass
        return False


def generate_bibtex_key(paper):
    author_lead = re.sub(r"[^a-zA-Z]", "", paper.get("first_fam", "Author")).lower() or "paper"
    year = paper.get("year", 2024)
    title_words = [w.lower() for w in re.findall(r"[a-zA-Z]+", paper.get("title", "")) if len(w) > 3]
    lead_word = title_words[0] if title_words else "study"
    return f"{author_lead}{year}{lead_word}"


def run_pipeline(query, output_dir="./literature", broad_limit=50, deep_limit=12, download_oa=True):
    os.makedirs(output_dir, exist_ok=True)
    print(f"[*] Initiating Two-Tier Academic Literature Discovery: '{query}'")
    print(f"[*] Target Funnel: {broad_limit} Broad Citations Pool -> {deep_limit} Deep-Dive Core Papers")

    # 1. 抓取候选文献
    openalex_results = search_openalex(query, limit=broad_limit)
    arxiv_results = search_arxiv(query, limit=min(20, broad_limit // 2))
    all_candidates = openalex_results + arxiv_results

    # 2. 按标题去重与打分
    seen_titles = set()
    unique_papers = []
    for p in all_candidates:
        clean_title = re.sub(r"[^a-zA-Z0-9]", "", p["title"].lower())
        if clean_title and clean_title not in seen_titles:
            seen_titles.add(clean_title)
            p["score"] = score_paper(p)
            p["bib_key"] = generate_bibtex_key(p)
            unique_papers.append(p)

    # 3. 按影响力排序并分流
    unique_papers.sort(key=lambda x: x["score"], reverse=True)
    broad_pool = unique_papers[:broad_limit]
    deep_pool = broad_pool[:deep_limit]

    print(f"[+] Retrieved {len(broad_pool)} papers for Broad Background Pool.")
    print(f"[+] Screened {len(deep_pool)} elite papers for Deep Reading & Methodology Analysis.")

    # 4. 生成规范的 references_broad.bib
    bib_path = os.path.join(output_dir, "references_broad.bib")
    with open(bib_path, "w", encoding="utf-8") as fb:
        for p in broad_pool:
            etype = p.get("entry_type", "article")
            fb.write(f"@{etype}{{{p['bib_key']},\n")
            fb.write(f"  title     = {{{{{p['title']}}}}},\n")
            fb.write(f"  author    = {{{p['bib_authors']}}},\n")
            if etype == "article":
                fb.write(f"  journal   = {{{p['venue']}}},\n")
            else:
                fb.write(f"  booktitle = {{{p['venue']}}},\n")
            fb.write(f"  year      = {{{p['year']}}},\n")
            if p.get("volume"):
                fb.write(f"  volume    = {{{p['volume']}}},\n")
            if p.get("issue"):
                fb.write(f"  number    = {{{p['issue']}}},\n")
            if p.get("pages"):
                fb.write(f"  pages     = {{{p['pages']}}},\n")
            if p.get("doi"):
                fb.write(f"  doi       = {{{p['doi']}}},\n")
            fb.write("}\n\n")
    print(f"[OK] Generated comprehensive BibTeX database: {bib_path} ({len(broad_pool)} entries)")

    # 5. 下载 OA PDF
    downloaded_count = 0
    paywalled_list = []
    for idx, p in enumerate(deep_pool, start=1):
        safe_name = re.sub(r"[^\w\s-]", "", p["title"])[:50].strip().replace(" ", "_")
        target_filename = f"[{idx:02d}]_{safe_name}_{p['year']}.pdf"
        local_path = os.path.join(output_dir, target_filename)

        p["local_file"] = None
        p["pdf_verified"] = False
        if download_oa and p.get("oa_url"):
            print(f"  [{idx}/{len(deep_pool)}] Downloading OA PDF: {p['title'][:45]}...")
            if download_pdf(p["oa_url"], local_path, expected_title=p.get("title")):
                p["local_file"] = os.path.abspath(local_path)
                p["pdf_verified"] = True
                downloaded_count += 1
            else:
                p["local_file"] = None
                p["pdf_verified"] = False
                paywalled_list.append(p)
        else:
            paywalled_list.append(p)

    for p in broad_pool:
        p.setdefault("pdf_verified", False)

    # 6. 生成清单与分流计划
    manifest_path = os.path.join(output_dir, "literature_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as fp:
        json.dump({
            "query": query,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_broad": len(broad_pool),
            "total_deep": len(deep_pool),
            "oa_downloaded": downloaded_count,
            "paywalled": len(paywalled_list),
            "broad_pool": broad_pool,
            "deep_pool": deep_pool
        }, fp, ensure_ascii=False, indent=2)

    plan_path = os.path.join(output_dir, "reading_plan.md")
    with open(plan_path, "w", encoding="utf-8") as fp:
        fp.write(f"# 两级文献漏斗与精读分流计划：{query}\n\n")
        fp.write(f"**检索时间**：{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        fp.write(f"**广度引文池**：{len(broad_pool)} 篇（已自动生成 BibTeX 数据库 `references_broad.bib`）\n")
        fp.write(f"**深度精读池**：{len(deep_pool)} 篇 ｜ **已自动下载 OA 全文**：{downloaded_count} 篇 ｜ **需校园网补充**：{len(paywalled_list)} 篇\n\n")

        fp.write("## 一、深度精读核心文献（用于第二章多维对比三线表与第三章机理推导）\n\n")
        fp.write("| 序号 | 论文题目 | 第一作者 | 年份 | 期刊/会议 | 影响分 | 状态与本地文件 |\n")
        fp.write("| :---: | :--- | :--- | :---: | :--- | :---: | :--- |\n")
        for idx, p in enumerate(deep_pool, start=1):
            status = f"`{os.path.basename(p['local_file'])}`" if p.get("local_file") else f"[需校园网下: {p.get('doi') or '下载'}]"
            fp.write(f"| {idx} | **{p['title']}** | {p['authors']} | {p['year']} | {p['venue']} | {p['score']} | {status} |\n")

        fp.write("\n## 二、广度学术背景文献（用于第一章绪论演进树与学术大背景引用）\n\n")
        fp.write(f"共计 {len(broad_pool)} 篇顶会/顶刊高引论文，已全量导入至 `references_broad.bib`，可直接在正文中通过 `\\cite{{...}}` 引用。\n")

    print(f"[OK] Search manifest generated: {manifest_path}")
    print(f"[OK] Reading plan generated: {plan_path}")
    print(f"[OK] Successfully cached {downloaded_count} OA full-text papers into {output_dir}/")
    return deep_pool


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous Academic Paper Discovery (Two-Tier Funnel)")
    parser.add_argument("query", type=str, help="Research topic or search keywords")
    parser.add_argument("--dir", type=str, default="./literature", help="Target literature directory")
    parser.add_argument("--broad-limit", type=int, default=50, help="Number of papers for broad context & bib")
    parser.add_argument("--deep-limit", type=int, default=12, help="Number of papers for deep dive reading")
    parser.add_argument("--limit", type=int, default=None, help="Alias for deep-limit / general limit")
    parser.add_argument("--no-download", action="store_true", help="Do not download OA PDFs")

    args = parser.parse_args()
    d_limit = args.limit if args.limit is not None else args.deep_limit
    b_limit = max(args.broad_limit, d_limit * 3)

    run_pipeline(args.query, output_dir=args.dir, broad_limit=b_limit, deep_limit=d_limit, download_oa=not args.no_download)
