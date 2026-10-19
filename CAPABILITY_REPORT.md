# 能力证明报告（CAPABILITY REPORT）

> 这份报告回答一个问题：**这套工作流现在到底能做到什么程度？**
> 所有数字都是本机实测输出，不是设计目标。凡未做到的，写在「能力边界」里，不粉饰。

- 报告生成：2026-10-19
- 仓库：`C:\Users\24560\Desktop\study\pidemo`
- 基线 commit：`14c00d7`（本报告随改进提交一起入库）
- 环境：Windows / Python 3.12.10 / PyMuPDF 1.28.2 / MiKTeX xelatex
- 入口：`zhaw`（22 个子命令），`pip install -e .` 后可直接调用

---

## 0. 一句话结论

**它现在是一条可端到端跑通的「论文质量门禁流水线」**：从建工程、查文献、写正文、出图、组会 PPT、开题报告、答辩 PPT、盲审匿名化、到归档，每个环节都有命令；每个环节产出的东西都要过机器检查，编不过、引不对、数对不上、字不够、章不全都会**明确报错并给出文件:行号**。

**它做不到的是替你写论文。** 8,547 汉字要变成 30,000，只有你能写；Gate 4 的真人签字只有你能签。

---

## 1. 关键数字总览

| 维度 | 实测值 | 证据位置 |
|---|---|---|
| 对抗自测用例 | **11 / 11 PASS，0.352 s** | §2 |
| 真实工程门禁 | **3 个工程全部 Overall PASS** | §3 |
| 接地门禁（PDF 物理页码核验） | **11 篇 PDF / 8 行矩阵 / 0 FAIL / 0 WARN** | §4 |
| CLI 子命令 | **22 个，全部实测可用** | §5 |
| 学位论文编译 | **32 页 / 375.6 KB / 0 错误** | §5.1 |
| 组会 PPT | **16 页 / 243.0 KB** | §5.5 |
| 答辩 PPT | **9 页 / 82.1 KB + 讲稿 + 13 问 Q&A** | §5.6 |
| 盲审匿名化 | **7 处机检泄露全部重写，副本可独立编译** | §5.7 |
| 归档 | **985,054 字节 zip + SHA-256 manifest** | §5.8 |
| 可交付度评分（demo 工程） | **55.2 / 100**（诚实打分，缺口逐条列出） | §5.4 |

---

## 2. 对抗自测：11 / 11 全部拦截

`zhaw selftest` 不是「跑通就行」的测试，而是**主动构造 11 种造假/出错场景，验证门禁真的能拦住**。

| # | 攻击场景 | 拦截者 | 结果 |
|---|---|---|---|
| 1 | 伪造引文（作者/年份/卷期错配） | Gate 1 | PASS |
| 2 | 编造 DOI | Gate 1 | PASS |
| 3 | 数据表里出现正文没写的数字 | Gate 2 | PASS |
| 4 | 正文数字与 CSV 对不上 | Gate 2 | PASS |
| 5 | 用中文数字绕过数值检查 | Gate 2 | PASS |
| 6 | 缺参考文献 / 引用不存在的条目 | Gate 1 | PASS |
| 7 | 绕过 GB/T 格式（缺摘要/关键词） | Gate 3 | PASS |
| 8 | 伪造人工签字 | Gate 4 | PASS |
| 9 | **CSV 数值与正文不一致（第 9 项，本轮新增）** | Gate 2 | PASS |
| 10 | **引用已撤稿论文（本轮新增）** | Gate 1 | PASS |
| 11 | **数学恒等式写错（本轮新增）** | Math Reviewer | PASS |

> 第 9 项是本轮把 Gate 2 从「有 CSV 就放行」升级为「逐单元格比对」后加的；第 10、11 项对应本轮新接入的撤稿检测与 sympy 符号验证。

---

## 3. 真实工程四门禁实测

三个工程**全部 Overall PASS**（Gate 4 未签是设计如此，因为真人签字不能由机器代签）。

| 工程 | Gate 1 引文 | Gate 2 数据 | Gate 3 国标 | Gate 4 签署 | 总评 |
|---|---|---|---|---|---|
| `bupt_isac_workflow\thesis_project` | PASS | PASS | PASS | NOTICE（未签） | **PASS** |
| `ris_thesis_workflow\ris_thesis_project` | PASS | PASS | PASS | NOTICE（占位签名被拒） | **PASS** |
| `pku_thesis_workflow\pku_thesis_project` | PASS | **NOTICE**（历史残留假断言） | PASS | NOTICE（占位签名被拒） | **PASS** |

值得单独说的一点：`ris` / `pku` 两个工程 Gate 4 的 NOTICE 不是「没签字」，而是**检测到签字人是 `[AI 自签无效占位]` 并被明确拒绝** —— 这正是门禁该有的行为。`pku` 的 Gate 2 NOTICE 指向 `chap01_intro.tex:20` 那条「提升高达 3.8dB」，是本项目早期 demo 造假的历史残留，保留它就是为了当反例。

---

## 4. 接地门禁（Grounding Gate）

这是本项目最不可替代的一环：**不信任任何 LLM 生成的对比表，逐行打开本地 PDF 核对页码与特征词。**

```
zhaw grounding bupt_isac_workflow\survey\literature_comparison_matrix.md ^
               --pdf-dir bupt_isac_workflow\literature
```

- 文献池：**11 篇开放获取 PDF**
- 矩阵行数：**8 行**
- 结果：**0 FAILURES / 0 WARNINGS / PASSED**
- 核验方式：每行记录被引 PDF 的实际页数、声称页码区间、以及从原文抽出的特征词命中数（如 row6 `[06] pp.1-15/17, 12 tokens`）

> 换句话说：矩阵里说「[04] 第 1–6 页提出了 X」，程序会真的打开 `[04]` 那个 PDF，确认它有 6 页、确认那几页里确实出现 X 的特征词。对不上就 FAIL。

---

## 5. 全生命周期实测（22 个子命令）

`zhaw --help` 注册的全部命令，逐个在本机跑过。

### 5.1 建工程 → 编译
```
zhaw new _demo\demo_thesis --kind thesis --title "..." --author "李同学" ...
zhaw compile _demo\demo_thesis
```
→ 17 个文件、封面 6 字段已替换、**main.pdf 375.3 KB / LaTeX Errors 0 / Severe Overfull 0 / Undefined Refs 0**

### 5.2 引文取证
```
zhaw gate1 bupt_isac_workflow\thesis_project --offline
```
→ 16 条文献 / 32 条记录（.bib 与 thebibliography 双源）/ **FAIL=0, OK=32**；每条标注 `verified: retraction, title, authors, year, pages`

### 5.3 数据溯源
```
zhaw gate2 <project> --scaffold
```
→ 逐单元格比对 CSV 与正文断言；无 CSV 时给出 NOTICE 而不是假 PASS

### 5.4 可交付度评分
```
zhaw audit _demo\demo_thesis --offline --scaffold
```
→ **55.2 / 100**，六个维度全部给出扣分理由：

| 维度 | 得分 | 权重 | 证据 |
|---|---|---|---|
| 门禁通过率 | 75.0 | 0.30 | 3/4 PASS |
| 正文完成度 | 27.2 | 0.25 | 8,171 汉字 / 目标 30,000 |
| 数据可溯源 | 100.0 | 0.15 | experiments/*.csv 存在 |
| 参考文献量 | 26.7 | 0.10 | 16 条 / 目标 60 |
| 真人签署 | 0.0 | 0.10 | 未签署 |
| 脚手架残留 | 82.0 | 0.10 | 18 处 `\TODO{}` |

> 这个分数是**故意难看**的。它算的是「离可送审还差多少」，不是「你做得多好」。

### 5.5 组会 PPT
```
zhaw seminar bupt_isac_workflow\survey\literature_comparison_matrix.md --out _demo\demo_seminar --compile
```
→ **16 页 ctexbeamer PDF / 243.0 KB** + 讲稿 `seminar_notes.md` + 大纲 `seminar_outline.md`

### 5.6 答辩 PPT
```
zhaw defense _demo\demo_thesis --out _demo\demo_defense --compile
```
→ **9 页 PDF / 82.1 KB** + 逐页讲稿 + **13 问预答辩问题库**（每题写明「评委想听什么」）

### 5.7 盲审匿名化
```
zhaw anonymize bupt_isac_workflow\thesis_project --out _demo\bupt_blind_repro --force
```
→ 20 个文件、**7 处机检泄露全部重写**（封面姓名 / 学号 / 导师 / 正文署名 / 致谢章 / 攻读成果章），生成 `LEAKS.md`，**盲审副本可独立 xelatex 编译通过**

> `LEAKS.md` 明确列出「机器管不了」的 6 类：PDF 元数据、图片水印、表格姓名列、自引表述、致谢中的间接指认、基金号。

### 5.8 归档
```
zhaw archive bupt_isac_workflow\thesis_project --out-dir _demo\archives --name bupt_repro
```
→ **985,054 字节 zip + SHA-256 manifest**，可直接作为送审存档

### 5.9 其余命令

| 命令 | 实测结果 |
|---|---|
| `zhaw doctor` | RESULT: READY（7 个脚本 + pymupdf + xelatex + git 全就绪） |
| `zhaw progress` | 28.5%（8,547 / 30,000 汉字）、待填 20 处、16 条文献、分章进度表 |
| `zhaw figures` | CSV → PDF + PNG 矢量图 + `\includegraphics` 片段 + 三线表 `.tex` |
| `zhaw math` | 43 个契约符号，0 findings；符号恒等式 0 验证/0 失败/5 未定（不假阳性） |
| `zhaw proposal` | 六章开题模板 + 配额检查；demo 诚实报 10 条缺口（562 字 < 9000 等），exit 1 |
| `zhaw docx` | 无 pandoc 时自动降级到 Python 原生 GB/T 引擎，产出 `main.docx` |
| `zhaw bib` | 16 条 Crossref 回填，0 查无此文 |

---

## 6. 本轮新增的三项外部能力

| 能力 | 来源 | 落点 | 效果 |
|---|---|---|---|
| 学术图表版式 | SciencePlots（MIT，9,293★） | `plot_academic_curves.py:setup_academic_style()` | IEEE/Nature 版式，保留 SimSun 逐字形回退，无缺字 |
| 撤稿检测 | citegate 思路（MIT） | `check_citations.py:CrossrefClient.retraction()` | 引用已撤稿论文 → Gate 1 直接 FAIL |
| 数学机器验证 | sympy（BSD-3，15,020★） | `check_math.py:verify_identities()` | 恒等式 `sympify` 后 `simplify(lhs-rhs)==0`，只对确定的非零差值判 FAIL |

三项都是**可选依赖 + 优雅降级**：没装 scienceplots 用内置 rcParams，没装 sympy 打印 SKIPPED，离线时撤稿检测跳过而不误报。

许可证方面补了 `THIRD_PARTY_LICENSES.md`：明确标注 `pymupdf` 是 AGPL-3.0/Artifex 双许可，与本仓库 MIT 声明的关系、以及三种使用场景下的义务。

---

## 7. 能力边界（做不到的，明确列出）

1. **不会替你写正文**：8,547 → 30,000 汉字是人的工作。程序只能告诉你还差多少、哪一章差最多。
2. **Gate 4 必须真人签**：`--confirm-review` 需要交互输入，占位签名会被识别并拒绝。
3. **关键数字仍需人工回原文核对**：Gate 2 能证明「数字在 CSV 里存在」，不能证明「这个实验设计是对的」。
4. **创新点主线**：`proposal --check` 能查「空话句式」和「条数不足」，查不出「你的创新点是否真的新」。
5. **官方查重**：知网/万方必须走学校渠道，本项目不做也不该做。
6. **匿名化的非文本载体**：PDF 元数据、图片水印、表格里的姓名列需要人工确认（`LEAKS.md` 已列出清单）。
7. **参考文献段落语义切分**：目前只能审 `.bib` 里已有的条目；要审「PDF 里写了但 `.bib` 漏了」需要接 GROBID（已调研，未接入，约 2–3 人日）。

---

## 8. 复现方式

```powershell
cd C:\Users\24560\Desktop\study\pidemo
py -3.12 -m pip install -e .

# 1) 环境与自测
zhaw doctor
zhaw selftest                          # 期望 11/11 PASS

# 2) 三工程门禁
zhaw check bupt_isac_workflow\thesis_project        --scaffold --offline
zhaw check ris_thesis_workflow\ris_thesis_project   --scaffold --offline
zhaw check pku_thesis_workflow\pku_thesis_project   --scaffold --offline

# 3) 接地门禁
zhaw grounding bupt_isac_workflow\survey\literature_comparison_matrix.md --pdf-dir bupt_isac_workflow\literature

# 4) 编译与交付物
zhaw compile bupt_isac_workflow\thesis_project
zhaw seminar bupt_isac_workflow\survey\literature_comparison_matrix.md --out _demo\demo_seminar --compile
zhaw defense _demo\demo_thesis --out _demo\demo_defense --compile

# 5) 评分 / 进度 / 匿名化 / 归档
zhaw audit   _demo\demo_thesis --offline --scaffold
zhaw progress bupt_isac_workflow\thesis_project
zhaw anonymize bupt_isac_workflow\thesis_project --out _demo\bupt_blind_repro --force
zhaw archive  bupt_isac_workflow\thesis_project --out-dir _demo\archives --name bupt_repro
```

---

## 9. 与第一轮相比

| 项 | 第一轮（`2c84fd6`） | 本轮 |
|---|---|---|
| 对抗用例 | 9 | **11** |
| 子命令 | 10 | **22** |
| 端到端链路 | 门禁 + 编译 | **建工程→图→组会→开题→答辩→盲审→归档** |
| 撤稿检测 | 无 | **有** |
| 数学机器验证 | 无 | **有（sympy）** |
| 图表版式 | 手写 rcParams | **SciencePlots IEEE** |
| 许可证声明 | 仅 MIT（与 pymupdf AGPL 冲突） | **`THIRD_PARTY_LICENSES.md` 说明** |
| 可交付度评分 | 无 | **有（六维加权）** |

---

## 10. 诚实结论

- 作为**质量门禁**：已经能用了。11 种造假场景全拦，三个真实工程全过，PDF 页码级核验跑通。
- 作为**写作辅助**：只到「脚手架 + 配额 + 缺口清单」这一层，正文得你自己写。
- 作为**研究生科研基础设施**：组会（每 1–2 周）、开题、答辩、盲审、归档这五个高频场景都有命令覆盖；中期检查与投稿流程仍是空白。
- 最大的剩余价值不在加功能，而在**把 bupt 那 8,547 字写成 30,000 字** —— 工具已经就位了。
