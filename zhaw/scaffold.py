"""Project scaffolding: `zhaw new <dir> --kind thesis|seminar|minimal`.

The point is to make the whole pipeline reusable in 10 seconds: a new thesis
directory that already satisfies the gate layout (chapters/, experiments/,
literature/, survey/, logs/, .human_review.json) instead of a bare LaTeX
skeleton that fails Gate 2/Gate 4 for structural reasons.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from ._util import now_iso, write_json, write_text
from ._paths import repo_root

# Build artifacts that must never be copied into a fresh project.
DROP_SUFFIXES = {
    ".aux", ".log", ".toc", ".lof", ".lot", ".out", ".nav", ".snm", ".vrb",
    ".bcf", ".run.xml", ".synctex.gz", ".fls", ".fdb_latexmk", ".blg", ".bbl",
    ".xdv", ".docx",
}
DROP_NAMES = {
    "main.pdf", "thesis.docx", "gate_summary.json", ".DS_Store", "Thumbs.db",
    # 从源工程继承的「证据缓存/审计报告」属于上一个课题，绝不能带进新工程：
    # 旧的 .citation_cache.json 会让 Gate 1 用别人的元数据「秒过」，
    # 旧的 audit_report.* 会让新工程看起来「已经完成了一半」。
    ".citation_cache.json", "audit_report.json", "audit_report.md",
    "LEAKS.md", "anonymize_report.json", "defense_report.json", "figures_report.json",
}
DROP_DIRS = {"__pycache__", ".pytest_cache", ".ipynb_checkpoints"}

EXPERIMENTS_README = """# experiments/ — 数据溯源目录（Gate 2 的唯一合法数据源）

本目录下的每一个 `*.csv` 都是 Gate 2 的取证对象。规则只有一条：

> **论文正文里出现的每一个定量断言（dB / % / 倍 / bps/Hz / 百分比），
> 都必须能在本目录某个 CSV 的某个单元格里找到对应数值（容差 0.5%）。**

找不到 → Gate 2 FAIL，并报出 `文件:行号`。

## 最小约定

| 列名 | 含义 |
|---|---|
| `scheme` | 方案名（proposed / baseline / ...） |
| `psnr_db` | 数值列，可多个 |
| `rate` | 数值列，可多个 |

`inject_experiment_data.py` 会自动识别数值列并生成三线表；
`plot_academic_curves.py` 用 `--x --y --series` 指定画哪几列。

## 可选元数据

在同名 `<csv>.meta.json` 里写硬件 / 重复次数 / 随机种子，
`inject_experiment_data.py --meta` 会把它渲染成表注。
"""

EXAMPLE_CSV = """scheme,psnr_db,nmse,rate_bps_hz,delta_pct
proposed,28.53,0.0141,12.40,35.0
baseline_time_sharing,22.10,0.0387,9.80,0.0
"""

EXAMPLE_META = {
    "hardware": "CPU: i7-12700H, RAM: 32GB",
    "repeats": 200,
    "seed": 20260914,
    "note": "示例数据，仅用于验证 Gate 2 / 表格 / 绘图链路；出真数据后请整体替换。",
}

GITIGNORE = """# build artifacts
*.aux
*.log
!logs/*.log
*.toc
*.lof
*.lot
*.out
*.nav
*.snm
*.vrb
*.bcf
*.run.xml
*.synctex.gz
*.fls
*.fdb_latexmk
*.blg
*.bbl
*.xdv

# generated deliverables
main.pdf
thesis.docx
*.docx

# python
__pycache__/
*.py[cod]
.pytest_cache/
*.egg-info/

# os / editor
.DS_Store
Thumbs.db
.vscode/
.idea/
"""


def _resolve_thesis_source() -> Path:
    """Pick the source template for a new thesis project.

    The clean template wins over the user's real thesis: copying a *live*
    project drags that project's chapters, citation cache and audit reports into
    every new project, so a brand-new thesis silently starts at "8,171 汉字已写".
    Pass ``--source`` explicitly to clone a real project on purpose.
    """
    root = repo_root()
    template = root / ".agents" / "skills" / "thesis-latex-writer" / "templates" / "thesis_project"
    if template.is_dir():
        return template
    candidate = root / "bupt_isac_workflow" / "thesis_project"
    if candidate.is_dir():
        return candidate
    raise SystemExit(
        "[zhaw new] no thesis source template found "
        "(expected .agents/skills/thesis-latex-writer/templates/thesis_project)"
    )


def _copy_filtered(src: Path, dst: Path) -> int:
    """Copy a project tree, dropping build artifacts. Returns file count."""
    copied = 0
    for item in sorted(src.rglob("*")):
        rel = item.relative_to(src)
        if any(part in DROP_DIRS for part in rel.parts):
            continue
        if item.is_dir():
            (dst / rel).mkdir(parents=True, exist_ok=True)
            continue
        if item.name in DROP_NAMES:
            continue
        # 只丢掉工程根目录下的编译产物 PDF；figures/ 里的矢量图必须保留
        if item.suffix.lower() == ".pdf" and len(rel.parts) == 1:
            continue
        lowered = item.name.lower()
        if any(lowered.endswith(suffix) for suffix in DROP_SUFFIXES):
            continue
        if item.name == ".human_review.json":
            continue
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        copied += 1
    return copied


def _split_title(title: str, width: int = 14) -> tuple[str, str]:
    """Split a long Chinese title into the template's two-line title block."""
    if len(title) <= width:
        return title, ""
    cut = len(title) // 2
    for delta in range(0, 4):
        for idx in (cut + delta, cut - delta):
            if 0 < idx < len(title) and title[idx - 1] not in "的与和及之":
                return title[:idx], title[idx:]
    return title[:cut], title[cut:]


def _neutralize_identity(main_tex: Path, meta: dict) -> list[str]:
    """Replace source-project identity strings that a cover patch cannot reach.

    A copied project still carries the *previous* author's school in the running
    header, the previous title in PDF metadata and the previous English subtitle.
    Leaving them in is exactly the kind of silent inheritance that makes a new
    thesis look finished while every page still says somebody else's university.
    """
    text = main_tex.read_text(encoding="utf-8", errors="replace")
    changed: list[str] = []

    school = meta.get("school") or meta.get("institute") or "[待填：学校名称]"
    school_en = meta.get("school_en") or "[待填：学校英文名]"

    # 页眉校名
    if re.search(r"\\fancyhead\[C\]\{[^}]*\}", text):
        text = re.sub(
            r"\\fancyhead\[C\]\{[^}]*\}",
            lambda m: r"\fancyhead[C]{\small " + school + r"硕士学位论文：\leftmark}",
            text,
            count=1,
        )
        changed.append("header_school")

    # 封面校名横幅：模板把校名逐字用 \quad 撑开（「北\quad 京\quad 大\quad 学」），
    # 普通字符串替换抓不到，必须整行替换。
    if re.search(r"\{\\Huge \\textbf\{[^}]*\}\\par\}", text):
        text = re.sub(
            r"\{\\Huge \\textbf\{[^}]*\}\\par\}",
            lambda m: r"{\Huge \textbf{" + school + r"}\par}",
            text,
            count=1,
        )
        changed.append("cover_school_banner")

    m_en = re.search(r"\{\\Large \\textbf\{[A-Z][A-Za-z\s\.\-]*\}\\par\}", text)
    if m_en:
        # 英文校名长短差异极大（PKU 16 字符 vs BUPT 47 字符），固定 \Large 会溢出行。
        if len(school_en) <= 30:
            line = r"{\Large \textbf{" + school_en + r"}\par}"
        elif len(school_en) <= 44:
            line = r"{\large \textbf{" + school_en + r"}\par}"
        else:
            line = r"{\large \textbf{\resizebox{0.92\textwidth}{!}{" + school_en + r"}}\par}"
        text = text[: m_en.start()] + line + text[m_en.end() :]
        changed.append("cover_school_banner_en")

    # 原创性声明标题里的校名
    if re.search(r"(\\chapter\*\{)[^}]*?(学位论文原创性声明)", text):
        text = re.sub(
            r"(\\chapter\*\{)[^}]*?(学位论文原创性声明)",
            lambda m: m.group(1) + school + m.group(2),
            text,
            count=1,
        )
        changed.append("declaration_school")

    # 兜底：残留的源工程校名
    for stale in ("北京大学", "清华大学", "北京邮电大学"):
        if stale != school and stale in text:
            text = text.replace(stale, school)
            changed.append("stale_school:" + stale)

    title = meta.get("title")
    if title:
        new_title, n = re.subn(r"pdftitle=\{[^}]*\}", lambda m: "pdftitle={" + title + "}", text, count=1)
        if n:
            text = new_title
            changed.append("pdf_title")

    if meta.get("author"):
        new_author, n = re.subn(r"pdfauthor=\{[^}]*\}", "pdfauthor={（作者姓名）}", text, count=1)
        if n:
            text = new_author
            changed.append("pdf_author")

    # 英文副标题来自源工程，必须换成占位符，否则新工程会顶着别人的英文题目。
    # 源工程把英文题目拆成两行，这里只保留第一行占位、删掉续行。
    subtitle = re.compile(r"(?m)^(\s*\{\\large \\textit\{)[^}]*(\}\\par\}\s*)$")
    matches = list(subtitle.finditer(text))
    if matches:
        parts: list[str] = []
        last = 0
        for idx, m in enumerate(matches):
            parts.append(text[last:m.start()])
            parts.append(m.group(1) + "[待填：英文题目]" + m.group(2) if idx == 0 else "")
            last = m.end()
        parts.append(text[last:])
        text = "".join(parts)
        changed.append("english_subtitle")

    main_tex.write_text(text, encoding="utf-8", newline="\n")
    return changed


def _inherited_content(dest: Path) -> list[str]:
    """List content that came from the source template and is NOT the user's work.

    A scaffold that silently inherits another project's chapters looks
    "half finished" to `zhaw audit`; the user must be told which pages are
    still somebody else's text.
    """
    notes: list[str] = []
    chapters = sorted((dest / "chapters").glob("*.tex"))
    hanzi = 0
    for path in chapters:
        text = path.read_text(encoding="utf-8", errors="replace")
        text = re.sub(r"(?<!\\)%.*", "", text)
        hanzi += len(re.findall(r"[\u4e00-\u9fff]", text))
    if chapters:
        notes.append(
            f"chapters/ 下 {len(chapters)} 个 .tex 来自模板，含约 {hanzi} 汉字模板正文 —— "
            "这些字不是你的，`zhaw audit` 的「正文完成度」会把它们算进去，请逐章替换"
        )
    for stale in (".citation_cache.json", "audit_report.json", "audit_report.md"):
        if (dest / stale).exists():
            notes.append(f"{stale} 来自源工程，必须删除或重建（否则 Gate 1 / audit 会用上一个课题的证据）")
    if (dest / "references.bib").exists():
        bib = (dest / "references.bib").read_text(encoding="utf-8", errors="replace")
        n = len(re.findall(r"(?m)^@\w+\{", bib))
        if n:
            notes.append(f"references.bib 含 {n} 条模板文献，换题后必须整表重建（author 禁止凭记忆写）")
    if notes:
        notes.append("确认无误后运行 `zhaw check <dir> --scaffold` 查看继承内容的门禁影响")
    return notes


def _patch_cover(main_tex: Path, meta: dict) -> list[str]:
    """Replace cover-page fields. Returns the list of fields actually patched."""
    if not meta:
        return []
    text = main_tex.read_text(encoding="utf-8", errors="replace")
    patched: list[str] = []

    title = meta.get("title")
    if title:
        first, second = _split_title(title)
        pattern = (
            r"\{\\LARGE \\textbf\{[^}]*\}\\par\}"
            r"(\s*\n\s*\\vspace\{0\.3cm\}\s*\n\s*)"
            r"\{\\LARGE \\textbf\{[^}]*\}\\par\}"
        )
        m = re.search(pattern, text)
        if m:
            if second:
                block = (
                    "{\\LARGE \\textbf{" + first + "}\\par}"
                    + m.group(1)
                    + "{\\LARGE \\textbf{" + second + "}\\par}"
                )
            else:
                block = "{\\LARGE \\textbf{" + first + "}\\par}"
            text = text[: m.start()] + block + text[m.end() :]
            patched.append("title")

    # (meta key aliases, cover label).  `--institute` 与模板里的「学院」是同一个字段，
    # 早先只认 "school" 导致 --institute 被静默丢弃、封面仍是模板默认值。
    field_map = [
        (("author",), "姓\\qquad 名"),
        (("student_id",), "学\\qquad 号"),
        (("institute", "school"), "院\\qquad 系"),
        (("institute", "school"), "学\\qquad 院"),
        (("major",), "专业领域"),
        (("direction",), "研究方向"),
        (("advisor",), "指导教师"),
    ]
    for keys, label in field_map:
        value = next((meta[k] for k in keys if meta.get(k)), None)
        if not value:
            continue
        pattern = r"(\{%s\}：\s*& )([^\\]*)( \\\\)" % re.escape(label)
        new_text, n = re.subn(pattern, lambda m: m.group(1) + value + m.group(3), text, count=1)
        if n:
            text = new_text
            patched.append(keys[0])

    if patched:
        main_tex.write_text(text, encoding="utf-8", newline="\n")
    return patched


def _init_gate_state(dst: Path, kind: str, name: str) -> None:
    write_json(
        dst / ".human_review.json",
        {
            "reviewer": "",
            "status": "PENDING_HUMAN_CONFIRMATION",
            "chapters_confirmed": [],
            "chapter_hashes": {},
            "_comment": (
                "Gate 4 必须由真人签署。AI 自签会被占位符正则拒绝。"
                f"签署方式: zhaw gate4 {name} --confirm-review --reviewer <你的真实姓名>"
            ),
            "created_at": now_iso(),
        },
    )


def _project_md(dst: Path, name: str, kind: str, patched: list[str]) -> str:
    return f"""# {name}

由 `zhaw new` 生成（kind=`{kind}`，{now_iso()}）。

## 这个目录里有什么

| 路径 | 作用 | 对应门禁 |
|---|---|---|
| `main.tex` / `chapters/` | 学位论文正文 | Gate 3（国标合规） |
| `references.bib` | 参考文献（**author 字段禁止凭记忆写**） | Gate 1（引文取证） |
| `experiments/*.csv` | 定量断言的唯一合法数据源 | Gate 2（数据溯源） |
| `literature/` | 本地 PDF 文献池 | Grounding（页码取证） |
| `survey/` | 文献对比矩阵、组会 PPT、调研报告 | Grounding |
| `logs/` | 每次门禁运行的真实日志 | 可复现性 |
| `.human_review.json` | Gate 4 真人签字（当前为待签状态） | Gate 4 |

## 三步开始

```powershell
zhaw check {name} --scaffold          # 先看四道门禁现在什么状态
zhaw figures {name}                   # 用 experiments/example_metrics.csv 生成三线表+曲线
zhaw audit {name} --offline           # 出一份完整审计报告
```

## 下一步（按顺序）

1. 把 `experiments/example_metrics.csv` 换成你的真实仿真数据（列名随意，数值列会被自动识别）。
2. 用 `zhaw bib {name} --apply` 把 `references.bib` 里每条记录的 author/title/卷期页按 Crossref 回填。
3. 写正文，每个数字都能在 CSV 里 grep 到。
4. 文献池放好 PDF 后跑 `zhaw grounding`。
5. 送审前 `zhaw gate4 {name} --confirm-review --reviewer <你的名字>`。

## 本次生成的字段替换

{', '.join(patched) if patched else '（未指定 --title/--author 等，沿用模板封面字段）'}
"""


def new_project(
    dest: Path,
    kind: str = "thesis",
    source: Path | None = None,
    meta: dict | None = None,
    force: bool = False,
) -> dict:
    """Create a new gate-ready project at *dest*."""
    dest = Path(dest)
    kind = (kind or "thesis").lower()
    meta = meta or {}
    name = dest.name

    if dest.exists() and any(dest.iterdir()):
        if not force:
            raise SystemExit(f"[zhaw new] target already exists and is not empty: {dest} (use --force)")
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    created: list[str] = []
    copied = 0
    patched: list[str] = []
    inherited: list[str] = []

    if kind == "thesis":
        src = Path(source) if source else _resolve_thesis_source()
        if not src.is_dir():
            raise SystemExit(f"[zhaw new] source not found: {src}")
        copied = _copy_filtered(src, dest)
        main_tex = dest / "main.tex"
        if main_tex.exists():
            patched = _patch_cover(main_tex, meta)
            patched += _neutralize_identity(main_tex, meta)
            inherited = _inherited_content(dest)
        created += ["main.tex", "chapters/", "references.bib"]

    elif kind == "seminar":
        root = repo_root()
        refs = root / ".agents" / "skills" / "phd-literature-survey" / "references"
        (dest / "survey").mkdir(parents=True, exist_ok=True)
        for fname in ("beamer-template.tex", "ppt-template.md", "report-template.md", "table-template.md"):
            src_file = refs / fname
            if src_file.exists():
                shutil.copy2(src_file, dest / "survey" / fname)
                copied += 1
        created += ["survey/beamer-template.tex", "survey/ppt-template.md"]

    elif kind == "minimal":
        pass
    else:
        raise SystemExit(f"[zhaw new] unknown kind '{kind}' (expected thesis|seminar|minimal)")

    # Gate-ready layout, always.
    (dest / "experiments").mkdir(exist_ok=True)
    (dest / "literature").mkdir(exist_ok=True)
    (dest / "survey").mkdir(exist_ok=True)
    (dest / "logs").mkdir(exist_ok=True)
    write_text(dest / "experiments" / "README.md", EXPERIMENTS_README)
    write_text(dest / "experiments" / "example_metrics.csv", EXAMPLE_CSV)
    write_json(dest / "experiments" / "example_metrics.csv.meta.json", EXAMPLE_META)
    write_text(dest / ".gitignore", GITIGNORE)
    _init_gate_state(dest, kind, name)
    write_text(dest / "PROJECT.md", _project_md(dest, name, kind, patched))

    return {
        "status": "PASS",
        "project": str(dest),
        "kind": kind,
        "files_copied": copied,
        "cover_fields_patched": patched,
        "inherited_content": inherited,
        "created": created + ["experiments/README.md", "experiments/example_metrics.csv",
                              ".human_review.json", ".gitignore", "PROJECT.md"],
        "next": [
            f"zhaw check {name} --scaffold",
            f"zhaw figures {name}",
            f"zhaw audit {name} --offline",
        ],
    }
