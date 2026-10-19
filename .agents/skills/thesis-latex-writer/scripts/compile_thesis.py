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
import time
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
    # 必须同时抓两种形式：
    #   "in paragraph at lines A--B"  普通段落超宽
    #   "detected at line N"          独立公式 / tabular 环境超宽（LaTeX 对这类用此形式）
    # 只匹配前者会静默漏掉表格与公式的超宽——实测 ris 论文里 80.5pt 的最严重一条
    # 正是 "detected at line 49"，工具报 Severe Overfull: 0 却漏了它。
    seen = set()
    for m in re.finditer(
        r"Overfull \\hbox \(([0-9.]+)pt too wide\)[^\n]*?"
        r"(?:in paragraph at lines ([0-9]+)--([0-9]+)|detected at line ([0-9]+))",
        text,
    ):
        pt = float(m.group(1))
        if pt <= 5.0:
            continue
        if m.group(2):
            where = f"Lines {m.group(2)}-{m.group(3)}"
        else:
            where = f"Line {m.group(4)} (display/table)"
        item = f"{where}: {pt:.1f}pt overflow"
        if item not in seen:
            seen.add(item)
            overfull.append(item)

    undefined = []
    # 不能只匹配 "LaTeX Warning:" —— natbib / biblatex / hyperref 的前缀是
    # "Package natbib Warning:" 等。只认内核前缀会让 GB/T 引文路径上的未定义引用
    # 静默放行（实测：删掉 main.bbl 后参考文献整章消失，工具仍报 Undefined Refs: 0）。
    for m in re.finditer(r"(?:Reference|Citation) [`']([^`']+)'[^\n]{0,120}?undefined", text):
        ref = m.group(1)
        if ref not in undefined:
            undefined.append(ref)
    if not undefined and re.search(r"undefined (?:references|citations)", text):
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

    # 是否需要 BibTeX：main.tex 里有 \bibliography{...} 且没有手写 thebibliography。
    # 早先这里只跑两遍 xelatex，从不跑 bibtex，导致 .bib 改动永远进不了 PDF。
    bib_needed = False
    try:
        with open(os.path.join(tex_dir, tex_file), "r", encoding="utf-8", errors="ignore") as fp:
            tex_src = fp.read()
        bib_needed = bool(re.search(r"\\bibliography\{", tex_src)) and not re.search(
            r"\\begin\{thebibliography\}", tex_src
        )
    except OSError:
        pass

    print(f"[*] Running Pass 1 (XeLaTeX {tex_file})...")
    p1 = subprocess.run(cmd, cwd=tex_dir, env=env, capture_output=True, text=True, errors="ignore")

    bibtex_log = ""
    if bib_needed:
        bibtex = shutil.which("bibtex")
        if not bibtex:
            for cand in ("bibtex", "bibtex.exe"):
                probe = os.path.join(bin_dir, cand)
                if os.path.isfile(probe):
                    bibtex = probe
                    break
        if bibtex:
            print("[*] Running BibTeX (bibliography detected)...")
            # MiKTeX 25.12 的 bibtex.exe 有一个非确定性的堆损坏 bug：完全相同的调用会随机
            # 返回 rc=0（正常生成 .bbl）或 rc=3221226356 (0xC0000374 STATUS_HEAP_CORRUPTION)。
            # 崩溃时 .bbl/.blg 都是 0 字节、stdout 全空 —— 表现成「bibtex 跑了但什么都没生成」，
            # 随后所有 \cite 变成 undefined，而编译工具还以为一切正常。
            # 实测同一条命令连跑三次：rc=0 / 崩溃 / rc=0。所以不能只跑一次，必须重试，
            # 并以 .bbl 产物（存在且非空）作为成功判据，而不是只看返回码。
            bbl_path = os.path.join(tex_dir, os.path.splitext(tex_file)[0] + ".bbl")
            bib = None
            for attempt in range(4):
                bib = subprocess.run(
                    [bibtex, os.path.splitext(tex_file)[0]],
                    cwd=tex_dir, env=None, capture_output=True, text=True, errors="ignore",
                )
                if os.path.exists(bbl_path) and os.path.getsize(bbl_path) > 0:
                    if attempt:
                        print(f"    [~] BibTeX crashed {attempt} time(s) and succeeded on retry "
                              f"(MiKTeX heap-corruption bug)")
                    break
                if attempt < 3:
                    time.sleep(0.2)
            bibtex_log = (bib.stdout or "") + (bib.stderr or "") if bib else ""
            if not (os.path.exists(bbl_path) and os.path.getsize(bbl_path) > 0):
                print("    [!] BibTeX failed after 4 attempts — .bbl is empty, citations will be undefined.")
            elif "I found no \\citation" in bibtex_log or "error message" in bibtex_log.lower():
                print("    [!] BibTeX reported a problem:")
                print("    " + bibtex_log.strip().splitlines()[-1][:200])
        else:
            print("[!] BibTeX not found but \\bibliography{} is used — citations may be undefined.")

    print("[*] Running Pass 2 (XeLaTeX to resolve references and TOC)...")
    p2 = subprocess.run(cmd, cwd=tex_dir, env=env, capture_output=True, text=True, errors="ignore")

    if bib_needed:
        print("[*] Running Pass 3 (XeLaTeX after BibTeX)...")
        p3 = subprocess.run(cmd, cwd=tex_dir, env=env, capture_output=True, text=True, errors="ignore")
        if p3.returncode == 0:
            p2 = p3

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
        # 有 LaTeX 错误时 xelatex 仍会吐出一个（残缺的）PDF，早先这里只看 PDF 是否存在，
        # 于是 2 个 LaTeX Error + 14 条未定义引文也照样打印 "Successfully compiled"。
        # 现在把 errors 也算作失败信号：PDF 生成了不等于编译成功了。
        if log_summary["errors"]:
            print(f"[-] PDF produced but LaTeX reported {len(log_summary['errors'])} error(s): {pdf_path} ({size_kb:.1f} KB)")
            return False
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
