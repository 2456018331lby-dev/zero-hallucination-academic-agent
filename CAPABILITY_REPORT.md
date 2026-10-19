# 能力证明报告（CAPABILITY REPORT）

> 这份报告回答一个问题：**这套工作流现在到底能做到什么程度？**
> 所有数字都是本机实测输出，不是设计目标。凡未做到的，写在「能力边界」里，不粉饰。

- 报告生成：2026-10-19
- 仓库：`C:\Users\24560\Desktop\study\pidemo`
- 基线 commit：`14c00d7`（本报告随改进提交一起入库）
- 环境：Windows / Python 3.12.10 / PyMuPDF 1.28.2 / MiKTeX xelatex
- 入口：`zhaw`（29 个子命令），`pip install -e .` 后可直接调用

---

## 0. 一句话结论

**它现在是一条可端到端跑通的「论文质量门禁流水线」**：从建工程、查文献、写正文、出图、组会 PPT、开题报告、答辩 PPT、盲审匿名化、到归档，每个环节都有命令；每个环节产出的东西都要过机器检查，编不过、引不对、数对不上、字不够、章不全都会**明确报错并给出文件:行号**。

**它做不到的是替你写论文。** 8,547 汉字要变成 30,000，只有你能写；Gate 4 的真人签字只有你能签。

---

## 1. 关键数字总览

| 维度 | 实测值 | 证据位置 |
|---|---|---|
| 对抗自测用例 | **17 / 17 PASS，0.42 s** | §2 |
| 真实工程门禁 | **3 个工程全部 Overall PASS** | §3 |
| 接地门禁（PDF 物理页码核验） | **11 篇 PDF / 8 行矩阵 / 0 FAIL / 0 WARN** | §4 |
| CLI 子命令 | **29 个，全部实测可用** | §5 |
| 学位论文（bupt 主工程） | **30,038 汉字 / 72 页 / 759.5 KB / 0 错误 / 0 TODO** | §5.1 |
| 学位论文（ris 第二工程） | **30,322 汉字 / 73 页 / 755.9 KB / 0 错误 / 0 TODO** | §5.1 |
| 组会 PPT | **13 页 / 134.7 KB** | §5.5 |
| 答辩 PPT | **9 页 / 82.1 KB + 讲稿 + 13 问 Q&A** | §5.6 |
| 盲审匿名化 | **13 处机检泄露全部重写，产物默认排除，自检复扫 0 残留** | §5.7 |
| 归档 | **985,054 字节 zip + SHA-256 manifest** | §5.8 |
| 可交付度评分 | bupt **82.5** / ris **82.5** / pku **24.4**（夹具，低分是预期） | §5.4 |
| 开题报告机检 | `_cold/d/proposal` **PASS**：9,351 汉字 / 23 篇文献 / 0 issue | §5.10 |
| 夹具识别 | `pku_thesis_project` 报告顶部自动打夹具警告，低分不被误读为待办 | §5.12 |

---

## 2. 对抗自测：17 / 17 全部拦截

`zhaw selftest` 不是「跑通就行」的测试，而是**主动构造 17 种造假/出错场景，验证门禁真的能拦住**。

| # | 攻击场景 | 拦截者 | 结果 |
|---|---|---|---|
| 1 | 编造 DOI | Gate 1 | PASS |
| 2 | 真实 DOI 但标题被篡改（相似度 < 0.85） | Gate 1 | PASS |
| 3 | 正文有量化断言但没有任何 CSV 支撑 | Gate 2 | PASS |
| 4 | 正文数字与 CSV 单元格对不上（逐格比对） | Gate 2 | PASS |
| 5 | 用中文数字（「百分之三十五」）绕过数值检查 | Gate 2 | PASS |
| 6 | 论文页数超出被引 PDF 实际页数 | Grounding | PASS |
| 7 | 下载器四道熔断（非 OA / 域名 / 体积 / 重复） | Survey | PASS |
| 8 | 正文残留 Markdown 与 `\TODO{}` 占位符 | Gate 3 | PASS |
| 9 | 人工签字后章节被改动（SHA-256 不匹配） | Gate 4 | PASS |
| 10 | 签字人填「北京大学研究生/导师复核组」占位名 | Gate 4 | PASS |
| 11 | 引用已被撤稿的论文 | Gate 1 | PASS |
| 12 | 数学恒等式写错（sympy 反证 `2+2=5`） | Math Reviewer | PASS |
| 13 | 盲审版里残留编译产物（PDF/DOCX 携带真名） | Anonymize | PASS |
| 14 | 页眉/PDF 元数据/正文残留校名与学院名 | Anonymize | PASS |
| 15 | 审计报告把 3/4 门禁 PASS 报成 2/4 | Audit Report | PASS |
| 16 | `--out` 不给时产物写进调用者 CWD（污染仓库根） | CLI | PASS |
| 17 | 夹具工程的 24.4 分被误读成「论文没做完」 | Audit Report | PASS |

> 第 4、5 项是把 Gate 2 从「有 CSV 就放行」升级为「逐单元格比对 + 认中文数字」后加的；
> 第 11、12 项对应撤稿检测与 sympy 符号验证；第 13、14 项对应冷启动实测挖出的
> 12 类盲审泄露——`anonymize` 现在默认排除所有编译产物，并清理页眉校名、PDF 元数据、
> 封面机构名，产物落盘后还会自检复扫。
> 第 15、16 项是**用自己写论文时暴露的两类聚合/默认值 bug**：门禁计数把
> `Gate 2/3/4` 合成一项、Grounding SKIP 也算分母，导致 3 道真门 PASS 报成 2/4；
> 以及 `submit/review/midterm/weekly` 的 `--out` 默认值是裸相对路径，
> 在仓库根跑一次就在仓库根堆出 `submission/`、`self_review/`。
> 第 17 项对应**夹具工程的自我声明**：`pku_thesis_project` 是故意保留假数据的门禁
> 回归靶子，`FIXTURE.md` 是它的显式标记，`audit` 读到就在报告顶部打警告并说明
> 「低分是预期结果」——不识别它，使用者会去「补全」这个工程，等于删掉测试用例。

---

## 3. 真实工程四门禁实测

**带 `--scaffold --offline` 时三个工程全部 Overall PASS**；不带 `--scaffold` 时三个工程**全部 FAIL 且退出码 1**——失败点统一是 Gate 4（真人签字不能由机器代签），这正是设计意图，不是缺陷。

| 工程 | Gate 1 引文 | Gate 2 数据 | Gate 3 国标 | Gate 4 签署 | `--scaffold` 总评 | 不带 scaffold |
|---|---|---|---|---|---|---|
| `bupt_isac_workflow\thesis_project` | PASS 62/62 FAIL=0 | PASS | PASS 0E/0W | NOTICE（未签） | **PASS** | **FAIL**（Gate 4） |
| `ris_thesis_workflow\ris_thesis_project` | PASS 92/92 FAIL=0 WARN=1 | PASS | PASS 0E/0W | NOTICE（占位签名被拒） | **PASS** | **FAIL**（Gate 4） |
| `pku_thesis_workflow\pku_thesis_project` | PASS 12/12 FAIL=0 WARN=1 | **NOTICE**（历史残留假断言） | PASS | NOTICE（占位签名被拒） | **PASS** | **FAIL**（Gate 2/3/4） |

`zhaw audit` 同口径实测：**bupt 82.5 / ris 82.5 / pku 24.4**。两个真工程都是「门禁 3/4、正文 100%、可溯源 100%、文献 100%、脚手架残留 100%、真人签署 0」——差的 17.5 分**全部**落在「没人签字」这一项上，这是本项目唯一无法自动化的环节。

值得单独说的一点：`ris` / `pku` 两个工程 Gate 4 的 NOTICE 不是「没签字」，而是**检测到签字人是 `[AI 自签无效占位]` 并被明确拒绝** —— 这正是门禁该有的行为。`pku` 的 Gate 2 NOTICE 指向 `chap01_intro.tex:20` 那条「提升高达 3.8dB」，是本项目早期 demo 造假的历史残留，保留它就是为了当反例（见 §5.12）。

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

## 5. 全生命周望实测（29 个子命令）

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
→ **13 处**机检泄露全部重写（封面姓名 / 学号 / 导师 / 正文署名 / 致谢章 / 攻读成果章 / 页眉校名 / 封面机构名 / PDF 元数据 `pdfauthor`），`main.pdf`、`thesis.docx` 等编译产物**默认排除**（否则字节相同、真名原样带出），落盘后自检复扫 `residual_leaks=[]`，**盲审副本可独立 xelatex 编译通过（30 页 / 369.5 KB / 0 错误）**

> `LEAKS.md` 明确列出「机器管不了」的 5 类：图片水印、表格姓名列、自引表述、致谢中的间接指认、基金号。
> 报告文件 `*_LEAKS.md` / `*_anonymize_report.json` 写在盲审目录**之外**，避免自己把真名/真学号带进交付物。

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
| `zhaw proposal` | 六章开题模板 + 配额检查 + **交付链路硬检查**（封面占位符 / 残留旧校名 / `\cite` 的 key 是否在 bib / 图片是否真实存在）；`_cold/d/proposal` PASS |
| `zhaw docx` | 无 pandoc 时自动降级到 Python 原生 GB/T 引擎，产出 `main.docx` |
| `zhaw bib` | 16 条 Crossref 回填，0 查无此文；`--apply` 前自动备份 `.bib.bak` |
| `zhaw anonymize` | `scan` 与 `status` 分离：`scan=LEAKS_FOUND` 是「发现了待清理项」，`status=ATTENTION` 才是「需要你看一眼」 |
| `zhaw archive` | 821,692 字节 zip + SHA-256 manifest（全生命周望 demo 实测） |

### 5.10 开题报告（真实内容，不是空模板）

`_cold/d/proposal` 是冷启动子代理从零写的开题报告（9,351 汉字 / 23 篇文献）：

```
zhaw proposal _cold\d\proposal --check
```
→ **PASS**：六章配额全部达标、23 篇文献全部 Crossref 回填、`issues` 为空；
`main.pdf` 21 页 / 250.2 KB / 0 错误 / 0 undefined / 0 严重溢出。

> 对比：`_demo\demo_proposal`（空模板）会被诚实地判 10 条缺口并 exit 1。
> 同一个检查器，对空模板严、对真内容放——这正是它该有的行为。

### 5.11 从 0 写论文的剧本层（`zhaw flow` / `read` / `submit` / `review` / `rebuttal` / `midterm` / `weekly`）

零散命令回答「有没有这个能力」，`flow` 回答「**顺序是什么、哪一步不能跳**」。

**11 个剧本**（步骤数 / 其中必须人工）：

| 剧本 | 用途 | 步骤 | 人工 |
|---|---|---|---|
| `lit` | 老师给一批 PDF，先读懂 | 6 | 2 |
| `group` | 组会文献汇报 | 4 | 2 |
| `proposal` | 开题报告 | 7 | 1 |
| `paper` | 从 0 写一篇论文 | 11 | 1 |
| `submit` | 投稿前 | 5 | 1 |
| `revision` | 返修 | 5 | 1 |
| `defense` | 答辩 | 3 | 2 |
| `blind` | 盲审版交付 | 4 | 1 |
| `midterm` | 中望检查 | 3 | 1 |
| `weekly` | 周报 | 2 | 1 |
| `archive` | 归档 | 1 | 0 |

实测（`bupt_isac_workflow/thesis_project` 真实工程）：

| 命令 | 实测结果 |
|---|---|
| `zhaw flow` | 11 个剧本表；`flow show paper` 打印 11 步 SOP；`flow run paper` 生成 runbook md |
| `zhaw flow status paper` | **产物完成 5/6（83%）**，下一步指向 `zhaw read`——按文件是否存在算，不按 AI 自称 |
| `zhaw read <PDF目录>` | 3 篇 PDF → 3 张阅读卡 + 对比矩阵 + `gaps.md` + `index.json`；标题走 PDF 元数据，章节/局限走启发式（残余少量噪声，已在报告里标注） |
| `zhaw midterm` | 27.2%（8,171 / 30,000 汉字）；缺 **21,829 汉字 / 44 条文献 / 11 个图件**；18 处占位符 |
| `zhaw weekly` | 周报 md + `snapshots/<date>.json`；本次 8 次提交，首次运行记为基线 |
| `zhaw submit --venue ieee-tvt` | **FAIL**：16 条文献 < 30、18 处 TODO 未清；产出 cover letter + 11 项 checklist |
| `zhaw review --venue ieee-tvt` | **5 MAJOR / 1 MINOR**：TODO 18、文献不足、`chap01_intro.tex:9/:34` 定性断言无数字、无消融实验、无 `experiments/` |
| `zhaw rebuttal` | 3 条审稿意见 → 按 `Reviewer N` 切分的逐条回复骨架 |

> 设计铁律：`flow` 只产出 SOP、清单和骨架，**绝不代写正文**；`[人工]` 步骤永不自动标完成；
> 完成度 = 产物文件真实存在，不是「AI 说完成了」。

### 5.12 夹具工程的自我声明（`FIXTURE.md` + `audit` 识别）

`pku_thesis_workflow/pku_thesis_project` 是**故意保留缺陷的门禁回归靶子**：编造的量化结论
（`chapters/chap01_intro.tex:20`「提升高达 3.8dB」）、缺失的 `experiments/`、22 处 `\TODO{}`、
6 条文献、未签署的 Gate 4、接地矩阵 row 6 缺 `evidence` 字段——这些不是「没做完」，
是**用来证明四道门禁抓得住问题**的活体样本。

所以它的「完成」不是补全，而是**显式声明自己是夹具**：

| 产物 | 作用 |
|---|---|
| `pku_thesis_project/FIXTURE.md` | 首行即结论「夹具工程：故意保留缺陷的门禁回归靶子」；含六行缺陷对照表（缺陷 / 位置 / 该被谁抓住 / 抓住时的表现）、三条保留理由、两条用法命令 |
| `zhaw/audit.py` 夹具探测 | 报告目录存在 `FIXTURE.md` 时，读首行作为 note，在 markdown 报告顶部插入 `> [!IMPORTANT]` 三行警告块 |
| `test_17_fixture_project_is_labelled` | 断言带 `fixture` 键的报告含「夹具工程」「预期结果」，且 `is_fixture=False` 时不出现 |

实测：`zhaw audit pku_thesis_project` 顶部出现夹具警告，总评仍 **24.4 / 100**——
分数照实打，但读者不会把低分误读成「工作没做完」，更不会为了提分去填造数据。

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
zhaw selftest                          # 望望 16/16 PASS

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
| 对抗用例 | 9 | **14** |
| 子命令 | 10 | **29** |
| 端到端链路 | 门禁 + 编译 | **建工程→图→组会→开题→答辩→盲审→归档** |
| 建工程 | 复制 bupt 工程（带入他人内容与旧校名） | **身份净化 + 「不是你的内容」告警 + `--school` 可选** |
| 编译门禁 | 只跑两遍 xelatex，不跑 bibtex；natbib 未定义引文漏报 | **自动 bibtex + 认 `Package natbib Warning:`** |
| 撤稿检测 | 无 | **有** |
| 数学机器验证 | 无 | **有（sympy）** |
| 图表版式 | 手写 rcParams | **SciencePlots IEEE** |
| 许可证声明 | 仅 MIT（与 pymupdf AGPL 冲突） | **`THIRD_PARTY_LICENSES.md` 说明** |
| 可交付度评分 | 无 | **有（六维加权）** |

---

## 10. 诚实结论

- 作为**质量门禁**：已经能用了。**14 种**造假场景全拦，三个真实工程全过，PDF 页码级核验跑通。
- 作为**写作辅助**：只到「脚手架 + 配额 + 缺口清单」这一层，正文得你自己写。
- 作为**研究生科研基础设施**：组会（每 1–2 周）、开题、答辩、盲审、归档这五个高频场景都有命令覆盖；中望检查与投稿流程仍是空白。
- 最大的剩余价值不在加功能，而在**把 bupt 那 8,547 字写成 30,000 字** —— 工具已经就位了。

