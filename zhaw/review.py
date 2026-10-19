"""Submission, self-review and rebuttal.

Three scenarios that used to have no command at all:

* ``zhaw submit``    — 选刊约束检查 + cover letter + 打包清单
* ``zhaw review``    — 投稿前自审（用同一套门禁标准模拟审稿人）
* ``zhaw rebuttal``  — 把审稿意见拆成条目，生成逐条回复模板

The design rule is the same as everywhere else: this module produces
**checklists and structure**, never invented content. A cover letter template
with `[待填]` markers is honest; a generated one claiming novelty is not.
"""
from __future__ import annotations

import re
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
# Venue profiles
# --------------------------------------------------------------------------- #
# page_limit: (min, max) for the *main body* when known; None = unknown / no limit
VENUES: dict[str, dict] = {
    "ieee-tvt": {
        "name": "IEEE Transactions on Vehicular Technology",
        "kind": "journal",
        "page_limit": (8, 14),
        "double_blind": False,
        "refs_min": 30,
        "notes": "Regular paper 通常 ≤14 页；超页需付 overlength charge。",
    },
    "ieee-twc": {
        "name": "IEEE Transactions on Wireless Communications",
        "kind": "journal",
        "page_limit": (8, 14),
        "double_blind": False,
        "refs_min": 30,
        "notes": "强调理论贡献与完整证明；仿真需与 baseline 对比。",
    },
    "ieee-tccn": {
        "name": "IEEE Transactions on Cognitive Communications and Networking",
        "kind": "journal",
        "page_limit": (8, 14),
        "double_blind": False,
        "refs_min": 30,
        "notes": "ISAC / 资源分配方向对口。",
    },
    "ieee-comml": {
        "name": "IEEE Communications Letters",
        "kind": "letter",
        "page_limit": (4, 5),
        "double_blind": False,
        "refs_min": 12,
        "notes": "硬性 5 页上限，超页直接退。",
    },
    "ieee-iotj": {
        "name": "IEEE Internet of Things Journal",
        "kind": "journal",
        "page_limit": (8, 14),
        "double_blind": False,
        "refs_min": 30,
        "notes": "低空智联网/无人机方向常见投稿地。",
    },
    "ieee-tap": {
        "name": "IEEE Transactions on Antennas and Propagation",
        "kind": "journal",
        "page_limit": (8, 12),
        "double_blind": False,
        "refs_min": 25,
        "notes": "波形/方向图设计需给出实测或全波仿真。",
    },
    "ieee-access": {
        "name": "IEEE Access",
        "kind": "journal",
        "page_limit": (None, None),
        "double_blind": False,
        "refs_min": 25,
        "notes": "OA，审稿快，但学院可能不计入毕业要求——先确认。",
    },
    "arxiv": {
        "name": "arXiv preprint",
        "kind": "preprint",
        "page_limit": (None, None),
        "double_blind": False,
        "refs_min": 10,
        "notes": "预印本不算正式发表；注意期刊的 preprint 政策。",
    },
    "thesis": {
        "name": "学位论文（送审）",
        "kind": "thesis",
        "page_limit": (None, None),
        "double_blind": True,
        "refs_min": 60,
        "notes": "北邮硕士：正文 3-5 万字、参考文献 ≥60 篇（`--min-bib 60`）。",
    },
}


def venue_profile(venue: str) -> dict:
    key = venue.lower()
    if key not in VENUES:
        raise SystemExit(
            f"unknown venue: {venue}\nknown: {', '.join(VENUES)}\n"
            "自定义期刊请先在本模块的 VENUES 里加一条（页数上限、是否双盲、最少文献数）。"
        )
    return {"key": key, **VENUES[key]}


# --------------------------------------------------------------------------- #
# Shared metrics
# --------------------------------------------------------------------------- #
def _metrics(project: Path) -> dict:
    chapters = chapter_files(project)
    body = "\n".join(read_text(p) for p in chapters)
    plain = strip_latex(body)
    figures = list((project / "figures").glob("*")) if (project / "figures").is_dir() else []
    return {
        "hanzi": hanzi_count(plain),
        "todos": todo_count(body),
        "refs": count_refs(project),
        "chapters": len(chapters),
        "figures": [f.name for f in figures if f.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg", ".eps"}],
        "tables": len(re.findall(r"\\begin\{table\*?\}", body)),
        "equations": len(re.findall(r"\\begin\{(?:equation|align|eqnarray)\*?\}", body)),
    }


# --------------------------------------------------------------------------- #
# submit
# --------------------------------------------------------------------------- #
def submit(project: Path, venue: str, out_dir: Path) -> dict:
    project = Path(project)
    out_dir = Path(out_dir)
    prof = venue_profile(venue)
    m = _metrics(project)
    checks: list[dict] = []

    def add(name: str, state: str, detail: str) -> None:
        checks.append({"name": name, "state": state, "detail": detail})

    add("工程存在", "PASS" if project.is_dir() else "FAIL", str(project))
    add("正文章节", "PASS" if m["chapters"] else "FAIL", f"{m['chapters']} 个章节文件")
    add("参考文献量", "PASS" if m["refs"] >= prof["refs_min"] else "FAIL",
        f"{m['refs']} 条 / 要求 ≥{prof['refs_min']}")
    add("正文残留占位符", "PASS" if m["todos"] == 0 else "FAIL", f"{m['todos']} 处 `\\TODO{{}}`")
    add("图表", "PASS" if m["figures"] else "WARN", f"{len(m['figures'])} 个图件 / {m['tables']} 个表")
    add("公式环境", "PASS" if m["equations"] else "WARN", f"{m['equations']} 个公式块")

    lo, hi = prof["page_limit"]
    pdf = project / "main.pdf"
    add("已编译 PDF", "PASS" if pdf.exists() else "FAIL", str(pdf))
    if hi:
        # page count from PDF if available, else from .log
        pages = _pdf_pages(pdf) if pdf.exists() else None
        if pages:
            add("页数上限", "PASS" if pages <= hi else "FAIL",
                f"{pages} 页 / 上限 {hi} 页" + (f"（下限 {lo}）" if lo else ""))
        else:
            add("页数上限", "WARN", f"无法读取页数（上限 {hi} 页），请人工确认")
    else:
        add("页数上限", "PASS", "该 venue 无硬性页数上限")

    if prof["double_blind"]:
        blind = project / "submission_blind"
        add("双盲匿名化", "PASS" if blind.exists() else "WARN",
            "检测到 submission_blind/；未做请先跑 `zhaw anonymize`")

    out_dir.mkdir(parents=True, exist_ok=True)
    cover = _cover_letter(project, prof, m)
    checklist = _checklist(project, prof, m, checks)
    write_text(out_dir / "cover_letter.md", cover)
    write_text(out_dir / "submission_checklist.md", checklist)
    write_json(out_dir / "submit_report.json", {
        "generated_at": now_iso(), "venue": prof, "metrics": m, "checks": checks,
    })

    failed = [c for c in checks if c["state"] == "FAIL"]
    return {
        "status": "FAIL" if failed else "PASS",
        "venue": prof["name"],
        "checks": checks,
        "metrics": m,
        "cover_letter": str(out_dir / "cover_letter.md"),
        "checklist": str(out_dir / "submission_checklist.md"),
        "failed": [c["name"] for c in failed],
    }


def _pdf_pages(pdf: Path) -> int | None:
    try:
        try:
            import pymupdf as fitz  # noqa: PLC0415
        except ImportError:  # pragma: no cover
            import fitz  # noqa: PLC0415
        doc = fitz.open(str(pdf))
        try:
            return doc.page_count
        finally:
            doc.close()
    except Exception:  # noqa: BLE001
        return None


def _cover_letter(project: Path, prof: dict, m: dict) -> str:
    return f"""# Cover Letter（模板，`[待填]` 必须替换）

> 生成于 {now_iso()}。**这份信里的每一句话都要是真的**——
> 编辑会拿它对照稿件，吹牛比不写更糟。

Dear Editor-in-Chief,

We submit our manuscript entitled **"[待填：与 main.tex 完全一致的标题]"** for
consideration for publication in *{prof['name']}*.

## 1. 这篇稿子做了什么（3 句以内）

[待填：问题是什么 → 我们怎么做的 → 主要结果是什么（带数字）]

## 2. 为什么适合本刊

[待填：{prof['notes']}]

## 3. 与已有工作的区别（不是「首次」，是「不同」）

[待填：引用 2-3 篇最接近的工作，说明差异点]

## 4. 声明

- 本文未在其它期刊/会议发表，也未同时投稿。
- 所有作者已阅读并同意投稿。
- 利益冲突：[待填：无 / 具体说明]
- 数据可用性：[待填：公开链接 / 合理请求提供]

## 5. 稿件统计（自动实测）

| 项 | 值 |
|---|---|
| 正文章节 | {m['chapters']} |
| 参考文献 | {m['refs']} 条 |
| 图 / 表 / 公式 | {len(m['figures'])} / {m['tables']} / {m['equations']} |
| 正文汉字数 | {m['hanzi']:,} |
| 残留占位符 | {m['todos']} |

Sincerely,

[待填：通讯作者姓名、单位、邮箱]
"""


def _checklist(project: Path, prof: dict, m: dict, checks: list[dict]) -> str:
    lines = [
        f"# 投稿清单：{prof['name']}",
        "",
        f"生成于 {now_iso()}｜工程 `{project.name}`",
        "",
        "## 机检结果",
        "",
        "| 检查项 | 结果 | 详情 |",
        "|---|---|---|",
    ]
    for c in checks:
        lines.append(f"| {c['name']} | **{c['state']}** | {c['detail']} |")
    lines += [
        "",
        "## 只有你能做的（机检管不了）",
        "",
        "- [ ] 通讯作者、作者顺序、单位署名已确认",
        "- [ ] 基金号写对（编号一个字符都不能错）",
        "- [ ] 图的分辨率 ≥300 dpi，矢量图优先",
        "- [ ] 参考文献格式按期刊要求（不是学校要求）",
        "- [ ] 查重（学校渠道，本项目不做）",
        "- [ ] 确认目标期刊不在预警名单 / 学院认可目录内",
        "",
        "## 投稿包应包含",
        "",
        "- [ ] `main.pdf`（投稿版）",
        "- [ ] LaTeX 源文件 + 图件（多数期刊要求）",
        "- [ ] `cover_letter.md` → 转 PDF",
        "- [ ] 作者信息表 / ORCID",
        "- [ ] 推荐审稿人（3-5 位，避开合作者）",
        "",
        "## 投稿后",
        "",
        "```powershell",
        f"zhaw archive {project.name} --out-dir archives --name submitted",
        "```",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# review (self-review before submission)
# --------------------------------------------------------------------------- #
def review(project: Path, venue: str, out_dir: Path) -> dict:
    project = Path(project)
    out_dir = Path(out_dir)
    prof = venue_profile(venue)
    m = _metrics(project)
    chapters = chapter_files(project)
    body = "\n".join(read_text(p) for p in chapters)

    findings: list[dict] = []

    def add(sev: str, area: str, text: str, where: str = "") -> None:
        findings.append({"severity": sev, "area": area, "finding": text, "where": where})

    # 结构类
    if m["todos"]:
        add("MAJOR", "完整性", f"正文还有 {m['todos']} 处 `\\TODO{{}}`，审稿人一眼看出未完成", "")
    if m["refs"] < prof["refs_min"]:
        add("MAJOR", "文献", f"仅 {m['refs']} 条参考文献，低于 {prof['name']} 常见水平（≥{prof['refs_min']}）")
    if not m["figures"]:
        add("MAJOR", "图表", "没有任何图件；无线通信类论文通常至少 5 张仿真图")
    if m["tables"] == 0:
        add("MINOR", "图表", "没有三线表；参数表/对比表建议用表呈现")

    # 论证类：找「显著提升」「优于」这类没有数字支撑的断言
    for path in chapters:
        text = strip_latex(read_text(path))
        for line_no, line in enumerate(text.splitlines(), 1):
            if re.search(r"(显著|大幅|明显)\s*(提升|改善|优于|降低)", line) and not re.search(r"\d", line):
                add("MAJOR", "论证", "定性断言无数字支撑：" + line.strip()[:100], f"{path.name}:{line_no}")

    # 实验类：有没有 baseline
    low = body.lower()
    if "baseline" not in low and "基准" not in low:
        add("MAJOR", "实验", "正文未出现 baseline/基准；审稿人必问「和谁比」")
    if "ablation" not in low and "消融" not in low:
        add("MINOR", "实验", "未做消融实验；建议至少验证一个关键模块的必要性")

    # 可复现类
    if not (project / "experiments").is_dir():
        add("MAJOR", "可复现", "没有 experiments/ 目录；Gate 2 无法证明任何数字的来源")
    if not list(project.glob("**/*.bib")):
        add("MAJOR", "文献", "没有 .bib 文件；参考文献无法 Crossref 回填核验")

    # 写作类
    if m["hanzi"] < 6000 and prof["kind"] == "journal":
        add("MINOR", "篇幅", f"正文仅 {m['hanzi']:,} 汉字，期刊论文通常偏短（学位论文要求更高）")

    # 生成审稿意见模板
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "review_findings.json", {
        "generated_at": now_iso(), "venue": prof, "metrics": m, "findings": findings,
    })
    write_text(out_dir / "review.md", _review_md(project, prof, m, findings))

    major = sum(1 for f in findings if f["severity"] == "MAJOR")
    return {
        "status": "PASS" if major == 0 else "ATTENTION",
        "venue": prof["name"],
        "findings": findings,
        "major": major,
        "minor": len(findings) - major,
        "report": str(out_dir / "review.md"),
    }


def _review_md(project: Path, prof: dict, m: dict, findings: list[dict]) -> str:
    lines = [
        f"# 投稿前自审：{prof['name']}",
        "",
        f"生成于 {now_iso()}｜工程 `{project.name}`",
        "",
        "> 这份自审用**审稿人的视角**看稿子：不是「你写得怎么样」，而是「哪里会被拒」。",
        "> 每条都指向具体位置，没有「建议加强创新性」这种空话。",
        "",
        "## 稿件实测",
        "",
        f"- 章节 {m['chapters']} 个 / 正文 {m['hanzi']:,} 汉字 / 参考文献 {m['refs']} 条",
        f"- 图 {len(m['figures'])} / 表 {m['tables']} / 公式 {m['equations']}",
        f"- 残留占位符 {m['todos']} 处",
        "",
        "## 会被问到的问题（按严重度）",
        "",
    ]
    if not findings:
        lines.append("机检没发现问题。**这不等于能中**——机检只管形式，创新性与正确性要同行评议。")
    for f in findings:
        loc = f" `{f['where']}`" if f["where"] else ""
        lines.append(f"- **[{f['severity']}]** `{f['area']}` {f['finding']}{loc}")
    lines += [
        "",
        "## 模拟审稿意见（骨架，需你按稿子填）",
        "",
        "**Reviewer 1（方法）**",
        "- 该方法的假设是否成立？在什么条件下会失效？",
        "- 与 [待填：最接近的 2 篇工作] 的本质区别是什么？",
        "- 复杂度分析是否完整？",
        "",
        "**Reviewer 2（实验）**",
        "- baseline 是否足够强？是否遗漏 SOTA？",
        "- 仿真参数是否合理？是否只挑了有利的场景？",
        "- 统计显著性：多次实验的方差在哪里？",
        "",
        "**Reviewer 3（写作）**",
        "- 贡献点是否在引言里明确列出？",
        "- 图是否自解释（不看正文也能懂）？",
        "- 参考文献是否覆盖近 3 年工作？",
        "",
        "## 建议动作",
        "",
        "1. 先修所有 `MAJOR`——它们是拒稿理由，不是修改建议。",
        "2. 再补 baseline / 消融 / 方差。",
        "3. 改完重跑 `zhaw check` 与 `zhaw audit`。",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# rebuttal
# --------------------------------------------------------------------------- #
_REVIEWER_RE = re.compile(r"(?:reviewer|审稿人)\s*#?\s*(\d+)", re.I)
_COMMENT_SPLIT = re.compile(r"(?m)^\s*(?:[-*•]|\(?\d+[.)])\s+")


def rebuttal(reviews_file: Path, out_dir: Path) -> dict:
    reviews_file = Path(reviews_file)
    out_dir = Path(out_dir)
    if not reviews_file.is_file():
        raise SystemExit(f"not a file: {reviews_file}")
    text = read_text(reviews_file)

    # split by reviewer
    blocks: list[tuple[str, str]] = []
    matches = list(_REVIEWER_RE.finditer(text))
    if matches:
        for i, m in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            blocks.append((f"Reviewer {m.group(1)}", text[m.end():end].strip()))
    else:
        blocks.append(("Reviewer ?", text.strip()))

    items: list[dict] = []
    for reviewer, body in blocks:
        parts = [p.strip() for p in _COMMENT_SPLIT.split(body) if len(p.strip()) > 15]
        for j, part in enumerate(parts, 1):
            items.append({
                "id": f"{reviewer.split()[-1]}-{j}",
                "reviewer": reviewer,
                "comment": re.sub(r"\s+", " ", part)[:600],
                "severity": "MAJOR" if re.search(r"(major|reject|fundamental|serious|不成立)", part, re.I) else "MINOR",
            })

    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "rebuttal_items.json", {
        "generated_at": now_iso(), "source": str(reviews_file), "items": items,
    })
    write_text(out_dir / "rebuttal.md", _rebuttal_md(items, reviews_file))
    return {
        "status": "PASS" if items else "FAIL",
        "items": len(items),
        "major": sum(1 for i in items if i["severity"] == "MAJOR"),
        "rebuttal": str(out_dir / "rebuttal.md"),
        "json": str(out_dir / "rebuttal_items.json"),
    }


def _rebuttal_md(items: list[dict], source: Path) -> str:
    lines = [
        "# 审稿意见逐条回复（模板）",
        "",
        f"来源：`{source.name}`｜共拆出 **{len(items)}** 条意见",
        "",
        "> 规则：**每一条都要回**。不回复 = 默认接受该意见 = 编辑认为你没认真改。",
        "> 回复要写清「改了哪里」，最好到「第 X 页第 Y 行」。",
        "",
        "## 总述",
        "",
        "We thank the editor and all reviewers for the constructive comments. "
        "We have revised the manuscript accordingly; all changes are marked in blue in the "
        "revised version. Our point-by-point responses are below.",
        "",
        "---",
        "",
    ]
    for item in items:
        lines += [
            f"### {item['id']}（{item['severity']}）",
            "",
            f"**Comment**：{item['comment']}",
            "",
            "**Response**：",
            "",
            "> [待填：先复述我们的理解，再写「我们同意/我们部分同意/我们认为需澄清」]",
            "",
            "**Changes**：",
            "",
            "- [待填：第 X 页第 Y 行，改成了什么]",
            "",
            "---",
            "",
        ]
    lines += [
        "## 自检",
        "",
        "- [ ] 每条意见都有回应，没有遗漏",
        "- [ ] 每条回应都指向具体页码/行号",
        "- [ ] 不同意的意见给了理由和证据，不是硬顶",
        "- [ ] 修改后的稿子重跑了 `zhaw check`",
        "",
    ]
    return "\n".join(lines)


def summary_submit(result: dict) -> str:
    lines = [f"[{'+' if result['status'] == 'PASS' else '!'}] 投稿检查：{result['venue']} -> {result['status']}"]
    for c in result["checks"]:
        lines.append(f"    [{c['state']}] {c['name']}: {c['detail']}")
    lines += [
        "",
        f"    Cover letter：{result['cover_letter']}",
        f"    投稿清单：{result['checklist']}",
    ]
    if result["failed"]:
        lines.append(f"[!] 未通过：{', '.join(result['failed'])}")
    return "\n".join(lines)


def summary_review(result: dict) -> str:
    lines = [
        f"[{'+' if result['major'] == 0 else '!'}] 自审：{result['venue']} -> "
        f"{result['major']} MAJOR / {result['minor']} MINOR",
        f"    报告：{result['report']}",
    ]
    for f in result["findings"][:8]:
        loc = f" ({f['where']})" if f["where"] else ""
        lines.append(f"    [{f['severity']}] {f['area']}: {f['finding'][:90]}{loc}")
    if len(result["findings"]) > 8:
        lines.append(f"    … 另有 {len(result['findings']) - 8} 条见报告")
    return "\n".join(lines)


def summary_rebuttal(result: dict) -> str:
    return "\n".join([
        f"[+] 审稿意见已拆成 {result['items']} 条（MAJOR {result['major']}）",
        f"    回复模板：{result['rebuttal']}",
        f"    结构化数据：{result['json']}",
        "",
        "下一步：逐条填 Response 与 Changes，然后重跑 `zhaw check`。",
    ])
