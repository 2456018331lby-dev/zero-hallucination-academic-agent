# 04 · 与既有资产的重复与差异（重要）

> **状态：方案 A 已执行完毕（2026-09-14）**。以 `phd-literature-review` 为主干，
> 把既有 `phd-literature-survey` 的 `verify_grounding.py` 与 `academic_extractor.py`
> 移植过来并增强。**`.agents/skills/` 下未修改或删除任何文件**。
> 执行细节见 **§三**。

本工作区**不是**从零开始。仓库里已存在一套成体系的博士科研技能族
（`…/pidemo/.agents/skills/`，建于 2026-09-06 ~ 09-10）。本文件如实记录
`newwork/skills/` 与它们的**重叠、差异与合并结果**，避免同一个人在两套东西之间来回切换。

## 一、既有技能族（`.agents/skills/`）

| 技能 | 职责 |
| :-- | :-- |
| `phd-literature-survey` | **与本工作区高度重叠**：15 维文献阅读对比表 + 7 章方向调研报告 + 组会/开题 PPT（**Marp** 格式） |
| `academic-paper-discovery` | 按主题检索顶会/顶刊（OpenAlex + arXiv），下载 OA 全文，产出文献池分流清单 |
| `citation-auditor` | 引文逐条审计门禁：DOI→CrossRef 回归比对，作者/卷期页错配一律 FAIL |
| `math-reviewer` | 数学严谨度与形式化推导复核（符号契约、定理与证明强度匹配） |
| `thesis-latex-writer` | 学位论文 LaTeX 起草（GB/T 7713.1-2006、GB/T 7714-2015） |
| `web-and-local-recon` | 多源信息采集与本地环境诊断 |
| `sync_skills.py` | 该技能族的同步脚本 |

## 二、重叠面：`phd-literature-survey` vs `phd-literature-review`

两者解决**同一个问题**，且遵守**同一套纪律**（零幻觉、「文献未说明」、8–12 篇精读筛选）。

| 维度 | `.agents/skills/phd-literature-survey`（既有） | `newwork/skills/phd-literature-review`（**合并后的主干**） |
| :-- | :-- | :-- |
| 三件套 | ✅ 表 + 报告 + PPT | ✅ 表 + 报告 + PPT |
| 表格格式 | Markdown 矩阵 | Markdown **+ XLSX**（openpyxl 渲染） |
| PPT 工具链 | **Marp**（Markdown → 幻灯片）——保留为备选输出 | **tencent-pptx / slidep**（→ 真 `.pptx`，可编辑） |
| PDF 抽取 | `academic_extractor.py`：双栏排版清洗 | ✅ **已移植**，接为 `extract_pdfs.py --engine auto\|academic`；缺失时回落 pypdf |
| 接地校验 | `verify_grounding.py`：物理页码门禁 | ✅ **已移植并增强**：保留物理页码模式，新增针对 `literature_table.json` 的**数字接地门禁** |
| 文献池入口 | `scan_literature.py` | ❌ 未移植（直接读目录已够用） |
| 子代理编排 | ❌ 无 | ✅ MiMo 主从编排（`scripts/orchestrate_mimo.py`） |

## 三、合并执行结果（方案 A 已落地）

**决策**：以 `phd-literature-review` 为主干，回填既有能力。**已执行**，`.agents/skills/`
下**没有修改或删除任何文件**（只读取后并入本工作区）。

### 3.1 `verify_grounding.py` → 已移植并增强

原脚本只支持「带 `evidence` 列的 Markdown 矩阵」。但本工作区的真值源是
`literature_table.json`（没有 evidence 列，而是每行直接给出 `results` / `setup` 这种更强的断言）。
所以移植时保留了**两种模式**：

| 模式 | 命令 | 作用 |
| :-- | :-- | :-- |
| **table（新，默认用法）** | `verify_grounding.py --table-json literature_table.json --pdftext _pdftext` | 逐篇核对：标题须在前两页可定位；`venue` 里的 arXiv 号/DOI 须在正文出现；`results`/`setup` 里**每一条定量断言**都必须能在该篇原文里找到 |
| **matrix（原样保留）** | `verify_grounding.py matrix.md --literature-dir literature` | PyMuPDF 物理页码校验：引用页码越界即 FAIL |

退出码 0 = 通过，1 = 不通过，可直接做流水线关卡。

**误报修复（移植时发现的真实缺陷）**——门禁必须对「拼写差异」宽容、对「事实是否存在」严格：

| 误报 | 原文真实写法 | 修正 |
| :-- | :-- | :-- |
| `6bit` 找不到 | `6-bit digital phase shifter` | 比较时同时用「去连字符」形式 |
| `10000` 找不到 | `10, 000 repeated experiments` | 归一化时去掉数字之间的千分位逗号 |
| `0–100km` 找不到 | `distributed between 0 and 100 km/h` | 范围 token 若整体匹配失败，改为在短窗口内校验两个端点 |

**反向验证**：注入 `实测增益提升 47.3 dB` 与假 arXiv 号 `9999.99999` → 两条都被 FAIL 拦下，
退出码 1；真实表格 → 11/11 通过（共核对 96 条定量断言），退出码 0。

### 3.2 `academic_extractor.py` → 已移植并接为可选前端

- 新增 `--libs`（与本工作区其它脚本一致的隔离依赖约定）；
- 页分隔标记统一为 `<<<PAGE n>>>`（接地门禁依赖此标记做分页定位）；
- 引擎优先级：`pymupdf4llm` → PyMuPDF 坐标分栏重建 → 报错让调用方回落 `pypdf`；
- `extract_pdfs.py` 新增 `--engine {auto,academic,pypdf}`，`auto` 在 PyMuPDF 可用时自动走双栏清洗。

**实测收益**：同一篇双栏论文，`pypdf` 抽出 `Multi-UA V`，双栏引擎修正为 `Multi-UAV`；
两套文本跑接地门禁均 11/11 通过（说明门禁不依赖具体引擎）。

### 3.3 保留在既有资产里的部分

`phd-literature-survey` 的 **Marp 路线**保留为「需要 .md 幻灯片时」的备选输出；
`academic-paper-discovery` / `citation-auditor` / `math-reviewer` / `thesis-latex-writer` /
`web-and-local-recon` 本次**不在合并范围内**，未做任何改动。

### 3.4 触发词边界（两套都装了怎么办）

以「文献调研 / 文献阅读表格 / 方向调研报告 / 组会(开题)汇报」为触发词时，
**优先用 `phd-literature-review`**；只有用户明确要 Markdown/Marp 幻灯片时才回落 `phd-literature-survey`。

## 四、不重叠的部分（本工作区的独有价值）

- `mimo-desktop-bridge` + `orchestrate_mimo.py`：**主从协作编排**，既有技能族完全没有。
- `build_table.py` → XLSX：可交付给导师直接看的表格。
- `slidep` → 真 `.pptx`：既有路线产的是 Marp 网页幻灯片，不是 Office 文件。
- 本工作区的**自包含打包**（docs + scripts + libs + examples），便于移植给其他 AI 接手。
