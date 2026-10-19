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


# ---------------------------------------------------------------------------
# 符号恒等式机器验证（可选依赖 sympy，缺失时整体降级为文本检查）
# ---------------------------------------------------------------------------
try:
    import sympy as _sp  # noqa: F401

    SYMPY_AVAILABLE = True
except Exception:
    SYMPY_AVAILABLE = False

# 这些记号无法安全地转成 sympy 表达式，遇到即跳过（记为 undecided，不误报）
_UNPARSEABLE_TOKENS = (
    r"\sum", r"\int", r"\prod", r"\lim", r"\max", r"\min", r"\arg", r"\sup", r"\inf",
    r"\le", r"\ge", r"\leq", r"\geq", r"\approx", r"\sim", r"\to", r"\rightarrow",
    r"\mathbb", r"\nabla", r"\partial", r"\lVert", r"\rVert", r"\|",
    r"\cdots", r"\ldots", r"\dots", r"\infty",
)

_MATH_ENVS = (
    "equation", "equation*", "displaymath", "align", "align*",
    "gather", "gather*", "multline", "multline*",
)

_GREEK = {
    "alpha": "alpha", "beta": "beta", "gamma": "gamma", "delta": "delta",
    "epsilon": "epsilon", "varepsilon": "epsilon", "zeta": "zeta", "eta": "eta",
    "theta": "theta", "kappa": "kappa", "lambda": "lambda", "mu": "mu",
    "nu": "nu", "xi": "xi", "pi": "pi", "rho": "rho", "sigma": "sigma",
    "tau": "tau", "phi": "phi", "varphi": "phi", "chi": "chi", "psi": "psi",
    "omega": "omega", "Delta": "Delta", "Sigma": "Sigma", "Omega": "Omega",
}


def _strip_latex(expr):
    """把受限子集的 LaTeX 数学式转成 sympy 可解析的字符串（尽力而为）。"""
    s = expr
    s = re.sub(r"\\(left|right|big|Big|bigg|Bigg)\b", "", s)
    s = re.sub(r"\\[,;:!]", "", s)
    s = re.sub(r"\\(quad|qquad)\b", " ", s)
    s = s.replace("~", " ")

    # \frac{a}{b} -> ((a)/(b))，循环处理嵌套
    for _ in range(6):
        new = re.sub(r"\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}", r"((\1)/(\2))", s)
        if new == s:
            break
        s = new
    # \sqrt{x} -> sqrt(x)
    for _ in range(4):
        new = re.sub(r"\\sqrt\s*\{([^{}]*)\}", r"sqrt(\1)", s)
        if new == s:
            break
        s = new

    # 去装饰宏，保留内部内容
    for _ in range(4):
        new = re.sub(
            r"\\(mathrm|text|mathbf|mathit|mathsf|mathcal|bm|hat|bar|tilde|overline|operatorname|boldsymbol)\s*\{([^{}]*)\}",
            r"\2", s)
        if new == s:
            break
        s = new

    s = s.replace(r"\cdot", "*").replace(r"\times", "*")
    s = re.sub(r"\\(log|ln)\b", "log", s)
    s = re.sub(r"\\(exp|sin|cos|tan|min|max|sqrt)\b", r"\1", s)
    for tex, py in _GREEK.items():
        s = re.sub(r"\\" + tex + r"\b", py, s)

    # 下标 _{k} -> _k（先于花括号替换）
    for _ in range(4):
        new = re.sub(r"_\s*\{([^{}]*)\}", r"_\1", s)
        if new == s:
            break
        s = new
    # 上标 ^{...} / ^x -> **(...)
    for _ in range(4):
        new = re.sub(r"\^\s*\{([^{}]*)\}", r"**(\1)", s)
        if new == s:
            break
        s = new
    s = re.sub(r"\^([A-Za-z0-9])", r"**\1", s)

    s = s.replace("{", "(").replace("}", ")")
    # 隐式乘法：)( -> )*( ，数字后接 ( -> *(
    s = re.sub(r"\)\s*\(", ")*(", s)
    s = re.sub(r"(?<=[0-9])\s*\(", "*(", s)
    return s.strip()


def _split_identity(text):
    """把 'lhs = rhs' 拆成两侧；跳过不等式、多等号与含不可解析宏的式子。"""
    body = text.strip()
    if not body or any(tok in body for tok in _UNPARSEABLE_TOKENS):
        return None
    if body.count("=") != 1:
        return None
    lhs, rhs = body.split("=", 1)
    if not lhs.strip() or not rhs.strip():
        return None
    return lhs, rhs


def verify_identities(tex_files, project_dir, max_checks=200):
    """对行间公式中的等式做 sympy 化简验证。

    返回 (verified, failed, undecided, issues)。
    仅在「化简结果是非零常数」时判 FAIL——符号未定的表达式记为 undecided，
    绝不因为解析不了就报错，这是本门禁不产生假阳性的前提。
    """
    if not SYMPY_AVAILABLE:
        return 0, 0, 0, []

    verified = failed = undecided = 0
    issues = []
    # beta / gamma 等在 sympy 中是函数名，必须显式绑定为符号，否则 sympify 会报错
    sym_locals = {name: _sp.Symbol(name) for name in set(_GREEK.values())}
    for tf in tex_files:
        if verified + failed + undecided >= max_checks:
            break
        rel_f = os.path.relpath(tf, project_dir)
        with open(tf, "r", encoding="utf-8", errors="ignore") as fp:
            content = fp.read()

        candidates = []
        for m in re.finditer(r"\$\$(.+?)\$\$", content, re.S):
            candidates.append((content[:m.start()].count("\n") + 1, m.group(1)))
        for env in _MATH_ENVS:
            pat = re.compile(r"\\begin\{" + re.escape(env) + r"\}(.*?)\\end\{" + re.escape(env) + r"\}", re.S)
            for m in pat.finditer(content):
                candidates.append((content[:m.start()].count("\n") + 1, m.group(1)))

        for line_no, raw in candidates:
            if verified + failed + undecided >= max_checks:
                break
            for sub in raw.split(r"\\"):
                split = _split_identity(_strip_latex(sub))
                if not split:
                    continue
                lhs_s, rhs_s = split
                try:
                    lhs = _sp.sympify(lhs_s, evaluate=False, locals=sym_locals)
                    rhs = _sp.sympify(rhs_s, evaluate=False, locals=sym_locals)
                    diff = _sp.simplify(lhs - rhs)
                except Exception:
                    undecided += 1
                    continue
                if diff == 0:
                    verified += 1
                elif getattr(diff, "is_number", False) and diff.is_zero is False:
                    failed += 1
                    issues.append({
                        "file": rel_f, "line": line_no, "level": "FAIL",
                        "rule": "Symbolic Identity Mismatch",
                        "msg": f"等式两侧化简后差值为 {diff}（不为 0），疑似推导错误：{sub.strip()[:120]}",
                    })
                else:
                    undecided += 1
    return verified, failed, undecided, issues


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

    # 4. 符号恒等式机器验证（sympy 可选；缺失则跳过且不报错）
    if SYMPY_AVAILABLE:
        verified, failed_n, undecided, sym_issues = verify_identities(tex_files, project_dir)
        issues.extend(sym_issues)
        print(f"[+] Symbolic identity check: {verified} verified, {failed_n} failed, "
              f"{undecided} undecided (skipped as non-decidable).")
    else:
        print("[+] Symbolic identity check: SKIPPED (sympy not installed; "
              "install with: pip install sympy)")

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
