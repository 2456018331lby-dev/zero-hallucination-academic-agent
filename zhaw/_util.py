"""Shared helpers for the zhaw CLI modules.

Everything here is deliberately dependency-free (stdlib only) so that the
package can be imported on a bare Python install, including CI runners with no
LaTeX and no PyMuPDF.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# IO
# ---------------------------------------------------------------------------

def read_text(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")
    return p


def write_json(path: Path, data) -> Path:
    return write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def now_iso() -> str:
    return _dt.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def rel(path: Path, root: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(Path(root).resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


# ---------------------------------------------------------------------------
# LaTeX text utilities
# ---------------------------------------------------------------------------

_CMD_WITH_ARG = re.compile(r"\\(?:textbf|textit|emph|textrm|text|mathrm|mathbf|mathcal|bm|cite|ref|label|input|include|url|href)\s*\{[^{}]*\}")
_MATH = re.compile(r"\$[^$]*\$")
_COMMENT = re.compile(r"(?<!\\)%.*$", re.MULTILINE)
_HANZI = re.compile(r"[\u4e00-\u9fff]")


def strip_latex(text: str) -> str:
    """Best-effort plain-text projection of a LaTeX fragment."""
    t = _COMMENT.sub("", text)
    t = _MATH.sub(" ", t)
    t = _CMD_WITH_ARG.sub(" ", t)
    t = re.sub(r"\\[a-zA-Z@]+\*?", " ", t)
    t = t.replace("{", " ").replace("}", " ").replace("~", " ")
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()


def hanzi_count(text: str) -> int:
    return len(_HANZI.findall(text))


def todo_count(text: str) -> int:
    return len(re.findall(r"\\TODO\s*\{", text))


def count_refs(bib_path: Path) -> int:
    """Count BibTeX entries.

    Accepts either the ``.bib`` file itself or the project directory that holds
    ``references.bib`` — callers used to pass the directory and crashed with
    ``PermissionError: [Errno 13]`` when ``read_text`` tried to open a folder.
    """
    path = Path(bib_path)
    if path.is_dir():
        path = path / "references.bib"
    if not path.is_file():
        return 0
    return len(re.findall(r"^\s*@\w+\s*\{", read_text(path), re.MULTILINE))


# ---------------------------------------------------------------------------
# Thesis project introspection
# ---------------------------------------------------------------------------

CHAPTER_GLOBS = ("chapters/*.tex", "chapters/**/*.tex", "chap*.tex")


def chapter_files(project_dir: Path) -> list[Path]:
    project_dir = Path(project_dir)
    seen: dict[str, Path] = {}
    for pattern in CHAPTER_GLOBS:
        for p in sorted(project_dir.glob(pattern)):
            if p.is_file() and p.name not in {"references.tex"}:
                seen[str(p.resolve())] = p
    return sorted(seen.values())


def thesis_metrics(project_dir: Path) -> dict:
    """Measured, reproducible numbers for a thesis project directory."""
    project_dir = Path(project_dir)
    chapters = chapter_files(project_dir)
    per_chapter = {}
    total_hanzi = 0
    total_todo = 0
    for ch in chapters:
        raw = read_text(ch)
        hz = hanzi_count(strip_latex(raw))
        td = todo_count(raw)
        per_chapter[rel(ch, project_dir)] = {"hanzi": hz, "todo": td}
        total_hanzi += hz
        total_todo += td
    return {
        "chapters": len(chapters),
        "per_chapter": per_chapter,
        "hanzi_total": total_hanzi,
        "todo_total": total_todo,
        "refs": count_refs(project_dir / "references.bib"),
        "has_experiments_csv": any((project_dir / "experiments").glob("*.csv"))
        if (project_dir / "experiments").is_dir()
        else False,
        "figures": len(list((project_dir / "figures").glob("*.pdf")))
        if (project_dir / "figures").is_dir()
        else 0,
    }


# ---------------------------------------------------------------------------
# Literature comparison matrix parsing
# ---------------------------------------------------------------------------

def _split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def parse_matrix(md_path: Path) -> dict:
    """Parse the 15+1 column literature comparison matrix into a dict.

    Returns {"title": str, "intro": str, "columns": [...], "rows": [{...}]}.
    Unknown extra columns are preserved under their header name.
    """
    text = read_text(md_path)
    lines = text.splitlines()
    title = ""
    intro_parts: list[str] = []
    table_lines: list[str] = []
    in_table = False
    for line in lines:
        s = line.strip()
        if s.startswith("#") and not title:
            title = s.lstrip("#").strip()
            continue
        if s.startswith("|"):
            in_table = True
            table_lines.append(s)
            continue
        if in_table:
            break
        if s and not s.startswith("!"):
            intro_parts.append(s)
    if not table_lines:
        raise ValueError(f"no markdown table found in {md_path}")
    header = _split_row(table_lines[0])
    rows: list[dict] = []
    for line in table_lines[1:]:
        cells = _split_row(line)
        if not cells or all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        if len(cells) < len(header):
            cells += [""] * (len(header) - len(cells))
        rows.append(dict(zip(header, cells)))
    return {
        "title": title,
        "intro": "\n".join(intro_parts).strip(),
        "columns": header,
        "rows": rows,
    }


def col(row: dict, *candidates: str, default: str = "文献未说明") -> str:
    """Fetch the first present column among several aliases."""
    for name in candidates:
        for key, value in row.items():
            if name in key and value:
                return value
    return default


def cell_plain(value: str) -> str:
    """Make a matrix cell safe for LaTeX body text."""
    s = value.strip()
    s = s.replace("\\", "\\textbackslash{}")
    for ch in ("&", "%", "$", "#", "_", "{", "}"):
        s = s.replace(ch, "\\" + ch)
    s = s.replace("^", "\\^{}").replace("~", "\\~{}")
    s = s.replace("\\textbackslash{}", "\\textbackslash{}")
    return s
