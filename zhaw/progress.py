"""`zhaw progress` / `zhaw archive` — 进度量化与毕业材料归档.

`progress` 回答三个一直悬着的问题:
    1. 论文写了多少？（分章汉字数 vs 配额）
    2. 还差什么？（全部 ``\\TODO{}`` 的 file:line 清单）
    3. 数据/图表/参考文献到位了吗？

`archive` 把要交的东西打成一份可校验的包（排除编译中间物与回收站），
并生成 sha256 manifest —— 答辩材料归档、多学期留存都用它。
"""
from __future__ import annotations

import hashlib
import re
import zipfile
from pathlib import Path

from ._util import chapter_files, hanzi_count, now_iso, write_json, write_text

# 硕士论文（3–5 万字）的默认分章配额，按章节标题关键字匹配
DEFAULT_QUOTAS: list[tuple[str, int, tuple[str, ...]]] = [
    ("绪论/引言", 5000, ("绪论", "引言", "背景", "intro")),
    ("相关工作/综述", 6000, ("相关", "综述", "现状", "related")),
    ("方法/建模", 10000, ("方法", "建模", "模型", "method", "设计")),
    ("实验/结果", 7000, ("实验", "结果", "验证", "experiment", "result")),
    ("结论/展望", 3000, ("结论", "展望", "总结", "conclusion")),
]
FALLBACK_QUOTA = 4000
TOTAL_TARGET = 30000

TODO_RE = re.compile(r"\\TODO\{([^}]*)\}")
SKIP_DIRS = {"__pycache__", ".git", "_trash", ".pytest_cache", "dist", ".ruff_cache"}
SKIP_SUFFIXES = {
    ".aux", ".log", ".out", ".toc", ".lof", ".lot", ".bbl", ".blg", ".fls",
    ".fdb_latexmk", ".nav", ".snm", ".vrb", ".bcf", ".run.xml", ".synctex.gz",
}


def _quota_for(title: str) -> tuple[str, int]:
    low = title.lower()
    for label, quota, keys in DEFAULT_QUOTAS:
        if any(key.lower() in low for key in keys):
            return label, quota
    return "其他章节", FALLBACK_QUOTA


def _todo_list(project: Path) -> list[dict]:
    out: list[dict] = []
    for path in sorted(project.rglob("*.tex")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        rel = path.relative_to(project).as_posix()
        for idx, line in enumerate(lines, start=1):
            for match in TODO_RE.finditer(line):
                out.append({"file": rel, "line": idx, "text": match.group(1).strip() or "(空)",
                            "context": line.strip()[:120]})
    return out


def progress(project: Path, target: int = TOTAL_TARGET) -> dict:
    project = Path(project).resolve()
    chapters = []
    total = 0
    for path in chapter_files(project):
        text = path.read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            continue
        match = re.search(r"\\chapter\*?\{(.+?)\}", text)
        if not match:
            match = re.search(r"\\section\*?\{(.+?)\}", text)
        if match:
            title = match.group(1)
            title = re.sub(r"\\[a-zA-Z]+\s*", "", title).strip()
        else:
            # 既无 \chapter 也无 \section：用文件名，但剥掉 chapNN_secNN_ 之类前缀
            stem = re.sub(r"^chap\d+_(?:sec\d+_)?", "", path.stem)
            title = stem.replace("_", " ").strip() or path.stem
        chars = hanzi_count(text)
        total += chars
        label, quota = _quota_for(title)
        chapters.append({
            "file": path.relative_to(project).as_posix(),
            "title": title,
            "category": label,
            "hanzi": chars,
            "quota": quota,
            "percent": round(min(100.0, 100.0 * chars / quota), 1) if quota else 0.0,
        })

    todos = _todo_list(project)
    figures = sorted(p.name for p in (project / "figures").glob("*.pdf")) if (project / "figures").is_dir() else []
    csvs = sorted(p.name for p in (project / "experiments").glob("*.csv")) if (project / "experiments").is_dir() else []
    bib = next(iter(sorted(project.glob("*.bib"))), None)
    refs = 0
    if bib and bib.exists():
        refs = len(re.findall(r"^@\w+\{", bib.read_text(encoding="utf-8", errors="replace"), re.MULTILINE))

    percent = round(min(100.0, 100.0 * total / target), 1) if target else 0.0
    status = "PASS" if percent >= 100 and not todos else "IN_PROGRESS"
    return {
        "generated_at": now_iso(),
        "project": str(project),
        "status": status,
        "total_hanzi": total,
        "target": target,
        "percent": percent,
        "remaining": max(0, target - total),
        "chapters": chapters,
        "todos": todos,
        "todo_count": len(todos),
        "figures": figures,
        "csv_files": csvs,
        "references": refs,
        "bib": str(bib) if bib else None,
    }


def render_progress(result: dict) -> str:
    bar_len = 30
    filled = int(round(bar_len * result["percent"] / 100.0))
    bar = "█" * filled + "·" * (bar_len - filled)
    lines = [
        "# 论文进度报告",
        "",
        f"- 工程: `{result['project']}`",
        f"- 进度: `{bar}` **{result['percent']}%**（{result['total_hanzi']} / {result['target']} 汉字，"
        f"还差 {result['remaining']}）",
        f"- 待填占位符: **{result['todo_count']}** 处",
        f"- 图表: {len(result['figures'])} 张矢量图 / {len(result['csv_files'])} 份 CSV",
        f"- 参考文献: {result['references']} 条",
        "",
        "## 分章进度",
        "",
        "| 章节 | 类别 | 汉字 | 配额 | 完成度 |",
        "|---|---|---|---|---|",
    ]
    for chap in result["chapters"]:
        lines.append(
            f"| {chap['title'][:24]} | {chap['category']} | {chap['hanzi']} | "
            f"{chap['quota']} | {chap['percent']}% |"
        )
    lines += ["", "## 待填清单（按文件行号）", ""]
    if result["todos"]:
        lines += ["| 文件 | 行 | 待填内容 |", "|---|---|---|"]
        for item in result["todos"][:200]:
            lines.append(f"| `{item['file']}` | {item['line']} | {item['text'][:60]} |")
        if result["todo_count"] > 200:
            lines.append(f"| … | … | 另有 {result['todo_count'] - 200} 处 |")
    else:
        lines.append("无")
    return "\n".join(lines) + "\n"


def archive(project: Path, out_dir: Path | None = None, name: str | None = None) -> dict:
    project = Path(project).resolve()
    out = Path(out_dir) if out_dir else project / "dist"
    out.mkdir(parents=True, exist_ok=True)
    stamp = now_iso()[:10].replace("-", "")
    zip_path = out / (name or f"{project.name}_{stamp}.zip")

    files: list[Path] = []
    for path in sorted(project.rglob("*")):
        if path.is_dir() or path.is_symlink():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name.endswith(".synctex.gz") or path.suffix in SKIP_SUFFIXES:
            continue
        if out in path.parents:
            continue
        files.append(path)

    manifest: list[dict] = []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in files:
            rel = path.relative_to(project).as_posix()
            zf.write(path, rel)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest.append({"path": rel, "bytes": path.stat().st_size, "sha256": digest})

    manifest_path = out / (zip_path.stem + "_manifest.json")
    write_json(manifest_path, {
        "generated_at": now_iso(),
        "source": str(project),
        "archive": str(zip_path),
        "file_count": len(manifest),
        "total_bytes": sum(item["bytes"] for item in manifest),
        "files": manifest,
    })
    write_text(out / (zip_path.stem + "_MANIFEST.md"),
               "# 归档清单\n\n" + f"- 源工程: `{project}`\n- 归档文件: `{zip_path.name}`\n"
               f"- 文件数: {len(manifest)}\n- 总大小: {sum(i['bytes'] for i in manifest) / 1024 / 1024:.2f} MB\n\n"
               + "| 文件 | 字节 | sha256(前16) |\n|---|---|---|\n"
               + "\n".join(f"| `{i['path']}` | {i['bytes']} | `{i['sha256'][:16]}` |" for i in manifest))
    return {
        "status": "PASS",
        "archive": str(zip_path),
        "manifest": str(manifest_path),
        "file_count": len(manifest),
        "bytes": sum(item["bytes"] for item in manifest),
        "zip_bytes": zip_path.stat().st_size,
    }
