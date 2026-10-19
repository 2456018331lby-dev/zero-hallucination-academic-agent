"""Mid-term review and weekly report.

Two recurring obligations that every graduate student has and that no existing
command covered:

* ``zhaw midterm``  — 中期检查表（学校有固定表格，但内容是自己的）
* ``zhaw weekly``   — 周报（导师要看的「这周干了什么」）

Both auto-fill everything that can be measured (字数、文献数、占位符、git 提交、
图表数) and leave `[待填]` only where a human judgement is genuinely required.
The weekly report keeps a snapshot per run so it can show the *delta* — which is
the only part a supervisor actually reads.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ._util import (
    chapter_files,
    count_refs,
    hanzi_count,
    now_iso,
    read_text,
    strip_latex,
    todo_count,
    write_json,
    write_text,
)


# --------------------------------------------------------------------------- #
# metrics + snapshot
# --------------------------------------------------------------------------- #
def _metrics(project: Path) -> dict:
    chapters = chapter_files(project)
    body = "\n".join(read_text(p) for p in chapters)
    plain = strip_latex(body)
    per_chapter = {}
    for p in chapters:
        per_chapter[p.name] = hanzi_count(strip_latex(read_text(p)))
    return {
        "hanzi": hanzi_count(plain),
        "todos": todo_count(body),
        "refs": count_refs(project),
        "chapters": len(chapters),
        "per_chapter": per_chapter,
        "figures": len([f for f in (project / "figures").glob("*") if f.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg", ".eps"}])
        if (project / "figures").is_dir() else 0,
        "citations": len(__import__("re").findall(r"\\cite[a-zA-Z]*\{", body)),
    }


def _git(project: Path, *args: str) -> str:
    try:
        out = subprocess.run(
            ["git", *args], cwd=str(project), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=20,
        )
        return out.stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def _git_commits_since(project: Path, days: int = 7) -> list[str]:
    raw = _git(project, "log", f"--since={days} days ago", "--pretty=%h %ad %s", "--date=short")
    return [line for line in raw.splitlines() if line.strip()]


# --------------------------------------------------------------------------- #
# weekly
# --------------------------------------------------------------------------- #
def weekly(project: Path, out_dir: Path, days: int = 7) -> dict:
    project = Path(project)
    out_dir = Path(out_dir)
    m = _metrics(project)
    commits = _git_commits_since(project, days)

    snap_dir = out_dir / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    prev = _latest_snapshot(snap_dir)
    delta = _delta(prev, m) if prev else {}

    stamp = now_iso()[:10]
    snap = {"date": stamp, "generated_at": now_iso(), "metrics": m}
    write_json(snap_dir / f"{stamp}.json", snap)

    md = _weekly_md(project, m, delta, commits, days, prev)
    target = out_dir / f"weekly_{stamp}.md"
    write_text(target, md)
    return {
        "status": "PASS",
        "report": str(target),
        "snapshot": str(snap_dir / f"{stamp}.json"),
        "delta": delta,
        "commits": len(commits),
    }


def _latest_snapshot(snap_dir: Path) -> dict | None:
    files = sorted(snap_dir.glob("*.json"))
    if not files:
        return None
    try:
        return json.loads(files[-1].read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _delta(prev: dict, cur: dict) -> dict:
    pm = prev.get("metrics", {})
    out = {}
    for key in ("hanzi", "todos", "refs", "figures", "citations"):
        a, b = pm.get(key, 0), cur.get(key, 0)
        out[key] = {"before": a, "after": b, "delta": b - a}
    return out


def _fmt_delta(d: dict, key: str, unit: str = "") -> str:
    if key not in d:
        return "—（首次记录）"
    v = d[key]["delta"]
    arrow = "→" if v == 0 else ("↑" if v > 0 else "↓")
    return f"{d[key]['before']:,}{unit} {arrow} {d[key]['after']:,}{unit}（{v:+,}{unit}）"


def _weekly_md(project: Path, m: dict, delta: dict, commits: list[str], days: int, prev: dict | None) -> str:
    lines = [
        f"# 周报（近 {days} 天）",
        "",
        f"工程 `{project.name}`｜生成于 {now_iso()}"
        + (f"｜对比基线 {prev.get('date')}" if prev else "｜首次记录，下次起会显示增量"),
        "",
        "## 1. 量化进展（自动实测）",
        "",
        "| 指标 | 变化 |",
        "|---|---|",
        f"| 正文汉字 | {_fmt_delta(delta, 'hanzi')} |",
        f"| 参考文献 | {_fmt_delta(delta, 'refs', ' 条')} |",
        f"| 图表 | {_fmt_delta(delta, 'figures', ' 个')} |",
        f"| 引用次数 | {_fmt_delta(delta, 'citations', ' 次')} |",
        f"| 待填占位符 | {_fmt_delta(delta, 'todos', ' 处')}（越少越好） |",
        "",
        f"当前总计：**{m['hanzi']:,} 汉字 / {m['refs']} 条文献 / {m['figures']} 个图件 / "
        f"{m['todos']} 处待填**。",
        "",
        "## 2. 代码与稿件提交",
        "",
    ]
    if commits:
        lines += ["```", *commits[:20], "```"]
        if len(commits) > 20:
            lines.append(f"（另有 {len(commits) - 20} 条）")
    else:
        lines.append("近 " + str(days) + " 天没有提交记录。**如果这周真的干了活，说明没提交——先提交。**")
    lines += [
        "",
        "## 3. 这周做了什么（人写，别写成流水账）",
        "",
        "[待填：3-5 条，每条写「做了什么 → 得到什么结论 → 下一步」]",
        "",
        "## 4. 遇到的问题",
        "",
        "[待填：卡在哪、试过什么、需要导师/同学提供什么]",
        "",
        "## 5. 下周计划",
        "",
        "[待填：可验收的具体目标，不要写「继续研究」]",
        "",
        "## 6. 分章进度",
        "",
        "| 章节 | 汉字数 |",
        "|---|---|",
    ]
    for name, n in sorted(m["per_chapter"].items()):
        lines.append(f"| `{name}` | {n:,} |")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# midterm
# --------------------------------------------------------------------------- #
def midterm(project: Path, out_dir: Path, target_hanzi: int = 30000) -> dict:
    project = Path(project)
    out_dir = Path(out_dir)
    m = _metrics(project)
    pct = min(100.0, m["hanzi"] / target_hanzi * 100) if target_hanzi else 0.0
    out_dir.mkdir(parents=True, exist_ok=True)

    md = f"""# 中期检查报告（模板）

工程 `{project.name}`｜生成于 {now_iso()}

> 学校有固定表格时，把下面各节内容搬进去即可。
> **`[待填]` 是必须你自己写的部分**——中期检查看的正是这部分。

## 1. 论文进展情况（自动实测）

| 项 | 当前 | 目标 | 完成度 |
|---|---|---|---|
| 正文汉字 | {m['hanzi']:,} | {target_hanzi:,} | **{pct:.1f}%** |
| 参考文献 | {m['refs']} 条 | 60 条 | {min(100.0, m['refs'] / 60 * 100):.1f}% |
| 图件 | {m['figures']} 个 | 15 个 | {min(100.0, m['figures'] / 15 * 100):.1f}% |
| 待填占位符 | {m['todos']} 处 | 0 | — |

### 分章完成情况

| 章节 | 汉字数 | 状态 |
|---|---|---|
"""
    for name, n in sorted(m["per_chapter"].items()):
        state = "已完成" if n >= 3000 else ("进行中" if n >= 800 else "待写")
        md += f"| `{name}` | {n:,} | {state} |\n"

    md += f"""
## 2. 已完成的研究工作

[待填：按「问题 → 方法 → 结果」写 3-5 条，每条给出可核验的结果]

## 3. 已取得的阶段性成果

[待填：论文/专利/软著/竞赛，写清状态（已投稿/在审/已录用/已授权）]

> 成果清单以 `main.tex` 的「攻读学位期间取得的成果」章节为准，别两处不一致。

## 4. 存在的主要问题

[待填：技术难点、数据获取、实验条件、时间安排]

## 5. 下一步工作计划

| 时间 | 工作内容 | 预期成果 |
|---|---|---|
| [待填] | [待填] | [待填] |

## 6. 需要说明的事项

[待填：延期风险、变更说明、导师意见]

---

## 附：机检建议

先跑完这两条再填表，避免「表格写 3 万字、实际 8 千字」的尴尬：

```powershell
zhaw progress {project.name}
zhaw audit    {project.name} --offline
```
"""
    target = out_dir / "midterm_report.md"
    write_text(target, md)
    write_json(out_dir / "midterm_metrics.json", {
        "generated_at": now_iso(), "metrics": m, "target_hanzi": target_hanzi,
        "completion_pct": round(pct, 1),
    })
    return {
        "status": "PASS",
        "report": str(target),
        "metrics": m,
        "completion_pct": round(pct, 1),
        "gaps": {
            "hanzi": max(0, target_hanzi - m["hanzi"]),
            "refs": max(0, 60 - m["refs"]),
            "figures": max(0, 15 - m["figures"]),
            "todos": m["todos"],
        },
    }


def summary_weekly(result: dict) -> str:
    d = result["delta"]
    lines = [f"[+] 周报已生成：{result['report']}"]
    if d:
        lines.append(
            f"    本周：汉字 {d['hanzi']['delta']:+,} / 文献 {d['refs']['delta']:+d} / "
            f"图件 {d['figures']['delta']:+d} / 占位符 {d['todos']['delta']:+d}"
        )
    else:
        lines.append("    首次记录，已存基线；下周起显示增量。")
    lines.append(f"    提交数：{result['commits']}")
    return "\n".join(lines)


def summary_midterm(result: dict) -> str:
    m = result["metrics"]
    g = result["gaps"]
    lines = [
        f"[+] 中期检查报告：{result['report']}",
        f"    正文完成度 {result['completion_pct']:.1f}%（{m['hanzi']:,} 汉字）",
        f"    还差：{g['hanzi']:,} 汉字 / {g['refs']} 条文献 / {g['figures']} 个图件 / {g['todos']} 处占位符",
    ]
    return "\n".join(lines)
