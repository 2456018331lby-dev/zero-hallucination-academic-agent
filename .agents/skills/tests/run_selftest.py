#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_selftest.py - Academic Quality Gates Adversarial Regression Test Runner

Executes 12 core adversarial attack vectors, verifies that each DoD quality gate
correctly blocks adversarial attempts, and prints a structured benchmark table.
"""

import os
import sys
import time
import unittest
import io

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure tests dir is importable
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
if TEST_DIR not in sys.path:
    sys.path.insert(0, TEST_DIR)

import test_gates

TEST_SPECS = [
    {
        "method": "test_01_gate1_fake_doi",
        "name": "Gate 1 Fake DOI Rejection",
        "gate": "Gate 1: Citation Gate",
        "input_desc": "Fake DOI: 10.9999/fake.test.2026",
        "expected": "FAIL (Crossref 404 Not Found)",
    },
    {
        "method": "test_02_gate1_tampered_metadata",
        "name": "Gate 1 Metadata Tamper Rejection",
        "gate": "Gate 1: Citation Gate",
        "input_desc": "Valid DOI with Fabricated Title (sim<0.85)",
        "expected": "FAIL (Title Mismatch)",
    },
    {
        "method": "test_03_gate4_hash_tamper",
        "name": "Gate 4 Hash Tamper Detection",
        "gate": "Gate 4: Human Sign-Off",
        "input_desc": "Chapter .tex modified post-signature",
        "expected": "FAIL (Hash Mismatch Invalidated)",
    },
    {
        "method": "test_04_gate4_placeholder_reviewer",
        "name": "Gate 4 Placeholder Rejection",
        "gate": "Gate 4: Human Sign-Off",
        "input_desc": "Reviewer: '北京大学研究生/导师复核组'",
        "expected": "FAIL (Defense) / NOTICE (Scaffold)",
    },
    {
        "method": "test_05_gate2_ungrounded_claims",
        "name": "Gate 2 Ungrounded Claims Catch",
        "gate": "Gate 2: Data Provenance",
        "input_desc": "'提升了 23.5%', '达到 35.2 dB' no CSV",
        "expected": "FAIL (Dual Regex Intercepted)",
    },
    {
        "method": "test_06_grounding_out_of_bounds",
        "name": "Grounding Page Out-of-Bounds",
        "gate": "Grounding Gate",
        "input_desc": "Missing PDF & page 999 on 14-page PDF",
        "expected": "FAIL (Physical Violation)",
    },
    {
        "method": "test_07_filter_circuit_breakers",
        "name": "Download Filter 4 Circuit Breakers",
        "gate": "PDF Landing Filter",
        "input_desc": "<40KB, fail-closed fitz, nav dump, sim<0.5",
        "expected": "REJECT All 4 Cases",
    },
    {
        "method": "test_08_gate3_markdown_and_todo",
        "name": "Gate 3 Markdown & TODO Rejection",
        "gate": "Gate 3: Compliance",
        "input_desc": "Literal '**' residue & 'TODO' in final draft",
        "expected": "FAIL (Exit code 1, Errors flagged)",
    },
    {
        "method": "test_09_gate2_csv_value_mismatch",
        "name": "Gate 2 CSV Value Mismatch Catch",
        "gate": "Gate 2: Data Provenance",
        "input_desc": "CSV has 28.53 dB, chapter claims 41.7 dB",
        "expected": "FAIL (Claim absent from every CSV cell)",
    },
    {
        "method": "test_10_retraction_detection",
        "name": "Gate 1 Retracted Paper Rejection",
        "gate": "Gate 1: Citation Gate",
        "input_desc": "Metadata perfect, but Crossref marks it retracted",
        "expected": "FAIL (Cited paper has been retracted)",
    },
    {
        "method": "test_11_symbolic_identity_mismatch",
        "name": "Math Symbolic Identity Mismatch",
        "gate": "Math Reviewer",
        "input_desc": "True identity + '2 + 2 = 5' in display math",
        "expected": "FAIL (sympy diff != 0)",
    },
    {
        "method": "test_12_anonymize_excludes_build_products",
        "name": "Blind Review PDF Leak Rejection",
        "gate": "Anonymizer",
        "input_desc": "Stale main.pdf (real name inside) next to main.tex",
        "expected": "PASS (PDF excluded, figures kept)",
    },
]


def run_all_selftests():
    print("=" * 115)
    print("  ACADEMIC QUALITY GATES ADVERSARIAL REGRESSION TEST SUITE (SELFTEST)")
    print(f"  Execution Time : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Python Runtime : {sys.version.split()[0]} ({sys.executable})")
    print(f"  Suite Target   : {len(TEST_SPECS)} DoD Adversarial Attack Vectors (Gate 1 - Gate 4 + Filter + Grounding)")
    print("=" * 115)

    results = []
    total_start = time.time()

    for idx, spec in enumerate(TEST_SPECS, 1):
        method_name = spec["method"]
        suite = unittest.TestSuite()
        suite.addTest(test_gates.TestQualityGatesAdversarial(method_name))

        # Redirect internal output to avoid noisy clutter during clean tabular presentation
        buf = io.StringIO()
        runner = unittest.TextTestRunner(stream=buf, verbosity=0)

        t0 = time.time()
        test_res = runner.run(suite)
        elapsed = time.time() - t0

        if test_res.wasSuccessful():
            status = "PASS"
            actual = spec["expected"].split()[0] + " (Caught)"
        else:
            status = "FAIL"
            actual = "UNCAUGHT / ERROR"

        results.append({
            "idx": idx,
            "name": spec["name"],
            "gate": spec["gate"],
            "input_desc": spec["input_desc"],
            "expected": spec["expected"],
            "actual": actual,
            "elapsed": elapsed,
            "status": status,
        })

    total_elapsed = time.time() - total_start

    # Print Table
    header_fmt = "| {:^4} | {:<32} | {:<22} | {:<16} | {:^10} | {:^8} |"
    row_fmt    = "| {:^4} | {:<32} | {:<22} | {:<16} | {:^10.3f} | {:^8} |"
    sep = "+" + "-" * 6 + "+" + "-" * 34 + "+" + "-" * 24 + "+" + "-" * 18 + "+" + "-" * 12 + "+" + "-" * 10 + "+"

    print(sep)
    print("|  ID  | Test Case Name                   | Target Gate / Linter   | Expected Intercept | Elapsed(s) |  Status  |")
    print(sep)

    passed_count = 0
    for r in results:
        if r["status"] == "PASS":
            passed_count += 1
        print(row_fmt.format(
            r["idx"],
            r["name"][:32],
            r["gate"][:22],
            r["expected"][:16],
            r["elapsed"],
            f"[{r['status']}]"
        ))

    print(sep)
    print(f"\n[*] Summary: {passed_count}/{len(results)} adversarial regression test cases PASSED.")
    print(f"[*] Total Benchmark Duration: {total_elapsed:.3f}s")

    if passed_count == len(results):
        print("[OK] ALL ADVERSARIAL GATES EFFECTIVELY INTERCEPTED! System defense integrity verified.\n")
        return True
    else:
        print("[-] REGRESSION DETECTED! Some quality gates failed to block adversarial inputs.\n", file=sys.stderr)
        return False


if __name__ == "__main__":
    ok = run_all_selftests()
    sys.exit(0 if ok else 1)
