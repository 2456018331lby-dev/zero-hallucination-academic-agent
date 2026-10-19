"""Lifecycle flows: the "say one sentence, execute a whole SOP" layer.

Every other module is a *tool*. This one is the *剧本*: it answers the question
"我有这个场景，接下来该按什么顺序做什么，每步怎么验收".

Design rules
------------
* A flow is data, not code — ``FLOWS`` is a dict, so adding a scenario is a
  ten-line edit and nothing else breaks.
* A flow never invents work: each step names a real ``zhaw`` command plus the
  artifact it must produce. ``status()`` checks the artifacts on disk, so
  "done" means "the file exists", not "the model said so".
* Steps that only a human can do are listed under ``human`` and are never
  auto-marked complete.

Usage::

    zhaw flow list                        # all scenarios
    zhaw flow show paper                  # the full SOP for one scenario
    zhaw flow run  paper --project thesis # write RUNBOOK.md into the project
    zhaw flow status paper --project thesis
"""
from __future__ import annotations

from pathlib import Path

from ._util import now_iso, write_json, write_text

# --------------------------------------------------------------------------- #
# Flow definitions
# --------------------------------------------------------------------------- #
# Each step: (kind, command, why, artifact)
#   kind      "cmd" = run it, "human" = only you can do it, "check" = verify
#   artifact  relative path (from project root) or "" when not file-based
FLOWS: dict[str, dict] = {
    "lit": {
        "title": "老师给了一批文献，让我读完做总结",
        "when": "导师/师兄丢来 5-20 篇 PDF，你要在一周内讲清楚它们各自做了什么",
        "output": "每篇一张阅读卡 + 对比矩阵 + 缺口清单 + 组会 PPT",
        "steps": [
            ("cmd", "zhaw read <文献目录> --out survey/read", "先把 PDF 变成可核验的卡片，字段全部带页码", "survey/read/index.json"),
            ("cmd", "zhaw read <文献目录> --out survey/read --digest", "生成综述骨架（正文仍要你自己写）", "survey/read/survey_draft.md"),
            ("human", "补完 comparison_matrix 的研究问题/方法/关键指标/主要结论四列", "这四列机器不猜，猜了就是幻觉", ""),
            ("cmd", "zhaw grounding survey/read/comparison_matrix.md --pdf-dir <文献目录>", "页码级核验：每行声称的页码必须真的在那篇 PDF 里", ""),
            ("cmd", "zhaw seminar survey/read/comparison_matrix.md --compile", "直接出组会 PPT + 讲稿", "survey/seminar_presentation.pdf"),
            ("human", "读一遍 gaps.md，把「作者没写局限」当成你自己的判断依据", "机器只报缺字段，不替你做判断", ""),
        ],
        "human": ["判断每篇论文的方法对不对", "判断数值结果可不可信", "决定哪些是竞品、哪些是背景"],
    },
    "group": {
        "title": "每周组会汇报",
        "when": "每 1-2 周一次，最频繁的场景",
        "output": "16 页左右 Beamer + 逐页讲稿 + 大纲",
        "steps": [
            ("cmd", "zhaw seminar <矩阵> --out-dir talks/group --compile", "从对比矩阵直接生成 PPT，不手打", "talks/group/seminar_presentation.pdf"),
            ("cmd", "zhaw seminar <矩阵> --out-dir talks/group --notes-only", "单独重出讲稿（改完矩阵后）", "talks/group/seminar_notes.md"),
            ("human", "把讲稿里「证据：第 X 页」逐个对照 PDF 确认", "讲错页码比讲错结论更丢人", ""),
            ("human", "准备 3 个导师可能追问的问题", "PPT 只有 16 页，深度在嘴上", ""),
        ],
        "human": ["决定这周讲哪几篇", "把「别人做了什么」和「我做了什么」分开讲"],
    },
    "proposal": {
        "title": "开题报告（研一最紧迫）",
        "when": "入学 3-6 个月，需要提交开题报告并答辩",
        "output": "六章开题报告（≥9000 字 / ≥20 篇文献）+ 机检 PASS + 开题 PPT",
        "steps": [
            ("cmd", "zhaw new my_proposal --kind proposal --title <题目>", "六章框架 + 字数配额，先有结构再填肉", "main.tex"),
            ("cmd", "zhaw read <文献目录> --out literature", "文献卡片，供第一章和第三章引用", "literature/index.json"),
            ("cmd", "zhaw bib my_proposal --apply", "参考文献全部 Crossref 回填，禁止凭记忆写 author", "references.bib"),
            ("human", "写正文：每章按 proposal.py 里的配额推进", "9,351 字这个量级机器写不了，也不该写", ""),
            ("cmd", "zhaw proposal my_proposal --check", "配额 + 封面 + \\cite key + 图片存在性四项硬检查", ""),
            ("cmd", "zhaw compile my_proposal", "编译，0 错误 0 未定义引文才叫完成", "main.pdf"),
            ("cmd", "zhaw defense my_proposal --out-dir talks/proposal --compile", "开题答辩 PPT + 13 问题库", "talks/proposal/defense_presentation.pdf"),
        ],
        "human": ["定选题（这是唯一不能外包的一步）", "写创新点三条", "确定技术路线图"],
    },
    "paper": {
        "title": "从 0 写一篇学位论文 / 期刊论文",
        "when": "有实验结果之后，要把它写成可送审的稿子",
        "output": "完整 LaTeX 论文 + 四门禁 PASS + 可交付度评分",
        "steps": [
            ("cmd", "zhaw new my_thesis --kind thesis --title <题目> --author <姓名> --school 北京邮电大学", "脚手架 + 身份净化（不会带入别人的正文）", "main.tex"),
            ("cmd", "zhaw read <文献目录> --out survey/read", "文献侧证据", "survey/read/index.json"),
            ("cmd", "zhaw figures my_thesis --csv experiments/run.csv --x snr --y psnr --series scheme", "CSV → 矢量图 + 三线表 + includegraphics 片段", "figures"),
            ("human", "把图注、表注、实验分析写进 chap04", "数字的物理含义只有你懂", ""),
            ("cmd", "zhaw bib my_thesis --apply", "引文回填", "references.bib"),
            ("cmd", "zhaw math my_thesis", "符号契约 + 定理强度 + sympy 恒等式", ""),
            ("cmd", "zhaw check my_thesis", "四门禁全过（Gate2 会逐单元格比对 CSV）", ""),
            ("cmd", "zhaw audit my_thesis", "六维可交付度评分 + 缺口清单", "audit_report.md"),
            ("cmd", "zhaw progress my_thesis", "还差多少字、哪章最空", ""),
            ("cmd", "zhaw compile my_thesis", "0 错误 0 溢出 0 未定义引文", "main.pdf"),
            ("cmd", "zhaw gate4 my_thesis --confirm-review", "真人签字（交互输入，占位签名会被拒）", ""),
        ],
        "human": ["写正文（8,000→30,000 字）", "确认每个关键数字与 CSV 的物理含义一致", "Gate 4 逐章签字"],
    },
    "submit": {
        "title": "投稿：选刊、格式化、打包",
        "when": "稿子写完，要投出去",
        "output": "投稿包（匿名稿 + cover letter + checklist + 归档 zip）",
        "steps": [
            ("cmd", "zhaw submit my_thesis --venue ieee-tvt --out-dir submission", "venue 格式检查 + cover letter + 打包清单", "submission/submission_checklist.md"),
            ("cmd", "zhaw anonymize my_thesis --out submission/blind", "双盲期刊必须先匿名化", "submission/blind"),
            ("cmd", "zhaw review my_thesis --venue ieee-tvt --out-dir submission/self_review", "投稿前自审：模拟审稿人会给什么意见", "submission/self_review/review.md"),
            ("human", "按自审意见改稿，改完重跑 zhaw check", "自审的价值在于提前挨骂", ""),
            ("cmd", "zhaw archive my_thesis --out-dir submission --name camera_ready", "zip + SHA-256 manifest，留档", ""),
        ],
        "human": ["决定投哪个刊/会（看 scope、周期、毕业要求）", "确认作者顺序与通讯作者", "在投稿系统里填表"],
    },
    "revision": {
        "title": "审稿意见回来了，要写回复",
        "when": "Major/Minor Revision",
        "output": "逐条回复信 + 修改后的稿子 + 变更清单",
        "steps": [
            ("cmd", "zhaw rebuttal reviews.md --out-dir revision", "把审稿意见拆成条目，生成逐条回复模板", "revision/rebuttal.md"),
            ("human", "逐条填「我们做了什么修改、在第几页第几行」", "回复信的说服力全靠具体到行", ""),
            ("cmd", "zhaw check my_thesis", "改完必须重跑门禁，防止改出新问题", ""),
            ("cmd", "zhaw review my_thesis --venue ieee-tvt --out-dir revision/re_review", "用同一套自审标准复查一遍", "revision/re_review/review.md"),
            ("cmd", "zhaw archive my_thesis --out-dir revision --name revised", "留档", ""),
        ],
        "human": ["判断哪条意见必须照改、哪条可以礼貌反驳", "回复信的语气（不卑不亢）"],
    },
    "defense": {
        "title": "答辩",
        "when": "论文送审通过后",
        "output": "答辩 PPT + 逐页讲稿 + 13 问题库",
        "steps": [
            ("cmd", "zhaw defense my_thesis --out-dir talks/defense --compile", "从论文正文自动抽章节做 PPT", "talks/defense/defense_presentation.pdf"),
            ("human", "把 13 问答案改成你自己的话", "题库给的是「评委想听什么」，不是标准答案", ""),
            ("human", "对着讲稿计时讲两遍", "超时是答辩最常见的死法", ""),
        ],
        "human": ["决定讲哪三个贡献点", "准备被问「创新点到底新在哪」"],
    },
    "blind": {
        "title": "盲审送审",
        "when": "论文定稿，要送外审",
        "output": "匿名稿 + 泄露清单 + 归档",
        "steps": [
            ("cmd", "zhaw anonymize my_thesis --out submission/blind", "13 类泄露清理 + 产物默认排除 + 自检复扫", "submission/blind"),
            ("human", "看 LEAKS.md，确认图片水印/表格姓名列/自引表述", "这三类机器管不了", ""),
            ("cmd", "zhaw compile submission/blind", "匿名版必须能独立编译", "submission/blind/main.pdf"),
            ("cmd", "zhaw archive my_thesis --out-dir submission --name blind_review", "送审留档", ""),
        ],
        "human": ["确认没有间接指认（「本人在导师的指导下」这类）", "确认基金号已删"],
    },
    "midterm": {
        "title": "中期检查",
        "when": "研二上，学院要求提交中期报告",
        "output": "中期报告 + 进度对照 + 成果清单",
        "steps": [
            ("cmd", "zhaw midterm my_thesis --out-dir reports/midterm", "中期报告框架 + 自动填入实测进度", "reports/midterm/midterm_report.md"),
            ("cmd", "zhaw progress my_thesis", "字数/文献/图表实测数字", ""),
            ("human", "补「阶段性成果」和「存在问题」", "成果清单要能对上学院表格", ""),
        ],
        "human": ["确认学制与进度表一致", "导师签字"],
    },
    "weekly": {
        "title": "周报 / 进展记录",
        "when": "每周向导师汇报，或自己留痕",
        "output": "一页周报：做了什么、卡在哪、下周计划、要导师决策什么",
        "steps": [
            ("cmd", "zhaw weekly my_thesis --since 7d --out reports/weekly", "从 git 提交 + 字数变化 + 门禁状态自动生成", "reports/weekly"),
            ("human", "补「卡在哪」和「需要导师决策什么」", "这两项决定导师能不能帮上忙", ""),
        ],
        "human": ["诚实写卡点（写「进展顺利」等于没写）"],
    },
    "archive": {
        "title": "归档 / 留痕",
        "when": "每个阶段结束（开题、中期、送审、答辩）",
        "output": "zip + SHA-256 manifest",
        "steps": [
            ("cmd", "zhaw archive my_thesis --out-dir archives --name <阶段名>", "可校验的存档，防「我改的是哪一版」", ""),
        ],
        "human": ["把 zip 存到学校要求的网盘/系统"],
    },
}


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def list_flows() -> list[dict]:
    return [
        {
            "name": name,
            "title": flow["title"],
            "when": flow["when"],
            "output": flow["output"],
            "steps": len(flow["steps"]),
            "human_steps": sum(1 for s in flow["steps"] if s[0] == "human"),
        }
        for name, flow in FLOWS.items()
    ]


def render_list() -> str:
    rows = list_flows()
    lines = [
        "# 场景剧本（`zhaw flow`）",
        "",
        "选一个场景，照着步骤做。**`human` 标记的步骤机器不替你做。**",
        "",
        "| 剧本 | 什么时候用 | 产出 | 步骤 | 其中人工 |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| `{r['name']}` | {r['when']} | {r['output']} | {r['steps']} | {r['human_steps']} |"
        )
    lines += [
        "",
        "```powershell",
        "zhaw flow show paper            # 看某个剧本的完整步骤",
        "zhaw flow run  paper --project my_thesis   # 写一份 RUNBOOK.md 到工程里",
        "zhaw flow status paper --project my_thesis # 哪些步骤的产物已经有了",
        "```",
        "",
    ]
    return "\n".join(lines)


def render_flow(name: str) -> str:
    if name not in FLOWS:
        raise SystemExit(
            f"unknown flow: {name}\navailable: {', '.join(FLOWS)}"
        )
    flow = FLOWS[name]
    lines = [
        f"# 剧本：{flow['title']}",
        "",
        f"**触发场景**：{flow['when']}",
        "",
        f"**最终产出**：{flow['output']}",
        "",
        "## 步骤",
        "",
    ]
    n = 0
    for kind, command, why, artifact in flow["steps"]:
        n += 1
        if kind == "human":
            lines.append(f"{n}. **[人工]** {command}")
            lines.append(f"   - 为什么：{why}")
        else:
            lines.append(f"{n}. `{command}`")
            lines.append(f"   - 为什么：{why}")
            if artifact:
                lines.append(f"   - 验收：产物 `{artifact}` 存在")
        lines.append("")
    if flow.get("human"):
        lines += ["## 这些事机器做不了", ""]
        for item in flow["human"]:
            lines.append(f"- {item}")
        lines.append("")
    lines += [
        "## 铁律",
        "",
        "1. 顺序不能跳：门禁没过就不要往下走。",
        "2. 标了 `[人工]` 的步骤不许让 AI 代写。",
        "3. 任何数字必须能回到 `experiments/*.csv` 或 PDF 页码。",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Run / status
# --------------------------------------------------------------------------- #
def run(name: str, project: Path | None, out: Path | None = None) -> dict:
    if name not in FLOWS:
        raise SystemExit(f"unknown flow: {name}\navailable: {', '.join(FLOWS)}")
    flow = FLOWS[name]
    text = render_flow(name)
    if project:
        project = Path(project)
        target = Path(out) if out else project / "reports" / "flows"
        path = target / f"{name}.md"
    else:
        path = Path(out) if out else Path(f"RUNBOOK_{name}.md")
    write_text(path, text)
    return {
        "status": "PASS",
        "flow": name,
        "runbook": str(path),
        "steps": len(flow["steps"]),
        "human_steps": sum(1 for s in flow["steps"] if s[0] == "human"),
        "generated_at": now_iso(),
    }


def status(name: str, project: Path) -> dict:
    if name not in FLOWS:
        raise SystemExit(f"unknown flow: {name}\navailable: {', '.join(FLOWS)}")
    project = Path(project)
    steps = []
    for kind, command, why, artifact in FLOWS[name]["steps"]:
        if kind == "human":
            state = "human"
        elif artifact:
            state = "done" if (project / artifact).exists() else "todo"
        else:
            state = "check"
        steps.append(
            {
                "kind": kind,
                "command": command,
                "why": why,
                "artifact": artifact,
                "state": state,
            }
        )
    done = sum(1 for s in steps if s["state"] == "done")
    total = sum(1 for s in steps if s["state"] in ("done", "todo"))
    return {
        "status": "PASS",
        "flow": name,
        "project": str(project),
        "steps": steps,
        "artifacts_done": done,
        "artifacts_total": total,
        "progress": round(done / total, 3) if total else 0.0,
        "next": next((s["command"] for s in steps if s["state"] == "todo"), ""),
    }


def render_status(result: dict) -> str:
    mark = {"done": "[x]", "todo": "[ ]", "human": "[人]", "check": "[验]"}
    lines = [
        f"# 剧本进度：{result['flow']}",
        "",
        f"工程：`{result['project']}`",
        f"产物完成：**{result['artifacts_done']} / {result['artifacts_total']}**"
        f"（{int(result['progress'] * 100)}%）",
        "",
    ]
    if result["next"]:
        lines += [f"下一步：`{result['next']}`", ""]
    lines += ["| | 步骤 | 验收产物 |", "|---|---|---|"]
    for step in result["steps"]:
        lines.append(
            f"| {mark.get(step['state'], '[ ]')} | `{step['command']}` | "
            f"{step['artifact'] or '—'} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_index(path: Path) -> Path:
    write_json(path, {"flows": list_flows(), "generated_at": now_iso()})
    return path
