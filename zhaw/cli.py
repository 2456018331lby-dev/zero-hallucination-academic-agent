"""Command-line entry point for the Zero-Hallucination Academic Workflow.

The full graduate-school lifecycle, one command per step::

    # 0. environment
    zhaw doctor                        # is this machine able to run everything?
    zhaw selftest                      # 9 adversarial regression cases (proves gates bite)

    # 1. start a project
    zhaw new  my_thesis                # thesis scaffold, ready to compile
    zhaw new  my_proposal --kind proposal   # 开题报告 scaffold
    zhaw new  my_talk --kind seminar        # 组会 PPT scaffold

    # 2. literature
    zhaw survey "<keywords>"           # build a pool from OpenAlex / arXiv
    zhaw grounding survey/matrix.md --pdf-dir literature   # page-level evidence gate

    # 3. write + verify
    zhaw bib    <project>              # rebuild every reference from Crossref (no memory)
    zhaw math   <project>              # notation contract + theorem strength
    zhaw check  <project>              # Gate 1 -> 2 -> 3 -> 4, fail-fast
    zhaw gate1|gate2|gate3|gate4 <project>
    zhaw audit  <project>              # everything + readiness score + gap list

    # 4. data -> figures -> tables
    zhaw figures <project> --csv experiments/run.csv --x snr --y psnr --series scheme

    # 5. deliverables
    zhaw compile  <project>            # XeLaTeX, strict about overfull/undefined refs
    zhaw docx     <project>            # single-source Word export (pandoc)
    zhaw seminar  <matrix> --compile   # 组会 Beamer from a comparison matrix
    zhaw defense  <project> --compile  # 答辩 Beamer + speaker notes + Q&A bank
    zhaw progress <project>            # how much is written, what is still TODO
    zhaw anonymize <project> --out <dir>   # 盲审匿名化 + leak report
    zhaw archive  <project>            # zip + sha256 manifest for submission

Exit codes are the gate contract: 0 = PASS, 1 = FAIL, 2 = strict-mode failure.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__
from ._paths import repo_root, script, skills_dir

GATE1 = "citation-auditor/scripts/check_citations.py"
GATE2_4 = "thesis-latex-writer/scripts/run_quality_gates.py"
GATE3 = "thesis-latex-writer/scripts/check_thesis_compliance.py"
GROUNDING = "phd-literature-survey/scripts/verify_grounding.py"
SELFTEST = "tests/run_selftest.py"
COMPILE = "thesis-latex-writer/scripts/compile_thesis.py"
SURVEY = "academic-paper-discovery/scripts/search_papers.py"
MATH = "math-reviewer/scripts/check_math.py"
TEX_TO_DOCX = "thesis-latex-writer/scripts/tex_to_docx.py"
EXPORT_WORD = "thesis-latex-writer/scripts/export_to_word.py"

OK, FAIL, WARN = 0, 1, 2


def _run(relative: str, args: list[str]) -> int:
    """Run a gate script as a child process, inheriting stdio."""
    cmd = [sys.executable, str(script(relative)), *args]
    return subprocess.run(cmd).returncode


def _load(relative: str, module_name: str):
    """Import a gate script as a module (used for single-gate invocation)."""
    path = script(relative)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"[ERR] Cannot import gate module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _emit_gate(result: dict) -> int:
    status = str((result or {}).get("status", "FAIL")).upper()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if status in ("PASS", "NOTICE"):
        return OK
    return FAIL


# --------------------------------------------------------------------------- #
# doctor
# --------------------------------------------------------------------------- #
def cmd_doctor(_args: argparse.Namespace) -> int:
    problems: list[str] = []
    print(f"zhaw {__version__}")
    print(f"python      : {sys.version.split()[0]}  ({sys.executable})")
    print(f"repository  : {repo_root()}")
    print()

    print("gate scripts:")
    for label, rel in (
        ("gate1 citations", GATE1),
        ("gate2/4 pipeline", GATE2_4),
        ("gate3 compliance", GATE3),
        ("grounding", GROUNDING),
        ("selftest", SELFTEST),
        ("compile", COMPILE),
        ("survey", SURVEY),
    ):
        try:
            path = script(rel)
        except SystemExit:
            print(f"  [MISSING] {label:<18} {rel}")
            problems.append(f"missing {rel}")
        else:
            print(f"  [ok]      {label:<18} {path.relative_to(repo_root())}")

    print()
    try:
        import fitz  # noqa: F401  (PyMuPDF)

        print(f"pymupdf     : {fitz.__doc__.strip().splitlines()[0]}")
    except Exception as exc:  # pragma: no cover - env dependent
        print(f"pymupdf     : MISSING ({exc})")
        problems.append("pymupdf not importable (pip install pymupdf)")

    xelatex = shutil.which("xelatex")
    if not xelatex:
        for cand in (
            Path.home() / "AppData/Local/Programs/MiKTeX/miktex/bin/x64/xelatex.exe",
            Path("C:/Program Files/MiKTeX/miktex/bin/x64/xelatex.exe"),
        ):
            if cand.is_file():
                xelatex = str(cand)
                break
    if xelatex:
        print(f"xelatex     : {xelatex}")
    else:
        print("xelatex     : NOT FOUND (needed only for `zhaw compile`)")

    try:
        head = subprocess.run(
            ["git", "-C", str(repo_root()), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if head.returncode == 0:
            dirty = subprocess.run(
                ["git", "-C", str(repo_root()), "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=False,
            ).stdout.strip()
            state = "dirty" if dirty else "clean"
            print(f"git         : {head.stdout.strip()} ({state})")
    except FileNotFoundError:
        pass

    print()
    if problems:
        print(f"RESULT: NOT READY - {len(problems)} problem(s)")
        for item in problems:
            print(f"  - {item}")
        return FAIL
    print("RESULT: READY - all gate scripts and pymupdf available.")
    return OK


# --------------------------------------------------------------------------- #
# gates
# --------------------------------------------------------------------------- #
def cmd_selftest(args: argparse.Namespace) -> int:
    return _run(SELFTEST, ["--verbose"] if args.verbose else [])


def cmd_gate1(args: argparse.Namespace) -> int:
    extra = []
    if args.offline:
        extra.append("--offline")
    if args.strict:
        extra.append("--strict")
    if args.json:
        extra += ["--json", args.json]
    return _run(GATE1, [args.project, *extra])


def cmd_gate2(args: argparse.Namespace) -> int:
    module = _load(GATE2_4, "zhaw_run_quality_gates")
    return _emit_gate(module.run_gate2_provenance(args.project, scaffold_mode=args.scaffold))


def cmd_gate3(args: argparse.Namespace) -> int:
    extra = ["--min-bib", str(args.min_bib)]
    if args.scaffold:
        extra.append("--scaffold")
    if args.strict:
        extra.append("--strict")
    if args.json:
        extra += ["--json", args.json]
    return _run(GATE3, [args.project, *extra])


def cmd_gate4(args: argparse.Namespace) -> int:
    if args.confirm_review:
        # The interactive sign-off protocol lives in the orchestrator; reuse it
        # verbatim so a human signature is collected exactly as documented.
        extra = ["--confirm-review"]
        if args.reviewer:
            extra += ["--reviewer", args.reviewer]
        if args.yes:
            extra.append("--yes")
        return _run(GATE2_4, [args.project, *extra])
    module = _load(GATE2_4, "zhaw_run_quality_gates")
    return _emit_gate(module.run_gate4_human_review(args.project, scaffold_mode=args.scaffold))


def cmd_check(args: argparse.Namespace) -> int:
    """Full pipeline: Gate 1 -> 2 -> 3 -> 4, fail-fast."""
    extra = ["--min-bib", str(args.min_bib)]
    if args.scaffold:
        extra.append("--scaffold")
    if args.offline:
        extra.append("--offline")
    if args.strict:
        extra.append("--strict")
    if args.json:
        extra += ["--json", args.json]
    return _run(GATE2_4, [args.project, *extra])


def cmd_grounding(args: argparse.Namespace) -> int:
    extra = []
    if args.table_json:
        extra += ["--table-json", args.table_json]
    if args.pdftext:
        extra += ["--pdftext", args.pdftext]
    if args.pdf_dir:
        extra += ["--pdf-dir", args.pdf_dir]
    return _run(GROUNDING, [args.matrix, *extra])


def cmd_compile(args: argparse.Namespace) -> int:
    extra = [args.tex_file]
    if args.strict:
        extra.append("--strict")
    return _run(COMPILE, [args.project, *extra])


def cmd_survey(args: argparse.Namespace) -> int:
    extra = ["--dir", args.dir]
    if args.broad_limit is not None:
        extra += ["--broad-limit", str(args.broad_limit)]
    if args.deep_limit is not None:
        extra += ["--deep-limit", str(args.deep_limit)]
    if args.no_download:
        extra.append("--no-download")
    return _run(SURVEY, [args.query, *extra])


# --------------------------------------------------------------------------- #
# lifecycle: new / bib / math / docx / seminar / defense / figures
#            audit / progress / anonymize / archive
# --------------------------------------------------------------------------- #
def cmd_new(args: argparse.Namespace) -> int:
    from . import proposal, scaffold

    meta = {
        "title": args.title or "",
        "author": args.author or "",
        "student_id": args.student_id or "",
        "institute": args.institute or "",
        "major": args.major or "",
        "direction": args.direction or "",
        "advisor": args.advisor or "",
    }
    meta = {k: v for k, v in meta.items() if v}
    if args.kind == "proposal":
        result = proposal.new_proposal(Path(args.dest), meta=meta, force=args.force)
    else:
        result = scaffold.new_project(
            Path(args.dest), kind=args.kind, source=args.source, meta=meta, force=args.force
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("status") != "PASS":
        return FAIL
    dest = Path(result.get("project") or result.get("dest") or args.dest)
    print()
    print(f"[OK] created: {dest}")
    print(f"     next: zhaw check {dest} --scaffold --offline")
    if (dest / "main.tex").is_file() and args.kind != "seminar":
        print(f"           zhaw compile {dest}")
    return OK


def cmd_proposal(args: argparse.Namespace) -> int:
    from . import proposal

    dest = Path(args.dest)
    if args.check:
        result = proposal.check_proposal(dest, min_total=args.min_total, min_refs=args.min_refs)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return OK if result["status"] == "PASS" else FAIL
    meta = {k: v for k, v in {
        "title": args.title, "author": args.author, "student_id": args.student_id,
        "institute": args.institute, "major": args.major, "topic": args.topic,
        "advisor": args.advisor,
    }.items() if v}
    result = proposal.new_proposal(dest, meta=meta, force=args.force)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print()
    print(f"[OK] proposal: {result.get('project', dest)}")
    print(f"     next: zhaw proposal {result.get('project', dest)} --check")
    return OK


def cmd_bib(args: argparse.Namespace) -> int:
    from . import bib

    result = bib.rebuild(
        Path(args.project), bib=args.bib, apply=args.apply,
        offline=args.offline, cache=args.cache,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print()
    print(bib.summary(result))
    return OK if result.get("status", "PASS") == "PASS" else FAIL


def cmd_math(args: argparse.Namespace) -> int:
    extra = [args.project]
    if args.notation:
        extra += ["--notation", args.notation]
    return _run(MATH, extra)


def cmd_docx(args: argparse.Namespace) -> int:
    from ._paths import script as _script

    out = args.output
    if args.survey:
        extra = ["--survey", args.survey]
        if args.output_survey:
            extra += ["--output-survey", args.output_survey]
        if args.thesis:
            extra += ["--thesis", args.thesis]
        if args.output_thesis:
            extra += ["--output-thesis", args.output_thesis]
        if out:
            extra += ["--output", out]
        if args.scaffold:
            extra.append("--scaffold")
        return _run(EXPORT_WORD, extra)

    extra = [args.tex_file]
    if out:
        extra += ["--output", out]
    if args.scaffold:
        extra.append("--scaffold")
    try:
        _script(TEX_TO_DOCX)
    except SystemExit:
        return _run(EXPORT_WORD, [args.project, *(["--output", out] if out else [])])
    return _run(TEX_TO_DOCX, [args.project, *extra])


def cmd_seminar(args: argparse.Namespace) -> int:
    from . import seminar

    result = seminar.build(
        Path(args.matrix), out_dir=args.out_dir, title=args.title, author=args.author,
        advisor=args.advisor, topic=args.topic, institute=args.institute,
        compile_pdf=args.compile,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("status") != "PASS":
        return FAIL
    print()
    print(f"[OK] seminar deck: {result['tex']}")
    print(f"     notes       : {result['notes']}")
    if result.get("pdf"):
        print(f"     pdf         : {result['pdf']}")
    return OK


def cmd_defense(args: argparse.Namespace) -> int:
    from . import defense

    result = defense.build(
        Path(args.project), out_dir=args.out_dir, title=args.title,
        author=args.author, advisor=args.advisor, institute=args.institute,
        compile=args.compile,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    outputs = result.get("outputs", {})
    tex = outputs.get("tex") or result.get("tex")
    if not tex or not Path(tex).is_file():
        return FAIL
    print()
    print(f"[OK] defense deck : {tex}")
    print(f"     speaker notes: {outputs.get('notes', result.get('notes'))}")
    print(f"     Q&A bank     : {outputs.get('qa', result.get('qa'))}")
    if args.compile:
        pdf = outputs.get("pdf") or result.get("pdf")
        if pdf:
            print(f"     pdf          : {pdf}")
        else:
            print("     [WARN] PDF not built — see compile_log_tail in defense_report.json")
    return OK


def cmd_figures(args: argparse.Namespace) -> int:
    from . import figures

    result = figures.build(
        Path(args.project), csv_file=args.csv, x=args.x, y=args.y, series=args.series,
        caption=args.caption, label=args.label, higher_better=args.higher_better,
        lower_better=args.lower_better, no_table=args.no_table,
        no_plot=args.no_plot, outdir=args.outdir,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("status") not in ("PASS", "NOTICE"):
        return FAIL
    snippet = figures.include_snippet(result, caption=args.caption or "", label=args.label or "")
    if snippet:
        print()
        print("[OK] paste into your chapter:")
        print(snippet)
    return OK


def cmd_audit(args: argparse.Namespace) -> int:
    from . import audit

    result = audit.run_audit(
        Path(args.project), offline=args.offline, scaffold=args.scaffold,
        min_bib=args.min_bib, matrix=args.matrix, pdf_dir=args.pdf_dir,
        out=args.out,
    )
    print(audit.render_markdown(result))
    print()
    print(f"[OK] report: {result['report_md']}")
    print(f"     json  : {result['report_json']}")
    return OK if result["overall"] in ("PASS", "NOTICE") else FAIL


def cmd_progress(args: argparse.Namespace) -> int:
    from . import progress as progress_mod

    result = progress_mod.progress(Path(args.project), target=args.target)
    text = progress_mod.render_progress(result)
    print(text)
    if args.out:
        from ._util import write_text

        write_text(Path(args.out), text)
        print(f"[OK] written: {args.out}")
    return OK if result["status"] == "PASS" else OK


def cmd_anonymize(args: argparse.Namespace) -> int:
    from . import anonymize

    scan = anonymize.scan(Path(args.project))
    print(json.dumps(scan, ensure_ascii=False, indent=2))
    if args.out:
        result = anonymize.emit(Path(args.project), Path(args.out), force=args.force)
        print()
        print(f"[OK] anonymized copy: {result['output']}")
        print(f"     leak report    : {Path(result['output']) / 'LEAKS.md'}")
        print(f"     files copied   : {result['files_copied']}")
        if scan["leak_count"]:
            print(f"     [WARN] {scan['leak_count']} machine-detectable leak(s) were rewritten —"
                  " read LEAKS.md and confirm by eye before submission")
    return OK if scan["leak_count"] == 0 or args.out else WARN


def cmd_archive(args: argparse.Namespace) -> int:
    from . import progress as progress_mod

    result = progress_mod.archive(
        Path(args.project), out_dir=args.out_dir, name=args.name
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print()
    print(f"[OK] archive : {result['archive']}")
    print(f"     manifest: {result['manifest']}")
    return OK


# --------------------------------------------------------------------------- #
# parser
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zhaw",
        description="Zero-Hallucination Academic Workflow — executable anti-fabrication gates.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "exit codes: 0 = PASS, 1 = FAIL, 2 = strict-mode failure\n"
            "typical use: zhaw doctor && zhaw check bupt_isac_workflow/thesis_project --scaffold"
        ),
    )
    parser.add_argument("--version", action="version", version=f"zhaw {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    p = sub.add_parser("doctor", help="check python/pymupdf/xelatex/gate scripts")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("selftest", help="run the 9 adversarial regression cases")
    p.add_argument("--verbose", action="store_true")
    p.set_defaults(func=cmd_selftest)

    p = sub.add_parser("gate1", help="citation gate: every reference vs Crossref")
    p.add_argument("project", help="LaTeX project directory")
    p.add_argument("--offline", action="store_true", help="use the local cache only")
    p.add_argument("--strict", action="store_true", help="WARN also fails")
    p.add_argument("--json", help="write a structured report here")
    p.set_defaults(func=cmd_gate1)

    p = sub.add_parser("gate2", help="data-provenance gate: claims must trace to CSV")
    p.add_argument("project", help="LaTeX project directory")
    p.add_argument("--scaffold", action="store_true", help="scaffold draft: placeholders become NOTICE")
    p.set_defaults(func=cmd_gate2)

    p = sub.add_parser("gate3", help="GB/T 7713.1-2006 + GB/T 7714-2015 compliance gate")
    p.add_argument("project", help="LaTeX project directory")
    p.add_argument("--scaffold", action="store_true")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--min-bib", type=int, default=60, help="minimum reference count (default 60)")
    p.add_argument("--json", help="write a structured report here")
    p.set_defaults(func=cmd_gate3)

    p = sub.add_parser("gate4", help="human sign-off gate (SHA-256 bound)")
    p.add_argument("project", help="LaTeX project directory")
    p.add_argument("--confirm-review", action="store_true", help="run the interactive human protocol")
    p.add_argument("--reviewer", help="reviewer real name")
    p.add_argument("--yes", action="store_true", help="auto-confirm (verification harnesses only)")
    p.add_argument("--scaffold", action="store_true")
    p.set_defaults(func=cmd_gate4)

    p = sub.add_parser("check", help="full pipeline: Gate 1 -> 2 -> 3 -> 4")
    p.add_argument("project", help="LaTeX project directory")
    p.add_argument("--scaffold", action="store_true")
    p.add_argument("--offline", action="store_true")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--min-bib", type=int, default=60)
    p.add_argument("--json", default="gate_summary.json", help="summary output path")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("grounding", help="physical page-evidence gate over real PDFs")
    p.add_argument("matrix", nargs="?", default="survey/literature_comparison_matrix.md",
                   help="comparison matrix markdown (default: survey/literature_comparison_matrix.md)")
    p.add_argument("--pdf-dir", dest="pdf_dir", help="local literature pool directory")
    p.add_argument("--table-json", help="table mode: literature_table.json")
    p.add_argument("--pdftext", help="table mode: extracted text directory (default _pdftext)")
    p.set_defaults(func=cmd_grounding)

    p = sub.add_parser("compile", help="XeLaTeX compile with strict checks")
    p.add_argument("project", help="LaTeX project directory")
    p.add_argument("tex_file", nargs="?", default="main.tex")
    p.add_argument("--strict", action="store_true")
    p.set_defaults(func=cmd_compile)

    p = sub.add_parser("survey", help="build a literature pool (OpenAlex + arXiv)")
    p.add_argument("query", help="research topic or keywords")
    p.add_argument("--dir", default="./literature")
    p.add_argument("--broad-limit", type=int)
    p.add_argument("--deep-limit", type=int)
    p.add_argument("--no-download", action="store_true")
    p.set_defaults(func=cmd_survey)

    # -- lifecycle ---------------------------------------------------------- #
    p = sub.add_parser("new", help="scaffold a thesis / proposal / seminar project")
    p.add_argument("dest", help="destination directory")
    p.add_argument("--kind", choices=("thesis", "proposal", "seminar"), default="thesis")
    p.add_argument("--source", help="override the template source directory")
    p.add_argument("--force", action="store_true", help="write into a non-empty directory")
    p.add_argument("--title")
    p.add_argument("--author")
    p.add_argument("--student-id", dest="student_id")
    p.add_argument("--institute")
    p.add_argument("--major")
    p.add_argument("--direction")
    p.add_argument("--advisor")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("proposal", help="scaffold a research proposal, or check one with --check")
    p.add_argument("dest", help="proposal directory to create (or to check with --check)")
    p.add_argument("--check", action="store_true", help="validate an existing proposal instead of creating one")
    p.add_argument("--force", action="store_true", help="write into a non-empty directory")
    p.add_argument("--min-total", dest="min_total", type=int, default=9000, help="minimum 汉字 for the whole proposal")
    p.add_argument("--min-refs", dest="min_refs", type=int, default=20, help="minimum reference count")
    p.add_argument("--title")
    p.add_argument("--author")
    p.add_argument("--student-id", dest="student_id")
    p.add_argument("--institute")
    p.add_argument("--major")
    p.add_argument("--topic")
    p.add_argument("--advisor")
    p.set_defaults(func=cmd_proposal)

    p = sub.add_parser("bib", help="rebuild .bib fields from Crossref (DOI/title anchored)")
    p.add_argument("project", help="LaTeX project directory")
    p.add_argument("--bib", help="path to the .bib file (default: auto-detect)")
    p.add_argument("--apply", action="store_true", help="overwrite the .bib (keeps a .bak)")
    p.add_argument("--offline", action="store_true")
    p.add_argument("--cache", help="citation cache path")
    p.set_defaults(func=cmd_bib)

    p = sub.add_parser("math", help="math-rigour review: symbols, notation, theorem strength")
    p.add_argument("project", help="LaTeX project directory")
    p.add_argument("--notation", help="notation table markdown")
    p.set_defaults(func=cmd_math)

    p = sub.add_parser("docx", help="export the thesis / survey to Word")
    p.add_argument("project", help="LaTeX project directory")
    p.add_argument("tex_file", nargs="?", default="main.tex")
    p.add_argument("--output", help="output .docx path")
    p.add_argument("--survey", help="survey directory to export instead of the thesis")
    p.add_argument("--output-survey", dest="output_survey")
    p.add_argument("--thesis", help="thesis directory when exporting a survey bundle")
    p.add_argument("--output-thesis", dest="output_thesis")
    p.add_argument("--scaffold", action="store_true")
    p.set_defaults(func=cmd_docx)

    p = sub.add_parser("seminar", help="build a group-meeting Beamer deck from a comparison matrix")
    p.add_argument("matrix", nargs="?", default="survey/literature_comparison_matrix.md")
    p.add_argument("--out-dir", dest="out_dir")
    p.add_argument("--title")
    p.add_argument("--author")
    p.add_argument("--advisor")
    p.add_argument("--topic")
    p.add_argument("--institute")
    p.add_argument("--compile", action="store_true", help="compile the PDF with xelatex")
    p.set_defaults(func=cmd_seminar)

    p = sub.add_parser("defense", help="build a defense deck + speaker notes + Q&A bank")
    p.add_argument("project", help="LaTeX thesis project directory")
    p.add_argument("--out-dir", dest="out_dir")
    p.add_argument("--title")
    p.add_argument("--author")
    p.add_argument("--advisor")
    p.add_argument("--institute")
    p.add_argument("--compile", action="store_true")
    p.set_defaults(func=cmd_defense)

    p = sub.add_parser("figures", help="CSV -> booktabs table + academic vector curve")
    p.add_argument("project", help="LaTeX project directory")
    p.add_argument("--csv", help="experiments CSV (default: first one found)")
    p.add_argument("--x", help="x column")
    p.add_argument("--y", help="y column")
    p.add_argument("--series", help="series column for multiple curves")
    p.add_argument("--caption")
    p.add_argument("--label")
    p.add_argument("--higher-better", dest="higher_better")
    p.add_argument("--lower-better", dest="lower_better")
    p.add_argument("--no-table", dest="no_table", action="store_true")
    p.add_argument("--no-plot", dest="no_plot", action="store_true")
    p.add_argument("--outdir")
    p.set_defaults(func=cmd_figures)

    p = sub.add_parser("audit", help="one report: gates + content + data + refs + readiness")
    p.add_argument("project", help="LaTeX project directory")
    p.add_argument("--offline", action="store_true")
    p.add_argument("--scaffold", action="store_true")
    p.add_argument("--min-bib", type=int, default=60)
    p.add_argument("--matrix", help="comparison matrix for the grounding gate")
    p.add_argument("--pdf-dir", dest="pdf_dir")
    p.add_argument("--out", help="output directory for audit_report.{md,json}")
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("progress", help="word-count quota, TODO list, figure/CSV/ref census")
    p.add_argument("project", help="LaTeX project directory")
    p.add_argument("--target", type=int, default=30000, help="total hanzi target (default 30000)")
    p.add_argument("--out", help="write the markdown report here")
    p.set_defaults(func=cmd_progress)

    p = sub.add_parser("anonymize", help="blind-review anonymisation: scan leaks, emit a clean copy")
    p.add_argument("project", help="LaTeX project directory")
    p.add_argument("--out", help="emit an anonymised copy into this directory")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_anonymize)

    p = sub.add_parser("archive", help="zip the project with a per-file SHA-256 manifest")
    p.add_argument("project", help="LaTeX project directory")
    p.add_argument("--out-dir", dest="out_dir")
    p.add_argument("--name")
    p.set_defaults(func=cmd_archive)

    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
