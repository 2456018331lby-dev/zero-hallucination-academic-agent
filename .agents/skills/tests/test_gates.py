#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_gates.py - Adversarial Regression Test Suite for Academic Quality Gates

Solidifies 8 core adversarial attack vectors and failure modes to ensure
DoD quality gates never regress:
  1. Gate 1: Fake DOI rejection (nonexistent DOI -> FAIL)
  2. Gate 1: Tampered metadata rejection (valid DOI with altered title -> FAIL)
  3. Gate 4: Hash tampering detection (chapter modified post-signature -> FAIL)
  4. Gate 4: Placeholder reviewer rejection (placeholder reviewer token -> FAIL)
  5. Gate 2: Ungrounded claims double-regex detection (quant assertions without CSV -> FAIL)
  6. Grounding: Out-of-bounds page or missing PDF detection (evidence out-of-bounds -> FAIL)
  7. Filter: 4-fold circuit breakers (<40KB, missing fitz, nav dump, title mismatch -> REJECT)
  8. Gate 3: Markdown syntax residue and unescaped TODO in non-scaffold mode -> FAIL
"""

import os
import sys
import shutil
import tempfile
import unittest
import json
import time
import re

# Add skills directories to sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(BASE_DIR, "citation-auditor", "scripts"))
sys.path.insert(0, os.path.join(BASE_DIR, "thesis-latex-writer", "scripts"))
sys.path.insert(0, os.path.join(BASE_DIR, "phd-literature-survey", "scripts"))
sys.path.insert(0, os.path.join(BASE_DIR, "academic-paper-discovery", "scripts"))
sys.path.insert(0, os.path.join(BASE_DIR, "math-reviewer", "scripts"))
REPO_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
sys.path.insert(0, REPO_ROOT)

import check_citations
import run_quality_gates
import check_thesis_compliance
import verify_grounding
import search_papers
import check_math


class TestQualityGatesAdversarial(unittest.TestCase):
    """Adversarial regression test cases for academic quality gates."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="gate_test_")
        self.client = check_citations.CrossrefClient(cache_path=None, offline=False)
        # Pre-seed deterministic Crossref cache to guarantee zero flaky network hiccups
        for u in [
            "https://api.crossref.org/works/10.9999/fake.test.2026",
            "https://api.crossref.org/works/10.9999%2Ffake.test.2026"
        ]:
            self.client.cache[u] = {
                "__error__": "HTTP Error 404: Not Found",
                "__kind__": "not_found"
            }
        
        twc_data = {
            "message": {
                "title": ["Intelligent Reflecting Surface Enhanced Wireless Network via Joint Active and Passive Beamforming"],
                "author": [
                    {"family": "Wu", "given": "Qingqing"},
                    {"family": "Zhang", "given": "Rui"}
                ],
                "issued": {"date-parts": [[2019]]},
                "volume": "67",
                "issue": "11",
                "page": "8279-8293",
                "DOI": "10.1109/twc.2019.2936025"
            }
        }
        for u in [
            "https://api.crossref.org/works/10.1109/twc.2019.2936025",
            "https://api.crossref.org/works/10.1109%2Ftwc.2019.2936025"
        ]:
            self.client.cache[u] = twc_data

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_gate1_fake_doi(self):
        """Case 1: Gate 1 catches nonexistent fake DOI (e.g. 10.9999/fake.test.2026)."""
        fake_entry = {
            "key": "fake2026",
            "type": "article",
            "fields": {
                "title": "Quantum Entangled Space-Air-Ground Integrated Beamforming",
                "author": "Fake, Author and Hallucination, AI",
                "doi": "10.9999/fake.test.2026"
            }
        }
        res = check_citations.audit_entry(fake_entry, self.client)
        self.assertEqual(res["status"], "FAIL", "Gate 1 must fail nonexistent fake DOI")
        self.assertTrue(
            any("Crossref 无此 DOI" in p or "404" in p for p in res["problems"]),
            f"Expected DOI not found failure message, got: {res['problems']}"
        )

    def test_02_gate1_tampered_metadata(self):
        """Case 2: Gate 1 catches metadata inconsistency when title is tampered."""
        tampered_entry = {
            "key": "wu2019tampered",
            "type": "article",
            "fields": {
                "title": "Completely Fabricated Title on Quantum Gravitational Teleportation",
                "author": "Wu, Qingqing and Zhang, Rui",
                "doi": "10.1109/TWC.2019.2936025"
            }
        }
        res = check_citations.audit_entry(tampered_entry, self.client)
        self.assertEqual(res["status"], "FAIL", "Gate 1 must fail tampered title")
        self.assertTrue(
            any("标题不匹配" in p for p in res["problems"]),
            f"Expected title mismatch problem, got: {res['problems']}"
        )

    def test_03_gate4_hash_tamper(self):
        """Case 3: Gate 4 detects post-sign-off modification of chapter .tex via SHA-256."""
        chap_dir = os.path.join(self.temp_dir, "chapters")
        os.makedirs(chap_dir, exist_ok=True)
        chapter_files = []
        for i in range(1, 6):
            cf = os.path.join(chap_dir, f"chap0{i}.tex")
            with open(cf, "w", encoding="utf-8") as f:
                f.write(f"\\chapter{{Chapter {i}}}\nOriginal genuine content.\n")
            chapter_files.append(cf)

        # Compute genuine hashes
        chapter_hashes = {}
        for cf in chapter_files:
            rel = os.path.relpath(cf, self.temp_dir).replace("\\", "/")
            chapter_hashes[rel] = run_quality_gates.compute_file_sha256(cf)

        # Write approved human review sign-off
        review_data = {
            "reviewer": "Prof. Genuine Reviewer",
            "review_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "APPROVED",
            "chapters_confirmed": list(chapter_hashes.keys()),
            "chapter_hashes": chapter_hashes,
            "comments": "Approved after comprehensive human audit."
        }
        with open(os.path.join(self.temp_dir, ".human_review.json"), "w", encoding="utf-8") as f:
            json.dump(review_data, f, indent=2)

        # Verify initial state is PASS
        res_before = run_quality_gates.run_gate4_human_review(self.temp_dir, scaffold_mode=False)
        self.assertEqual(res_before["status"], "PASS")

        # Tamper chapter 3
        with open(chapter_files[2], "a", encoding="utf-8") as f:
            f.write("\n% Malicious adversarial injection post-signature\n")

        # Verify Gate 4 fails with hash mismatch
        res_after = run_quality_gates.run_gate4_human_review(self.temp_dir, scaffold_mode=False)
        self.assertEqual(res_after["status"], "FAIL", "Gate 4 must FAIL on hash mismatch")
        self.assertIn("hash mismatch", res_after["details"])

    def test_04_gate4_placeholder_reviewer(self):
        """Case 4: Gate 4 rejects placeholder reviewer names (e.g. 北京大学研究生, TBD)."""
        chap_dir = os.path.join(self.temp_dir, "chapters")
        os.makedirs(chap_dir, exist_ok=True)
        chapter_hashes = {}
        for i in range(1, 6):
            cf = os.path.join(chap_dir, f"chap0{i}.tex")
            with open(cf, "w", encoding="utf-8") as f:
                f.write(f"\\chapter{{Chapter {i}}}\nGenuine content.\n")
            rel = os.path.relpath(cf, self.temp_dir).replace("\\", "/")
            chapter_hashes[rel] = run_quality_gates.compute_file_sha256(cf)

        # Reviewer with placeholder name
        review_data = {
            "reviewer": "北京大学研究生 / 导师复核组 [AI 自签无效占位]",
            "review_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "APPROVED",
            "chapters_confirmed": list(chapter_hashes.keys()),
            "chapter_hashes": chapter_hashes,
            "comments": "Autonomous AI sign-off attempt."
        }
        with open(os.path.join(self.temp_dir, ".human_review.json"), "w", encoding="utf-8") as f:
            json.dump(review_data, f, indent=2)

        # In non-scaffold mode, placeholder causes FAIL
        res_fail = run_quality_gates.run_gate4_human_review(self.temp_dir, scaffold_mode=False)
        self.assertEqual(res_fail["status"], "FAIL", "Placeholder reviewer must trigger FAIL in defense mode")
        self.assertIn("placeholder", res_fail["details"])

        # In scaffold mode, placeholder causes NOTICE
        res_notice = run_quality_gates.run_gate4_human_review(self.temp_dir, scaffold_mode=True)
        self.assertEqual(res_notice["status"], "NOTICE", "Placeholder reviewer must trigger NOTICE in scaffold mode")

    def test_05_gate2_ungrounded_claims(self):
        """Case 5: Gate 2 detects ungrounded quantitative claims via dual regex patterns without CSV."""
        chap_dir = os.path.join(self.temp_dir, "chapters")
        os.makedirs(chap_dir, exist_ok=True)
        chap_file = os.path.join(chap_dir, "chap04_experiments.tex")
        with open(chap_file, "w", encoding="utf-8") as f:
            f.write(
                "\\chapter{实验结果与分析}\n"
                "仿真表明所提波束赋形方案使系统和速率提升了 23.5%，同时信噪比达到 35.2 dB。\n"
            )

        res = run_quality_gates.run_gate2_provenance(self.temp_dir, scaffold_mode=False)
        self.assertEqual(res["status"], "FAIL", "Gate 2 must FAIL when quantitative claims have no CSV provenance")
        claims_detected = " ".join(res["details"])
        self.assertTrue("提升了 23.5%" in claims_detected or "23.5%" in claims_detected)
        self.assertTrue("达到 35.2 dB" in claims_detected or "35.2" in claims_detected)

    def test_06_grounding_out_of_bounds(self):
        """Case 6: verify_grounding rejects missing PDF and out-of-bounds page range."""
        # Use existing literature directory for genuine PDF test
        repo_lit_dir = os.path.abspath(r"ris_thesis_workflow/literature")
        target_pdf = "[11]_Deep_Reinforcement_Learning-Based_Intelligent_Refl_2020.pdf"

        # A: Nonexistent PDF in evidence
        matrix_fake_pdf = os.path.join(self.temp_dir, "matrix_fake_pdf.md")
        with open(matrix_fake_pdf, "w", encoding="utf-8") as f:
            f.write(
                "| 序号 | 论文题目 | 第一作者 | 年份 | 期刊/会议 | 证据溯源 |\n"
                "| :---: | :--- | :--- | :---: | :--- | :--- |\n"
                "| 1 | Nonexistent Study On Ghost Signals | Ghost, A. | 2024 | Ghost Conf | `[99]_Nonexistent_Paper_2024.pdf`, pp. 1-10 |\n"
            )
        success_a = verify_grounding.verify_grounding(matrix_fake_pdf, repo_lit_dir)
        self.assertFalse(success_a, "Must FAIL when PDF does not exist in pool")

        # B: Out-of-bounds page range (page 999 on a 14-page PDF)
        matrix_oob = os.path.join(self.temp_dir, "matrix_oob.md")
        with open(matrix_oob, "w", encoding="utf-8") as f:
            f.write(
                "| 序号 | 论文题目 | 第一作者 | 年份 | 期刊/会议 | 证据溯源 |\n"
                "| :---: | :--- | :--- | :---: | :--- | :--- |\n"
                f"| 1 | Deep Reinforcement Learning-Based Intelligent Reflecting Surface | Huang, C. | 2020 | IEEE TWC | `{target_pdf}`, pp. 1-999 |\n"
            )
        success_b = verify_grounding.verify_grounding(matrix_oob, repo_lit_dir)
        self.assertFalse(success_b, "Must FAIL when page range exceeds physical PDF page count")

    def test_07_filter_circuit_breakers(self):
        """Case 7: search_papers validate_downloaded_pdf triggers 4-fold circuit breakers."""
        pdf_dir = os.path.abspath(r"ris_thesis_workflow/literature")
        valid_pdf = os.path.join(pdf_dir, "[02]_Intelligent_Reflecting_Surface_Aided_Wireless_Comm_2019.pdf")
        valid_title = "Intelligent Reflecting Surface Aided Wireless Communication: Modeling and Offline Optimization"

        # 1. Size < 40KB
        tiny_file = os.path.join(self.temp_dir, "tiny_dummy.pdf")
        with open(tiny_file, "wb") as f:
            f.write(b"%PDF-1.4 header dummy small bytes")
        valid_1, reason_1 = search_papers.validate_downloaded_pdf(tiny_file, expected_title=valid_title)
        self.assertFalse(valid_1)
        self.assertIn("体积过小", reason_1)

        # 2. Fail-closed when HAS_PYMUPDF = False
        orig_has = search_papers.HAS_PYMUPDF
        try:
            search_papers.HAS_PYMUPDF = False
            valid_2, reason_2 = search_papers.validate_downloaded_pdf(valid_pdf, expected_title=valid_title)
            self.assertFalse(valid_2)
            self.assertIn("依赖缺失", reason_2)
            self.assertIn("fail-closed", reason_2.lower())
        finally:
            search_papers.HAS_PYMUPDF = orig_has

        # 3. Nav words in first 500 characters
        nav_text = "<html>Skip to main content. Welcome to Research Explorer. Please sign in to subscribe.</html>"
        nav_match = search_papers.NAV_WORDS_PATTERN.search(nav_text)
        self.assertIsNotNone(nav_match, "Nav pattern must detect landing page words")

        # 4. Composite title similarity < 0.50
        bad_title = "Quantum Computing and Post-Quantum Cryptography in Distributed Ledger Architectures"
        import fitz
        doc = fitz.open(valid_pdf)
        p1_text = doc[0].get_text()
        doc.close()
        sim_bad = search_papers.calculate_page_title_similarity(p1_text, bad_title)
        self.assertLess(sim_bad, 0.50, f"Unrelated title composite score must be < 0.50, got {sim_bad:.3f}")
        valid_4, reason_4 = search_papers.validate_downloaded_pdf(valid_pdf, expected_title=bad_title)
        self.assertFalse(valid_4)
        self.assertIn("相似度过低", reason_4)

    def test_08_gate3_markdown_and_todo(self):
        """Case 8: Gate 3 compliance linter catches markdown syntax and TODO in non-scaffold mode."""
        main_tex = os.path.join(self.temp_dir, "main.tex")
        with open(main_tex, "w", encoding="utf-8") as f:
            f.write(
                "\\documentclass{article}\n"
                "\\begin{document}\n"
                "This is an unescaped **markdown bold** residue.\n"
                "And here is a placeholder: TODO: fill experimental figures.\n"
                "\\end{document}\n"
            )
        # In non-scaffold mode, should return failure code (1)
        res_code = check_thesis_compliance.check_thesis(self.temp_dir, scaffold_mode=False, strict=False)
        self.assertEqual(res_code, 1, "Gate 3 must return exit code 1 when markdown or TODO leaks into non-scaffold draft")

    def test_09_gate2_csv_value_mismatch(self):
        """Case 9: Gate 2 resolves each claimed number against an actual CSV cell.

        Historical hole: the presence of *any* experiments/*.csv made every claim
        pass. This case pins the fix — a CSV that exists but does not contain the
        asserted number must still FAIL, and the same claim must PASS once the
        number is genuinely there (rounding- and percent-aware).
        """
        exp_dir = os.path.join(self.temp_dir, "experiments")
        os.makedirs(exp_dir)
        csv_path = os.path.join(exp_dir, "snr_results.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("scheme,psnr_db,rate,delta_pct\n")
            f.write("proposed,28.53,12.4,35.0\n")
            f.write("baseline,22.10,9.8,0.0\n")

        chap_file = os.path.join(self.temp_dir, "chap04_experiments.tex")
        with open(chap_file, "w", encoding="utf-8") as f:
            f.write("所提方案使 PSNR 达到 28.5 dB，和速率达到 12.4 bps/Hz，较基线提升了约百分之三十五。\n")

        res_ok = run_quality_gates.run_gate2_provenance(self.temp_dir, scaffold_mode=False)
        self.assertEqual(
            res_ok["status"], "PASS",
            f"Gate 2 must PASS when every number exists in the CSV, got: {res_ok['details']}",
        )
        self.assertEqual(len(res_ok["csv_files"]), 1, "Gate 2 must discover the experiments CSV")

        # Fabricate one number that is nowhere in the CSV.
        with open(chap_file, "w", encoding="utf-8") as f:
            f.write("所提方案使 PSNR 达到 41.7 dB，较基线提升了约百分之六十二。\n")

        res_bad = run_quality_gates.run_gate2_provenance(self.temp_dir, scaffold_mode=False)
        self.assertEqual(
            res_bad["status"], "FAIL",
            "Gate 2 must FAIL when a CSV exists but the claimed number is not in it",
        )
        details = " ".join(res_bad["details"])
        self.assertIn("41.7", details)
        self.assertIn("chap04_experiments.tex:1", details, "Gate 2 must report file:line for the fabricated claim")

        # Scaffold mode downgrades the same finding to NOTICE instead of blocking a draft.
        res_scaffold = run_quality_gates.run_gate2_provenance(self.temp_dir, scaffold_mode=True)
        self.assertEqual(res_scaffold["status"], "NOTICE")


    # ---------------------------------------------------------------
    # 10. Gate 1: Retraction detection (metadata all correct, but paper retracted -> FAIL)
    # ---------------------------------------------------------------
    def test_10_retraction_detection(self):
        """A citation whose metadata matches Crossref perfectly must still FAIL if retracted."""
        cache_path = os.path.join(self.temp_dir, "retract_cache.json")
        base = {
            "author": [{"family": "Zhang", "given": "Wei"}],
            "issued": {"date-parts": [[2023]]},
            "volume": "1",
            "page": "1-10",
        }
        cache = {
            "https://api.crossref.org/works/10.9999/retracted.test": {
                "message": dict(
                    base,
                    DOI="10.9999/retracted.test",
                    title=["A Retracted Paper on ISAC Waveforms"],
                    relation={"is-retracted-by": [{"id": "10.9999/retraction.notice", "id-type": "doi"}]},
                )
            },
            "https://api.crossref.org/works/10.9999/clean.test": {
                "message": dict(
                    base,
                    DOI="10.9999/clean.test",
                    title=["A Clean Paper on ISAC Waveforms"],
                )
            },
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)

        def entry(doi, title):
            return {"key": "t", "fields": {
                "doi": doi, "title": title, "author": "Zhang, Wei",
                "year": "2023", "volume": "1", "pages": "1-10",
            }}

        client = check_citations.CrossrefClient(cache_path=cache_path, offline=True)
        bad = check_citations.audit_entry(entry("10.9999/retracted.test", "A Retracted Paper on ISAC Waveforms"), client)
        self.assertEqual(bad["status"], "FAIL", "Gate 1 must FAIL when the cited paper has been retracted")
        self.assertIn("撤稿", " ".join(bad["problems"]))
        self.assertIn("retraction", bad["checked"])

        good = check_citations.audit_entry(entry("10.9999/clean.test", "A Clean Paper on ISAC Waveforms"), client)
        self.assertEqual(good["status"], "OK", "A clean paper with matching metadata must not be flagged")
        self.assertNotIn("撤稿", " ".join(good["problems"]))

    # ---------------------------------------------------------------
    # 11. Math: Symbolic identity mismatch (wrong derivation -> FAIL)
    # ---------------------------------------------------------------
    def test_11_symbolic_identity_mismatch(self):
        """sympy-backed math gate must catch a false equation and keep a true one."""
        if not check_math.SYMPY_AVAILABLE:
            self.skipTest("sympy not installed")
        tex = os.path.join(self.temp_dir, "chap_math.tex")
        with open(tex, "w", encoding="utf-8") as f:
            f.write(
                "\\documentclass{article}\n\\begin{document}\n"
                "$$a^2 - b^2 = (a-b)(a+b)$$\n"
                "$$2 + 2 = 5$$\n"
                "\\end{document}\n"
            )
        verified, failed, undecided, issues = check_math.verify_identities([tex], self.temp_dir)
        self.assertGreaterEqual(verified, 1, "A true algebraic identity must be machine-verified")
        self.assertGreaterEqual(failed, 1, "A false equation must be caught")
        self.assertTrue(any(i["rule"] == "Symbolic Identity Mismatch" for i in issues))
        self.assertTrue(any(i["level"] == "FAIL" for i in issues))

    # ---------------------------------------------------------------
    # 12. Anonymize: compiled PDF must never reach the blind copy
    # ---------------------------------------------------------------
    def test_12_anonymize_excludes_build_products(self):
        """A stale main.pdf carries the real name in text + metadata.

        The blind-review copy must drop every build product that has a sibling
        .tex, while keeping figure PDFs (which have no sibling .tex) so the
        blind copy still compiles.
        """
        try:
            from zhaw import anonymize
        except Exception as exc:  # pragma: no cover - zhaw not installed
            self.skipTest(f"zhaw package not importable: {exc}")

        src = os.path.join(self.temp_dir, "thesis_leak")
        os.makedirs(os.path.join(src, "figures"), exist_ok=True)
        with open(os.path.join(src, "main.tex"), "w", encoding="utf-8") as f:
            f.write("\\documentclass{ctexbook}\n\\begin{document}\n正文\n\\end{document}\n")
        with open(os.path.join(src, "main.pdf"), "wb") as f:
            f.write(b"%PDF-1.4 fake compiled output with real name")
        with open(os.path.join(src, "figures", "curve.pdf"), "wb") as f:
            f.write(b"%PDF-1.4 vector figure")

        out = os.path.join(self.temp_dir, "thesis_blind")
        report = anonymize.emit(src, out, force=True)

        self.assertFalse(
            os.path.exists(os.path.join(out, "main.pdf")),
            "Compiled main.pdf must NOT be copied into the blind-review copy",
        )
        self.assertTrue(
            os.path.exists(os.path.join(out, "figures", "curve.pdf")),
            "Figure PDFs must be preserved so the blind copy still compiles",
        )
        self.assertIn("main.pdf", report.get("skipped_build_products", []))
        self.assertTrue(os.path.exists(os.path.join(out, "LEAKS.md")))


if __name__ == "__main__":
    unittest.main()
