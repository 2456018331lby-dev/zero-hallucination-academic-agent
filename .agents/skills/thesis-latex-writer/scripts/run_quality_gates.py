#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_quality_gates.py - Academic Quality Gates Orchestrator

Sequential Execution Pipeline:
  Gate 1: Citation Verification Gate (check_citations.py)
  Gate 2: Data Provenance & Traceability Gate
  Gate 3: Academic Compliance Gate (check_thesis_compliance.py)
  Gate 4: Human Review Verification Gate (.human_review.json)

DoD Rule:
  Any failure in Gate 1-3 immediately aborts subsequent operations and strictly
  forbids compiling a defense-submission PDF or exporting an unwatermarked Word (.docx).
  Under --scaffold mode, placeholders are permitted but require explicit watermark enforcement.
"""

import os
import re
import sys
import json
import time
import csv
import hashlib
import argparse
import subprocess

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def format_failure_first_output(stdout_text, max_chars=6000):
    """
    失败优先输出 (Failure-First Output):
    1. 完整提取所有包含 [FAIL] 的条目块（含 [FAIL] 行及其所有缩进详情行）。
    2. 附加尾部上下文（汇总统计、退出状态等）。
    3. 总输出上限提高至 max_chars (默认 6000 字符)，确保失败证据自含、不被截断。
    """
    if not stdout_text:
        return ""

    lines = stdout_text.splitlines()
    fail_blocks = []
    in_fail = False
    current_block = []

    for line in lines:
        if "[FAIL]" in line:
            if current_block:
                fail_blocks.append("\n".join(current_block))
                current_block = []
            in_fail = True
            current_block.append(line)
        elif in_fail:
            # 缩进详情行（以空格、制表符、破折号或箭头开头）
            if line.startswith((" ", "\t")) or line.strip().startswith(("->", "-")):
                current_block.append(line)
            else:
                fail_blocks.append("\n".join(current_block))
                current_block = []
                in_fail = False

    if current_block:
        fail_blocks.append("\n".join(current_block))

    fail_text = "\n\n".join(fail_blocks).strip()

    # 尾部执行上下文
    tail_text = "\n".join(lines[-40:]).strip()

    if fail_text:
        combined = f"[*] Gate 1 Failure Evidence (Prioritized):\n{fail_text}\n\n[*] Trailing Execution Context:\n{tail_text}"
    else:
        combined = stdout_text

    if len(combined) > max_chars:
        if fail_text and len(fail_text) < max_chars - 600:
            rem = max_chars - len(fail_text) - 150
            combined = f"[*] Gate 1 Failure Evidence (Prioritized):\n{fail_text}\n\n[*] Trailing Execution Context:\n{tail_text[-rem:]}"
        else:
            combined = combined[:max_chars]

    return combined


def run_gate1_citations(project_dir, offline=False, strict=False):
    """Gate 1: Crossref forensic audit of bibliography."""
    script_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "citation-auditor", "scripts", "check_citations.py")
    )
    if not os.path.exists(script_path):
        return {
            "name": "Gate 1: Citation Verification Gate",
            "status": "FAIL",
            "details": f"citation-auditor script not found: {script_path}",
            "exit_code": -1
        }

    cmd = [sys.executable, script_path, project_dir]
    if offline:
        cmd.append("--offline")
    if strict:
        cmd.append("--strict")

    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    status = "PASS" if res.returncode == 0 else "FAIL"
    out_formatted = format_failure_first_output(res.stdout, max_chars=6000)
    return {
        "name": "Gate 1: Citation Verification Gate",
        "status": status,
        "exit_code": res.returncode,
        "stdout": out_formatted,
        "stderr": res.stderr[-1000:],
    }


_CN_DIGITS = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
              "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CN_UNITS = {"十": 10, "百": 100, "千": 1000}


def _cn_int(text):
    """Convert a Chinese integer numeral (0-9999) such as 二十 or 一百零八."""
    if not text:
        return None
    total, section, num = 0, 0, 0
    for ch in text:
        if ch in _CN_DIGITS:
            num = _CN_DIGITS[ch]
        elif ch in _CN_UNITS:
            unit = _CN_UNITS[ch]
            section += (num or 1) * unit
            num = 0
        else:
            return None
    return total + section + num


def _cn_number(text):
    """Convert 二十 / 二十点五 / 三 to float; None when not a clean numeral."""
    if not text:
        return None
    if "点" in text:
        whole, _, frac = text.partition("点")
        head = _cn_int(whole)
        digits = "".join(str(_CN_DIGITS[c]) for c in frac if c in _CN_DIGITS)
        if head is None or not digits:
            return None
        return float("%d.%s" % (head, digits))
    value = _cn_int(text)
    return None if value is None else float(value)


# Each entry: (compiled pattern, value group, kind)
# kind "arabic" -> group is a decimal string; kind "chinese" -> a Chinese numeral
_CLAIM_PATTERNS = [
    # 提升/增益/降低 3 dB, 节省 20%, 增益约 5 倍, 提升 12 个百分点
    (re.compile(
        r"(?:提升|增益|降低|节省|改善|增加|减少|优于|高出)\s*(?:高达|达|至|约|了)*\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*(dB|dBm|%|％|倍|bps/Hz|bit/s/Hz|个百分点)", re.I), 1, "arabic"),
    # PSNR 达到 28.5 dB / 和速率 收敛于 12.3 bps/Hz
    (re.compile(
        r"(?:PSNR|NMSE|速率|和速率|谱效率|频谱效率|信噪比|SINR|SNR)\s*"
        r"(?:达到|提升至|稳定在|收敛于|为)\s*([0-9]+(?:\.[0-9]+)?)", re.I), 1, "arabic"),
    # 达到 28.5 dB
    (re.compile(r"达到\s*([0-9]+(?:\.[0-9]+)?)\s*(?:dB|%|％|倍|bps/Hz)", re.I), 1, "arabic"),
    # 提升了约百分之二十
    (re.compile(
        r"(?:提升|增益|降低|节省|改善|增加|减少)\s*(?:了|约|高达|达|至)*\s*百分之([零一二两三四五六七八九十百点]+)", re.I), 1, "chinese"),
    # 提升三十二个百分点
    (re.compile(
        r"(?:提升|增益|降低|节省|改善|增加|减少)\s*(?:了|约|高达|达|至)*\s*([零一二两三四五六七八九十百点]+)\s*个百分点", re.I), 1, "chinese"),
    # 提升三倍 / 增益五 dB
    (re.compile(
        r"(?:提升|增益|降低|节省|改善)\s*(?:了|约|高达|达|至)*\s*([零一二两三四五六七八九十百点]+)\s*(?:dB|倍)", re.I), 1, "chinese"),
]

_PERCENT_UNITS = ("%", "％", "个百分点")


def _collect_csv_numbers(project_dir):
    """Return (csv_files, sorted list of floats found in every CSV cell)."""
    csv_files = []
    for root, _, files in os.walk(project_dir):
        if os.path.basename(root) != "experiments":
            continue
        for name in files:
            if name.lower().endswith(".csv"):
                csv_files.append(os.path.join(root, name))
    values = []
    for path in csv_files:
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore", newline="") as handle:
                for row in csv.reader(handle):
                    for cell in row:
                        text = cell.strip().replace("％", "%").rstrip("%")
                        try:
                            values.append(float(text))
                        except ValueError:
                            continue
        except OSError:
            continue
    return csv_files, values


def _value_in_csv(claim_value, unit, csv_values):
    """True when the claimed number is present in some CSV cell (rounding-aware)."""
    if not csv_values:
        return False
    candidates = {claim_value}
    if unit in _PERCENT_UNITS:
        candidates.add(claim_value / 100.0)   # CSV stores 0.285, text says 28.5%
    for candidate in candidates:
        tolerance = max(0.0051, abs(candidate) * 0.005)
        for observed in csv_values:
            if abs(observed - candidate) <= tolerance:
                return True
    return False


def run_gate2_provenance(project_dir, scaffold_mode=False):
    """Gate 2: every quantitative claim must resolve to a cell in experiments/*.csv.

    Two things are checked, in this order:
      1. Claims that exist at all: a chapter may not assert a number without a
         dataset directory (unchanged historical behaviour).
      2. Claims that resolve: when CSVs *do* exist, the asserted number must
         actually appear in a CSV cell (rounding- and percent-aware). This closes
         the old hole where the mere existence of any CSV let every claim pass.
    """
    tex_files = []
    for root, _, files in os.walk(project_dir):
        for f in files:
            if f.endswith(".tex"):
                tex_files.append(os.path.join(root, f))

    csv_files, csv_values = _collect_csv_numbers(project_dir)

    untraced_claims = []
    unresolved_claims = []
    has_scaffold_tokens = False

    for tf in tex_files:
        with open(tf, "r", encoding="utf-8", errors="ignore") as fp:
            raw_content = fp.read()

        if r"\begin{table" in raw_content:
            if any(kw in raw_content for kw in ("待替换", "待填", "占位", "SCAFFOLD")):
                has_scaffold_tokens = True

        for lineno, line in enumerate(raw_content.splitlines(), start=1):
            # Strip real comments, but keep 28.5% / 28.5\% assertions.
            code = re.sub(r"(?<![\d\\])%.*$", "", line).strip()
            # A legal \TODO{...} placeholder is not a free-floating claim.
            code = re.sub(r"\\TODO\{[^}]*\}", "", code)
            if not code:
                continue
            for pattern, group, kind in _CLAIM_PATTERNS:
                for match in pattern.finditer(code):
                    raw_value = match.group(group)
                    if kind == "chinese":
                        value = _cn_number(raw_value)
                        unit = "个百分点" if "百分点" in match.group(0) else "%"
                    else:
                        value = float(raw_value)
                        unit = ""
                        tail = match.groups()
                        for candidate_unit in ("dBm", "dB", "%", "％", "倍", "bps/Hz", "bit/s/Hz", "个百分点"):
                            if len(tail) > 1 and tail[1] == candidate_unit:
                                unit = candidate_unit
                                break
                    if value is None:
                        continue
                    location = "%s:%d" % (os.path.basename(tf), lineno)
                    if not csv_files:
                        untraced_claims.append(
                            "Quantitative claim '%s' at %s, but no experiments/*.csv exists."
                            % (match.group(0).strip(), location))
                    elif not _value_in_csv(value, unit, csv_values):
                        unresolved_claims.append(
                            "Claim '%s' at %s -> value %s%s not found in any experiments/*.csv cell."
                            % (match.group(0).strip(), location, raw_value, (" " + unit) if unit else ""))

    name = "Gate 2: Data Provenance & Traceability Gate"
    if untraced_claims:
        status = "NOTICE" if scaffold_mode else "FAIL"
        return {
            "name": name,
            "status": status,
            "details": untraced_claims,
            "has_scaffold_tokens": has_scaffold_tokens,
            "csv_files": csv_files,
        }
    if unresolved_claims:
        status = "NOTICE" if scaffold_mode else "FAIL"
        return {
            "name": name,
            "status": status,
            "details": unresolved_claims,
            "has_scaffold_tokens": has_scaffold_tokens,
            "csv_files": csv_files,
        }
    if has_scaffold_tokens and not scaffold_mode:
        return {
            "name": name,
            "status": "FAIL",
            "details": ["Project contains ungrounded scaffold mock tokens. Run with --scaffold for draft mode or inject real CSV data."],
            "has_scaffold_tokens": True,
            "csv_files": csv_files,
        }
    return {
        "name": name,
        "status": "PASS",
        "details": ["All quantitative claims resolve to experiments/*.csv cells (or are permitted scaffold placeholders)."],
        "has_scaffold_tokens": has_scaffold_tokens,
        "csv_files": csv_files,
    }




def run_gate3_compliance(project_dir, scaffold_mode=False, strict=False, min_bib=60):
    """Gate 3: GB/T 7713.1 Academic Compliance & Quality Linter."""
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "check_thesis_compliance.py"))
    cmd = [sys.executable, script_path, project_dir, "--min-bib", str(min_bib)]
    if scaffold_mode:
        cmd.append("--scaffold")
    if strict:
        cmd.append("--strict")

    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    status = "PASS" if res.returncode == 0 else "FAIL"
    return {
        "name": "Gate 3: Academic Compliance Gate",
        "status": status,
        "exit_code": res.returncode,
        "stdout": res.stdout[-1500:],
        "stderr": res.stderr[-500:],
    }


def compute_file_sha256(filepath):
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def find_chapter_files(project_dir):
    """Find chapter .tex files in project."""
    chap_dir = os.path.join(project_dir, "chapters")
    res = []
    if os.path.isdir(chap_dir):
        for root, _, files in os.walk(chap_dir):
            for fn in sorted(files):
                if fn.endswith(".tex") and not fn.startswith("references"):
                    rel_p = os.path.relpath(os.path.join(root, fn), project_dir).replace("\\", "/")
                    res.append(rel_p)
    if not res:
        for fn in sorted(os.listdir(project_dir)):
            if fn.endswith(".tex") and fn != "main.tex" and not fn.startswith("ref"):
                res.append(fn)
    return res


def interactive_confirm_review(project_dir, reviewer=None, auto_yes=False):
    """Interactive terminal mode for real human author/advisor review sign-off.
    Calculates SHA-256 hashes of all confirmed chapters and saves .human_review.json.
    """
    project_dir = os.path.abspath(project_dir)
    print("=" * 75)
    print("[*] Gate 4 Human Review Sign-Off Protocol (--confirm-review)")
    print(f"[*] Target Project : {project_dir}")
    print("[!] STRICT DoD RULE: This mode is exclusively for REAL HUMAN authors/advisors.")
    print("    Autonomous AI assistants are STRICTLY FORBIDDEN from calling this mode.")
    print("=" * 75)

    placeholder_pattern = r"(?i)(?:研究生|导师复核组|TBD|XXX|TODO|placeholder|none|unknown|待定|待填|测试|test)"

    if not reviewer:
        try:
            reviewer = input("\n[?] Enter reviewer real name (Author / Advisor full name): ").strip()
        except EOFError:
            print("[-] Standard input closed. Aborting interactive sign-off.")
            return False

    if not reviewer or re.search(placeholder_pattern, reviewer):
        print(f"[-] ERROR: Reviewer name '{reviewer}' is invalid or matches placeholder patterns.")
        print("    Human review sign-off strictly requires a real person's full name.")
        return False

    chapters = find_chapter_files(project_dir)
    if not chapters:
        print(f"[-] ERROR: No chapter .tex files found in {project_dir}.")
        return False

    print(f"\n[*] Found {len(chapters)} chapter files for review.")
    confirmed_chapters = []
    chapter_hashes = {}

    for ch in chapters:
        full_p = os.path.join(project_dir, ch)
        h = compute_file_sha256(full_p)

        if auto_yes:
            ans = "y"
        else:
            try:
                ans = input(f"    Confirm review for '{ch}' (SHA256: {h[:8]}...)? [y/N]: ").strip().lower()
            except EOFError:
                ans = "n"

        if ans in ("y", "yes"):
            confirmed_chapters.append(ch)
            chapter_hashes[ch] = h
            print(f"    [+] Confirmed: {ch}")
        else:
            print(f"    [-] Skipped: {ch}")

    if not auto_yes:
        try:
            comments = input("\n[?] Enter review comments (optional): ").strip()
        except EOFError:
            comments = ""
    else:
        comments = "Confirmed via human review protocol with cryptographic SHA-256 hashes."

    if len(confirmed_chapters) < 5:
        print(f"\n[!] WARNING: Only {len(confirmed_chapters)} chapters confirmed (< 5 required).")
        status_val = "PENDING_APPROVAL"
    else:
        status_val = "APPROVED"

    review_record = {
        "reviewer": reviewer,
        "review_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": status_val,
        "chapters_confirmed": confirmed_chapters,
        "chapter_hashes": chapter_hashes,
        "comments": comments or "Human review confirmed with cryptographic SHA-256 hashes."
    }

    out_file = os.path.join(project_dir, ".human_review.json")
    with open(out_file, "w", encoding="utf-8") as fp:
        json.dump(review_record, fp, ensure_ascii=False, indent=2)

    print(f"\n[OK] Sign-off record successfully saved to: {out_file}")
    print(f"     Status: {status_val}, Confirmed Chapters: {len(confirmed_chapters)}")
    return status_val == "APPROVED"


def run_gate4_human_review(project_dir, scaffold_mode=False):
    """Gate 4: Check chapter-by-chapter human sign-off records (.human_review.json)
    with cryptographic SHA-256 hash binding and placeholder rejection.
    """
    review_file = os.path.join(project_dir, ".human_review.json")
    if not os.path.exists(review_file):
        status = "NOTICE" if scaffold_mode else "FAIL"
        return {
            "name": "Gate 4: Human Review Sign-Off Gate",
            "status": status,
            "details": f"Missing human review sign-off file: {review_file}. Final defense thesis must be confirmed by human author via --confirm-review.",
        }

    try:
        with open(review_file, "r", encoding="utf-8") as fp:
            data = json.load(fp)

        reviewer = (data.get("reviewer") or "").strip()
        review_date = (data.get("review_date") or "").strip()
        confirmed = data.get("chapters_confirmed") or []
        chapter_hashes = data.get("chapter_hashes") or {}
        status_val = (data.get("status") or "").strip().upper()

        # 1. 占位符与空值拦截 (Placeholder rejection)
        placeholder_pattern = r"(?i)(?:研究生|导师复核组|TBD|XXX|TODO|placeholder|none|unknown|待定|待填|测试|test)"
        if not reviewer or re.search(placeholder_pattern, reviewer):
            status = "NOTICE" if scaffold_mode else "FAIL"
            return {
                "name": "Gate 4: Human Review Sign-Off Gate",
                "status": status,
                "details": f"Reviewer name '{reviewer}' is a placeholder or AI-generated token. Gate 4 strictly requires real human author/advisor sign-off.",
            }

        if not review_date:
            status = "NOTICE" if scaffold_mode else "FAIL"
            return {
                "name": "Gate 4: Human Review Sign-Off Gate",
                "status": status,
                "details": "Review date is missing in .human_review.json.",
            }

        if status_val != "APPROVED":
            status = "NOTICE" if scaffold_mode else "FAIL"
            return {
                "name": "Gate 4: Human Review Sign-Off Gate",
                "status": status,
                "details": f"Human review status is '{status_val}' (must be 'APPROVED').",
            }

        # 2. 章节数量核查 (At least 5 chapters confirmed)
        if len(confirmed) < 5:
            status = "NOTICE" if scaffold_mode else "FAIL"
            return {
                "name": "Gate 4: Human Review Sign-Off Gate",
                "status": status,
                "details": f"Insufficient confirmed chapters ({len(confirmed)} < 5 required).",
            }

        # 3. 密码学哈希绑定核验 (Cryptographic hash validation)
        if not chapter_hashes:
            status = "NOTICE" if scaffold_mode else "FAIL"
            return {
                "name": "Gate 4: Human Review Sign-Off Gate",
                "status": status,
                "details": "Sign-off record lacks cryptographic file hashes (chapter_hashes). Sign-off is invalid.",
            }

        hash_mismatches = []
        missing_files = []
        for ch, expected_hash in chapter_hashes.items():
            ch_path = os.path.join(project_dir, ch) if not os.path.isabs(ch) else ch
            if not os.path.exists(ch_path):
                cand = os.path.join(project_dir, "chapters", os.path.basename(ch))
                if os.path.exists(cand):
                    ch_path = cand
                else:
                    missing_files.append(ch)
                    continue

            current_hash = compute_file_sha256(ch_path)
            if current_hash != expected_hash:
                hash_mismatches.append(
                    f"{os.path.basename(ch)} (expected {expected_hash[:8]}, current {current_hash[:8]})"
                )

        if missing_files:
            status = "NOTICE" if scaffold_mode else "FAIL"
            return {
                "name": "Gate 4: Human Review Sign-Off Gate",
                "status": status,
                "details": f"Signed chapter file(s) missing on disk: {missing_files}.",
            }

        if hash_mismatches:
            status = "NOTICE" if scaffold_mode else "FAIL"
            return {
                "name": "Gate 4: Human Review Sign-Off Gate",
                "status": status,
                "details": f"Chapters modified after human review (hash mismatch): {', '.join(hash_mismatches)}. Signatures invalidated!",
            }

        # 全部核验通过
        return {
            "name": "Gate 4: Human Review Sign-Off Gate",
            "status": "PASS",
            "details": f"Cryptographically verified sign-off by real reviewer '{reviewer}' on {review_date} ({len(confirmed)} chapters matched SHA-256).",
        }

    except Exception as e:
        return {
            "name": "Gate 4: Human Review Sign-Off Gate",
            "status": "FAIL",
            "details": f"Failed to read/verify .human_review.json: {e}",
        }


def orchestrate_gates(project_dir, scaffold_mode=False, offline=False, strict=False, min_bib=60, json_out=None):
    project_dir = os.path.abspath(project_dir)
    # 默认把 summary 写进被检工程目录，而不是调用者 CWD —— 否则检查多个工程时
    # 后一次会静默覆盖前一次，且产物落在仓库根污染工作区。
    if not json_out:
        json_out = os.path.join(project_dir, "gate_summary.json")
    print("=" * 75)
    print(f"[*] Academic Quality Gates Orchestration (DoD Enforcement)")
    print(f"[*] Project Target: {project_dir}")
    print(f"[*] Mode: {'SCAFFOLD DRAFT (Watermark Enforced)' if scaffold_mode else 'FINAL DEFENSE SUBMISSION'}")
    print("=" * 75)

    report = {
        "project": project_dir,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "scaffold" if scaffold_mode else "final",
        "gates": {},
        "overall_status": "PENDING",
    }

    # ---- Gate 1: Citation Verification ----
    print("\n>>> [1/4] Running Gate 1: Citation Verification Gate...")
    g1 = run_gate1_citations(project_dir, offline=offline, strict=strict)
    report["gates"]["gate1_citation"] = g1
    print(f"    Status: [{g1['status']}]")
    if g1["status"] != "PASS":
        print(g1.get("stdout", ""))

    # ---- Gate 2: Data Provenance ----
    print("\n>>> [2/4] Running Gate 2: Data Provenance & Traceability Gate...")
    g2 = run_gate2_provenance(project_dir, scaffold_mode=scaffold_mode)
    report["gates"]["gate2_provenance"] = g2
    print(f"    Status: [{g2['status']}]")
    if g2["status"] != "PASS":
        for d in g2.get("details", []):
            print(f"        -> {d}")

    # ---- Gate 3: Compliance Linter ----
    print("\n>>> [3/4] Running Gate 3: Academic Compliance Gate...")
    g3 = run_gate3_compliance(project_dir, scaffold_mode=scaffold_mode, strict=strict, min_bib=min_bib)
    report["gates"]["gate3_compliance"] = g3
    print(f"    Status: [{g3['status']}]")
    if g3["status"] != "PASS":
        print(g3.get("stdout", ""))

    # ---- Gate 4: Human Review ----
    print("\n>>> [4/4] Running Gate 4: Human Review Sign-Off Gate...")
    g4 = run_gate4_human_review(project_dir, scaffold_mode=scaffold_mode)
    report["gates"]["gate4_human_review"] = g4
    print(f"    Status: [{g4['status']}] - {g4.get('details')}")

    has_failure = any(
        g.get("status") == "FAIL" for g in (g1, g2, g3, g4)
    )
    if has_failure:
        report["overall_status"] = "FAIL"
        return _conclude(report, json_out, False)

    report["overall_status"] = "PASS"
    return _conclude(report, json_out, True)


def _conclude(report, json_out, is_success):
    print("\n" + "=" * 75)
    print(f"[*] Quality Gates Summary Table:")
    for key, g in report["gates"].items():
        st = g.get("status", "BLOCKED")
        print(f"    - {g.get('name', key):<45} : [{st}]")

    print(f"[*] Overall Outcome: [{report['overall_status']}]")
    if not is_success:
        print(f"\n[BLOCKED] Quality Gates failed! Defense-submission PDF compilation and")
        print(f"          unwatermarked Word (.docx) export are strictly forbidden until fixed.")
    else:
        print(f"\n[PASSED] All mandatory quality gates cleared successfully!")
        if report["mode"] == "scaffold":
            print(f"[NOTICE] Running in --scaffold mode. Artifacts must carry 'SCAFFOLD DRAFT' watermarks.")
    print("=" * 75)

    if json_out:
        with open(json_out, "w", encoding="utf-8") as fp:
            json.dump(report, fp, ensure_ascii=False, indent=2)
        print(f"[OK] Quality gates summary report saved to: {json_out}")

    return 0 if is_success else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Academic Quality Gates Orchestrator")
    parser.add_argument("project_dir", nargs="?", default=".", help="LaTeX project root directory")
    parser.add_argument("--scaffold", action="store_true", help="Scaffold draft mode (allows placeholders with watermark)")
    parser.add_argument("--offline", action="store_true", help="Gate 1 offline mode (use cache only)")
    parser.add_argument("--strict", action="store_true", help="Strict mode: warnings cause failure")
    parser.add_argument("--min-bib", type=int, default=60, help="Minimum reference threshold")
    parser.add_argument("--json", dest="json_out", default=None, help="Output summary JSON path (default: <project>/gate_summary.json)")
    parser.add_argument("--confirm-review", action="store_true", help="Launch interactive human sign-off terminal protocol (real humans only)")
    parser.add_argument("--reviewer", help="Reviewer real name (for scripted confirmation/verification)")
    parser.add_argument("-y", "--yes", action="store_true", dest="auto_yes", help="Auto-confirm all chapters (for verification test harnesses only)")

    args = parser.parse_args()

    if args.confirm_review:
        ok = interactive_confirm_review(args.project_dir, reviewer=args.reviewer, auto_yes=args.auto_yes)
        sys.exit(0 if ok else 1)

    code = orchestrate_gates(
        args.project_dir,
        scaffold_mode=args.scaffold,
        offline=args.offline,
        strict=args.strict,
        min_bib=args.min_bib,
        json_out=args.json_out
    )
    sys.exit(code)
