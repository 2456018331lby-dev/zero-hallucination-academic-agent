#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_citations.py - Citation Verification Gate (CrossRef Forensic Audit)

审计 LaTeX 工程参考文献的事实正确性：
1. 解析工程内 *.bib 条目与 .tex 中 thebibliography 环境的 \\bibitem 条目；
2. 以 DOI 为锚调用 Crossref 官方 API 回填权威元数据（无 DOI 条目按标题检索定位）；
3. 逐字段比对：标题相似度、作者姓集合、年份、卷、期、页码；
4. 任何作者张冠李戴 / 卷期页错配 / 查无此文献一律 FAIL，退出码非 0。

设计动机：大模型生成引文时 DOI/标题多来自真实检索，而作者与卷期页常凭参数记忆
脑补（实测 demo 工程 6/6 条目有错、2 条作者整列虚构）。因此本工具"只信 API，不信记忆"。

用法：
    python check_citations.py <工程路径> [--json OUT.json] [--offline] [--strict]
退出码：0=通过；1=存在 FAIL；2=仅严格模式下失败（存在 WARN）。
"""

import os
import re
import sys
import json
import time
import argparse
import difflib
import urllib.request
import urllib.parse

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

CROSSREF_UA = "citation-auditor/1.0 (mailto:thesis-gate@example.edu)"
REQUEST_INTERVAL = 0.3
TITLE_MATCH_THRESHOLD = 0.85

# ---------------------------------------------------------------------------
# 通用工具
# ---------------------------------------------------------------------------

def norm_text(s):
    """小写化并去除非字母数字，用于标题模糊比对。"""
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def title_similarity(a, b):
    return difflib.SequenceMatcher(None, norm_text(a), norm_text(b)).ratio()


def norm_pages(s):
    if not s:
        return ""
    s = str(s).replace("--", "-").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", "", s)


def norm_doi(s):
    s = (s or "").strip()
    s = re.sub(r"^\s*(?:https?://)?(?:dx\.)?doi\.org/", "", s, flags=re.I)
    return s.lower()


# ---------------------------------------------------------------------------
# .bib 解析（花括号配平）
# ---------------------------------------------------------------------------

def parse_bib_file(path):
    """解析 BibTeX 文件，返回条目列表 [{type,key,fields{...}}]。"""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    entries = []
    i = 0
    while True:
        at = text.find("@", i)
        if at < 0:
            break
        brace = text.find("{", at)
        if brace < 0:
            break
        # 花括号配平扫描
        depth, j = 0, brace
        while j < len(text):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        body = text[brace + 1:j]
        i = j + 1

        head_end = body.find(",")
        if head_end < 0:
            continue
        etype = text[at + 1:brace].strip().lower()
        key = body[:head_end].strip()
        fields = {}
        rest = body[head_end + 1:]
        for m in re.finditer(r"(\w+)\s*=\s*", rest):
            start = m.end()
            if start < len(rest) and rest[start] == "{":
                depth, k = 0, start
                while k < len(rest):
                    if rest[k] == "{":
                        depth += 1
                    elif rest[k] == "}":
                        depth -= 1
                        if depth == 0:
                            break
                    k += 1
                val = rest[start + 1:k]
            else:
                nm = re.match(r'"([^"]*)"', rest[start:])
                if nm:
                    val = nm.group(1)
                else:
                    val = rest[start:].split(",")[0]
            fields[m.group(1).lower()] = re.sub(r"\s+", " ", val).strip()
        entries.append({"origin": os.path.basename(path), "type": etype,
                        "key": key, "fields": fields})
    return entries


# ---------------------------------------------------------------------------
# \bibitem 解析（GB/T 7714 风格文本）
# ---------------------------------------------------------------------------

BIBITEM_RE = re.compile(r"\\bibitem\{([^}]+)\}")
# 形如 "XIE H T, QIN Z Q, LI G Y, et al. Deep learning enabled ...[J]. IEEE ..., 2021, 69: 2663--2675."
GB_TEXT_RE = re.compile(
    r"^\s*(?P<authors>.+?)\.\s+(?P<title>.+?)"
    r"\[(?P<type>[A-Z]{1,3}(?:/OL)?)\]\.\s*(?P<rest>.+?)\.?\s*$",
    re.S,
)
GB_TAIL_RE = re.compile(
    r"(?P<venue>.+?),\s*(?P<year>(?:19|20)\d{2})"
    r"(?:,\s*(?P<volume>[A-Za-z]?\d+))?"
    r"(?:\s*\((?P<issue>[^)]+)\))?"
    r"(?:\s*:\s*(?P<pages>[\d]+\s*[-–—~]+\s*[\d]+))?"
)


def parse_bibitems(tex_path):
    """从 .tex 提取 thebibliography 中 \\bibitem 条目并解析 GB/T 文本字段。"""
    with open(tex_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    entries = []
    matches = list(BIBITEM_RE.finditer(text))
    for idx, m in enumerate(matches):
        key = m.group(1)
        body = text[m.end(): matches[idx + 1].start() if idx + 1 < len(matches) else len(text)]
        body = re.sub(r"%.*", "", body)  # 去注释
        body = " ".join(body.split())
        entry = {"origin": os.path.basename(tex_path), "type": "bibitem",
                 "key": key, "fields": {}}
        gm = GB_TEXT_RE.match(body)
        if gm:
            entry["fields"]["author"] = gm.group("authors")
            entry["fields"]["title"] = gm.group("title")
            tail = gm.group("rest")
            tm = GB_TAIL_RE.search(tail)
            if tm:
                entry["fields"]["journal"] = tm.group("venue").strip()
                entry["fields"]["year"] = tm.group("year")
                if tm.group("volume"):
                    entry["fields"]["volume"] = tm.group("volume")
                if tm.group("issue"):
                    entry["fields"]["number"] = tm.group("issue")
                if tm.group("pages"):
                    entry["fields"]["pages"] = tm.group("pages")
            else:
                entry["fields"]["journal"] = tail.strip()
        else:
            entry["fields"]["raw"] = body[:400]

        m_doi = re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", body)
        if m_doi:
            entry["fields"]["doi"] = m_doi.group(0).rstrip(".,;")

        entries.append(entry)
    return entries, text


def collect_cite_keys(text):
    keys = set()
    for m in re.finditer(r"\\cite[tp]?\{([^}]+)\}", text):
        for k in m.group(1).split(","):
            k = k.strip()
            if k:
                keys.add(k)
    return keys


# ---------------------------------------------------------------------------
# 作者解析：返回 [{family, given}] 序列
# 支持：BibTeX 'Family, Given and Family, Given'、GB/T 'SURNAME I N, SURNAME I N, et al.'、
#       自然语序 'Given Family and Given Family'
# ---------------------------------------------------------------------------


def parse_authors(author_field):
    s = re.sub(r"[{}\\]", "", author_field or "").strip()
    if not s:
        return [], False
    truncated = bool(re.search(r"et\s+al|等(?![a-zA-Z])", s, re.I))
    s = re.sub(r",?\s*(?:et\s+al\.?|等)\s*", "", s, flags=re.I)

    authors = []
    if " and " in s or ";" in s:
        # BibTeX / 自然语序：按 and/; 分隔
        for part in re.split(r"\s+and\s+|;", s):
            part = part.strip().strip(",")
            if not part:
                continue
            if "," in part:
                fam, _, giv = part.partition(",")
                authors.append({"family": fam.strip(), "given": giv.strip()})
            else:
                toks = part.split()
                if len(toks) >= 2 and toks[0].isupper() and len(toks[0]) > 1:
                    authors.append({"family": toks[0], "given": " ".join(toks[1:])})
                elif len(toks) >= 2:
                    authors.append({"family": toks[-1], "given": " ".join(toks[:-1])})
                else:
                    authors.append({"family": toks[0], "given": ""})
    else:
        # GB/T 文本：逗号分隔作者，姓全大写在前（'XIE H T'）或姓在后
        for part in s.split(","):
            part = part.strip()
            if not part:
                continue
            toks = part.split()
            if not toks:
                continue
            if len(toks) >= 2 and toks[0].isupper() and len(toks[0]) > 1:
                authors.append({"family": toks[0], "given": " ".join(toks[1:])})
            elif len(toks) >= 2:
                authors.append({"family": toks[-1], "given": " ".join(toks[:-1])})
            else:
                authors.append({"family": toks[0], "given": ""})
    return authors, truncated


def _given_initials(given):
    """'Huiqiang' -> ['H'] ; 'Geoffrey Ye' -> ['G','Y']"""
    return [t[0].upper() for t in re.split(r"[-\s]+", given or "") if t]


def _is_initials_only(given):
    """'H T' / 'H.-T.' -> True；'Kai' / 'Jin-Cheng' -> False（每个分隔 token 必须是单字母）。"""
    tokens = [t for t in re.split(r"[\s\-.]+", (given or "").strip()) if t]
    return bool(tokens) and all(len(t) == 1 for t in tokens)


def compare_given(ours_given, ref_given, position):
    """比对名（given）字段。返回 (problems, warn_problems)。
    缩写首字母与官方名首字母不符 / 全名相似度过低 → FAIL；
    缩写个数多于官方名 token（如 'J C' vs 'Jincheng' 的合法缩写约定）→ WARN。"""
    problems, warns = [], []
    if not ours_given or not ref_given:
        return problems, warns
    if _is_initials_only(ours_given):
        oi = [t.upper() for t in re.split(r"[\s\-.]+", ours_given.strip()) if t]
        ri = _given_initials(ref_given)
        if oi and ri:
            if oi[0] != ri[0]:
                problems.append(f"第{position}作者名缩写首字母不符：条目='{ref_given.split()[0] if ref_given.split() else ref_given}'姓作者名缩写 '{' '.join(oi)}' vs 官方名 '{ref_given}'（首字母 {ri}）")
            elif len(oi) > len(ri):
                warns.append(f"第{position}作者名缩写数多于官方名 token（'{' '.join(oi)}' vs '{ref_given}'），可能为合法双名缩写约定，请人工确认")
    else:
        sim = title_similarity(ours_given, ref_given)
        if sim < 0.6:
            problems.append(f"第{position}作者名不匹配：条目='{ours_given}' vs Crossref='{ref_given}'")
    return problems, warns


# ---------------------------------------------------------------------------
# Crossref 客户端（带缓存与限速）
# ---------------------------------------------------------------------------

class CrossrefClient:
    def __init__(self, cache_path=None, offline=False):
        self.cache_path = cache_path
        self.offline = offline
        self.cache = {}
        if cache_path and os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}
        self._last_call = 0.0
        self.network_used = False

    def _save(self):
        if self.cache_path:
            try:
                with open(self.cache_path, "w", encoding="utf-8") as f:
                    json.dump(self.cache, f, ensure_ascii=False, indent=1)
            except Exception:
                pass

    def _get(self, url):
        key = url
        if key in self.cache:
            return self.cache[key]
        if self.offline:
            return None
        now = time.time()
        if now - self._last_call < REQUEST_INTERVAL:
            time.sleep(REQUEST_INTERVAL - (now - self._last_call))
        try:
            req = urllib.request.Request(url, headers={"User-Agent": CROSSREF_UA})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            self.cache[key] = data
            self._last_call = time.time()
            self.network_used = True
            self._save()
            return data
        except urllib.error.HTTPError as e:
            # 404 = Crossref 明确答复该 DOI/查询不存在，属可判定事实，需与网络故障区分
            kind = "not_found" if e.code in (404, 400) else "http_error"
            self.cache[key] = {"__error__": str(e), "__kind__": kind}
            return self.cache[key]
        except Exception as e:
            self.cache[key] = {"__error__": str(e), "__kind__": "network"}
            return self.cache[key]

    def by_doi(self, doi):
        data = self._get(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}")
        if data and "__error__" not in data:
            return data.get("message")
        return None

    def doi_error_kind(self, doi):
        data = self._get(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}")
        if data and "__error__" in data:
            return data.get("__kind__", "network")
        return None

    def retraction(self, doi):
        """检测 DOI 是否已被撤稿。返回 (is_retracted, detail)；无法判定时返回 (None, None)。

        依据 Crossref 官方元数据中的撤稿关系（与 citegate 的思路一致，不引入其代码）：
          - relation.is-retracted-by : 本作品被这些撤稿声明撤稿（最直接的信号）
          - update-to[].type == "retraction" : 本作品有撤稿更新记录
        反向的 relation.is-retraction-of 属于撤稿声明自身，不在此判定范围内。
        离线/网络异常时返回 (None, None)，由调用方跳过而不是误报。
        """
        item = self.by_doi(doi)
        if not item:
            return None, None
        rel = item.get("relation") or {}
        by = rel.get("is-retracted-by") or []
        if by:
            ids = [r.get("id") for r in by if isinstance(r, dict) and r.get("id")]
            return True, "Crossref relation.is-retracted-by: " + (", ".join(ids) or "(未给出撤稿声明 DOI)")
        for upd in (item.get("update-to") or []):
            if isinstance(upd, dict) and (upd.get("type") or "").lower() == "retraction":
                return True, "Crossref update-to type=retraction: " + str(upd.get("DOI") or "(无 DOI)")
        return False, None

    def by_title(self, title, authors=None):
        """按标题检索；若提供作者姓序列，则优先选标题相似且作者兼容的候选。"""
        q = urllib.parse.quote(title)
        data = self._get(f"https://api.crossref.org/works?query.bibliographic={q}&rows=5")
        if not data or "__error__" in data:
            return None, None, (data or {}).get("__kind__", "network") if data else "network"
        best, best_key = None, (-1.0, -1.0)
        ours_fams = [a["family"].lower() for a in (authors or []) if a.get("family")]
        for item in data.get("message", {}).get("items", []):
            ct = (item.get("title") or [""])[0]
            ratio = title_similarity(title, ct)
            ref_fams = [a.get("family", "").lower() for a in item.get("author", []) if a.get("family")]
            author_hit = 0.0
            if ours_fams and ref_fams:
                author_hit = sum(1 for a in ours_fams[:3] if a in ref_fams) / max(1, len(ours_fams[:3]))
            key = (ratio, author_hit)
            if key > best_key:
                best, best_key = item, key
        return best, best_key[0], None


def crossref_fields(item):
    """从 Crossref message 提取比对所需字段。"""
    year = None
    for k in ("issued", "published-print", "published-online"):
        dp = (item.get(k) or {}).get("date-parts") or []
        if dp and dp[0] and dp[0][0]:
            year = dp[0][0]
            break
    authors = [{"family": a.get("family", ""), "given": a.get("given", "")}
               for a in item.get("author", []) if a.get("family")]
    return {
        "title": (item.get("title") or [""])[0],
        "year": year,
        "volume": item.get("volume") or "",
        "issue": item.get("issue") or "",
        "pages": item.get("page") or "",
        "container": (item.get("container-title") or [""])[0],
        "authors": authors,
        "doi": (item.get("DOI") or "").lower(),
    }


# ---------------------------------------------------------------------------
# 单条比对
# ---------------------------------------------------------------------------

def audit_entry(entry, client):
    """返回 {status, problems[], warns[], checked[], resolved_doi}"""
    f = entry["fields"]
    title = f.get("title", "")
    problems, warn_problems, checked = [], [], []

    doi = norm_doi(f.get("doi", ""))
    item, ratio = (None, None)
    if doi:
        item = client.by_doi(doi)
        if item is None:
            kind = client.doi_error_kind(doi) or "network"
            if kind == "not_found":
                return {"status": "FAIL", "problems": [f"Crossref 无此 DOI（DOI 本身虚构或转录错误）: {doi}"],
                        "warns": [], "checked": ["doi"], "resolved_doi": None}
            return {"status": "WARN", "problems": [], "warns": [f"网络/服务异常，DOI 暂无法核验: {doi}"],
                    "checked": [], "resolved_doi": None}
    elif title:
        ours_authors, _ = parse_authors(f.get("author", ""))
        item, ratio, err = client.by_title(title, authors=ours_authors)
        if err:
            return {"status": "WARN", "problems": [], "warns": ["网络/服务异常，标题检索暂无法核验"],
                    "checked": [], "resolved_doi": None}
        if item is None or ratio < TITLE_MATCH_THRESHOLD:
            return {"status": "FAIL", "problems": ["无 DOI 且按标题检索 Crossref 无命中（疑似虚构文献）"],
                    "warns": [], "checked": ["doi", "title"], "resolved_doi": None}
        doi = (item.get("DOI") or "").lower()
    else:
        return {"status": "FAIL", "problems": ["条目缺少 title 与 doi，无法审计"],
                "warns": [], "checked": [], "resolved_doi": None}

    ref = crossref_fields(item)

    # 撤稿检测：引用了已被撤稿的论文属学术事故，直接 FAIL。
    # 这是本项目原先的盲区——元数据全对，但文献本身已失效。
    if doi:
        retracted, ret_detail = client.retraction(doi)
        if retracted is not None:
            checked.append("retraction")
        if retracted:
            problems.append(f"该文献已被撤稿（引用撤稿论文属学术事故）：{doi} — {ret_detail}")

    # 标题
    if title:
        checked.append("title")
        r = title_similarity(title, ref["title"])
        if r < TITLE_MATCH_THRESHOLD:
            problems.append(f"标题不匹配 (相似度 {r:.2f})：条目='{title[:60]}' vs Crossref='{ref['title'][:60]}'")

    # 作者：姓序列前缀比对 + 名（given）逐位校验（可捕获姓名伪造与缩写错配）
    if f.get("author"):
        checked.append("authors")
        ours, truncated = parse_authors(f["author"])
        theirs = [a for a in ref["authors"] if a["family"]]
        if ours and theirs:
            lo = [a["family"].lower() for a in ours]
            lt = [a["family"].lower() for a in theirs]
            if lo[0] != lt[0]:
                problems.append(f"第一作者姓不匹配：条目='{ours[0]['family']}' vs Crossref='{theirs[0]['family']}'（疑似张冠李戴）")
            else:
                n = len(lo)
                match_cnt = sum(1 for a, b in zip(lo, lt[:n]) if a == b)
                if match_cnt < max(1, int(0.6 * n)):
                    problems.append(
                        f"作者姓序列错配 {match_cnt}/{n}：条目={[a['family'] for a in ours]}"
                        f" vs Crossref={[a['family'] for a in theirs[:max(n, 3)]]}"
                        + ("（条目为 et al. 截断列表）" if truncated else ""))
                else:
                    # 名（given）校验：仅比对条目中给出且 Crossref 也有的前缀部分
                    for i, (a, b) in enumerate(zip(ours, theirs)):
                        if not a.get("given") or not b.get("given"):
                            continue
                        p, w = compare_given(a["given"], b["given"], i + 1)
                        problems += p
                        warn_problems += w
                        if truncated and i >= len(ours) - 1:
                            break
        else:
            warn_problems.append("条目或 Crossref 缺少作者数据，作者维度未核验")

    # 年份
    if f.get("year"):
        checked.append("year")
        try:
            if int(re.sub(r"\D", "", str(f["year"]))) != int(ref["year"] or 0):
                problems.append(f"年份不匹配：条目={f['year']} vs Crossref={ref['year']}")
        except (ValueError, TypeError):
            pass

    # 卷 / 期 / 页
    for our_key, ref_key, label in (("volume", "volume", "卷"), ("number", "issue", "期"), ("pages", "pages", "页码")):
        ours = f.get(our_key)
        theirs = ref[ref_key]
        if ours and theirs:
            checked.append(ref_key)
            if norm_pages(ours) != norm_pages(theirs) and norm_text(ours) != norm_text(theirs):
                problems.append(f"{label}不匹配：条目='{ours}' vs Crossref='{theirs}'")
        elif ours and not theirs:
            warn_problems.append(f"{label}单侧缺失（Crossref 无 {label} 数据）")

    status = "FAIL" if problems else ("WARN" if warn_problems else "OK")
    return {"status": status, "problems": problems, "warns": warn_problems, "checked": checked, "resolved_doi": doi}


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run(project_dir, json_out=None, offline=False, strict=False):
    project_dir = os.path.abspath(project_dir)
    bib_files, tex_files = [], []
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "node_modules")]
        for fn in files:
            p = os.path.join(root, fn)
            if fn.endswith(".bib"):
                bib_files.append(p)
            elif fn.endswith(".tex"):
                tex_files.append(p)

    cache_path = os.path.join(project_dir, ".citation_cache.json")
    client = CrossrefClient(cache_path, offline=offline)

    entries, cite_keys, tex_with_biblio = [], set(), []
    for p in bib_files:
        entries += parse_bib_file(p)
    for p in tex_files:
        items, text = parse_bibitems(p)
        if items:
            tex_with_biblio.append(os.path.relpath(p, project_dir))
        entries += items
        cite_keys |= collect_cite_keys(text)

    # 引用完整性
    defined_keys = {e["key"] for e in entries}
    dangling = sorted(cite_keys - defined_keys)
    uncited = sorted(k for k in defined_keys if k not in cite_keys) if cite_keys else []

    results = []
    for e in entries:
        res = audit_entry(e, client)
        results.append({
            "key": e["key"], "origin": e["origin"], **res,
            "entry_title": e["fields"].get("title", e["fields"].get("raw", ""))[:120],
        })

    n_fail = sum(1 for r in results if r["status"] == "FAIL")
    n_ok = sum(1 for r in results if r["status"] == "OK")
    dual_source = bool(bib_files and tex_with_biblio)
    n_warn = sum(1 for r in results if r["status"] == "WARN") + len(dangling) + (1 if dual_source else 0)

    report = {
        "project": project_dir,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "offline" if offline else ("online" if client.network_used else "cached"),
        "stats": {
            "total_entries": len(results),
            "fail": n_fail, "warn": n_warn, "ok": n_ok,
            "dangling_cites": dangling, "uncited_entries": uncited,
            "dual_reference_source": dual_source,
        },
        "entries": results,
    }

    # ---- 控制台输出 ----
    print("=" * 72)
    print(f"[citation-auditor] {report['timestamp']}  mode={report['mode']}")
    print(f"[*] 条目 {len(results)} 条：FAIL={n_fail}  WARN={n_warn}  OK={report['stats']['ok']}")
    print("=" * 72)
    for r in results:
        mark = {"FAIL": "[FAIL]", "WARN": "[WARN]", "OK": "[ OK ]"}[r["status"]]
        print(f"{mark} {r['key']}  ({r['origin']})  {r['entry_title']}")
        for p in r.get("problems", []):
            print(f"        -> {p}")
        for w in r.get("warns", []):
            print(f"        [WARN] {w}")
        if not r.get("problems") and not r.get("warns"):
            print("        verified:", ", ".join(r["checked"]))
    if dangling:
        print(f"[WARN] 悬空 \\cite（无对应条目）: {dangling}")
    if dual_source:
        print("[WARN] 同时存在 .bib 与 thebibliography 双参考源，应保持单一事实源")
    print("=" * 72)

    if json_out:
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"[OK] 报告已写入: {json_out}")

    if n_fail:
        return 1
    if strict and n_warn:
        return 2
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Citation Verification Gate (CrossRef forensic audit)")
    ap.add_argument("project", help="LaTeX 工程路径")
    ap.add_argument("--json", dest="json_out", default=None, help="结构化报告输出路径")
    ap.add_argument("--offline", action="store_true", help="仅使用缓存，不出网")
    ap.add_argument("--strict", action="store_true", help="WARN 也判失败")
    args = ap.parse_args()
    sys.exit(run(args.project, json_out=args.json_out, offline=args.offline, strict=args.strict))
