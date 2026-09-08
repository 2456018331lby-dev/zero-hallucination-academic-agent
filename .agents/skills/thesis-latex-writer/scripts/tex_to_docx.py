#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tex_to_docx.py - Single-Source LaTeX to Word (.docx) Conversion Pipeline

Architecture:
1. Pandoc Pipeline (Primary):
   - Converts main.tex directly to native Word docx using Pandoc.
   - Preserves mathematical formulas, cross-references, and tables.
2. Graceful Fallback Pipeline (Secondary):
   - When Pandoc is not installed on the system, outputs clear installation instructions:
     `winget install JohnMacFarlane.Pandoc`
   - Gracefully delegates to `export_to_word.py` to produce a GB/T 7713.1 compliant docx.
"""

import os
import sys
import shutil
import argparse
import subprocess

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def check_pandoc():
    p = shutil.which("pandoc")
    if p:
        return p
    # Check common Windows install paths
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Pandoc\pandoc.exe"),
        os.path.expandvars(r"%ProgramFiles%\Pandoc\pandoc.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Pandoc\pandoc.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def convert_via_pandoc(pandoc_bin, project_dir, main_tex, output_docx):
    tex_path = os.path.join(project_dir, main_tex)
    bib_path = os.path.join(project_dir, "references.bib")

    cmd = [pandoc_bin, tex_path, "-o", output_docx]
    if os.path.exists(bib_path):
        cmd += ["--citeproc", f"--bibliography={bib_path}"]

    print(f"[*] Running Pandoc: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True, errors="ignore")
    if res.returncode == 0 and os.path.exists(output_docx):
        print(f"[OK] Successfully compiled docx via Pandoc: {output_docx}")
        return True
    else:
        print(f"[-] Pandoc conversion failed: {res.stderr[:500]}", file=sys.stderr)
        return False


def fallback_export_to_word(project_dir, output_docx, scaffold=False):
    export_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "export_to_word.py"))
    if not os.path.exists(export_script):
        print(f"[-] Fallback exporter not found: {export_script}", file=sys.stderr)
        return False

    cmd = [sys.executable, export_script, "--thesis", project_dir, "--output-thesis", output_docx]
    if scaffold:
        cmd.append("--scaffold")

    print(f"[*] Executing native Python fallback exporter...")
    res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    print(res.stdout)
    if res.returncode == 0 and os.path.exists(output_docx):
        print(f"[OK] Fallback docx generated successfully: {output_docx}")
        return True
    return False


def main(project_dir=".", main_tex="main.tex", output_docx=None, scaffold=False):
    project_dir = os.path.abspath(project_dir)
    if not output_docx:
        base_name = os.path.splitext(main_tex)[0]
        output_docx = os.path.join(project_dir, f"{base_name}.docx")
    else:
        output_docx = os.path.abspath(output_docx)

    pandoc = check_pandoc()
    if pandoc:
        print(f"[*] Detected Pandoc: {pandoc}")
        success = convert_via_pandoc(pandoc, project_dir, main_tex, output_docx)
        if success:
            return True
        print("[*] Pandoc failed; trying native Python fallback...")

    # Pandoc 未安装或运行失败，给出安装指引并降级
    print("=" * 70)
    print("[-] Pandoc binary was not found in PATH or standard directories.")
    print("    Tip: To enable native Pandoc LaTeX->Docx AST compilation, run:")
    print("         winget install JohnMacFarlane.Pandoc")
    print("[*] Gracefully falling back to native Python GB/T docx engine...")
    print("=" * 70)

    return fallback_export_to_word(project_dir, output_docx, scaffold=scaffold)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LaTeX to Word docx conversion pipeline")
    parser.add_argument("project_dir", nargs="?", default=".", help="LaTeX project directory")
    parser.add_argument("main_tex", nargs="?", default="main.tex", help="Main LaTeX entry file")
    parser.add_argument("--output", dest="output_docx", default=None, help="Output docx file path")
    parser.add_argument("--scaffold", action="store_true", help="Scaffold mode: insert red warning banners")

    args = parser.parse_args()
    ok = main(args.project_dir, args.main_tex, args.output_docx, scaffold=args.scaffold)
    sys.exit(0 if ok else 1)
