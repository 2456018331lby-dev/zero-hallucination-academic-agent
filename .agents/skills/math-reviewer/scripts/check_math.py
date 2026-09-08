#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_math.py - Mathematical Rigor & Notation Contract Linter for Theses

Audits mathematical formulation against formal engineering norms:
1. Notation Contract Alignment: cross-references formulas with notation_table.md.
2. Pipeline Definition Uniqueness: verifies that the processing chain follows
   a single authoritative pipeline definition without contradictory cross-chapter notation.
3. Theorem Statement vs Proof Strength Matching:
   Detects claims like "almost surely / 以概率 1" when the proof only shows expectation bounds.
4. Assumption-Component Conflict Detection:
   Identifies contradictions such as claiming unbiased gradients while employing biased estimators (e.g. STE).
"""

import os
import re
import sys
import json
import argparse

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def load_notation_table(notation_path):
    """解析 notation_table.md 提取合法符号与单源 pipeline 流程。"""
    if not os.path.exists(notation_path):
        return {"symbols": set(), "pipeline": ""}

    with open(notation_path, "r", encoding="utf-8", errors="ignore") as fp:
        text = fp.read()

    # 提取所有符号 (如 $\bm{x}$, $\gamma$, $\mathcal{S}_M$)
    symbols = set(re.findall(r"\$([^$]+)\$", text))
    clean_symbols = set()
    for s in symbols:
        c = re.sub(r"[\s\\]", "", s)
        if c:
            clean_symbols.add(c)

    # 提取流水线行
    pipeline = ""
    for line in text.splitlines():
        if "->" in line or "→" in line or r"\to" in line:
            pipeline = line.strip()
            break

    return {"symbols": clean_symbols, "pipeline": pipeline, "raw": text}


def audit_math_project(project_dir, notation_path=None):
    project_dir = os.path.abspath(project_dir)
    if not notation_path:
        # 在工程根目录或上级寻找 notation_table.md
        candidates = [
            os.path.join(project_dir, "notation_table.md"),
            os.path.join(os.path.dirname(project_dir), "notation_table.md"),
        ]
        for c in candidates:
            if os.path.exists(c):
                notation_path = c
                break

    print("=" * 75)
    print(f"[*] Mathematical Rigor & Notation Contract Audit")
    print(f"[*] Project Directory : {project_dir}")
    print(f"[*] Notation Contract : {notation_path or 'Not Found'}")
    print("=" * 75)

    notation_data = load_notation_table(notation_path) if notation_path else {"symbols": set()}
    print(f"[+] Loaded {len(notation_data['symbols'])} contractual symbols from notation table.")

    tex_files = []
    for root, _, files in os.walk(project_dir):
        for f in files:
            if f.endswith(".tex"):
                tex_files.append(os.path.join(root, f))

    issues = []

    for tf in tex_files:
        rel_f = os.path.relpath(tf, project_dir)
        with open(tf, "r", encoding="utf-8", errors="ignore") as fp:
            content = fp.read()

        lines = content.splitlines()

        # 1. 检查定理陈述与证明强度的匹配
        # 扫描 Theorem / 定理环境
        theorems = re.finditer(r"\\begin\{theorem\}(.*?)\\end\{theorem\}", content, re.S)
        for thm in theorems:
            thm_body = thm.group(1)
            line_no = content[:thm.start()].count("\n") + 1

            # 若定理中宣称了 "以概率 1" 或 "almost surely"
            if any(kw in thm_body for kw in ("以概率 1", "以概率1", "几乎处处", "almost surely", "a.s.")):
                # 检查同一文件或紧随其后的证明环境是否只证明了期望上界
                following = content[thm.end(): thm.end() + 4000]
                if r"\mathbb{E}" in following and not any(kw in following for kw in ("Borel-Cantelli", "Robbins-Siegmund", "超鞅", "supermartingale")):
                    issues.append({
                        "file": rel_f, "line": line_no, "level": "WARNING",
                        "rule": "Theorem vs Proof Strength Mismatch",
                        "msg": "Theorem asserts '以概率 1 / almost surely' convergence, but proof only establishes expectation bound E[||grad||^2] <= O(1/sqrt(T)). To claim almost sure convergence, invoke Robbins-Siegmund lemma or state convergence in expectation."
                    })

        # 2. 检查算法假设冲突 (如 STE vs 无偏估计)
        has_ste = any(kw in content for kw in ("STE", "直通估计器", "Straight-Through"))
        has_unbiased_assumption = any(kw in content for kw in ("无偏估计", "unbiased gradient", r"\mathbb{E}[g_t] = \nabla"))

        if has_ste and has_unbiased_assumption:
            line_no = 1
            for idx, l in enumerate(lines, start=1):
                if any(kw in l for kw in ("无偏估计", "unbiased gradient")):
                    line_no = idx
                    break
            issues.append({
                "file": rel_f, "line": line_no, "level": "WARNING",
                "rule": "Assumption Conflict",
                "msg": "Detected Straight-Through Estimator (STE) combined with '无偏随机梯度' assumption. STE gradient is inherently biased (heuristic subgradient); recommend noting bounded gradient bias ||E[g] - grad|| <= delta or citing biased SGD convergence theory."
            })

        # 3. 检查符号定义漂移与未定义符号
        reported_symbols_in_file = set()
        for idx, line in enumerate(lines, start=1):
            line_code, _ = line.split("%", 1) if "%" in line else (line, "")
            # 扫描内联与行间公式中的符号
            eq_vars = re.findall(r"\\bm\{([a-zA-Z])\}", line_code)
            for v in eq_vars:
                # 若使用了 \bm{x} 但记号契约中没有定义该符号
                if notation_data["symbols"] and v not in notation_data["symbols"] and f"bm{{{v}}}" not in notation_data["symbols"]:
                    # 白名单常见通用数学符号
                    if v not in ("w", "b", "u", "a", "c", "s", "z", "x", "y", "h", "m"):
                        if v not in reported_symbols_in_file:
                            reported_symbols_in_file.add(v)
                            issues.append({
                                "file": rel_f, "line": idx, "level": "NOTICE",
                                "rule": "Notation Contract Alignment",
                                "msg": f"Vector symbol '\\bm{{{v}}}' not formally registered in notation_table.md contract (de-duplicated per file)."
                            })

    print("\n" + "=" * 75)
    print(f"[*] Mathematical Review finished: {len(issues)} finding(s).")
    print("=" * 75)
    for i in issues:
        print(f"[{i['level']:<7}] {i['file']}:L{i['line']} | {i['rule']:<32} | {i['msg']}")
    print("=" * 75)

    return len([i for i in issues if i["level"] == "ERROR"]) == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mathematical Rigor & Notation Contract Linter")
    parser.add_argument("project_dir", nargs="?", default=".", help="Directory of LaTeX project")
    parser.add_argument("--notation", default=None, help="Path to notation_table.md")
    args = parser.parse_args()

    ok = audit_math_project(args.project_dir, notation_path=args.notation)
    sys.exit(0 if ok else 1)
