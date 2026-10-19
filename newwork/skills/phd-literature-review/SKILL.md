---
name: phd-literature-review
description: Turn a folder of LOCAL research PDFs into a complete PhD-level literature-review package in one pass — (1) a 15-field reading comparison table in Markdown + XLSX, (2) a 7-section direction survey report, (3) a 15-page academic group-meeting PPT. Every quantitative claim is traced back to a source PDF; anything the papers do not say is written as 「文献未说明」; paper metadata, results and conclusions are NEVER fabricated. Use when the user asks for 文献调研 / 文献阅读表格 / 方向调研报告 / 组会(开题)汇报 PPT / literature review / survey a research direction from local PDFs.
agent_created: true
---

# PhD Literature Review (local PDFs → table + report + PPT)

One repeatable pass that converts a directory of research papers into three
deliverables a PhD student can take to a group meeting / proposal defence.

**Core promise:** the output is *auditable*. Every number on the table, in the
report and on the slides must be traceable to a line in a local PDF. If the
papers don't state it, the deliverable says 「文献未说明」 — it is never filled
in from the model's prior knowledge.

---

## 0. Non-negotiable rules

1. **Local-only evidence.** All content comes from the PDFs the user supplied.
   Do not import facts from memory, the web, or other corpora.
2. **No fabrication.** Never invent titles, authors, venues, arXiv IDs, dataset
   names, parameters, or experimental numbers. If unsure → re-read the PDF.
3. **Explicit gaps.** Missing field → 「文献未说明」 (or "not stated" in EN).
4. **Screen before deep-reading.** If there are many PDFs, inventory **all** of
   them first, then select the **8–12** most relevant for close reading. Say
   which ones were dropped and why.
5. **Research tone, not popular science.** Audience = supervisor + same-field
   grad students. Use precise terminology; state limitations and costs.
6. **Never trust a pre-existing table in the repo.** Older comparison files are
   often wrong (wrong IDs, copied numbers). Extract from the PDFs yourself.

---

## 1. Workflow (do these in order)

### Step 1 — Inventory every PDF
List the source folder (`*.pdf`). For each: filename, page count, and the
first-page header (title / authors / venue). This is the "browse all" pass.

```bash
PY=<python with pypdf, or with PyMuPDF for the better engine>
$PY scripts/extract_pdfs.py --src "<LIT_DIR>" --out "<WORK>/_pdftext" \
    --libs "<WORK>/_libs" --engine auto
```
This writes one cleaned `.txt` per PDF (page-delimited with `<<<PAGE n>>>`)
and prints a page/char summary plus the first-page head. Read the heads, then
decide the shortlist.

`--engine` controls the extractor:
* `auto` (default) — uses `academic_extractor.py` when PyMuPDF is importable,
  otherwise falls back to `pypdf` and says so.
* `academic` — two-column de-interleaving (IEEE/ACM/Springer/arXiv), strips
  running headers/footers, repairs line-wrap hyphenation. **Use this for any
  two-column paper**: `pypdf` interleaves the columns and the resulting text is
  hard to deep-read and easy to misquote.
* `pypdf` — plain per-page extraction.

Do not change the `<<<PAGE n>>>` markers; the grounding gate uses them.

### Step 2 — Screen to 8–12 papers
Rank by relevance to the user's direction. Record the exclusion list and the
reason (off-topic / survey-only / paywalled / duplicate). Do not silently drop.

### Step 3 — Deep-read the shortlist
For each selected paper, read the extracted text and pull the 15 fields below.
Keep a scratch evidence file (paper → field → exact quote/page) so later
verification is cheap. Verify **every** arXiv ID, dataset name and number by
string-searching the extracted text.

### Step 4 — Build `literature_table.json`
One object per paper, 15 keys (see §2). Plus a `meta` block:
`direction`, `subtitle`, `source_note`, `rules`, `generated`.
This JSON is the single source of truth for both the Markdown and the XLSX.

### Step 5 — Render the table
```bash
$PY scripts/build_table.py --json "<WORK>/literature_table.json" --out-dir "<WORK>"
```
Emits `文献阅读对比表格.md` (overview + 3 thematic tables + per-paper 15-field
cards) and `文献阅读对比表格.xlsx` (15 columns, frozen header, wrapped cells).

### Step 6 — Run the grounding gate (HARD GATE — do this before writing prose)
```bash
$PY scripts/verify_grounding.py --table-json "<WORK>/literature_table.json" \
    --pdftext "<WORK>/_pdftext"
```
For every paper it locates the extracted `.txt` via the JSON `file` field and
fails if a title, an arXiv id / DOI, or **any** quantitative claim in `results`
or `setup` cannot be found in the paper's own text. Exit code 1 = gate failed.

**Do not proceed on a failure.** Either the number is wrong (fix it from the
PDF) or it is a genuine phantom (delete it). Never "fix" it by loosening the
gate. Optionally re-run it on `_pdftext` as a second, independent opinion when
you extracted with a different engine.

### Step 7 — Write the survey report
`方向调研报告.md`, 7 sections — see §3. Ground each claim in a paper `[n]`.

### Step 8 — Build the PPT
Follow `references/ppt-storyboard.md`: 15 pages, academic style. Use the
`tencent-pptx` (slidep) skill. Draft a `STORY.md` first (narrative + page
table), then write slides one at a time, validating each before upserting.

### Step 9 (optional) — Add entrance animations
Only if the user asks. Use the local `tencent-local-office-edit` editor SDK to
add effects, then post-process the `.pptx` timing with
`scripts/retime_animations.py` (the SDK cannot express "after previous" and
always emits click-triggered 1000 ms fades, so N effects = N clicks otherwise).
Animate only the visual anchors (cover, part dividers' giant numerals, KPI
numbers, summary) and leave dense body pages static. Full procedure +
XML pitfalls: `docs/05-ppt-animations.md` in the `newwork` workspace.

---

## 2. The 15 table fields (exact keys)

| key | 中文列 | content |
|---|---|---|
| `id` | 序号 | `[1]`, `[2]` … (reused as the citation tag everywhere) |
| `title` | 论文题目 | English title as printed |
| `authors` | 作者 | first author + et al., or full list |
| `year` | 年份 | publication year |
| `venue` | 会议/期刊 | journal/conference, or arXiv preprint + ID |
| `problem` | 研究问题 | the specific question the paper attacks |
| `method` | 核心方法 | the mechanism (waveform / architecture / algorithm) |
| `innovation` | 主要创新点 | what is genuinely new |
| `setup` | 数据集/实验设置 | datasets, scenario, key params, baselines |
| `results` | 关键实验结果 | numbers **from the paper**, with the metric |
| `pros` | 方法优点 | strengths |
| `cons` | 方法局限 | limits/costs — state them plainly |
| `relation` | 与本研究方向的关系 | role in the direction's timeline |
| `recommend` | 是否建议重点汇报 | 推荐 / 可选 / 仅作背景 |
| `why` | 推荐汇报理由 | one-line justification |

Keep the JSON keys exactly as above so `build_table.py` works unchanged.

---

## 3. The 7 report sections

1. **概述** — the direction in one paragraph: why it matters, scope, the tension.
2. **发展脉络** — 3–5 phases, each with the papers that define it.
3. **方法分类** — 3–5 mutually exclusive families; each: idea, reps, cost.
4. **代表性文献** — 5–8 papers, each critically dissected (not summarised).
5. **对比总结** — a "已解决 / 未解决" split (e.g. N solved vs M open).
6. **挑战与未来方向** — challenges → **concrete PhD entry points** (with a
   recommended/medium/cautious flag). This is what the supervisor wants.
7. **总结** — one paragraph on the core research logic; close on the crux.

---

## 4. Environment & tooling notes

* **PDF text, plain:** `pypdf` (always works, but interleaves two-column pages).
  Install isolated, never globally:
  `pip install --target <WORK>/_libs pypdf` then
  `sys.path.insert(0, "<WORK>/_libs")` (or pass `--libs`).
* **PDF text, two-column:** `pymupdf` (PyMuPDF) powers `academic_extractor.py`:
  `pip install --target <WORK>/_libs pymupdf`. Import it as `pymupdf` — the old
  `fitz` module name is deprecated. Both scripts accept `--libs`.
* **XLSX:** `openpyxl`, same isolation pattern.
* **PPT:** the `tencent-pptx` skill. `slidep` CLI lives under the node install
  (`<node>/node_modules/@tencent/slidep/dist/`). See references/ppt-storyboard.md.
* Working dir convention: keep everything under one `<WORK>` folder with
  `literature/`, `_pdftext/`, `_libs/`, and `deliverables/`.

---

## 5. Pitfalls (learned the hard way)

* **A repo may already contain `literature_comparison_matrix.md` with wrong
  data.** Ignore it; rebuild from PDFs.
* `slidep-validate` / `slidep upsert-dsl` need an **absolute, forward-slash**
  `--project` path, otherwise you get a bogus `C:\c\Users\...`.
* Watch slide **vertical budget**: 720px total; the footer band is ~40px + a
  20px spacer. Content areas must fit or the page silently overflows.
* Keep the page-number footer in sync with the real index after re-ordering.
* If a "helpful-looking" table or digest exists but its numbers don't match the
  PDF, treat the PDF as truth and delete/redo the derivative.
* **The grounding gate is deliberately permissive about *spelling* and strict
  about *existence*.** Three false FAILs were hit and fixed while porting it;
  do not undo these normalisations or the gate becomes noise:
  * `6bit` vs `6-bit` — compare with hyphens stripped as well as kept.
  * `10000` vs `10, 000` — drop thousands separators between digits.
  * `0-100km` vs "between 0 and 100 km/h" — a range whose exact spelling is
    absent is retried as two endpoints inside a short window.
  What it still catches: an invented number, a wrong arXiv id, a title that
  belongs to a different PDF. It does **not** gate bare integers < 100 (too
  noisy to be meaningful) — those still need a human eye.
* `grep` may treat an extracted `.txt` as binary (stray bytes) and print
  nothing useful; use `grep -a`, or read with `errors="ignore"` in Python.
* Prefer the `academic` engine for two-column PDFs. Plain `pypdf` output looks
  plausible but interleaves the columns, which is exactly the condition that
  produces confidently wrong reading notes.

---

## 6. Related / overlapping skills

`phd-literature-survey` (in this user's `.agents/skills/`) solves the same
problem. **The merge decision was made: this skill is the trunk.** The two
capabilities worth keeping from that skill have been ported here:

| ported in | what | where it now lives |
|---|---|---|
| grounding gate | physical page-range + claim existence check | `scripts/verify_grounding.py` (table mode + the original matrix mode) |
| two-column cleanup | de-interleaving, header/footer stripping, hyphen repair | `scripts/academic_extractor.py`, wired in as `extract_pdfs.py --engine auto\|academic` |

That skill's **Marp** slide route stays there as an alternative output when the
user wants Markdown slides instead of a real `.pptx`; its
`scan_literature.py` / `citation-auditor` / `math-reviewer` / LaTeX assets were
never in scope here. Nothing under `.agents/skills/` was modified or deleted.

So: if both skills are installed, prefer **this one** for
「文献调研 / 组会汇报 / 开题」, and fall back to `phd-literature-survey` only for
Marp output. Full comparison: `newwork/docs/04-related-assets.md`.
