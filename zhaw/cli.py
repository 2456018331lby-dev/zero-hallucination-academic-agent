"""Command-line entry point for the Zero-Hallucination Academic Workflow.

One command per gate, plus ``check`` which runs the full pipeline:

    zhaw doctor                      # is this machine able to run the gates?
    zhaw selftest                    # 8 adversarial regression cases
    zhaw check  <project>            # Gate 1 -> 2 -> 3 -> 4, fail-fast
    zhaw gate1  <project>            # citations vs Crossref
    zhaw gate2  <project>            # every quantitative claim backed by a CSV
    zhaw gate3  <project>            # GB/T 7713.1-2006 + GB/T 7714-2015 compliance
    zhaw gate4  <project>            # real human sign-off, SHA-256 bound
    zhaw grounding <matrix> --pdf-dir <dir>   # physical page evidence in real PDFs
    zhaw compile <project>           # XeLaTeX, strict about overfull/undefined refs
    zhaw survey <query>              # build a literature pool from OpenAlex/arXiv

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

    p = sub.add_parser("selftest", help="run the 8 adversarial regression cases")
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
