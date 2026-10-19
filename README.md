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
`zhaw selftest` 用 9 个"故意造假"的用例证明门禁真的会拦（零网络，约 0.2 秒）。

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
  * 源码位于 `thesis_project/`，生成符合 GB/T 7713.1-2006 标准的学位论文 `thesis_project/main.pdf`（32 页，375.4 KB，0 LaTeX 错误，0 严重溢出，0 未定义引用）与单源 Word 转换成果 `thesis_project/thesis.docx`（带 `C00000` 红条水印）；
  * 包含单源数学符号契约 `notation_table.md`，第 4 章采用严格规范的纯脚手架模式（**0 虚构量化数据**）；
* **文献与数据闭环**：
  * 实际下载 **11 篇开源物理 OA PDF** 至 `literature/`；
  * 15+1 维对比矩阵经 PyMuPDF 真实物理页码核验达成 **0 FAIL, 0 WARN**；
  * 论文 16 篇参考文献（32 条记录）全部直连 Crossref 官方 REST API 权威元数据核验（**FAIL=0, OK=32**）；
  * 完整保留从自检到编译的 **7 大原始无润色终端执行日志**（`logs/00_selftest.log` 至 `06_compile.log`）。
* **当前真实成色（诚实标注，不吹）**：
  * 正文 **8,547 汉字**（硕士常规 3–5 万字）→ 约完成 20–25%；
  * 第 4 章有 **18 处 `\TODO{}`** 占位，`experiments/*.csv` 尚未产出，所以 Gate 2 目前只能证明"没有自由漂浮的数字"，还不能证明"数字是对的"；
  * Gate 4 **未签署**——`.human_review.json` 不存在是设计如此，送审前必须由真人在终端执行 `zhaw gate4 bupt_isac_workflow/thesis_project --confirm-review --reviewer <你的名字>`；
  * 组会 PPT 14 页（目标 15–20 页）。

### 2. `ris_thesis_workflow/` —— 终审验收与对抗防御夹具
* **课题设定**：面向 6G 的 RIS（可重构智能表面）辅助通信波束赋形与信道估计；
* **定位与价值**：为了向第三方审计方证明“平台换一套全新课题，机制上不可能再造假”，从零搭建的验收夹具。成功拦截了恶意假引文注入、虚假数据百分比注入以及 Gate 4 SHA-256 哈希篡改攻击；
* **与你目标的关系**：仅交付了论文脚手架，未做组会 Beamer 汇报，属于平台的防伪实证档案。

### 3. `pku_thesis_workflow/` —— 初号机与整改基准夹具
* **课题设定**：面向高速时变信道的轻量化自适应信源信道联合语义通信机制研究（Deep JSCC）；
* **定位与价值**：平台最初的试验田与问题暴露地。最初发现传统 AI 辅助科研存在引文虚构、数据脑补、橡皮图章等严重问题后，在此目录下完成了全部缺陷定性与最初的门禁脚本试验。其保留的 [`PROJECT_SUMMARY.md`](pku_thesis_workflow/PROJECT_SUMMARY.md) 记录了最完整的整改背景与平台技术路线演进。

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

### 3. 门禁自身对抗回归（9 个用例，零网络）
```bash
zhaw selftest                       # 期望 9/9 PASS
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

---

## 五、许可证 (License)

本项目采用 [MIT License](LICENSE) 开源协议。
