# 面向 6G 通信工程研究生学位论文与学术调研的全流程 AI Agent 工作流项目总结（v2 勘误与整改版）

> **致接力此项目的下一位 AI / 合作开发者**：  
> 本文档记录了本工程的**真实架构设计、工具链规范、测试夹具现状与质量门禁体系**。
> **特别提示（勘误声明）**：前期版本曾将 demo 产物宣传为“最终送审级/批注级”，该定性存在严重事实错误（盲审实测发现第四章数据整体编造、引文 6/6 存在事实性错误、正文残留 Markdown 标记、缺前后件与图表）。
> 本项目核心使命是**打造不可造假的科研工作流平台（Skill 层）**，`pku_thesis_workflow/` 仅为基准测试夹具。所有产物在送审前必须全量通过 **四道质量门禁 (Four Quality Gates DoD)**。

---

## 一、项目宏观定位与整改根基

### 1. 核心目标：构建杜绝学术造假的确定性科研底座
传统“大模型辅助科研”多依赖未经约束的自由生成，存在四大系统性毒性：
1. **引文凭记忆脑补**：模型凭参数记忆编造作者名、虚构卷期页甚至捏造不存在的 DOI（实测 demo 引文 6/6 有错，2 篇作者整列虚构，正文还杜撰了中文名）；
2. **数据无据编造**：无真实 GPU 日志时自动编造量化数据，假结论（如“2.6dB 增益/时延降 56%”）渗入摘要、绪论、结论与 Word 文档；
3. **工具承诺与实现脱节**：文档声称具备合规检查，实际未实现图表标题位置检查、静默丢弃 Markdown 表格、内置硬编码假曲线；
4. **多平台副本漂移**：技能分散在本地与全局多个目录，缺乏单一事实源与强制同步校验。

本项目确立最高原则：**平台层强制校验，新课题绝不可能再产出假数据与假引文**。

### 2. 基准实测依托的学科题目（测试夹具）
* **培养单位与专业**：北京大学 电子学院 / 信息科学技术学院，电子信息类（专业代码：`085402 通信工程`）
* **论文主攻方向**：面向高速时变信道的轻量化自适应信源信道联合语义通信机制研究（Deep JSCC for 6G）
* **核心机制设计**：
  * 基于物理信噪比驱动的微秒级动态神经门控通道剪枝（DCGU）；
  * 面向标准 QAM 星座图映射的离散可微分量化（DDQ）与直通估计器（STE）退火策略；
  * 基于 Robbins-Monro 条件的随机衰落信道收敛性证明框架。

---

## 二、运行环境与四副本同步拓扑 (Architecture & Sync Topology)

### 1. 本地基础环境
* **操作系统**：Windows 11 (pwsh / PowerShell)
* **TeX 发行版**：`MiKTeX 25.12 (x64)`，`initexmf --set-config-value [MPM]AutoInstall=1` 静默双遍自动化编译；
* **Python 工具链**：Python 3.12+（已装 `matplotlib`、`python-docx`、`numpy`）。

### 2. 四副本镜像同步拓扑
为了解决多 AI 客户端（Gemini / Codex / Claude Code）各自读取全局目录导致技能分叉的问题，确立以下拓扑：
* **唯一主副本（事实源）**：`c:\Users\24560\Desktop\study\pidemo\.agents\skills\`
* **全局镜像区 1**：`C:\Users\24560\.gemini\skills\`
* **全局镜像区 2**：`C:\Users\24560\.codex\skills\`
* **全局镜像区 3**：`C:\Users\24560\.claude\skills\`
* **同步工具**：[sync_skills.py](file:///c:/Users/24560/Desktop/study/pidemo/.agents/skills/sync_skills.py)
  * 执行单向镜像同步 + 差异比对（Diff）+ 同步后 0 差异完整性校验；
  * **铁律**：对 `.agents/skills/` 下任何代码或文档修改后，必须运行 `python .agents/skills/sync_skills.py`。

---

## 三、四大核心技能 (Skill) 与重构工具链

### 1. `citation-auditor`（学术引文逐条审计门禁）
* **脚本核心**：`scripts/check_citations.py`
* **审计能力**：
  * 以 DOI 为锚或根据标题检索，直连 Crossref 官方 REST API（带本地 `.citation_cache.json` 缓存与 0.3s 限速）；
  * 逐字段强核验：作者姓序列、名缩写首字母、论文标题相似度（阈值 0.85）、出版年份、卷号、期号、页码；
  * 发现作者张冠李戴、卷期页错配或查无此文献一律判定 **FAIL（退出码 1）**；
  * 严禁大模型凭参数记忆撰写 author 字段，所有引文字段必须来自权威 API 回填。

### 2. `thesis-latex-writer`（国标学位论文与质量门禁体系）
* **四道质量门编排器**：`scripts/run_quality_gates.py`（严格串联 Gate 1 引文门 $\to$ Gate 2 溯源门 $\to$ Gate 3 合规门 $\to$ Gate 4 人工门）：
  * **Gate 4 人工门硬化**：杜绝“橡皮图章”缺陷。引入 SHA-256 密码学哈希防篡改绑定（签署后任一章节被修改签名立即失效）；严格拒绝占位签名（如 `研究生|导师复核组|TBD|XXX|TODO|placeholder`）；严禁 AI 自主代签，仅限真实人类作者/导师在终端通过 `--confirm-review --reviewer <姓名>` 交互签署。
* **合规机检工具**：`scripts/check_thesis_compliance.py`（重构版，覆盖 9 大审查）：
  1. Markdown 语法残留（非注释行 `**`、`__`、`|---|`、```` ``` ````）；
  2. 三线表规范（禁用竖线 `|`，检查版心溢出）；
  3. 图表标题位置（表格标题在表上方，插图标题在图下方）；
  4. 资源物理存在性与图表总数检查（严禁全文零图，扫描 `figures/` 死文件）；
  5. 前后件清单校验（英文摘要/关键词、图表目录、符号表、致谢、声明、成果清单）；
  6. 参考文献规模与完整性（硕士默认 $\ge 60$ 篇，检查悬空 `\cite` 与未引用条目）；
  7. 占位符泄漏检测（`TODO`、`待填`、`占位`、`SCAFFOLD` 在非注释行一律报错，`--scaffold` 模式放行）；
  8. Anti-AIGC 套话过滤；
  9. 编译日志后处理（解析 `main.log` 中的 Error、Overfull \hbox > 5pt、未定义引用）。
* **真实数据注入工具**：`scripts/inject_experiment_data.py`
  * 真·列级最优值加粗（`--higher-better` / `--lower-better`），消除“含 Ours 整行加粗”；
  * 伴生元数据检测：从 CSV 伴生 `<csv>.meta.json` 提取硬件、重复次数与 seed，无元数据绝不伪造方法学表注；
  * 包含数据源 SHA256 溯源注释。
* **学术曲线绘制工具**：`scripts/plot_academic_curves.py`
  * 彻底删除内置假曲线，纯输入驱动（`--csv --x --y --series`）；
  * 生成 IEEE / GB 规范的高解析度矢量图（PDF/PNG）。
* **国标 Word 单源转换流水线**：`scripts/tex_to_docx.py`（降级至 `scripts/export_to_word.py`）
  * 优先使用 Pandoc 解析 LaTeX AST 单源精准转换为 Word，缺失 Pandoc 时无缝降级至原生 Python 解析引擎；
  * 修复 Markdown 调研表格静默丢弃问题，渲染原生 Word 三线表；
  * 消除 314 行手工复制粘贴死文本，基于 LaTeX 动态提取；
  * 脚手架模式强制附加首页醒目红字横幅：“【SCAFFOLD DRAFT —— 本文含未验证脚手架数据，严禁外发或提交送审】”。

### 3. `academic-paper-discovery`（两级文献发掘技能）
* **脚本核心**：`scripts/search_papers.py`
* **重构项**：补齐通信顶刊/顶会权重（JSAC, TWC, TSP, COMST, TIT, TMC, ICC, GLOBECOM，9~10 分）并外置 `venue_weights.json`；修复 BibTeX 生成（完整作者、真实卷期页、规范引用键）；修正文档命令行参数。

### 4. `phd-literature-survey`（学术深层调研技能）
* **脚本核心**：`scripts/verify_grounding.py` 与 `scripts/scan_literature.py`
* **重构项**：引入严苛依据校验，对比矩阵 15 维正式扩展第 16 维 `evidence`（对应本地 PDF 文件名与页码），每篇文献必须物理存在于 `./literature/`，否则判定 FAIL；
* **测试样本双轨说明**：
  * `survey/literature_comparison_matrix.md`：前期参数记忆无证据草稿样本（未提供第 16 维证据与本地 PDF），作为**负向测试用例 (Negative Test Fixture)** 供门禁机检验证（实测精准报出 6 FAIL, 4 WARN）；
  * `survey/literature_comparison_matrix_grounded.md`：严格基于本地 5 篇真实 OA PDF 提纯并填写的 16 维全证据对照矩阵，实测 `verify_grounding.py` **0 FAIL, 0 WARN (100% PASS)**。

---

## 四、当前测试夹具产物目录映射与真实状态

测试夹具目录：`c:\Users\24560\Desktop\study\pidemo\pku_thesis_workflow\`

```
pku_thesis_workflow/
├── PROJECT_SUMMARY.md                      # 本全景交接文档（v2 勘误与第三方审计整改版）
├── notation_table.md                       # 全局数学符号与变量统一契约表
├── export_to_word.py                       # 修复后的国标 Word 导出脚本
├── citation_audit_before.json              # 引文审计整改前基线（12 条文献全 FAIL，真实错误捕获）
│
├── literature_v2/                          # 两级文献漏斗检索池
│   ├── references_broad.bib                # 50 篇广度参考文献库
│   ├── literature_manifest.json            # 检索元数据全量结构化索引
│   ├── reading_plan.md                     # 12 篇核心文献精读分流计划
│   └── [01]~[11]_*.pdf                     # 下载的开源 OA 全文 PDF
│
├── survey/                                 # 调研与组会汇报支撑产物
│   ├── seminar_presentation.tex            # Beamer 组会汇报源码
│   ├── seminar_presentation.pdf            # 组会汇报幻灯片
│   ├── research_direction_survey_report.md # 7 大章节学术调研报告
│   ├── Research_Direction_Survey_Report.docx# 调研报告 Word 版（已支持三线表）
│   ├── literature_comparison_matrix.md     # 15 维文献对比矩阵（负向测试用例：未标注 evidence，供 verify_grounding.py 验证拦截能力）
│   └── literature_comparison_matrix_grounded.md # 16 维文献对比矩阵（正向基准：基于本地 5 篇 OA PDF 锚定，100% 通过门禁）
│
└── pku_thesis_project/                     # 学位论文测试夹具工程
    ├── main.tex                            # 论文母体入口
    ├── main.pdf                            # 编译输出 PDF（必须过四道门才可用于评审）
    ├── Peking_University_Thesis_085402.docx# 导出的 Word 文档（草稿强制带红字横幅）
    ├── gate_summary.json                   # 四道质量门禁执行记录
    ├── .human_review.json                  # 人工复核签署记录（密码学哈希绑定，demo 预置无效占位符以确保不发生自签造假）
    ├── figures/                            # 插图目录
    └── chapters/                           # 模块化章节
        ├── chap01_intro.tex                # 第一章 绪论
        ├── chap02_related_work.tex         # 第二章 国内外研究现状
        ├── chap03_methodology.tex          # 第三章 核心方法母体
        ├── chap03/                         # 第三章 4 大深写小节
        ├── chap04_experiments.tex          # 第四章 实验设置与定量验证
        ├── chap05_conclusion.tex           # 第五章 总结与展望
        └── references.bib                  # 权威回填修复后的参考文献数据库
```

---

## 五、操作指南与质量守则 (Standard Operating Procedures)

### 1. 绝对红线（严禁违背）
* **禁止凭记忆写引文**：新增任何参考文献必须经 `check_citations.py` 检索 DOI 与权威元数据回填；
* **禁止编造实验结论**：在未取得真实 GPU 训练日志前，第四章必须保持 `\TODO{}` 占位或标记为脚手架模式，严禁编造具体数字作为结论在摘要或结论中宣传；
* **禁止跳过门禁直接扩写**：前期版本提出的“直接扩写至 50~65 页”已作废。任何扩写必须先通过 P0 四道质量门禁；
* **严禁 AI 代签人工门**：AI 严禁自主调用 `--confirm-review` 生成假的 `.human_review.json`。人工门签字必须由真实人类作者在终端交互确认。

### 2. 标准开发与验收流水线
修改论文或扩写章节后，必须依次执行：
```bash
# 1. 执行质量门禁全检
python .agents/skills/thesis-latex-writer/scripts/run_quality_gates.py pku_thesis_workflow/pku_thesis_project --scaffold

# 2. 编译 PDF
python .agents/skills/thesis-latex-writer/scripts/compile_thesis.py pku_thesis_workflow/pku_thesis_project main.tex

# 3. 导出带警示标记的 Word 单源转换
python .agents/skills/thesis-latex-writer/scripts/tex_to_docx.py pku_thesis_workflow/pku_thesis_project --output pku_thesis_workflow/pku_thesis_project/Peking_University_Thesis_085402.docx --scaffold

# 4. 同步技能四副本
python .agents/skills/sync_skills.py
```

---

## 六、第三方审计缺陷整改与实测闭环记录

针对第三方独立审计提出的专项核查意见，已完成全面技术闭环：

### 1. Gate 4 人工门硬化（彻底消灭“橡皮图章”缺陷）
- **密码学 SHA-256 哈希绑定**：签署时必须记录每章 `.tex` 文件的 SHA-256。每次运行 `run_quality_gates.py` 动态重算哈希，任一章节在签署后被修改，签名即刻失效并输出报错警示；
- **占位符智能拦截**：自动拦截 `研究生|导师复核组|TBD|XXX|TODO|placeholder|none|unknown|待定` 等占位人名与空日期；
- **防造假保护基线**：Demo 夹具 `.human_review.json` 预置为无效占位符，实测在 `--scaffold` 下输出：
  `Gate 4: [NOTICE] - Reviewer name '北京大学研究生 / 导师复核组 [AI 自签无效占位]' is a placeholder or AI-generated token.`
  在非草稿正式送审模式下严格阻断退出；
- **终端交互签名协议**：提供 `python run_quality_gates.py <dir> --confirm-review --reviewer <真实姓名>` 供人类作者在终端按章节确认。AI 自主执行时严禁调用该命令。

### 2. 三个小项闭环
1. **CMD7 Word 转换命令对齐**：SOP 与交接清单全面更新为使用 `scripts/tex_to_docx.py` 单源转换引擎，具备 Pandoc 与原生解析器双轨容灾；
2. **调研对比矩阵依据门禁测试闭环**：
   - `literature_comparison_matrix.md` 作为早期无证据样本，供负向测试校验，`verify_grounding.py` 准确捕获 6 FAIL / 4 WARN 并阻断；
   - 新建 `literature_comparison_matrix_grounded.md`，基于 `literature_v2/` 中 5 篇 OA PDF 原文构建 16 维矩阵，实测 `verify_grounding.py` **0 FAIL, 0 WARN 100% PASS**；
3. **`check_math.py` 符号告警去重机证实测**：
   - 代码层通过 `reported_symbols_in_file` 集合维护文件级去重标记；
   - 在 `pku_thesis_project` 上实跑验证：在 `chap03_sec04_loss_and_convergence.tex` 内，同一未注册向量符号 `\bm{g}` 虽多次出现，仅报告 1 次 NOTICE：
     `[NOTICE ] chapters\chap03\chap03_sec04_loss_and_convergence.tex:L61 | Notation Contract Alignment | Vector symbol '\bm{g}' not formally registered in notation_table.md contract (de-duplicated per file).`
   - 全工程未注册符号告警由 15 条压缩为 4 条，去重降噪幅度达 73.3%，且无任何漏报。
4. **对抗回归测试套件固化 (Adversarial Regression Test Suite)**：
   - 在 `.agents/skills/tests/` 新建标准库自动化回归套件 `test_gates.py` 与运行器 `run_selftest.py`；
   - 覆盖 Gate 1~Gate 4、落地页过滤器与依据校验全部 8 大对抗攻击向量，实测 8/8 拦截率 100%（留档 `10_selftest_baseline.log`）；
   - 通过 `sync_skills.py` 保持四平台镜像目录（Gemini/Codex/Claude）零差异完全同步。

---

## 七、全新课题 E2E 实战演练与平台终审验收记录 (2026-09-07)

为兑现“平台级防伪机制必须在全新课题上自证闭环”的最高要求，开展了与 Deep JSCC 完全正交的全新硬核通信课题实战演练：**“面向 6G 的 RIS（可重构智能表面）辅助通信波束赋形与信道估计”**。全程零复用 demo 内容，从零目录 `ris_thesis_workflow/` 独立派生并交付。

### 1. 全流程六阶段验证证据矩阵

| 演练阶段 | 输入 / 工具 | 输出产物 | 验收机检实证数据 |
| :--- | :--- | :--- | :--- |
| **Phase 1: 文献层** | `search_papers.py` | `literature/` 5 篇 OA PDF<br>`references_broad.bib` (49 篇)<br>`reading_plan.md` | 3 篇随机抽取对 Crossref 官方 JSON 核验：标题、第一作者姓、出版年 **100% 一致**。 |
| **Phase 2: 调研层** | `verify_grounding.py` (PyMuPDF) | `survey/literature_comparison_matrix.md` | 覆盖 16 项维度（含真实 PDF 物理页码范围）；PyMuPDF 物理核验页码与文本特征词：**0 FAIL, 0 WARN (100% PASS)**。统一兼容 `--pdf-dir` 与 `--literature-dir` 参数别名。 |
| **Phase 3: 写作层** | `notation_table.md`<br>LaTeX 模板 | `ris_thesis_project/` 5 章完整论文草稿<br>`references.bib` (11 篇精选真文献) | 第 3 章子文件彻底去残留更名为 `beamforming_optimization.tex` 与 `ris_phase_quantization.tex`；第 4 章采用纯脚手架模式（参数扫描空间 $M \in \{32,64,128\}$，性能指标全量 `\TODO{}` 占位，**0 伪造数据**）；引文全部经 Crossref 回填。 |
| **Phase 4: 门禁层** | `run_quality_gates.py --scaffold` | `gate_summary.json` | **Gate 1: PASS, Gate 2: PASS, Gate 3: PASS, Gate 4: NOTICE**；总判定：**[PASS]**。Gate 4 准确识别 AI 占位签名并阻断非草稿送审。 |
| **Phase 5: 输出层** | `compile_thesis.py`<br>`tex_to_docx.py` | `ris_thesis_project/main.pdf` (428.4 KB)<br>`ris_thesis_project/thesis.docx` | XeLaTeX 双 pass 编译 **0 Errors, 0 Undefined References**；Word 导出内嵌真实红色页眉水印与警示边框（`w:color="C00000"`），且题目动态提取为 RIS 真实课题。 |
| **Phase 6: 对抗自检** | 主动注入攻击测试 | 真实终端日志留档于 `ris_thesis_workflow/logs/` | 假引文被 Gate 1 拦截；扩容后的 `%` 句式（`增益 28.5%`）与 `"达到 X dB"` 句式（`达到 24.6dB`）被 Gate 2 精准捕获；恢复后门禁全绿，证明防御机制物理生效。 |

### 2. 对抗性注入自检实录（Red / Green 对抗证明）

* **红态拦截 (Red State Interception)**：
  - 在 `references.bib` 与 `chap01_intro.tex` 注入假引文 `smith2024hallucinated`（伪造作者 Smith、假标题、假年份 2024 挂靠真实 DOI）；
  - 在 `chap04_experiments.tex` 注入未受 `\TODO{}` 保护且无 CSV 支撑的两条虚假定量断言：
    - `%` 句式：“*所提自适应主被动协同波束赋形架构实现了和速率增益 28.5%*”；
    - `"达到 X dB"` 句式：“*在复杂多径莱斯衰落信道环境下，接收端信噪比稳定达到 24.6dB*”；
  - 运行门禁后，Gate 1 当场报出：`[FAIL] smith2024hallucinated -> 标题不匹配 / 第一作者姓不匹配 (Smith vs Wu) / 年份不匹配 (2024 vs 2019)`；
  - Gate 2 扩容正则当场报出：
    - `-> Found quantitative claim '增益 28.5%' in chap04_experiments.tex, but no experiments/*.csv found!`
    - `-> Found quantitative claim '达到 24.6dB' in chap04_experiments.tex, but no experiments/*.csv found!`
  - 总状态立即变为 **[FAIL]**，编译与导出流水线阻断。
* **绿态恢复 (Green State Recovery)**：
  - 撤回假引文与假实验断言，恢复合规脚手架 `\TODO{}`；
  - 重新执行门禁，Gate 1-3 PASS，Gate 4 NOTICE，总评判定恢复为 **[PASS]**。

全部真实终端输出日志已逐字留档于 `ris_thesis_workflow/logs/`（含 `01_verify_grounding.log` 至 `06_adversarial_green_recovery.log`），详报请参阅 [E2E_VERIFICATION_REPORT.md](../ris_thesis_workflow/E2E_VERIFICATION_REPORT.md)。

---

## 八、北京邮电大学通信硕士新课题全流程实战双交付记录（2026-09-08）

为进一步验证工作流跨学科方向（低空智联网 UAV-ISAC）、跨培养单位（北京邮电大学 085402 通信工程）以及双产物（学位论文脚手架 + 周度组会汇报 Beamer 幻灯片）的泛化能力与学术纯洁性，平台从零目录 `bupt_isac_workflow/` 独立启动全新课题演练：**《面向低空智联网的无人机通感一体化波形设计与感知辅助通信资源管理》**。

### 1. 双交付核心产物与验证矩阵

| 交付产物 | 核心文件位置 | 关键指标与工程规范 | 真实物理验证结果 |
| :--- | :--- | :--- | :--- |
| **交付 A: 硕士论文脚手架** | `bupt_isac_workflow/thesis_project/main.pdf`<br>`bupt_isac_workflow/thesis_project/thesis.docx` | 符合 GB/T 7713.1-2006；封面标注北邮电子信息 085402 专业代码与校准注释；模式 C 分块深写；严格遵守 `notation_table.md` 单源契约；第 4 章采用纯脚手架模式（参数扫描空间三线表，**0 伪造量化实验数据**）。 | **XeLaTeX 双遍编译 0 错误、0 严重 Overfull 溢出、0 未定义引用**（PDF 375.4 KB）；Word 导出保留 `C00000` 红色页眉水印；**四道门禁 Gate 1-3 PASS, Gate 4 NOTICE**（总评 [PASS]）。 |
| **交付 B: 周度组会文献汇报** | `bupt_isac_workflow/survey/seminar_presentation.pdf`<br>`bupt_isac_workflow/survey/seminar_presentation.tex` | `ctexbeamer` 16:9 宽屏，北邮经典蓝 Madrid 主题；14 页幻灯片；每张技术页含页脚本地物理文献证据链与 `\note{}` 逐字演讲稿。 | **XeLaTeX 编译生成 14 页真实 PDF**；涵盖多无人机后验克拉美罗界（PCRB）、双基地 OFDM 子载波注水与抗高多普勒 UW-OCDM 机制。 |

### 2. 真实性闭环与证据留档
* **文献层与 15+1 维对比矩阵**：下载 **11 篇真实开源（OA）PDF 全文**至 `bupt_isac_workflow/literature/`；8 篇精读文献 15+1 维对比矩阵经 `verify_grounding.py` 严格核验物理页码与文本特征，**0 FAIL, 0 WARN**；
* **引文 Crossref 官方取证**：16 篇论文参考文献（共 32 条记录）全部直连 Crossref REST API 权威元数据比对，**FAIL=0, OK=32**；
* **数学符号契约机检**：通过 `check_math.py` 审查，未定义符号 0 条、定理与证明强度错配 0 条、算法假设冲突 0 条；
* **原始终端日志留档**：从自检 `00_selftest.log` 到编译 `06_compile.log` 共 7 大原始日志完整留档于 `bupt_isac_workflow/logs/`。详报参见 [bupt_isac_workflow/E2E_VERIFICATION_REPORT.md](../bupt_isac_workflow/E2E_VERIFICATION_REPORT.md)。



