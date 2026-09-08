---
name: thesis-latex-writer
description: >-
  学位论文与学术手稿 LaTeX 规范化起草助手。严格对齐国家标准 GB/T 7713.1-2006（学位论文编写规则）与 GB/T 7714-2015（参考文献著录）。
  支持“半成品脚手架模式”（尚未出实验结果时预置可编译的三线表与待填占位符）与“真实数据注入模式”（自动化将 CSV 实验日志转换为加粗三线表与学术分析）。
  内置反 AIGC 查重（知网/万方/维普）去模型化重构协议，消除 AI 套话与假大空词汇。
metadata:
  version: "1.0.0"
  domain: academic-writing
  role: thesis-latex-architect
  scope: thesis-drafting, latex-typesetting, gbt7713-compliance, anti-aigc
  triggers: 写论文, 毕业论文, latex论文, 论文排版, 学位论文, thesis writing, latex paper
---

# 学位论文与学术手稿 LaTeX 助手 (Thesis LaTeX Writer)

面向本科生、硕士生与博士生毕业论文及学术期刊手稿的模块化 LaTeX 写作系统。
严格遵循中国学术规范与高校送审要求，杜绝学术捏造，提供扎实的脚手架与实验数据注入机制。

---

## 核心工作模式 (Dual Operating Modes)

### 模式 A：半成品脚手架模式 (Scaffold / Mock Mode)
**适用场景**：开题报告准备阶段、实验尚未跑完、代码仍在调试，但需要先拿出一份结构完备、格式严谨的初稿或开题文本。
- **产出内容**：
  1. 完整严谨的 **第一章（绪论）** 与 **第二章（国内外研究现状）**（直接承接前序调研文献）；
  2. **第三章（核心方法）** 的形式化数学建模、算法伪代码框架及模块划分；
  3. **第四章（实验分析）** 提供**预置的标准三线表与消融对比表格（含明确的预期数据范围与 `[TODO: 待填入真实测试数据]` 明确注释）**；
  4. 全套工程**立即可用 XeLaTeX 编译成无报错的 PDF 预览文档**，方便提交导师提前审阅章节脉络与技术路线！

---

### 模式 B：真实数据注入模式 (Real Data Integration Mode)
**适用场景**：您已经跑出了自己的实验结果、训练日志或保存了 CSV/Excel 数据表格。
- **执行流程**：
  1. 运行配套脚本：`scripts/inject_experiment_data.py your_results.csv --caption "..."`；
  2. 自动生成加粗最优值、带显著性标记的 LaTeX `booktabs` 三线表代码；
  3. 基于真实指标差异，自动匹配严谨、客观的学术分析论述（拒绝 AI 假大空夸赞，完全以数据变化为依据）。

---

### 模式 C：分块深写模式 (Hierarchical Block-by-Block Deep Writing Mode)
**适用场景**：突破大模型单次输出 token 限制，产出达到 50~70 页体量、具有工科博士/硕士严谨深度与密集公式的正式学位论文。
- **执行协议**：
  1. **第一步：确立全局数学记号契约 (`notation_table.md`)**：
     - 在动笔写任何章节前，必须首先生成全局统一的符号字典（如输入样本 $\bm{x}$、信道矩阵 $\bm{H}$、信噪比 $\gamma$、维数 $K$），严禁跨章节符号漂移。
  2. **第二步：树状大纲与字数配额分解**：
     - 将论文划分为 12~18 个小节逻辑块，为每个块分配 2000~3000 字专属配额及必备要素（如“3.2 节：包含 1 个系统框图、3 个连续公式、1 个参数表与李雅普诺夫稳定性证明”）。
  3. **第三步：逐块深写与公式推导**：
     - 每次独立调用只深写当前小节，完整展开张量维度映射、算法伪代码及机理剖析。
  4. **第四步：模块化组装与合规机检**：
     - 通过母体 `main.tex` 的 `\input{chapters/...}` 实现自动化拼装；
     - 运行 `scripts/check_thesis_compliance.py` 自动扫描是否存在国标排版违规或 AI 套话；
     - 运行 `scripts/compile_thesis.py` 完成双遍 XeLaTeX 编译。

---

## 环境前置条件

运行本技能工具链（门禁编排、Word 转换、数据作图与合规检查）前，请确保安装依赖：

```bash
pip install -r requirements.txt
```

## 自动化科研工具链与脚本库 (Automated Toolchain)

- **四道质量门禁编排器 (Quality Gates Orchestrator)**：
  `scripts/run_quality_gates.py [工程路径] [--scaffold] [--offline] [--strict]`
  - 严格串联执行四道质量门禁：Gate 1 引文门 $\to$ Gate 2 溯源门 $\to$ Gate 3 合规门 $\to$ Gate 4 人工门。任一门禁失败立即阻断送审版编译与 Word 导出。
- **一键双遍 XeLaTeX 编译**：
  `scripts/compile_thesis.py [工程路径] [主入口.tex]`
  - 自动检测 Windows PATH 及标准 MiKTeX / TeX Live 路径，静默双遍编译解决目录与交叉引用，编译后自动解析日志汇总溢出与未定义引用。
- **国标 Word (.docx) 单源转换流水线**：
  `scripts/tex_to_docx.py [工程路径] [--output out.docx] [--scaffold]`
  - 优先通过 Pandoc 实现 LaTeX AST 单源精准转换为 Word，若未安装 Pandoc 则优雅降级至 `scripts/export_to_word.py`；
  - 严格对齐 GB/T 7713.1-2006：小四号宋体正文、1.35 倍行距、首行缩进两字、动态三线表渲染；脚手架模式强制附加红字警示横幅。
- **国标学术合规性自动机检**：
  `scripts/check_thesis_compliance.py [工程路径] [--scaffold] [--strict]`
  - 覆盖 Markdown 残留、三线表竖线、图表标题位置、前后件完整性、资源存在性、占位符泄漏等 9 大合规审查。
- **学术级矢量图自动绘制**：
  `scripts/plot_academic_curves.py --csv <data.csv> --x <col> --y <cols> --output-pdf <out.pdf>`
  - 基于 Matplotlib 与输入 CSV 生成符合 IEEE / 国标规范的学术矢量性能曲线（无内置假数据）。
- **实验数据三线表注入工具**：
  `scripts/inject_experiment_data.py your_results.csv --caption "..." --meta your_results.csv.meta.json`
  - 将真实仿真 CSV 数据自动转换为列级最优值加粗的 LaTeX booktabs 三线表，杜绝编造表注。

---

## 质量控制与四道门机制 (Four Quality Gates DoD)

送审前必须全量通过四道门禁（由 `scripts/run_quality_gates.py` 严格编排）：

1. **Gate 1 引文门 (Citation Verification Gate)**：
   - 必须通过 `citation-auditor` 的 Crossref 逐字段核验（作者姓、名缩写、年份、卷期页、DOI）；
   - 严禁大模型凭参数记忆撰写 author 字段，杜绝张冠李戴与虚构文献。
2. **Gate 2 溯源门 (Data Provenance Gate)**：
   - 正文所有核心量化断言与图表必须在 `experiments/` 目录下拥有可重现的真实 CSV 数据文件与伴生 `.meta.json`；
   - 未跑完实验时必须显式标注 `\TODO{}` 占位并启用 `--scaffold` 模式，严禁伪造数字进入结论。
3. **Gate 3 合规门 (Academic Compliance Gate)**：
   - 必须通过 `check_thesis_compliance.py` 扫描：零 Markdown 语法泄漏、图表标题次序符合国标、图表环境齐全、前后件完整。
4. **Gate 4 人工门 (Human Review Gate)**：
   - **密码学哈希防篡改绑定**：定稿送审前必须由真实人类作者在终端执行逐章复核签名。签名记录于 `.human_review.json`，强制记录所有确认章节的 SHA-256 哈希值；门禁每次运行实时重算哈希，签署后若任一章节文件被修改，对应签名立即自动失效（报 NOTICE/FAIL）；
   - **自动拒绝占位签名**：复核人字段匹配占位符模式（如 `研究生|导师复核组|TBD|XXX|TODO|placeholder|none|unknown|待定` 等）或日期为空时判定无效；
   - **终端交互签名工具**：`python scripts/run_quality_gates.py <工程路径> --confirm-review --reviewer <真实姓名>`；
   - **【AI 自主执行铁律禁令】**：AI 助手**严禁自主调用** `--confirm-review` 参数代签或伪造人工签名！该命令仅限真实人类作者/导师在终端手工交互确认。任何未经真实人类交互由 AI 自动写入的批准签名一律视为违规伪造。

### 模式 A 脚手架水印铁律
当工程处于“模式 A（半成品脚手架）”时，生成的 PDF 页眉与 Word 首页必须强制带有 **“SCAFFOLD DRAFT —— 本文含未验证脚手架数据，严禁外发或提交送审”** 显著警示，禁止直接用于任何开题或答辩外发。

---

> **四副本同步铁律**：本技能为多平台工作流资产。平台开发者在 `.agents/skills/` 对本技能源码或文档做任何改动后，必须运行 `python .agents/skills/sync_skills.py` 保持 Gemini/Codex/Claude 三大全局镜像区完全一致。


