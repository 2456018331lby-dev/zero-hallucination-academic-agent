"""`zhaw audit <project>` — one command that runs every gate and writes a report.

This is the "prove what it can do" command: it does not trust any previous
report, it re-runs the gates, measures the manuscript, and emits both a
human-readable Markdown report and a machine-readable JSON with the exact
numbers it observed.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from ._paths import script
from ._util import now_iso, read_text, rel, thesis_metrics, write_json, write_text

GATES = [
    ("Gate 1 · 引文取证", "citation-auditor/scripts/check_citations.py"),
    ("Gate 2-4 · 质量门禁", "thesis-latex-writer/scripts/run_quality_gates.py"),
    ("Gate 3 · 国标合规", "thesis-latex-writer/scripts/check_thesis_compliance.py"),
    ("Grounding · 页码取证", "phd-literature-survey/scripts/verify_grounding.py"),
]

VERDICT = {0: "PASS", 1: "FAIL", 2: "WARN"}


def _run(script_rel: str, args: list[str], timeout: int = 600) -> dict:
    try:
        target = script(script_rel)
    except SystemExit as exc:  # missing script
        return {"status": "MISSING", "exit": -1, "stdout": "", "stderr": str(exc)}
    proc = subprocess.run(
        [sys.executable, str(target), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return {
        "status": VERDICT.get(proc.returncode, f"EXIT{proc.returncode}"),
        "exit": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _tail(text: str, n: int = 12) -> list[str]:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return lines[-n:]


def _gate1(project: Path, offline: bool) -> dict:
    with tempfile.TemporaryDirectory() as td:
        json_out = Path(td) / "gate1.json"
        args = [str(project), "--json", str(json_out)]
        if offline:
            args.append("--offline")
        res = _run("citation-auditor/scripts/check_citations.py", args)
        stats = {}
        if json_out.exists():
            try:
                stats = json.loads(read_text(json_out)).get("stats", {})
            except json.JSONDecodeError:
                stats = {}
        res["stats"] = stats
        res["summary"] = (
            f"{stats.get('ok', '?')}/{stats.get('total_entries', '?')} 条记录命中 Crossref，"
            f"FAIL={stats.get('fail', '?')} WARN={stats.get('warn', '?')}"
            if stats
            else "（未产出 JSON 统计）"
        )
        return res


def _gates234(project: Path, scaffold: bool, offline: bool, min_bib: int) -> dict:
    args = [str(project), "--min-bib", str(min_bib)]
    if scaffold:
        args.append("--scaffold")
    if offline:
        args.append("--offline")
    res = _run("thesis-latex-writer/scripts/run_quality_gates.py", args)
    summary_path = project / "gate_summary.json"
    gates = {}
    if summary_path.exists():
        try:
            data = json.loads(read_text(summary_path))
            gates = data.get("gates", data if isinstance(data, dict) else {})
        except json.JSONDecodeError:
            gates = {}
    res["gates"] = gates
    return res


def _gate3(project: Path, scaffold: bool, min_bib: int) -> dict:
    args = [str(project), "--min-bib", str(min_bib)]
    if scaffold:
        args.append("--scaffold")
    return _run("thesis-latex-writer/scripts/check_thesis_compliance.py", args)


def _grounding(matrix: Path, pdf_dir: Path | None) -> dict:
    args = [str(matrix)]
    if pdf_dir:
        args += ["--pdf-dir", str(pdf_dir)]
    return _run("phd-literature-survey/scripts/verify_grounding.py", args)


def _readiness(metrics: dict, gate_status: dict, signed: bool) -> dict:
    """A transparent 0-100 score. Weights are documented, not magic."""
    gates_ok = sum(1 for s in gate_status.values() if s == "PASS")
    gates_total = max(1, len(gate_status))
    gate_score = 100.0 * gates_ok / gates_total
    content = min(100.0, 100.0 * metrics["hanzi_total"] / 30000.0)
    data = 100.0 if metrics["has_experiments_csv"] else 0.0
    todo_penalty = min(30.0, metrics["todo_total"] * 1.0)
    refs = min(100.0, 100.0 * metrics["refs"] / 60.0)
    human = 100.0 if signed else 0.0

    overall = (
        0.30 * gate_score
        + 0.25 * content
        + 0.15 * data
        + 0.10 * refs
        + 0.10 * human
        + 0.10 * max(0.0, 100.0 - todo_penalty)
    )
    return {
        "gate_score": round(gate_score, 1),
        "content_score": round(content, 1),
        "data_score": round(data, 1),
        "refs_score": round(refs, 1),
        "human_score": round(human, 1),
        "todo_penalty": round(todo_penalty, 1),
        "overall": round(overall, 1),
        "weights": {
            "gates": 0.30, "content": 0.25, "data": 0.15,
            "refs": 0.10, "human": 0.10, "no_todo": 0.10,
        },
    }


def run_audit(
    project: Path,
    offline: bool = False,
    scaffold: bool = False,
    min_bib: int = 60,
    matrix: Path | None = None,
    pdf_dir: Path | None = None,
    out: Path | None = None,
) -> dict:
    project = Path(project).resolve()
    if not project.is_dir():
        raise SystemExit(f"[zhaw audit] project directory not found: {project}")

    # 夹具工程（FIXTURE.md）：故意保留缺陷用于回归测试，低分是预期结果而不是待办。
    # 不识别它的话，audit 会把「故意留的假数据」当成「没做完的论文」，误导使用者。
    fixture_note = ""
    fixture_path = project / "FIXTURE.md"
    if fixture_path.exists():
        fixture_note = read_text(fixture_path).strip().splitlines()[0].lstrip("# ").strip()

    metrics = thesis_metrics(project)

    hr_path = project / ".human_review.json"
    signed = False
    reviewer = ""
    if hr_path.exists():
        try:
            hr = json.loads(read_text(hr_path))
            signed = bool(hr.get("chapter_hashes")) and hr.get("status") == "CONFIRMED"
            reviewer = hr.get("reviewer", "") or ""
        except json.JSONDecodeError:
            pass

    gate1 = _gate1(project, offline)
    gates234 = _gates234(project, scaffold, offline, min_bib)
    gate3 = _gate3(project, scaffold, min_bib)

    matrix_path = Path(matrix) if matrix else None
    if matrix_path is None:
        for candidate in (project / "survey" / "literature_comparison_matrix.md",
                          project.parent / "survey" / "literature_comparison_matrix.md"):
            if candidate.exists():
                matrix_path = candidate
                break
    grounding = {"status": "SKIP", "exit": -1, "stdout": "", "stderr": "no matrix"}
    if matrix_path and matrix_path.exists():
        if pdf_dir is None:
            for candidate in (project / "literature", project.parent / "literature"):
                if candidate.is_dir():
                    pdf_dir = candidate
                    break
        grounding = _grounding(matrix_path, pdf_dir)

    # 评分只数 DoD 的四道门（1/2/3/4）。`run_quality_gates.py` 一次跑 2-4 并写
    # gate_summary.json，这里按组件拆开，避免把三道门折成一道、又把 Grounding 这个
    # 诊断项算进分母（那会把 3/4 报成 2/4）。
    component = gates234.get("gates") or {}

    def _comp(key: str, fallback: str) -> str:
        item = component.get(key) if isinstance(component, dict) else None
        return item.get("status", fallback) if isinstance(item, dict) else fallback

    gate_status = {
        "Gate 1": gate1["status"],
        "Gate 2": _comp("gate2_provenance", gates234["status"]),
        "Gate 3": _comp("gate3_compliance", gate3["status"]),
        "Gate 4": _comp("gate4_human_review", gates234["status"]),
    }
    readiness = _readiness(metrics, gate_status, signed)

    report = {
        "generated_at": now_iso(),
        "project": str(project),
        "mode": {"offline": offline, "scaffold": scaffold, "min_bib": min_bib},
        "metrics": metrics,
        "gates": {
            "gate1": {"status": gate1["status"], "stats": gate1.get("stats", {}),
                      "tail": _tail(gate1["stdout"])},
            "gate2_4": {"status": gates234["status"], "gates": gates234.get("gates", {}),
                        "tail": _tail(gates234["stdout"])},
            "gate3": {"status": gate3["status"], "tail": _tail(gate3["stdout"])},
            "grounding": {"status": grounding["status"],
                          "matrix": rel(matrix_path, project) if matrix_path else None,
                          "pdf_dir": str(pdf_dir) if pdf_dir else None,
                          "tail": _tail(grounding["stdout"])},
        },
        # DoD 四道门的逐项状态（评分与"差什么"都以它为准）
        "gate_table": gate_status,
        "human_review": {"signed": signed, "reviewer": reviewer},
        "readiness": readiness,
        "fixture": {"is_fixture": bool(fixture_note), "note": fixture_note},
    }
    statuses = list(gate_status.values()) + [grounding["status"]]
    report["overall"] = (
        "FAIL" if "FAIL" in statuses
        else "NOTICE" if any(s in ("NOTICE", "SKIP") for s in statuses)
        else "PASS"
    )

    out_path = Path(out) if out else project / "audit_report.json"
    write_json(out_path, report)
    md_path = out_path.with_suffix(".md")
    write_text(md_path, _render_markdown(report))
    report["report_json"] = str(out_path)
    report["report_md"] = str(md_path)
    return report


def _bar(value: float) -> str:
    filled = int(round(value / 10.0))
    return "█" * filled + "░" * (10 - filled)


def _render_markdown(report: dict) -> str:
    m = report["metrics"]
    r = report["readiness"]
    g = report["gates"]
    fixture = report.get("fixture") or {}
    lines = [
        f"# 审计报告 · {Path(report['project']).name}",
        "",
        f"生成时间：`{report['generated_at']}`  ",
        f"模式：`offline={report['mode']['offline']}` `scaffold={report['mode']['scaffold']}` "
        f"`min_bib={report['mode']['min_bib']}`",
        "",
    ]
    if fixture.get("is_fixture"):
        lines += [
            "> [!IMPORTANT]",
            f"> **这是夹具工程（fixture），不是待完成的论文。** {fixture.get('note', '')}",
            "> 它故意保留假数据、缺 CSV、未签署等缺陷，用来回归测试四道门禁能否抓住问题。",
            "> **下面的低分是预期结果**——不要拿它当「工作没做完」的证据，也不要为了提分去填造数据。",
            "",
        ]
    lines += [
        "## 1. 总评",
        "",
        f"**可交付度 {r['overall']} / 100**",
        "",
        "| 维度 | 得分 | 权重 | 依据 |",
        "| --- | :---: | :---: | --- |",
        f"| 门禁通过率 | {r['gate_score']} | {r['weights']['gates']} | {_dod_pass_text(report)} |",
        f"| 正文完成度 | {r['content_score']} | {r['weights']['content']} | {m['hanzi_total']} 汉字 / 目标 30,000 |",
        f"| 数据可溯源 | {r['data_score']} | {r['weights']['data']} | experiments/*.csv {'存在' if m['has_experiments_csv'] else '缺失'} |",
        f"| 参考文献量 | {r['refs_score']} | {r['weights']['refs']} | {m['refs']} 条 / 目标 60 |",
        f"| 真人签署 | {r['human_score']} | {r['weights']['human']} | {'已签：' + report['human_review']['reviewer'] if report['human_review']['signed'] else '未签署'} |",
        f"| 脚手架残留 | {round(100 - r['todo_penalty'], 1)} | {r['weights']['no_todo']} | {m['todo_total']} 处 `\\TODO{{}}` |",
        "",
        "## 2. 门禁明细",
        "",
        "| 门禁 | 结果 | 观察到的证据 |",
        "| --- | :---: | --- |",
        f"| Gate 1 引文取证 | **{g['gate1']['status']}** | {_gate1_line(g['gate1'])} |",
        f"| Gate 2 数据溯源 | **{_dod_status(report, 'Gate 2')}** | {_gate234_evidence(g['gate2_4'], 'gate2_provenance')} |",
        f"| Gate 3 国标合规 | **{_dod_status(report, 'Gate 3')}** | {_gate234_evidence(g['gate2_4'], 'gate3_compliance')} |",
        f"| Gate 4 真人签署 | **{_dod_status(report, 'Gate 4')}** | {_gate234_evidence(g['gate2_4'], 'gate4_human_review')} |",
        f"| Grounding 页码取证 | **{g['grounding']['status']}** | {_last(g['grounding']['tail'])} |",
        "",
        "## 3. 手稿实测",
        "",
        f"- 章节文件：**{m['chapters']}** 个",
        f"- 正文汉字：**{m['hanzi_total']:,}**（硕士常规 30,000–50,000）",
        f"- `\\TODO{{}}` 占位：**{m['todo_total']}** 处",
        f"- 参考文献：**{m['refs']}** 条",
        f"- 图片：**{m['figures']}** 个 PDF",
        f"- `experiments/*.csv`：**{'有' if m['has_experiments_csv'] else '无'}**",
        "",
        "### 分章汉字数",
        "",
        "| 章节 | 汉字 | TODO |",
        "| --- | ---: | ---: |",
    ]
    for name, stat in m["per_chapter"].items():
        lines.append(f"| `{name}` | {stat['hanzi']:,} | {stat['todo']} |")

    lines += [
        "",
        "## 4. 距离可交付还差什么",
        "",
    ]
    gaps = _gaps(report)
    if gaps:
        for i, gap in enumerate(gaps, 1):
            lines.append(f"{i}. {gap}")
    else:
        lines.append("没有阻断项。")
    lines += [
        "",
        "## 5. 复现命令",
        "",
        "```powershell",
        f"zhaw audit {Path(report['project']).name} "
        f"{'--offline ' if report['mode']['offline'] else ''}"
        f"{'--scaffold ' if report['mode']['scaffold'] else ''}"
        f"--min-bib {report['mode']['min_bib']}",
        "```",
        "",
        "> 本报告由 `zhaw audit` 现场重跑生成，未读取任何历史报告的数字。",
        "",
    ]
    return "\n".join(lines)


def render_markdown(report: dict) -> str:
    """公开别名：把审计结果渲染成 Markdown 报告。"""
    return _render_markdown(report)


def _gate1_line(gate: dict) -> str:
    stats = gate.get("stats") or {}
    if not stats:
        return _last(gate.get("tail", []))
    return (
        f"{stats.get('ok', '?')}/{stats.get('total_entries', '?')} 条命中 Crossref，"
        f"FAIL={stats.get('fail', '?')}，WARN={stats.get('warn', '?')}"
    )


def _gate234_line(gate: dict) -> str:
    gates = gate.get("gates") or {}
    if isinstance(gates, dict) and gates:
        parts = []
        for name, value in gates.items():
            status = value.get("status") if isinstance(value, dict) else value
            parts.append(f"{name}={status}")
        return "，".join(parts)
    return _last(gate.get("tail", []))


def _gate234_evidence(gate: dict, key: str) -> str:
    """把某一道门自己的 details 摘要成一句，而不是把三/四道门串成一串。"""
    gates = gate.get("gates") or {}
    item = gates.get(key) if isinstance(gates, dict) else None
    if not isinstance(item, dict):
        return _last(gate.get("tail", []))
    details = item.get("details")
    if isinstance(details, list):
        text = "；".join(str(d) for d in details if str(d).strip())
    else:
        text = str(details or "")
    text = text.strip()
    if not text:
        # 有些门（如 Gate 3）不写 details，只把结论打在 stdout 里
        picked: list[str] = []
        for line in str(item.get("stdout") or "").splitlines():
            flat = line.strip()
            if not flat or _SEPARATOR_RE.match(flat):
                continue
            if "Results:" in flat or flat.startswith(("[WARNING]", "[ERROR]")):
                picked.append(flat)
            if len(picked) >= 3:
                break
        text = "；".join(picked) or "（无附加说明）"
    return _cell(text, 160)


def _dod_status(report: dict, name: str) -> str:
    return (report.get("gate_table") or {}).get(name, "SKIP")


def _dod_pass_text(report: dict) -> str:
    table = report.get("gate_table") or {}
    if not table:
        return "（无门禁结果）"
    ok = sum(1 for s in table.values() if s == "PASS")
    failed = [n for n, s in table.items() if s not in ("PASS", "NOTICE")]
    tail = f"，未过：{'、'.join(failed)}" if failed else ""
    return f"{ok}/{len(table)} 项 PASS{tail}"


def _cell(text: str, limit: int) -> str:
    """Markdown 表格单元格里不能有裸 | 和换行。"""
    flat = " ".join(str(text).split()).replace("|", "\\|")
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


_SEPARATOR_RE = re.compile(r"^[=\-*_~#]{8,}$")


def _last(tail: list[str]) -> str:
    for line in reversed(tail or []):
        text = line.strip()
        if text and not _SEPARATOR_RE.match(text):
            return _cell(text, 160)
    return "（无输出）"


def _gaps(report: dict) -> list[str]:
    m = report["metrics"]
    g = report["gates"]
    gaps: list[str] = []
    table = report.get("gate_table") or {}
    dod = {
        "Gate 1": "**Gate 1 未过**：参考文献 author/卷期页与 Crossref 不一致，送审会被盲审抓。",
        "Gate 2": "**Gate 2 未过**：正文有 CSV 里找不到的定量断言（数据溯源断了）。",
        "Gate 3": "**Gate 3 未过**：GB/T 7713.1-2006 / GB/T 7714-2015 合规检查未通过。",
        "Gate 4": "Gate 4 未签署 —— 这是设计如此，必须真人执行 `--confirm-review`。",
    }
    for name, message in dod.items():
        status = table.get(name)
        if status is None:
            continue
        if name == "Gate 4":
            if not report["human_review"]["signed"]:
                gaps.append(message)
            continue
        if status not in ("PASS", "NOTICE"):
            gaps.append(message)
    if g["grounding"]["status"] == "FAIL":
        gaps.append("**Grounding 未过**：文献矩阵里的页码/特征词在本地 PDF 中核不到。")
    if not m["has_experiments_csv"]:
        gaps.append("`experiments/*.csv` 缺失 —— Gate 2 无法证明任何数字有出处。")
    if m["hanzi_total"] < 30000:
        need = 30000 - m["hanzi_total"]
        gaps.append(f"正文只有 {m['hanzi_total']:,} 汉字，距 3 万字还差 **{need:,}** 字。")
    if m["todo_total"]:
        gaps.append(f"仍有 **{m['todo_total']}** 处 `\\TODO{{}}` 占位。")
    if m["refs"] < 60:
        gaps.append(f"参考文献 {m['refs']} 条，硕士论文常规要求 ≥60。")
    return gaps
