# Zero-Hallucination Academic Agent Workflow (不可造假的学术科研 Agent 工作流平台)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![LaTeX Engine](https://img.shields.io/badge/LaTeX-XeLaTeX-green.svg)](https://miktex.org/)
[![DoD Quality Gates](https://img.shields.io/badge/DoD%20Gates-Gate%201~4%20PASS-success.svg)](#四道质量门禁体系-dod-enforcement)
[![Quality Gates CI](https://github.com/2456018331lby-dev/zero-hallucination-academic-agent/actions/workflows/quality-gates.yml/badge.svg)](https://github.com/2456018331lby-dev/zero-hallucination-academic-agent/actions/workflows/quality-gates.yml)

本项目是一个**机制上杜绝学术造假、零幻觉（Zero-Hallucination）且具备端到端落地能力**的 AI 科研协作工作流底座。通过在工具层与门禁层设立硬约束，彻底解决大模型在科研协助中“引文凭记忆脑补、量化数据无据捏造、人工复核流于橡皮图章”等系统性缺陷。

**30 秒上手**（装一次，之后任何目录都能用）：

```bash
pip install -e . && zhaw doctor && zhaw selftest
```

`zhaw doctor` 打印环境体检（Python / PyMuPDF / XeLaTeX / 7 个门禁脚本）；
`zhaw selftest` 用 17 个"故意造假"的用例证明门禁真的会拦（零网络，约 0.4 秒）。

**这套东西现在到底能做到什么程度？** 见 [`CAPABILITY_REPORT.md`](CAPABILITY_REPORT.md)：
29 个子命令逐个实测、17/17 对抗用例、三个真实工程门禁全过、接地门禁 0 FAIL、盲审副本可独立编译（13 处泄露全清、产物默认排除）。

**你是 AI Agent、要接手这个仓库？** 直接读 [`AGENTS.md`](AGENTS.md)——那是给机器看的说明书：
仓库地图（哪些能改哪些别碰）、29 个命令按场景速查、四个任务剧本、以及**绝对不能做的六件事**。

---

## 一、三大工作流目录全解（哪个才能帮你做组会和写论文？）

在本项目中包含 3 个以 `*_workflow` 命名的工程目录。它们的演进历程与分工如下：

```
pidemo/
├── .agents/skills/           # 核心基础设施：四大防伪技能与自动化对抗回归自检套件
├── bupt_isac_workflow/       # ★【当前主力生产工程】北邮通信硕士新课题“双交付”（组会 PPT + 毕业论文）
├── ris_thesis_workflow/      # 【历史演练与终审夹具】面向 6G 的 RIS 辅助通信全流程 E2E 对抗实战
└── pku_thesis_workflow/      # 【初号机与整改基准夹具】Deep JSCC 课题，包含平台历史总结 PROJECT_SUMMARY.md
```

### 1. `bupt_isac_workflow/` —— ★ 真正完成你目标的主力双交付工程
* **课题设定**：北京邮电大学 信息与通信工程学院 电子信息专业（专业代码：`085402 通信工程`）硕士研究生课题——**《面向低空智联网的无人机通感一体化（ISAC）波形设计与感知辅助通信资源管理》**；
* **真正帮你做组会（交付 B）**：
  * 源码位于 `survey/seminar_presentation.tex`，编译成果为 `survey/seminar_presentation.pdf`（14 页 16:9 宽屏 Beamer 幻灯片）；
  * 每张技术幻灯片均包含**本地真实物理文献证据链页脚**，并内置了完整的 `\note{}` **逐字演讲稿**；
* **真正帮你写论文（交付 A）**：
  * 源码位于 `thesis_project/`，生成符合 GB/T 7713.1-2006 标准的学位论文 `thesis_project/main.pdf`（**72 页，759.5 KB，0 LaTeX 错误，0 严重溢出，0 未定义引用**）；
  * **正文 30,038 汉字，0 处 `\TODO{}`**，五章正文 + 附录 CRB 推导全部写完；
  * 第 4 章的数字全部来自 `thesis_project/experiments/*.csv`（8 个 CSV，由 `sim_bupt.py` 产出）与 7 张图（`make_bupt_figures.py`）；
* **文献与数据闭环**：
  * 实际下载 **11 篇开源物理 OA PDF** 至 `literature/`；
  * 15+1 维对比矩阵经 PyMuPDF 真实物理页码核验达成 **0 FAIL, 0 WARN**；
  * 论文 **62 条参考文献**（手写 `thebibliography`）经 Crossref 官方 REST API 逐字段核验，**FAIL=0**；作者字段按 GB/T 7714 格式 `SURNAME I N` 回填；
  * 完整保留从自检到编译的 **7 大原始无润色终端执行日志**（`logs/00_selftest.log` 至 `06_compile.log`）。
* **当前真实成色（诚实标注，不吹）**：
  * 四门禁：Gate 1 PASS（62/62）、Gate 2 PASS（数字逐格命中 CSV）、Gate 3 PASS（0 ERROR / 0 WARNING）、Gate 4 **FAIL（未签署，设计如此）**；
  * `zhaw audit` = **82.5 / 100**，扣掉的 17.5 分全部落在「真人签字」这一项上；
  * 仿真模型为「ZF + 匹配感知波束 + 一维闭式功率分配 + MMSE 不动点」的可实现方案，**未实现 SDR 基准**（cvxpy 未安装，且开销高三个数量级），正文已如实声明，没有编造 SDR 对比数字；
  * Gate 4 送审前必须由真人在终端执行 `zhaw gate4 bupt_isac_workflow/thesis_project --confirm-review --reviewer <你的名字>`；
  * 组会 PPT 14 页（目标 15–20 页）。

### 2. `ris_thesis_workflow/` —— 第二套真实工程（换课题复现的验收证据）
* **课题设定**：面向 6G 的 RIS（可重构智能表面）辅助多用户 MISO 联合波束赋形与级联信道估计；
* **定位与价值**：为了向第三方审计方证明「平台换一套全新课题，机制上不可能再造假」，从零搭建的第二个真实工程（不是空壳夹具）——它跑通的是同一套门禁，但课题、仿真、正文、文献全部另起一套；
* **实测成色**：正文 **30,322 汉字 / 0 处 `\TODO{}`**；`main.pdf` **73 页 / 755.9 KB / 0 错误 / 0 严重溢出 / 0 未定义引用**；**81 条参考文献**；`experiments/` 8 个 CSV（`sim_ris.py`）+ 6 张图（`make_ris_figures.py`）；四门禁 Gate 1/2/3 PASS + Gate 4 FAIL（未签）；`zhaw audit` = **82.5 / 100**；
* **刻意保留的负结果**：OMP 压缩感知在该级联信道模型下**失效**（−0.25/−0.14/−0.76/−0.42 dB），根因是 `g = diag(h_r^H) G w_p` 的逐元素 rank-1 调制使 DFT 域不稀疏——正文如实报告并给出理论解释，而不是删掉这个实验。

### 3. `pku_thesis_workflow/` —— 初号机与**门禁回归夹具**（不要「修好」它）
* **课题设定**：面向高速时变信道的轻量化自适应信源信道联合语义通信机制研究（Deep JSCC）；
* **定位与价值**：平台最初的试验田与问题暴露地。它**故意保留**了编造的量化结论、缺失的 `experiments/`、22 处 `\TODO{}`、6 条文献、未签署的 Gate 4、接地矩阵缺字段——这些不是「没做完」，是用来证明四道门禁抓得住问题的**活体样本**；
* **`zhaw audit` = 24.4 / 100，低分是预期结果**：`pku_thesis_project/FIXTURE.md` 显式声明它是夹具，`audit` 读到就在报告顶部打 `> [!IMPORTANT]` 警告并说明「不要为了提分去填造数据」；

---

## 二、平台核心防伪架构（四大底层技能）

平台核心资产位于 `.agents/skills/`，为跨平台（Gemini / Codex / Claude Code）单一事实源：

1. **`citation-auditor`（学术引文官方取证门禁）**：
   * 直连 Crossref 官方 REST API，逐字段比对标题、作者全量序列、年份、卷期页码与 DOI；
   * 严禁大模型凭参数记忆撰写 author 字段，作者张冠李戴或查无此文献一律判 **FAIL**。
2. **`phd-literature-survey`（博士级文献精读与物理溯源门禁）**：
   * 生成 15+1 维精读对比矩阵，第 16 维强制要求 `evidence` 必须指向本地真实 PDF 文件名与实际页码；
   * 调用 PyMuPDF (fitz) 打开本地 PDF，核验页码真实性并提取正文做关键词存在性验证，杜绝假出处。
3. **`math-reviewer`（数学符号契约与形式化推导审查）**：
   * 依托 `notation_table.md` 单源契约，审查公式符号定义一致性；
   * 审查定理陈述与证明强度匹配（杜绝在未证明超鞅的前提下妄称“以概率 1 收敛”）。
4. **`thesis-latex-writer`（国标学位论文与四道质量门禁体系）**：
   * 严格遵循 GB/T 7713.1-2006（学位论文编写规则）与 GB/T 7714-2015（文后参考文献著录规则）；
   * 支持“半成品脚手架模式”（预置三线表与待填占位符，数据未经验证严禁入正文）与单源 Word 导出；
   * 编排调度四道质量门禁（DoD Enforcement）。

---

## 三、四道质量门禁体系 (DoD Enforcement)

在学位论文编译送审前，必须全量通过 `run_quality_gates.py` 调度执行的四道质量门禁：

```
       [待审论文源码工程]
               │
               ▼
   ┌───────────────────────┐
   │ Gate 1: 引文官方取证门禁 │ ──(Crossref API 校验作者/标题/卷期页)──► FAIL=0 拦截假引文
   └───────────────────────┘
               │ PASS
               ▼
   ┌───────────────────────┐
   │ Gate 2: 数据溯源与证据链 │ ──(校验断言是否具备真实 CSV 支撑)───► 拦截无据量化宣称
   └───────────────────────┘
               │ PASS
               ▼
   ┌───────────────────────┐
   │ Gate 3: 国标学术合规门禁 │ ──(GB/T 7713 规范、三线表、反套话)───► 消除排版与 AI 套话
   └───────────────────────┘
               │ PASS
               ▼
   ┌───────────────────────┐
   │ Gate 4: 真实人工签字门禁 │ ──(绑定章节 SHA-256 哈希，拒占位符)──► 杜绝 AI 橡皮图章自签
   └───────────────────────┘
               │
               ▼
      [交付合格 PDF 与 Word]
```

---

## 四、快速开始与一键复现指南

### 1. 安装（一次性）
```bash
pip install -e .                    # 核心依赖只有 pymupdf
pip install -e ".[full]"            # 需要 Word 导出 / 画图时再加 python-docx / matplotlib / numpy
```

### 2. 环境自检
```bash
zhaw doctor                         # Python / PyMuPDF / XeLaTeX / 7 个门禁脚本是否就位
```

### 3. 门禁自身对抗回归（17 个用例，零网络）
```bash
zhaw selftest                       # 期望 17/17 PASS
```

### 4. 四道门禁（一条命令，或分开跑）
```bash
# 串跑 + 生成 gate_summary.json
zhaw check bupt_isac_workflow/thesis_project --scaffold --offline

# 分开跑
zhaw gate1 bupt_isac_workflow/thesis_project --offline      # 引文取证（DOI → Crossref 逐字段）
zhaw gate2 bupt_isac_workflow/thesis_project --scaffold     # 数据溯源（数字必须落进 CSV 单元格）
zhaw gate3 bupt_isac_workflow/thesis_project --scaffold     # 国标合规（GB/T 7713.1 + 7714-2015）
zhaw gate4 bupt_isac_workflow/thesis_project --scaffold     # 签字状态（送审时换 --confirm-review）
```

### 5. 文献页码物理取证
```bash
zhaw grounding bupt_isac_workflow/survey/literature_comparison_matrix.md \
  --pdf-dir bupt_isac_workflow/literature
```

### 6. 编译论文 / 组会 PPT
```bash
zhaw compile bupt_isac_workflow/thesis_project      # 严格模式：overfull > 5pt 或未定义引用即失败
cd bupt_isac_workflow/survey && xelatex -interaction=nonstopmode seminar_presentation.tex
```

### 7. 转 Word 审阅稿（带红条水印）
```bash
python .agents/skills/thesis-latex-writer/scripts/tex_to_docx.py \
  bupt_isac_workflow/thesis_project main.tex \
  --output bupt_isac_workflow/thesis_project/thesis.docx --scaffold
```

> 不想装 CLI？`zhaw xxx` 等价于 `py -3.12 -m zhaw xxx`，也等价于直接调用
> `.agents/skills/<技能>/scripts/<脚本>.py`。CI（`.github/workflows/quality-gates.yml`）会在
> Ubuntu / Windows / macOS × Python 3.12 上重跑同一套命令，任何一条红则 PR 红。

### 8. 研究生全生命周期（不止门禁）
```bash
zhaw new _demo/my_thesis --kind thesis --title "..." --author "..."   # 建工程（论文 / 开题）
zhaw proposal _demo/my_proposal --force --title "..."                  # 开题报告六章模板
zhaw proposal _demo/my_proposal --check                                # 开题配额与空话句式检查
zhaw figures _demo/my_thesis                                           # CSV → 矢量图 + 三线表 + includegraphics 片段
zhaw seminar  bupt_isac_workflow/survey/literature_comparison_matrix.md --compile   # 组会 Beamer
zhaw defense  _demo/my_thesis --compile                                # 答辩 PPT + 讲稿 + 13 问 Q&A
zhaw audit    _demo/my_thesis --offline --scaffold                     # 可交付度六维加权评分
zhaw progress bupt_isac_workflow/thesis_project                        # 字数进度 / 待填清单 / 分章配额
zhaw anonymize bupt_isac_workflow/thesis_project --out _demo/blind --force  # 盲审匿名化 + LEAKS.md
zhaw archive  bupt_isac_workflow/thesis_project --out-dir _demo/archives    # zip + SHA-256 manifest
zhaw math     bupt_isac_workflow/thesis_project                        # 符号契约 + sympy 恒等式验证
zhaw docx     bupt_isac_workflow/thesis_project                        # 转 Word（无 pandoc 自动降级）
```

### 8b. 从 0 写一篇论文的剧本层（`zhaw flow`）
零散命令解决「有没有这个能力」，`flow` 解决「**顺序是什么、哪一步不能跳**」。
11 个剧本覆盖读文献 → 组会 → 开题 → 写作 → 投稿 → 返修 → 答辩 → 盲审 → 中期 → 周报 → 归档：

```bash
zhaw flow                                   # 列出 11 个剧本（步骤数 / 其中必须人工几步）
zhaw flow show paper                        # 看某个剧本的逐步 SOP
zhaw flow run paper --project _demo/my_thesis --out _demo/flows   # 生成 runbook md
zhaw flow status paper --project _demo/my_thesis                  # 按产物是否存在算完成度 + 下一步
zhaw read  <PDF目录> --out _demo/read --digest                     # 批量读 PDF → 阅读卡/矩阵/gaps/综述草稿
zhaw submit   _demo/my_thesis --venue ieee-tvt --out _demo/submission   # 投稿前 11 项机检
zhaw review   _demo/my_thesis --venue ieee-tvt --out _demo/self_review  # 自审 MAJOR/MINOR
zhaw rebuttal <审稿意见.md> --out _demo/rebuttal                   # 按 Reviewer 切分 → 逐条回复骨架
zhaw midterm  _demo/my_thesis --out _demo/midterm                  # 中期检查报告
zhaw weekly   _demo/my_thesis --out _demo/weekly                   # 周报 + 快照
```

> `flow` 只给 SOP、清单和骨架，**绝不代写正文**；标 `[人工]` 的步骤永远不会被自动标完成。
> 完成度按「产物文件是否真实存在」计算，不按「AI 说完成了」计算。


### 9. 可选增强能力（装了就用，没装自动降级）
| 能力 | 依赖 | 行为 |
|---|---|---|
| IEEE / Nature 学术版式 | `scienceplots`（MIT） | 装了用 `plt.style.use(["science","ieee","no-latex"])`，没装用内置 rcParams |
| 数学恒等式机器验证 | `sympy`（BSD-3） | 装了 `sympify` 后 `simplify(lhs-rhs)==0`，没装打印 `SKIPPED` |
| 引用撤稿检测 | 无需额外依赖 | 走 Crossref `relation.is-retracted-by` / `update-to`，离线时跳过而不误报 |

```bash
pip install -e ".[full]"            # 一次装齐 scienceplots / sympy / python-docx / matplotlib
```

---

## 五、许可证 (License)

本项目采用 [MIT License](LICENSE) 开源协议。

> ⚠️ **依赖许可证提示**：本仓库**代码**是 MIT，但核心依赖 `pymupdf` / `pymupdf4llm` 是
> **AGPL-3.0 / Artifex 商业双许可**。若你要把本项目打包成对外分发的软件，AGPL 的义务会传导到你，
> 需要二选一：整体改用 AGPL-3.0 开源，或向 Artifex 购买商业许可。详见
> [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md)。仅自己科研使用（不分发）没有这个义务。

