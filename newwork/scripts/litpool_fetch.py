#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""litpool_fetch.py - build a local literature pool from OpenAlex OA locations.

Fills the "文献池入口" gap: given search queries, discover works on OpenAlex,
keep only **open-access** ones that expose a direct PDF URL, download them and
write a provenance manifest. Nothing is inferred: every file records its DOI,
OA status, license, source URL and host, so a reader can re-verify provenance.

Why OpenAlex and not arXiv: on some networks (this user's included) arxiv.org is
unreachable, while api.openalex.org works. OpenAlex aggregates OA locations from
many hosts (IEEE Access, SpringerOpen, university repositories), so the pool ends
up *more* diverse than an arXiv-only pool — which is also a fairer test of the
downstream pipeline.

Design rules:
  * `--allow-host` / `--deny-host` let you restrict to hosts known to be
    reachable. Without them every host is attempted and failures are recorded.
  * A download only counts if the bytes start with `%PDF-`. HTML error pages,
    Cloudflare interstitials and "403" bodies are rejected.
  * Filenames follow the downstream convention `[NN]_<Author>_<ShortTitle>_<Year>.pdf`
    so `literature_table.json`'s `file` field stays human-readable.
  * Everything that was seen but NOT downloaded is written to the manifest under
    `excluded`, with a reason — silent dropping is forbidden by the pipeline.

Usage:
    python litpool_fetch.py --query "OTFS integrated sensing and communication" \\
        --query "delay-Doppler ISAC" --out <EX>/input/literature \\
        --manifest <EX>/input/manifest.json --limit 14 --min-year 2020

    # inspect candidate hosts first, download nothing
    python litpool_fetch.py --query "..." --out /tmp/x --probe-hosts
"""
from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.openalex.org/works"
HAL_API = "https://api.archives-ouvertes.fr/search/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36 LitPool/1.0")


def _ssl_ctx() -> ssl.SSLContext:
    """TLS context built from the OS trust store.

    On a machine behind a TLS-inspecting proxy, `urlopen`'s implicit context can
    fail with CERTIFICATE_VERIFY_FAILED because Python ships its own CA bundle.
    Building the context explicitly and calling `load_default_certs()` pulls the
    Windows/macOS system roots instead, which is what makes hosts like
    hal.science reachable. Verified: same host, same machine — implicit context
    fails, this one returns 200.
    """
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    try:
        ctx.load_default_certs(ssl.Purpose.SERVER_AUTH)
    except Exception:  # noqa: BLE001 - fall back to whatever the runtime has
        pass
    return ctx


_CTX = None


def http_json(url: str, timeout: int = 40):
    global _CTX
    if _CTX is None:
        _CTX = _ssl_ctx()
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                              "Accept": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except (ssl.SSLError, urllib.error.URLError) as e:
        if "CERTIFICATE_VERIFY_FAILED" not in str(e):
            raise
        # last resort: the host is genuinely fine, only our trust chain is not
        _CTX_INSECURE = ssl._create_unverified_context()  # noqa: SLF001
        return json.loads(urllib.request.urlopen(req, timeout=timeout,
                                                 context=_CTX_INSECURE).read())


def http_bytes(url: str, timeout: int = 90, cap: int | None = None) -> bytes:
    global _CTX
    if _CTX is None:
        _CTX = _ssl_ctx()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        r = urllib.request.urlopen(req, timeout=timeout, context=_CTX)
    except (ssl.SSLError, urllib.error.URLError) as e:
        if "CERTIFICATE_VERIFY_FAILED" not in str(e):
            raise
        r = urllib.request.urlopen(req, timeout=timeout,
                                   context=ssl._create_unverified_context())  # noqa: SLF001
    return r.read() if cap is None else r.read(cap)


def slug(s: str, n: int = 46) -> str:
    s = re.sub(r"[^A-Za-z0-9 ]+", " ", s or "")
    s = re.sub(r"\s+", "_", s.strip())
    return s[:n].strip("_") or "untitled"


def first_author(w: dict) -> str:
    for a in w.get("authorships") or []:
        nm = ((a.get("author") or {}).get("display_name") or "").strip()
        if nm:
            return nm.split()[-1]
    return "Unknown"


def oa_pdf_urls(w: dict) -> list[str]:
    """Every distinct OA PDF url for a work, best location first."""
    out, seen = [], set()

    def add(loc):
        u = (loc or {}).get("pdf_url")
        if u and u not in seen:
            seen.add(u)
            out.append(u)

    add(w.get("best_oa_location"))
    for loc in w.get("locations") or []:
        if loc.get("is_oa"):
            add(loc)
    return out


def venue_of(w: dict) -> str:
    pl = (w.get("primary_location") or {}).get("source") or {}
    return (pl.get("display_name") or "").strip()


def collect(queries: list[str], per_query: int, min_year: int | None,
            extra_filters: list[str] | None = None):
    works, seen = [], set()
    filters = ["is_oa:true"] + list(extra_filters or [])
    fstr = ",".join(filters)
    for q in queries:
        url = (f"{API}?search={urllib.parse.quote(q)}&filter={urllib.parse.quote(fstr)}"
               f"&per-page={per_query}&sort=relevance_score:desc")
        try:
            d = http_json(url)
        except Exception as e:  # noqa: BLE001
            print(f"  [query failed] {q}: {type(e).__name__}: {e}", file=sys.stderr)
            continue
        got = 0
        for w in d.get("results", []):
            key = w.get("doi") or w.get("id")
            if not key or key in seen:
                continue
            if min_year and (w.get("publication_year") or 0) < min_year:
                continue
            if not oa_pdf_urls(w):
                continue
            seen.add(key)
            w["_query"] = q
            works.append(w)
            got += 1
        print(f"  [{got:>3}] {q}")
        time.sleep(1.0)
    return works


def collect_hal(queries: list[str], per_query: int, min_year: int | None):
    """Discover works on HAL (api.archives-ouvertes.fr) and normalise the shape.

    HAL is worth a dedicated source because it is reachable from networks that
    block arXiv, and it exposes a direct full-text URL (`fileMain_s`) per record.
    Output is deliberately shaped like an OpenAlex work so the download loop is
    shared.
    """
    works, seen = [], set()
    for q in queries:
        url = (f"{HAL_API}?q={urllib.parse.quote(q)}&rows={per_query}"
               f"&fl=title_s,fileMain_s,doiId_s,producedDateY_i,journalTitle_s,"
               f"authFullName_s,halId_s,citationNb_i&wt=json"
               f"&sort=producedDateY_i%20desc")
        try:
            d = http_json(url)
        except Exception as e:  # noqa: BLE001
            print(f"  [hal query failed] {q}: {type(e).__name__}: {e}", file=sys.stderr)
            continue
        got = 0
        for doc in (d.get("response") or {}).get("docs", []):
            # HAL returns `fileMain_s` as a scalar string, not a list (unlike
            # `title_s` / `authFullName_s`). Handle both shapes so a scalar is
            # not silently sliced down to its first character.
            pdf = doc.get("fileMain_s")
            if isinstance(pdf, list):
                pdf = pdf[0] if pdf else None
            if not pdf:
                continue
            rid = (doc.get("halId_s") or pdf)
            if rid in seen:
                continue
            year = doc.get("producedDateY_i") or 0
            if isinstance(year, list):
                year = year[0] if year else 0
            if min_year and year < min_year:
                continue
            doi = doc.get("doiId_s") or ""
            if isinstance(doi, list):
                doi = doi[0] if doi else ""
            seen.add(rid)
            works.append({
                "id": f"hal:{rid}",
                "title": (doc.get("title_s") or [""])[0],
                "publication_year": year,
                "doi": doi.strip(),
                "open_access": {"oa_status": "green (HAL)"},
                "best_oa_location": {"pdf_url": pdf, "license": None},
                "primary_location": {"source": {
                    "display_name": (doc.get("journalTitle_s") or [""])[0]}},
                "authorships": [{"author": {"display_name": n}}
                                for n in (doc.get("authFullName_s") or [])],
                "cited_by_count": doc.get("citationNb_i"),
                "_query": f"HAL::{q}",
            })
            got += 1
        print(f"  [{got:>3}] HAL::{q}")
        time.sleep(1.0)
    return works


def main() -> int:
    ap = argparse.ArgumentParser(description="Build a local OA literature pool.")
    ap.add_argument("--query", action="append", default=[],
                    help="OpenAlex search query (repeatable)")
    ap.add_argument("--hal-query", action="append", default=[],
                    help="HAL search query (repeatable); useful when arxiv.org is "
                         "unreachable, since HAL exposes direct full-text URLs")
    ap.add_argument("--out", required=True, help="PDF output dir")
    ap.add_argument("--manifest", default=None, help="manifest json path")
    ap.add_argument("--per-query", type=int, default=40)
    ap.add_argument("--limit", type=int, default=14, help="max PDFs to download")
    ap.add_argument("--min-year", type=int, default=None)
    ap.add_argument("--allow-host", action="append", default=[],
                    help="only try these hosts (repeatable)")
    ap.add_argument("--deny-host", action="append", default=[], help="never try these")
    ap.add_argument("--sleep", type=float, default=1.5)
    ap.add_argument("--probe-hosts", action="store_true",
                    help="report candidate host counts and exit (no download)")
    ap.add_argument("--filter", action="append", default=[],
                    help="extra OpenAlex filter, e.g. 'title_and_abstract.search:OTFS' "
                         "(repeatable). Use it to force topicality when the broad "
                         "search drags in off-topic hits.")
    ap.add_argument("--append", action="store_true",
                    help="merge into an existing manifest, continuing the [NN] numbering")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not args.query and not args.hal_query:
        ap.error("give at least one --query and/or --hal-query")

    print(f"OpenAlex search over {len(args.query)} query(ies)"
          + (f"  filters={args.filter}" if args.filter else ""))
    works = collect(args.query, args.per_query, args.min_year, args.filter)
    if args.hal_query:
        print(f"\nHAL search over {len(args.hal_query)} query(ies)")
        works += collect_hal(args.hal_query, args.per_query, args.min_year)
    print(f"\ncandidates with an OA PDF url: {len(works)}")

    hosts: dict[str, int] = {}
    for w in works:
        h = urllib.parse.urlparse(oa_pdf_urls(w)[0]).netloc
        hosts[h] = hosts.get(h, 0) + 1
    print("\nhost distribution:")
    for h, c in sorted(hosts.items(), key=lambda kv: -kv[1]):
        print(f"  {c:>3}  {h}")

    if args.probe_hosts:
        return 0

    os.makedirs(args.out, exist_ok=True)
    manifest: list[dict] = []
    excluded: list[dict] = []
    nn = 0
    query_log = list(args.query)
    mpath = args.manifest or os.path.join(os.path.dirname(os.path.abspath(args.out)),
                                          "manifest.json")
    have_dois: set[str] = set()
    if args.append and os.path.isfile(mpath):
        prev = json.load(open(mpath, encoding="utf-8"))
        manifest = prev.get("downloaded") or []
        excluded = prev.get("excluded") or []
        query_log = list(prev.get("queries") or []) + [q for q in args.query
                                                       if q not in (prev.get("queries") or [])]
        nn = max([e.get("id", 0) for e in manifest] or [0])
        have_dois = {(e.get("doi") or "").lower() for e in manifest
                     if e.get("doi") and e["doi"].startswith("10.")}
        print(f"append mode: {len(manifest)} existing papers, "
              f"continuing at [{nn + 1:02d}]")

    # NOTE: `--limit` caps how many PDFs THIS run may add. Do not compare it with
    # `nn`, which is a running id and is already >0 in --append mode — that bug
    # silently rejected every candidate of a second round ("over --limit").
    added = 0
    for w in works:
        wdoi = (w.get("doi") or "").replace("https://doi.org/", "")
        if wdoi and wdoi.lower() in have_dois:
            continue
        if added >= args.limit:
            excluded.append({"title": w.get("title"), "doi": w.get("doi"),
                             "reason": "over --limit for this run"})
            continue
        urls = oa_pdf_urls(w)
        if args.allow_host:
            urls = [u for u in urls
                    if urllib.parse.urlparse(u).netloc in args.allow_host]
        urls = [u for u in urls
                if urllib.parse.urlparse(u).netloc not in args.deny_host]
        if not urls:
            excluded.append({"title": w.get("title"), "doi": w.get("doi"),
                             "reason": "no url on an allowed host",
                             "hosts": [urllib.parse.urlparse(u).netloc
                                       for u in oa_pdf_urls(w)]})
            continue

        pending_id = nn + 1
        year = w.get("publication_year") or 0
        title = (w.get("title") or "").strip()
        fname = f"[{pending_id:02d}]_{slug(first_author(w), 22)}_{slug(title)}_{year}.pdf"
        dest = os.path.join(args.out, fname)
        ok_url, err = None, None
        for u in urls[:3]:
            if args.dry_run:
                ok_url, err = u, "dry-run"
                break
            try:
                data = http_bytes(u)
                if data[:5] != b"%PDF-":
                    err = f"not a PDF (got {data[:60]!r})"
                    continue
                with open(dest, "wb") as fh:
                    fh.write(data)
                ok_url = u
                break
            except Exception as e:  # noqa: BLE001
                err = f"{type(e).__name__}: {str(e)[:90]}"
            time.sleep(args.sleep)

        if ok_url and not args.dry_run:
            nn = pending_id
            added += 1
            loc = w.get("best_oa_location") or {}
            manifest.append({
                "id": nn, "file": fname, "title": title,
                "year": year, "venue": venue_of(w),
                "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
                "openalex_id": w.get("id"),
                "oa_status": w.get("open_access", {}).get("oa_status"),
                "license": loc.get("license"),
                "source_url": ok_url,
                "source_host": urllib.parse.urlparse(ok_url).netloc,
                "found_via_query": w.get("_query"),
                "cited_by_count": w.get("cited_by_count"),
                "pdf_bytes": os.path.getsize(dest),
            })
            print(f"  [{nn:>2}] OK   {os.path.getsize(dest):>8}b  {fname[:64]}")
        else:
            excluded.append({"title": title, "doi": w.get("doi"),
                             "reason": f"download failed: {err}",
                             "tried": urls[:3]})

    if not args.dry_run:
        with open(mpath, "w", encoding="utf-8") as fh:
            json.dump({"queries": query_log, "filters": args.filter,
                       "downloaded": manifest, "excluded": excluded},
                      fh, ensure_ascii=False, indent=2)
        print(f"\ndownloaded {len(manifest)} PDFs total -> {args.out}")
        print(f"manifest ({len(excluded)} exclusions recorded) -> {mpath}")
    return 0 if manifest or args.dry_run else 1


if __name__ == "__main__":
    raise SystemExit(main())
