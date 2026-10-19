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
DROP_NAMES = {"main.pdf", "thesis.docx", "gate_summary.json", ".DS_Store", "Thumbs.db"}
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
    root = repo_root()
    candidate = root / "bupt_isac_workflow" / "thesis_project"
    if candidate.is_dir():
        return candidate
    fallback = root / ".agents" / "skills" / "thesis-latex-writer" / "templates" / "thesis_project"
    if fallback.is_dir():
        return fallback
    raise SystemExit("[zhaw new] no thesis source template found (expected bupt_isac_workflow/thesis_project)")


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


def _patch_cover(main_tex: Path, meta: dict) -> list[str]:
    """Replace cover-page fields. Returns the list of fields actually patched."""
    if not meta:
        return []
    text = main_tex.read_text(encoding="utf-8", errors="replace")
    patched: list[str] = []

    title = meta.get("title")
    if title:
        # Two consecutive \LARGE \textbf{...} lines form the Chinese title block.
        pattern = r"(\\vspace\{1\.5cm\}\s*\n\s*\{\\LARGE \\textbf\{)([^}]*)(\}\\par\}\s*\n\s*\\vspace\{0\.3cm\}\s*\n\s*\{\\LARGE \\textbf\{)([^}]*)(\}\\par\}\s*\n)"
        if re.search(pattern, text):
            text = re.sub(pattern, lambda m: m.group(1) + title + m.group(3) + "" + m.group(5), text, count=1)
            patched.append("title")

    field_map = {
        "author": ("姓\\qquad 名", None),
        "student_id": ("学\\qquad 号", None),
        "school": ("学\\qquad 院", None),
        "major": ("专业领域", None),
        "direction": ("研究方向", None),
        "advisor": ("指导教师", None),
    }
    for key, (label, _) in field_map.items():
        value = meta.get(key)
        if not value:
            continue
        pattern = r"(\{%s\}：\s*& )([^\\]*)( \\\\)" % re.escape(label)
        new_text, n = re.subn(pattern, lambda m: m.group(1) + value + m.group(3), text, count=1)
        if n:
            text = new_text
            patched.append(key)

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

    if kind == "thesis":
        src = Path(source) if source else _resolve_thesis_source()
        if not src.is_dir():
            raise SystemExit(f"[zhaw new] source not found: {src}")
        copied = _copy_filtered(src, dest)
        main_tex = dest / "main.tex"
        if main_tex.exists():
            patched = _patch_cover(main_tex, meta)
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
        "created": created + ["experiments/README.md", "experiments/example_metrics.csv",
                              ".human_review.json", ".gitignore", "PROJECT.md"],
        "next": [
            f"zhaw check {name} --scaffold",
            f"zhaw figures {name}",
            f"zhaw audit {name} --offline",
        ],
    }
