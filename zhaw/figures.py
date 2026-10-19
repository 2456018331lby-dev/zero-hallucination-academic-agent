"""`zhaw figures <project>` — experiments/*.csv  →  三线表 + 学术矢量曲线.

Thin orchestration over the two scripts that already existed but were never
reachable from the CLI:

  * ``inject_experiment_data.py``  CSV → booktabs 三线表（自动列级加粗最优值）
  * ``plot_academic_curves.py``    CSV → vector PDF + high-DPI PNG

The command also auto-detects numeric columns, so a user who just drops a CSV
into ``experiments/`` gets a table and a figure without remembering any flags.
"""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

from ._paths import script
from ._util import now_iso, read_text, write_json, write_text

MAX_SAMPLE_ROWS = 2000


def _read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        raise SystemExit(f"[zhaw figures] empty CSV: {path}")
    header = [h.strip() for h in rows[0]]
    body = rows[1:][:MAX_SAMPLE_ROWS]
    return header, body


def _is_number(text: str) -> bool:
    try:
        float(text)
        return True
    except (TypeError, ValueError):
        return False


def _numeric_columns(header: list[str], body: list[list[str]]) -> list[int]:
    out = []
    for idx in range(len(header)):
        values = [r[idx] for r in body if idx < len(r) and r[idx].strip()]
        if values and all(_is_number(v) for v in values):
            out.append(idx)
    return out


def _run(script_rel: str, args: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    target = script(script_rel)
    return subprocess.run(
        [sys.executable, str(target), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
    )


def build(
    project: Path,
    csv_file: Path | None = None,
    x: str | None = None,
    y: str | None = None,
    series: str | None = None,
    caption: str | None = None,
    label: str | None = None,
    higher_better: str | None = None,
    lower_better: str | None = None,
    no_table: bool = False,
    no_plot: bool = False,
    outdir: Path | None = None,
) -> dict:
    project = Path(project).resolve()
    exp_dir = project / "experiments"
    if csv_file is None:
        candidates = sorted(exp_dir.glob("*.csv")) if exp_dir.is_dir() else []
        if not candidates:
            raise SystemExit(
                f"[zhaw figures] no CSV under {exp_dir}. "
                "先放一份实验数据（如 experiments/example_metrics.csv）再运行。"
            )
        csv_file = candidates[0]
    csv_file = Path(csv_file).resolve()
    if not csv_file.exists():
        raise SystemExit(f"[zhaw figures] CSV not found: {csv_file}")

    header, body = _read_csv(csv_file)
    numeric = _numeric_columns(header, body)
    if not numeric:
        raise SystemExit(f"[zhaw figures] no numeric column in {csv_file.name}")

    fig_dir = Path(outdir) if outdir else project / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    stem = csv_file.stem

    report: dict = {
        "generated_at": now_iso(),
        "project": str(project),
        "csv": str(csv_file),
        "header": header,
        "numeric_columns": [header[i] for i in numeric],
        "rows": len(body),
        "table": None,
        "figure": None,
        "warnings": [],
    }

    # ---- 三线表 -----------------------------------------------------------
    if not no_table:
        args = [str(csv_file)]
        if caption:
            args += ["--caption", caption]
        if label:
            args += ["--label", label]
        if higher_better:
            args += ["--higher-better", higher_better]
        if lower_better:
            args += ["--lower-better", lower_better]
        meta_candidate = csv_file.with_suffix(csv_file.suffix + ".meta.json")
        if meta_candidate.exists():
            args += ["--meta", str(meta_candidate)]
        proc = _run("thesis-latex-writer/scripts/inject_experiment_data.py", args)
        if proc.returncode != 0:
            report["warnings"].append(f"table failed: {(proc.stderr or proc.stdout).strip()[:400]}")
        else:
            table_tex = fig_dir / f"tab_{stem}.tex"
            write_text(table_tex, proc.stdout)
            report["table"] = str(table_tex)
            report["table_lines"] = len(proc.stdout.splitlines())

    # ---- 矢量曲线 ---------------------------------------------------------
    if not no_plot:
        if y:
            y_cols = [c.strip() for c in y.split(",") if c.strip()]
        else:
            # Default: first numeric column as Y; if >=2 numeric columns and the
            # first is an X-like index/SNR column, plot the rest against it.
            y_cols = [header[numeric[-1]]] if len(numeric) == 1 else [header[numeric[1]]]
        if x:
            x_col = x
        elif len(numeric) >= 2:
            x_col = header[numeric[0]]
        else:
            x_col = header[0]
        pdf_out = fig_dir / f"{stem}_curve.pdf"
        png_out = fig_dir / f"{stem}_curve.png"
        args = [
            "--csv", str(csv_file),
            "--x", x_col,
            "--y", ",".join(y_cols),
            "--output-pdf", str(pdf_out),
            "--output-png", str(png_out),
        ]
        if series:
            args += ["--series", series]
        if caption:
            args += ["--title", caption]
        proc = _run("thesis-latex-writer/scripts/plot_academic_curves.py", args)
        if proc.returncode != 0:
            report["warnings"].append(f"plot failed: {(proc.stderr or proc.stdout).strip()[:400]}")
        else:
            report["figure"] = {
                "pdf": str(pdf_out) if pdf_out.exists() else None,
                "png": str(png_out) if png_out.exists() else None,
                "x": x_col,
                "y": y_cols,
            }

    report["status"] = "PASS" if (report["table"] or report["figure"]) else "FAIL"
    write_json(fig_dir / "figures_report.json", report)
    return report


def include_snippet(report: dict, rel_prefix: str = "../figures",
                    caption: str = "", label: str = "") -> str:
    """A copy-pasteable LaTeX include block for the generated artefacts.

    caption/label 缺省时保留占位符（而不是编造一个图注），因为图注必须由作者写。
    """
    lines = ["% 由 `zhaw figures` 生成，可直接 \\input 进章节"]
    if report.get("table"):
        name = Path(report["table"]).name
        lines.append(f"\\input{{{rel_prefix}/{name}}}")
    if report.get("figure") and report["figure"].get("pdf"):
        name = Path(report["figure"]["pdf"]).name
        cap = caption or "[待填：图注]"
        lab = label or "fig:[待填]"
        lines.append(
            "\\begin{figure}[htbp]\n"
            "  \\centering\n"
            f"  \\includegraphics[width=0.85\\linewidth]{{{rel_prefix}/{name}}}\n"
            f"  \\caption{{{cap}}}\n"
            f"  \\label{{{lab}}}\n"
            "\\end{figure}"
        )
    return "\n".join(lines) + "\n"


def tail_of(text: str, n: int = 8) -> list[str]:
    return [ln for ln in (text or "").splitlines() if ln.strip()][-n:]


def _unused_read_text() -> str:
    return read_text
