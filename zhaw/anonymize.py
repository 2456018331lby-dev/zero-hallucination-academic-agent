"""`zhaw anonymize` — 送审盲审匿名化（泄露作者身份 = 直接挂，且不可返工）.

两个动作:

``scan(project)``
    只读扫描，返回所有可能泄露身份的**位置与行号**：作者/导师姓名、致谢章、
    攻读学位期间成果章、基金资助、\\thanks、邮箱、ORCID、学号。

``emit(project, out)``
    复制一份工程到 ``out``，在副本上做匿名化：
      1. ``\\author{...}`` → ``\\author{匿名}``，删除 ``\\thanks{...}``；
      2. 删除「致谢」章节整块；
      3. 删除「攻读学位期间研究成果」章节整块；
      4. 删除基金/资助/Acknowledgments 段落；
      5. 正文出现的作者姓名替换为「作者」；
      6. 输出 ``anonymize_report.json`` 与 ``LEAKS.md``。

注意：这是**机检 + 机械替换**，不能替代人眼通读。表格里的姓名、图片里的
水印、PDF 元数据（由 xelatex 写入的 ``\\author``）都必须人工再确认一遍。
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from ._util import now_iso, write_json, write_text

# 编译产物与缓存，复制时跳过
SKIP_DIRS = {"__pycache__", ".git", "_trash", "defense", "dist"}
SKIP_SUFFIXES = {
    ".aux", ".log", ".out", ".toc", ".lof", ".lot", ".bbl", ".blg",
    ".synctex.gz", ".fls", ".fdb_latexmk", ".nav", ".snm", ".vrb", ".bcf", ".run.xml",
}

# 由 .tex 编译/导出而来的二进制成品（PDF/DOCX/PPTX）——**必须排除**：
# 它们内嵌了真实姓名、学号与 PDF 元数据，复制进盲审版等于直接泄露。
# 判定规则：同目录下存在同名 .tex 才算构建产物；figures/*.pdf 没有同名 .tex，予以保留。
BUILD_PRODUCT_SUFFIXES = {".pdf", ".docx", ".pptx"}

# 章节级：整块删除。标题里常有 \quad/\qquad 撑字距，所以先把排版命令剥掉再匹配。
CHAPTER_TITLE_RE = re.compile(r"\\chapter\*?\{([^{}]*)\}")
TITLE_NOISE_RE = re.compile(r"\\(?:quad|qquad|,|;|:|!| )|~|\s+")
DROP_TITLE_KEYS = ("致谢", "作者简介")

FUND_PATTERNS = [
    re.compile(r"^.*(?:国家自然科学基金|国家重点研发|基金项目|资助项目|基金资助|项目编号).*$", re.MULTILINE),
    re.compile(r"^.*(?:Acknowledg(?:e)?ments?|funded by|grant (?:no|number)).*$", re.MULTILINE | re.IGNORECASE),
]

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
ORCID_RE = re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b")
THANKS_RE = re.compile(r"\\thanks\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}")
AUTHOR_RE = re.compile(r"\\author(?:\[[^\]]*\])?\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}")

# 封面表格行：`\textbf{姓\qquad 名}： & 李同学 \\`
COVER_ROW_RE = re.compile(r"^(?P<head>[^%&]*&)(?P<value>[^&\\]*?)\\\\$")
COVER_KEYS = [
    ("author", re.compile(r"姓\s*(?:\\qquad|\s)*名|作\s*者")),
    ("student_id", re.compile(r"学\s*(?:\\qquad|\s)*号")),
    ("advisor", re.compile(r"指\s*导\s*教\s*师|导\s*师")),
    ("institution", re.compile(r"学\s*校|校\s*名|学\s*院|单\s*位|University|College|Institute", re.I)),
]
COVER_FIX = {
    "author": ("匿名", "封面姓名 → 匿名"),
    "student_id": ("000000000", "封面学号 → 000000000"),
    "advisor": ("导师", "封面指导教师 → 导师"),
    "institution": ("—", "封面机构名 → —"),
}

# 机构标识：校名/学院名会印在**每一页页眉**或封面上，比姓名更隐蔽。
# 盲审版必须去掉，否则整本论文每一页都在自报家门。
INSTITUTION_RE = re.compile(
    r"[\u4e00-\u9fa5]{2,12}(?:大学|学院|研究院|研究所)"
    r"|BEIJING\s+UNIVERSITY[^}\\]*"
    r"|UNIVERSITY\s+OF\s+[A-Z ]{3,}"
    r"|\bBUPT\b",
    re.IGNORECASE,
)
# 页眉页脚：`\fancyhead[C]{北京邮电大学硕士学位论文：\leftmark}`
FANCYHEAD_RE = re.compile(
    r"\\(?:fancyhead|fancyfoot|lhead|chead|rhead)\s*(?:\[[^\]]*\])?\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"
)
# hypersetup 里的 PDF 元数据：`pdfauthor={北京邮电大学硕士研究生}`
PDFMETA_RE = re.compile(
    r"(pdf(?:author|subject|keywords|creator))\s*=\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}",
    re.IGNORECASE,
)
# 这些是**本工具自己的报告**，含绝对路径与真实学号，绝不能进提交目录
REPORT_NAMES = {
    "LEAKS.md", "anonymize_report.json", "audit_report.json", "audit_report.md",
    "gate_summary.json", "figures_report.json", "progress_report.json",
    "seminar_report.json", "defense_report.json", "proposal_report.json",
}
# Crossref 回填缓存：含检索关键词与作者机构，不是论文源文件
CACHE_NAMES = {".citation_cache.json"}
_ABS_PATH_RE = re.compile(r"[A-Za-z]:\\[^\s|]*")


def _redact(text: str) -> str:
    """报告里的绝对路径与长数字（学号/手机号）一律打码，防止「防泄露报告自己泄露」。"""
    text = _ABS_PATH_RE.sub("[路径已隐藏]", text)
    return re.sub(r"\d{6,}", lambda m: m.group(0)[:4] + "*" * (len(m.group(0)) - 4), text)


def _iter_tex(project: Path) -> list[Path]:
    out = []
    for path in sorted(project.rglob("*.tex")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        out.append(path)
    return out


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _author_names(project: Path) -> list[str]:
    main = project / "main.tex"
    names: list[str] = []
    if main.exists():
        text = _read(main)
        for match in AUTHOR_RE.finditer(text):
            raw = match.group(1)
            raw = re.sub(r"\\[a-zA-Z]+\s*", "", raw)
            for part in re.split(r"[\\;,，、]|and\b|\\\\", raw):
                clean = part.strip().strip("{}").strip()
                if clean and 1 < len(clean) < 30 and not clean.startswith("待填"):
                    names.append(clean)
        # 中文模板的封面常常是 tabular 而不是 \author{}
        for _, kind, value in _cover_fields(text):
            if kind == "author" and 1 < len(value) < 30:
                names.append(value)
    return list(dict.fromkeys(names))


def _cover_fields(text: str) -> list[tuple[int, str, str]]:
    """返回封面表格里的 ``(行号, kind, 值)``，kind ∈ author/student_id/advisor。"""
    out: list[tuple[int, str, str]] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("%"):
            continue
        match = COVER_ROW_RE.match(line)
        if not match:
            continue
        head = match.group("head")
        value = match.group("value").strip()
        if not value:
            continue
        for kind, key_re in COVER_KEYS:
            if key_re.search(head):
                out.append((idx, kind, value))
                break
    return out


def _chapter_title(line: str) -> str:
    """抽出章节标题并把 ``\\quad``/``\\qquad``/空白 剥掉，便于关键词匹配。"""
    match = CHAPTER_TITLE_RE.search(line)
    if not match:
        return ""
    return TITLE_NOISE_RE.sub("", match.group(1))


def _is_dropped_chapter(line: str) -> bool:
    title = _chapter_title(line)
    if not title:
        return False
    if any(key in title for key in DROP_TITLE_KEYS):
        return True
    if "攻读" in title and ("成果" in title or "发表" in title):
        return True
    return title.lower().startswith("acknowledg")


def _chapter_blocks(text: str) -> list[tuple[int, int]]:
    """返回需要整块删除的 (start, end) 行号区间。"""
    lines = text.splitlines(keepends=True)
    blocks: list[tuple[int, int]] = []
    for idx, line in enumerate(lines):
        if not _is_dropped_chapter(line):
            continue
        start = idx
        # 章节标题前常有一行 \addcontentsline，一起删掉，否则目录里留下孤儿条目
        while start > 0 and lines[start - 1].lstrip().startswith("\\addcontentsline"):
            start -= 1
        end = len(lines)
        for jdx in range(idx + 1, len(lines)):
            stripped = lines[jdx].lstrip()
            if stripped.startswith("\\chapter") or stripped.startswith("\\backmatter") \
                    or stripped.startswith("\\end{document}") or stripped.startswith("\\appendix"):
                end = jdx
                break
        blocks.append((start, end))
    return blocks


def scan(project: Path) -> dict:
    project = Path(project).resolve()
    leaks: list[dict] = []
    names = _author_names(project)

    for path in _iter_tex(project):
        rel = path.relative_to(project).as_posix()
        text = _read(path)
        lines = text.splitlines()

        for idx, line in enumerate(lines, start=1):
            is_comment = line.lstrip().startswith("%")
            if AUTHOR_RE.search(line) and "匿名" not in line:
                leaks.append({"file": rel, "line": idx, "kind": "author_field",
                              "detail": line.strip()[:120],
                              "fix": "\\author{匿名}（盲审版）"})
            if THANKS_RE.search(line):
                leaks.append({"file": rel, "line": idx, "kind": "thanks",
                              "detail": line.strip()[:120], "fix": "删除 \\thanks{}"})
            if not is_comment:
                for pattern in FUND_PATTERNS:
                    if pattern.search(line):
                        leaks.append({"file": rel, "line": idx, "kind": "funding",
                                      "detail": line.strip()[:120], "fix": "删除基金/资助声明"})
                        break
            if EMAIL_RE.search(line):
                leaks.append({"file": rel, "line": idx, "kind": "email",
                              "detail": EMAIL_RE.search(line).group(0), "fix": "删除或替换邮箱"})
            if ORCID_RE.search(line):
                leaks.append({"file": rel, "line": idx, "kind": "orcid",
                              "detail": ORCID_RE.search(line).group(0), "fix": "删除 ORCID"})
            if re.search(r"学\s*号", line) and re.search(r"\d{6,}", line):
                leaks.append({"file": rel, "line": idx, "kind": "student_id",
                              "detail": line.strip()[:120], "fix": "盲审版删除学号"})
            for name in names:
                if name in line and not AUTHOR_RE.search(line):
                    leaks.append({"file": rel, "line": idx, "kind": "author_name",
                                  "detail": name, "fix": "替换为「作者」"})
                    break

        # 封面表格字段（中文模板最常见：\textbf{姓\qquad 名}： & 李同学 \\）
        for idx, kind, value in _cover_fields(text):
            _, fix = COVER_FIX[kind]
            leaks.append({"file": rel, "line": idx, "kind": "cover_field",
                          "detail": f"{kind}: {value}", "fix": fix})

        # 页眉页脚里的校名：会印在每一页上，是最隐蔽的一类
        for idx, line in enumerate(lines, start=1):
            match = FANCYHEAD_RE.search(line)
            if match and INSTITUTION_RE.search(match.group(1)):
                leaks.append({"file": rel, "line": idx, "kind": "header_institution",
                              "detail": line.strip()[:120],
                              "fix": "页眉去校名，只留「硕士学位论文：\\leftmark」"})

        # PDF 元数据（hypersetup）：xelatex 会把它写进 PDF Info
        for idx, line in enumerate(lines, start=1):
            for match in PDFMETA_RE.finditer(line):
                if INSTITUTION_RE.search(match.group(2)):
                    leaks.append({"file": rel, "line": idx, "kind": "pdf_metadata",
                                  "detail": line.strip()[:120],
                                  "fix": f"{match.group(1)}={{匿名}}"})

        # 正文/封面里裸露的校名、学院名（工具不敢自动全删，列出来给人确认）
        for idx, line in enumerate(lines, start=1):
            if line.lstrip().startswith("%"):
                continue
            if FANCYHEAD_RE.search(line) or PDFMETA_RE.search(line):
                continue
            if COVER_ROW_RE.match(line.rstrip("\n")):
                continue  # 封面行已由 cover_field 覆盖
            found = INSTITUTION_RE.search(line)
            if found:
                leaks.append({"file": rel, "line": idx, "kind": "institution_text",
                              "detail": found.group(0), "fix": "人工确认：盲审版应删除校名/学院名"})

        for start, end in _chapter_blocks(text):
            leaks.append({"file": rel, "line": start + 1, "kind": "chapter_block",
                          "detail": lines[start].strip()[:120],
                          "fix": f"删除第 {start + 1}--{end} 行整块"})

    kinds = sorted({item["kind"] for item in leaks})
    # 注意语义：这里是「扫描结论」，不是「匿名化是否成功」。
    # 冷启动实测踩过坑：把扫描 status 当成结果 status，会让人误以为 emit 失败。
    # 真正的成败看 emit() 返回的 residual_after_emit。
    return {
        "scan": "CLEAN" if not leaks else "LEAKS_FOUND",
        "status": "PASS" if not leaks else "ATTENTION",
        "project": str(project),
        "author_names": names,
        "leak_count": len(leaks),
        "kinds": kinds,
        "leaks": leaks,
    }


def _rewrite_cover_line(line: str) -> str:
    """把封面表格行的值替换为匿名占位符，保留缩进与 ``\\\\`` 行尾。"""
    stripped = line.rstrip("\n")
    match = COVER_ROW_RE.match(stripped)
    if not match:
        return line
    head = match.group("head")
    for kind, key_re in COVER_KEYS:
        if key_re.search(head):
            new_value, _ = COVER_FIX[kind]
            rebuilt = f"{head} {new_value} \\\\"
            return rebuilt + ("\n" if line.endswith("\n") else "")
    return line


def _rewrite_header(match: re.Match) -> str:
    """页眉去校名，保留 ``\\leftmark`` 让章节标题仍然显示。"""
    prefix = match.group(0).split("{", 1)[0]
    inner = match.group(1)
    mark = "\\leftmark" if "\\leftmark" in inner else ""
    return f"{prefix}{{硕士学位论文：{mark}}}" if mark else f"{prefix}{{}}"


def _anonymize_text(text: str, names: list[str]) -> str:
    lines = text.splitlines(keepends=True)
    drop: set[int] = set()
    for start, end in _chapter_blocks(text):
        drop.update(range(start, end))
    kept = [
        _rewrite_cover_line(line)
        for idx, line in enumerate(lines)
        if idx not in drop
    ]
    body = "".join(kept)

    body = AUTHOR_RE.sub(r"\\author{匿名}", body)
    body = THANKS_RE.sub("", body)
    for pattern in FUND_PATTERNS:
        body = pattern.sub("", body)
    body = EMAIL_RE.sub("[邮箱已移除]", body)
    body = ORCID_RE.sub("[ORCID 已移除]", body)
    for name in names:
        if len(name) >= 2:
            body = body.replace(name, "作者")
    body = FANCYHEAD_RE.sub(_rewrite_header, body)
    body = PDFMETA_RE.sub(lambda m: f"{m.group(1)}={{匿名}}", body)
    body = INSTITUTION_RE.sub("某单位", body)
    return body


def _is_build_product(src: Path) -> bool:
    """DOCX/PPTX 一律是导出成品；PDF 仅当有同名 ``.tex`` 或名为 main/thesis 才算构建产物。

    冷启动实测教训：``thesis.docx`` 没有同名 ``thesis.tex``，旧规则（只认同名 .tex）
    把它原样复制进盲审目录，直接推翻「编译产物已全部排除」的声明。
    """
    suffix = src.suffix.lower()
    if suffix in {".docx", ".pptx"}:
        return True
    if suffix == ".pdf":
        return src.with_suffix(".tex").exists() or src.stem in {"main", "thesis"}
    return False


def _residual_leaks(out_dir: Path, names: list[str]) -> list[str]:
    """对**产物目录**再扫一遍：emit 之后仍残留的身份词（校名/姓名/机构）。

    这是一道自检闸门 —— 正常应返回空列表；非空说明替换逻辑有洞。
    """
    hits: list[str] = []
    for path in sorted(out_dir.rglob("*.tex")):
        rel = path.relative_to(out_dir).as_posix()
        for idx, line in enumerate(_read(path).splitlines(), start=1):
            if line.lstrip().startswith("%"):
                continue
            hit = next((n for n in names if n and len(n) >= 2 and n in line), None)
            if hit:
                hits.append(f"{rel}:{idx} 含姓名「{hit}」")
                continue
            found = INSTITUTION_RE.search(line)
            if found:
                hits.append(f"{rel}:{idx} 含机构名「{found.group(0)}」")
    return hits


def emit(project: Path, out: Path, force: bool = False) -> dict:
    project = Path(project).resolve()
    out = Path(out).resolve()
    if out.exists():
        if not force:
            raise SystemExit(f"[zhaw anonymize] output exists: {out} (use --force)")
        shutil.rmtree(out)

    result = scan(project)
    names = result["author_names"]
    out.mkdir(parents=True)

    copied = 0
    skipped_build = []
    for src in sorted(project.rglob("*")):
        if src.is_dir():
            continue
        if any(part in SKIP_DIRS for part in src.parts):
            continue
        if src.suffix in SKIP_SUFFIXES or src.name.endswith(".synctex.gz"):
            continue
        if src.name in REPORT_NAMES or src.name in CACHE_NAMES:
            continue
        if _is_build_product(src):
            skipped_build.append(str(src.relative_to(project)))
            continue
        if src.resolve() == out or out in src.resolve().parents:
            continue
        rel = src.relative_to(project)
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix == ".tex":
            write_text(dest, _anonymize_text(_read(src), names))
        else:
            shutil.copy2(src, dest)
        copied += 1

    residual = _residual_leaks(out, names)

    leaks_md = [f"# 匿名化报告：{project.name}", "", f"生成时间：{now_iso()}", "",
                f"- 检出泄露点：**{result['leak_count']}**",
                f"- 涉及类型：{', '.join(result['kinds']) or '无'}", "",
                "## 已自动处理", "",
                "1. `\\author{}` → `\\author{匿名}`；2. 删除 `\\thanks{}`；3. 删除致谢章；",
                "4. 删除攻读期间成果章；5. 删除基金声明；6. 姓名→「作者」；7. 邮箱/ORCID 打码；",
                "8. 页眉校名 → 「硕士学位论文：\\leftmark」；9. `pdfauthor` 等 PDF 元数据 → 匿名；",
                "10. 封面机构名 → 「—」；11. 正文校名/学院名 → 「某单位」。", "",
                "## 必须人工再确认（机器管不了）", "",
                "- **重新编译**：编译产物（PDF/DOCX/PPTX）已排除，盲审版必须重新编译后再提交",
                "- **⚠️ 编译会重新注入路径泄露**：在盲审目录跑 xelatex 会在 `main.log` 里写入",
                "  `C:\\Users\\<用户名>\\...` 八十余次。**提交前删掉 `main.log`/`*.aux`/`*.synctex.gz`**，",
                "  或只提交 `main.tex` + 章节 + 图 + `references.bib`。",
                "- **本报告 `LEAKS.md` 与 `*_report.json` 不进提交目录**（它们必须写出被删的校名/路径，",
                "  本身必然含身份词）",
                "- PDF 元数据里的作者名（xelatex 会写入 `\\author`）",
                "- 图片/截图中的姓名、单位、水印",
                "- 表格里的姓名列",
                "- 参考文献中的自引（`[作者等, 2025]` 这种一眼能认出的）",
                "- 正文叙述里的「我们实验室」「本课题组」等间接标识",
                "- 致谢之外的章节里出现的导师姓名", "",
                "## 已排除的编译产物（含真实姓名，禁止直接提交）", ""]
    if skipped_build:
        leaks_md += [f"- `{name}`" for name in skipped_build]
    else:
        leaks_md.append("无")
    leaks_md += ["", "## 产物自检（emit 后复扫，正常应为 0）", ""]
    if residual:
        leaks_md += [f"- ❌ {_redact(line)}" for line in residual]
    else:
        leaks_md.append("✅ 产物目录内未再检出姓名/校名/学院名")
    leaks_md += ["", "## 泄露点清单", ""]
    if result["leaks"]:
        leaks_md += ["| 文件 | 行 | 类型 | 内容 | 处理 |", "|---|---|---|---|---|"]
        for item in result["leaks"]:
            leaks_md.append(
                f"| `{item['file']}` | {item['line']} | {item['kind']} | "
                f"{_redact(item['detail']).replace('|', '\\|')[:80]} | {item['fix']} |"
            )
    else:
        leaks_md.append("无")
    # 报告写到提交目录**外面**：报告必须写出被删的校名/路径，本身必然含身份词。
    # 冷启动实测教训：报告留在 blind/ 里等于「防泄露报告自己泄露」。
    report_dir = out.parent
    leaks_md_path = report_dir / f"{out.name}_LEAKS.md"
    report_json_path = report_dir / f"{out.name}_anonymize_report.json"

    write_text(leaks_md_path, "\n".join(leaks_md) + "\n")

    report = {
        "generated_at": now_iso(),
        "source": str(project),
        "output": str(out),
        "files_copied": copied,
        "skipped_build_products": skipped_build,
        "leak_count": result["leak_count"],
        "kinds": result["kinds"],
        "author_names": names,
        "residual_after_emit": residual,
        "status": "PASS" if copied and not residual else "FAIL",
        "leaks_md": str(leaks_md_path),
        "report_json": str(report_json_path),
    }
    # 落盘版把绝对路径打码（报告可能被随手打包进提交目录，路径含用户名 = 身份）；
    # 返回值保留真实路径供 CLI 打印。
    write_json(report_json_path, {
        **report, "source": _redact(report["source"]), "output": _redact(report["output"]),
    })
    return report
