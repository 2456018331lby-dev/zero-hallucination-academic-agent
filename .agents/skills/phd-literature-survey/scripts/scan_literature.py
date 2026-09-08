#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scan_literature.py - PhD Literature Survey Pre-processor
Scans a target directory for PDF/MD/TXT papers, extracts titles, authors, abstracts,
and years using fitz (PyMuPDF) or pdfplumber, and outputs a structured intake inventory.
"""

import os
import sys
import json
import re

EXCLUDE_DIRS = {
    "node_modules", ".git", "dist", "build", ".next", ".nuxt",
    ".gemini", ".codex", ".claude", ".agents", ".system_generated",
    "vendor", "__pycache__", ".venv", "venv"
}

def extract_pdf_metadata(pdf_path):
    entry = {
        "file": os.path.basename(pdf_path),
        "path": os.path.abspath(pdf_path),
        "pages": 0,
        "title": "",
        "authors": "",
        "year": "文献未说明",
        "venue": "文献未说明",
        "abstract": "",
        "sections": [],
        "status": "ok"
    }
    
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        entry["pages"] = len(doc)
        
        meta = doc.metadata or {}
        if meta.get("title") and len(meta["title"].strip()) > 3:
            entry["title"] = meta["title"].strip()
        if meta.get("author") and len(meta["author"].strip()) > 2:
            entry["authors"] = meta["author"].strip()
            
        first_pages_text = ""
        for i in range(min(3, len(doc))):
            first_pages_text += doc[i].get_text() + "\n"
        doc.close()
        
        lines = [l.strip() for l in first_pages_text.splitlines() if l.strip()]
        if not entry["title"] and lines:
            entry["title"] = lines[0]
            
        abs_match = re.search(r'(?i)abstract[:\s]*(.*?)(?=(?:1\.?\s+introduction|introduction|keywords|\n\n[A-Z]))', first_pages_text, re.DOTALL)
        if abs_match:
            entry["abstract"] = " ".join(abs_match.group(1).split())[:1200]
        else:
            entry["abstract"] = " ".join(first_pages_text[:800].split())
            
        year_match = re.search(r'(?:19|20)\d{2}', first_pages_text[:2000])
        if year_match:
            entry["year"] = year_match.group(0)
            
        venue_patterns = [
            r'(CVPR|ICCV|ECCV|NeurIPS|ICML|ICLR|AAAI|IJCAI|ACL|EMNLP|NAACL|KDD|SIGIR|TPAMI|T-PAMI|TIP|TMM)\s*(20\d{2})?',
            r'arXiv:\d{4}\.\d{4,5}'
        ]
        for pat in venue_patterns:
            vm = re.search(pat, first_pages_text[:2000], re.IGNORECASE)
            if vm:
                entry["venue"] = vm.group(0)
                break
                
    except Exception as e:
        entry["status"] = f"error: {str(e)}"
        
    return entry

def scan_literature(directory="."):
    supported = (".pdf", ".md", ".txt")
    results = []
    
    for root, dirs, files in os.walk(directory):
        # Prune unwanted directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]
        
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in supported:
                # Skip package/readme files that aren't literature
                lower_f = f.lower()
                if lower_f in ("readme.md", "readme_cn.md", "license", "package.json", "agents.md", "claude.md", "design.md"):
                    continue
                full_path = os.path.join(root, f)
                if ext == ".pdf":
                    results.append(extract_pdf_metadata(full_path))
                else:
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                            raw = fp.read()
                        first_line = raw.splitlines()[0] if raw.splitlines() else f
                        results.append({
                            "file": f,
                            "path": os.path.abspath(full_path),
                            "pages": 1,
                            "title": first_line.lstrip("#").strip(),
                            "authors": "文献未说明",
                            "year": "文献未说明",
                            "venue": "文献未说明",
                            "abstract": " ".join(raw[:800].split()),
                            "sections": [],
                            "status": "ok"
                        })
                    except Exception as e:
                        results.append({"file": f, "path": full_path, "status": f"error: {str(e)}"})
                        
    return results

if __name__ == "__main__":
    scan_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    print(f"[*] Scanning literature in: {os.path.abspath(scan_dir)}")
    papers = scan_literature(scan_dir)
    print(f"[*] Discovered {len(papers)} candidate literature files.")
    
    out_file = os.path.join(scan_dir, "literature_inventory.json")
    with open(out_file, "w", encoding="utf-8") as fp:
        json.dump(papers, fp, ensure_ascii=False, indent=2)
    print(f"[+] Output written to: {out_file}")
