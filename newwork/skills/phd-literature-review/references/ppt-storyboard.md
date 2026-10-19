# PPT storyboard — 15-page academic 组会汇报

Built with the **tencent-pptx** skill (slidep CLI). Write a `STORY.md` first
(one-paragraph claim + page table), then author slides one at a time.

## Style preset — academic blue/white

| token | value |
|---|---|
| page | 1280 × 720 |
| deep blue (title bars, cover) | `#0E3F8C` |
| primary blue | `#1E4FA8` |
| accent blue (rules, arrows, PART labels) | `#3D7BD9` |
| body text | `#1A2230` / `#4A5568` |
| muted | `#8B97A8` |
| panel background | `#F7F9FC`, border `#D6DCE5` |
| dark-bg body text | `#A8C2E8` / `#E6EEFA` |
| highlight / gold (on dark pages) | `#FFC24B` |
| font | `'Source Han Sans SC','Microsoft YaHei',sans-serif` |
| Chinese names | NOT italic, NOT underlined |

Consistent furniture: a 30px title in the top bar of content pages, a right-side
小标签, and a footer `「方向名」· 文献调研` + `n / 15`.

## Page plan

| # | 页面 | 角色 | content | visual |
|---|---|---|---|---|
| 01 | 封面 | ceremony | CN+EN title, sub-direction, 文献基础, 汇报人/日期 | deep-blue top rule + big title |
| 02 | 目录 | nav | 3-act structure, 5 items | numbered strip |
| 03 | 篇章扉页 一 | ceremony | giant `01` · 为什么难 | huge numeral |
| 04 | 方向定位 | preface | ≥220 字 long-text: the real failure modes, spectrum economics, safety-intrinsic | bottom emphasis line |
| 05 | 三重矛盾 | 3 columns | 波形层/空间层/系统层, each with essence + representative refs | 3 cards + connectors |
| 06 | 篇章扉页 二 | ceremony | giant `02` · 文献格局 | huge numeral |
| 07 | 四阶段演进 | timeline | 4 nodes: 固定基站 → 机动协同 → 消除开销 → 多维并行 | 4-node chain |
| 08 | 五类方法 | keyword matrix | 波形调制 / 波束架构 / 资源轨迹 / 感知算法 / 安全数据 | 2×3 matrix |
| 09 | 代表文献 I | 2-column | two KPI papers, contrast + each paper's cost | KPI numbers |
| 10 | 代表文献 II | 2-column | two KPI papers | KPI numbers |
| 11 | 代表文献 III | 2-column | two KPI papers | KPI numbers |
| 12 | 篇章扉页 三 | ceremony | giant `03` · 还缺什么 | huge numeral |
| 13 | 对比总结 | 2-column VS | 已解决 N 项 vs 未解决 M 项 | VS 中轴 |
| 14 | 挑战与切入 | keyword matrix | 5 challenges → 5 PhD entry points (推荐高/中) | numbered matrix |
| 15 | 总结 | punchline | the core logic chain + closing quote | quote bar on dark bg |

Every KPI number on pages 09–11 must appear in the reading table with the same
value. If it isn't in a PDF, it does not go on a slide.

## slidep commands

```bash
NODE=<node.exe>
SLIDEP=<node>/node_modules/@tencent/slidep/dist

# one-time: create the deck
"$NODE" "$SLIDEP/index.js" create "<WORK>/deliverables/<NAME>/<NAME>.pptx"

# per page: validate THEN upsert
"$NODE" "$SLIDEP/slidep-validate.js" "slides/07.slide" \
  --project "C:/abs/path/to/<NAME>"          # absolute + forward slashes!
"$NODE" "$SLIDEP/index.js" upsert-dsl "<NAME>.pptx" --dsl-file slides/07.slide
# to OVERWRITE an existing page (0-based), add: --page-index 6
```

* Omit `--page-index` to **append** a new page; supply it to replace page N.
* Validate prints `{"success":true,"id":"07","status":"ready"}`.
* After re-ordering, re-check the footer page numbers.

## Layout budget

* Total height 720. Content band for a title-bar page = `720 − topbar − footer(40) − spacer(20)`.
* A title-bar content page: topbar 80 → content 580 → footer 40 → spacer 20.
* Card stacks: `n·h + (n−1)·gap ≤ 580`. (e.g. 5 cards @88 + 4 gaps @10 = 480 + a 42 header + 52 footer note fits.)
* Prefer `justifyContent:'center'` on full-bleed dark pages so short content
  doesn't cling to the top.
