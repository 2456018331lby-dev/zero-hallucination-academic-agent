#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compile_thesis.py - Dual-Pass XeLaTeX Compiler & Post-Processing Linter

Features:
- Automatically detects XeLaTeX binaries via PATH, %LOCALAPPDATA%, %ProgramFiles%, or TeX Live.
  Zero hardcoded user usernames.
- Dual-pass compilation resolving cross-references, citations, and table of contents.
- Post-compilation log analysis summarizing LaTeX errors, Overfull \\hbox (>5pt), and undefined references.
- --strict mode: exits with code 2 if severe overfull hboxes or undefined references exist.
"""

import os
import re
import sys
import shutil
import argparse
import subprocess

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def find_xelatex():
    # 1. System PATH
    which_path = shutil.which("xelatex")
    if which_path:
        return which_path

    # 2. Generic Windows installation roots
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64\xelatex.exe"),
        os.path.expandvars(r"%ProgramFiles%\MiKTeX\miktex\bin\x64\xelatex.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\MiKTeX\miktex\bin\x64\xelatex.exe"),
        r"C:\texlive\2026\bin\windows\xelatex.exe",
        r"C:\texlive\2025\bin\windows\xelatex.exe",
        r"C:\texlive\2024\bin\windows\xelatex.exe",
        r"C:\texlive\2023\bin\windows\xelatex.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def parse_compilation_log(log_path):
    """解析 .log 文件，提取错误、Overfull 溢出与未定义引用。"""
    if not os.path.exists(log_path):
        return {"errors": [], "overfull": [], "undefined": []}

    with open(log_path, "r", encoding="utf-8", errors="ignore") as fp:
        text = fp.read()

    errors = []
    for m in re.finditer(r"(?:! LaTeX Error:|! Package \w+ Error:)\s*(.*?)(?=\n\s*\n|\n!)", text, re.S):
        errors.append(m.group(0).strip().replace("\n", " ")[:120])

    overfull = []
    for m in re.finditer(r"Overfull \\hbox \(([0-9.]+)pt too wide\) in paragraph at lines ([0-9]+)--([0-9]+)", text):
        pt = float(m.group(1))
        if pt > 5.0:
            overfull.append(f"Lines {m.group(2)}-{m.group(3)}: {pt:.1f}pt overflow")

    undefined = []
    for m in re.finditer(r"LaTeX Warning: (?:Reference `([^']+)' on page \d+ undefined|Citation `([^']+)' on page \d+ undefined)", text):
        ref = m.group(1) or m.group(2)
        undefined.append(ref)

    if "There were undefined references" in text and not undefined:
        undefined.append("(General undefined references flagged)")

    return {"errors": errors, "overfull": overfull, "undefined": undefined}


def compile_pdf(tex_dir, tex_file="main.tex", strict=False):
    tex_dir = os.path.abspath(tex_dir)
    xelatex = find_xelatex()
    if not xelatex:
        print("[-] XeLaTeX executable not found in PATH or standard installation roots.", file=sys.stderr)
        return False

    print(f"[*] Found XeLaTeX compiler: {xelatex}")
    env = os.environ.copy()
    bin_dir = os.path.dirname(xelatex)
    env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")

    cmd = [xelatex, "-interaction=nonstopmode", "-synctex=1", tex_file]

    print(f"[*] Running Pass 1 (XeLaTeX {tex_file})...")
    p1 = subprocess.run(cmd, cwd=tex_dir, env=env, capture_output=True, text=True, errors="ignore")

    print("[*] Running Pass 2 (XeLaTeX to resolve references and TOC)...")
    p2 = subprocess.run(cmd, cwd=tex_dir, env=env, capture_output=True, text=True, errors="ignore")

    pdf_name = os.path.splitext(tex_file)[0] + ".pdf"
    pdf_path = os.path.join(tex_dir, pdf_name)
    log_name = os.path.splitext(tex_file)[0] + ".log"
    log_path = os.path.join(tex_dir, log_name)

    # 日志分析
    log_summary = parse_compilation_log(log_path)

    print("\n" + "=" * 70)
    print(f"[*] Compilation Log Summary for {log_name}:")
    print(f"    - LaTeX Errors      : {len(log_summary['errors'])}")
    print(f"    - Severe Overfull   : {len(log_summary['overfull'])}")
    print(f"    - Undefined Refs    : {len(log_summary['undefined'])}")

    for err in log_summary['errors'][:5]:
        print(f"      [!] Error: {err}")
    for ovf in log_summary['overfull'][:5]:
        print(f"      [~] {ovf}")
    if log_summary['undefined']:
        print(f"      [?] Undefined: {', '.join(log_summary['undefined'][:8])}")
    print("=" * 70)

    if os.path.exists(pdf_path):
        size_kb = os.path.getsize(pdf_path) / 1024
        print(f"[OK] Successfully compiled PDF: {pdf_path} ({size_kb:.1f} KB)")
        if strict and (log_summary["overfull"] or log_summary["undefined"]):
            print("[-] Strict mode failure: severe overfull boxes or undefined references present.", file=sys.stderr)
            return False
        return True
    else:
        print("[-] PDF compilation failed. Log snippet:", file=sys.stderr)
        print(p2.stdout[-1200:], file=sys.stderr)
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="One-Click Dual-Pass XeLaTeX Compiler")
    parser.add_argument("project_dir", nargs="?", default=".", help="Directory containing LaTeX project")
    parser.add_argument("tex_file", nargs="?", default="main.tex", help="Main LaTeX entrance file")
    parser.add_argument("--strict", action="store_true", help="Fail if overfull > 5pt or undefined references exist")

    args = parser.parse_args()
    success = compile_pdf(args.project_dir, args.tex_file, strict=args.strict)
    sys.exit(0 if success else 1)
