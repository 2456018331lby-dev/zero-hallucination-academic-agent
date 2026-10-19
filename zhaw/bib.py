"""`zhaw bib <project>` — rebuild references.bib from Crossref.

This closes the loop on the project's hardest rule: **never write an `author`
field from memory**. The command does not trust the existing `.bib`; it resolves
every entry against Crossref (by DOI first, then by title) and emits a new
`.bib` whose bibliographic fields are the API's, not the model's.
"""
from __future__ import annotations

import importlib.util
import re
import shutil
from pathlib import Path

from ._paths import repo_root, script
from ._util import now_iso, read_text, write_json, write_text


def _load_check_citations():
    path = script("citation-auditor/scripts/check_citations.py")
    spec = importlib.util.spec_from_file_location("zhaw_check_citations", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"[zhaw bib] cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fmt_authors(authors: list[dict]) -> str:
    parts = []
    for a in authors:
        family = (a.get("family") or "").strip()
        given = (a.get("given") or "").strip()
        if not family:
            continue
        parts.append(f"{family}, {given}" if given else family)
    return " and ".join(parts)


def _fmt_pages(pages: str) -> str:
    s = (pages or "").strip()
    if not s:
        return ""
    return re.sub(r"\s*[-\u2013\u2014]\s*", "--", s)


def _pick_type(entry_type: str, container: str, doi: str) -> str:
    et = (entry_type or "").lower()
    if et in {"article", "inproceedings", "conference", "book", "misc", "techreport"}:
        return et
    low = (container or "").lower()
    if doi and ("arxiv" not in low):
        return "article"
    if any(k in low for k in ("conference", "symposium", "workshop", "proc")):
        return "inproceedings"
    return "article"


def _render_entry(key: str, etype: str, fields: dict) -> str:
    order = ["author", "title", "journal", "booktitle", "publisher", "year",
             "volume", "number", "pages", "doi", "url", "note"]
    lines = [f"@{etype}{{{key},"]
    for name in order:
        value = fields.get(name)
        if not value:
            continue
        lines.append(f"  {name:<9} = {{{value}}},")
    for name, value in fields.items():
        if name in order or not value:
            continue
        lines.append(f"  {name:<9} = {{{value}}},")
    if len(lines) > 1:
        lines[-1] = lines[-1].rstrip(",")
    lines.append("}")
    return "\n".join(lines)


def _fields_from_crossref(ref: dict, etype: str) -> dict:
    fields = {
        "author": _fmt_authors(ref.get("authors") or []),
        "title": (ref.get("title") or "").strip(),
        "year": str(ref.get("year") or ""),
        "volume": (ref.get("volume") or "").strip(),
        "number": (ref.get("issue") or "").strip(),
        "pages": _fmt_pages(ref.get("pages") or ""),
        "doi": (ref.get("doi") or "").strip(),
    }
    container = (ref.get("container") or "").strip()
    if etype == "inproceedings":
        fields["booktitle"] = container
    else:
        fields["journal"] = container
    return {k: v for k, v in fields.items() if v}


def rebuild(
    project: Path,
    bib: Path | None = None,
    apply: bool = False,
    offline: bool = False,
    cache: Path | None = None,
) -> dict:
    project = Path(project).resolve()
    bib_path = Path(bib) if bib else project / "references.bib"
    if not bib_path.exists():
        raise SystemExit(f"[zhaw bib] no .bib file at {bib_path}")

    cc = _load_check_citations()
    cache_path = Path(cache) if cache else project / ".citation_cache.json"
    client = cc.CrossrefClient(cache_path=str(cache_path), offline=offline)

    entries = cc.parse_bib_file(str(bib_path))
    results = []
    rendered: list[str] = []

    for entry in entries:
        key = entry["key"]
        f = entry["fields"]
        doi = cc.norm_doi(f.get("doi", ""))
        title = f.get("title", "")
        item = None
        how = ""

        if doi:
            item = client.by_doi(doi)
            how = "doi"
            if item is None:
                kind = client.doi_error_kind(doi) or "network"
                results.append({
                    "key": key, "status": "NO_MATCH" if kind == "not_found" else "NETWORK",
                    "how": "doi", "doi": doi,
                    "detail": "Crossref 无此 DOI" if kind == "not_found" else "网络异常，未能核验",
                })
                rendered.append(_render_entry(key, entry["type"] or "article", f))
                continue
        elif title:
            authors, _ = cc.parse_authors(f.get("author", ""))
            item, ratio, err = client.by_title(title, authors=authors)
            how = "title"
            if err or item is None or (ratio is not None and ratio < cc.TITLE_MATCH_THRESHOLD):
                results.append({
                    "key": key,
                    "status": "NETWORK" if err else "NO_MATCH",
                    "how": "title", "title": title,
                    "detail": "标题检索无命中或相似度过低" if not err else "网络异常",
                })
                rendered.append(_render_entry(key, entry["type"] or "article", f))
                continue
        else:
            results.append({"key": key, "status": "SKIPPED", "how": "",
                            "detail": "条目既无 doi 也无 title"})
            rendered.append(_render_entry(key, entry["type"] or "article", f))
            continue

        ref = cc.crossref_fields(item)
        etype = _pick_type(entry["type"], ref.get("container") or "", ref.get("doi") or "")
        new_fields = _fields_from_crossref(ref, etype)

        changed = []
        for name in ("author", "title", "year", "volume", "number", "pages", "doi"):
            old = re.sub(r"\s+", " ", (f.get(name) or "")).strip()
            new = re.sub(r"\s+", " ", (new_fields.get(name) or "")).strip()
            if old != new:
                changed.append({"field": name, "old": old, "new": new})

        results.append({
            "key": key,
            "status": "UPDATED" if changed else "UNCHANGED",
            "how": how,
            "doi": new_fields.get("doi", ""),
            "changed": changed,
        })
        rendered.append(_render_entry(key, etype, new_fields))

    header = (
        "% =============================================================================\n"
        "% references.bib — 由 `zhaw bib` 从 Crossref 回填生成\n"
        f"% 生成时间: {now_iso()}\n"
        f"% 源文件: {bib_path.name}\n"
        f"% 条目数: {len(entries)}\n"
        "%\n"
        "% 铁律: author / title / 卷期页 全部来自 Crossref API，禁止凭记忆修改。\n"
        "% 复核: zhaw gate1 <project> --offline\n"
        "% =============================================================================\n\n"
    )
    new_text = header + "\n\n".join(rendered) + "\n"

    out_path = bib_path.with_suffix(".rebuilt.bib")
    write_text(out_path, new_text)

    report = {
        "generated_at": now_iso(),
        "source_bib": str(bib_path),
        "output_bib": str(out_path),
        "offline": offline,
        "entries": len(entries),
        "updated": sum(1 for r in results if r["status"] == "UPDATED"),
        "unchanged": sum(1 for r in results if r["status"] == "UNCHANGED"),
        "no_match": sum(1 for r in results if r["status"] == "NO_MATCH"),
        "network": sum(1 for r in results if r["status"] == "NETWORK"),
        "skipped": sum(1 for r in results if r["status"] == "SKIPPED"),
        "applied": False,
        "details": results,
    }

    if apply:
        backup = bib_path.with_suffix(".bib.bak")
        shutil.copy2(bib_path, backup)
        shutil.copy2(out_path, bib_path)
        report["applied"] = True
        report["backup"] = str(backup)

    write_json(project / "bib_report.json", report)
    return report


def summary(report: dict) -> str:
    total = report["entries"]
    bad = report["no_match"] + report["network"] + report["skipped"]
    if bad == 0:
        status = "PASS"
    elif report["network"] and bad == report["network"]:
        status = "WARN"
    else:
        status = "FAIL"
    return (
        f"{status}: {report['updated']} 条按 Crossref 回填, "
        f"{report['unchanged']} 条本来就一致, "
        f"{report['no_match']} 条查无此文, {report['network']} 条网络异常, "
        f"{report['skipped']} 条跳过 (共 {total} 条)"
    )
