# E2E 验证报告（可复现记录 · bupt_isac_workflow）

> **这份报告替代 2026-09 的旧版。** 旧版中的数字（11 篇 PDF、16 维矩阵 0 FAIL、16 篇 32 条 Crossref 全 OK）
> 在当时那个 commit 上是真的，但工作区随后发生了漂移：5 篇文献 PDF 被删除，导致证据链断裂。
> 本版的原则是**每个数字都必须能在当前工作区用一条命令复现**，复现不了的就不写。

| 项 | 值 |
| :--- | :--- |
| 报告生成时间 | 2026-10-19 |
| 论文交付物基线 commit | `275882650e2d83c831ed798025a2dc8356606e58`（`2758826`） |
| 门禁代码与本报告 | 随最近一次 `git log -1` 提交（含 `zhaw` CLI、CI、Gate 2 CSV 级溯源） |
| 运行时 | Python 3.12.10 · PyMuPDF 1.28.2 · MiKTeX XeLaTeX |
| 复现入口 | `zhaw doctor && zhaw selftest && zhaw check bupt_isac_workflow/thesis_project --scaffold --offline` |
| 结论 | 四道门禁 **3 PASS + 1 NOTICE**，Overall **PASS**；论文本身仍是脚手架（见 §5 诚实缺口） |

---

## 1. 门禁总览（当前实测）

```
- Gate 1: Citation Verification Gate            : [PASS]
- Gate 2: Data Provenance & Traceability Gate   : [PASS]
- Gate 3: Academic Compliance Gate              : [PASS]
- Gate 4: Human Review Sign-Off Gate            : [NOTICE]
[*] Overall Outcome: [PASS]
```

- **Gate 1 PASS**：`zhaw gate1 bupt_isac_workflow/thesis_project --offline` → 32 条记录（16 篇文献 × `.bib`/`thebibliography` 双参考源）全部命中 Crossref 缓存，
  0 FAIL，1 WARN（`.bib` 与 `thebibliography` 双参考源，建议收敛为单一事实源）。
- **Gate 2 PASS（scaffold）**：第 4 章的数字都在 `\TODO{}` 占位符内，属受控脚手架；未发现"自由漂浮"的量化断言。
- **Gate 3 PASS（脚手架模式）**：GB/T 7713.1-2006 结构、GB/T 7714-2015 著录、三线表、图表标题位置、前后件齐备、Markdown 残留 = 0。
  ⚠️ **这个 PASS 只在 `--scaffold` 下成立**。按 `AGENTS.md` §5 铁律 4「正式交付必须不带 `--scaffold` 跑」，去掉该参数后
  Gate 3 报 **20 条 ERROR**（第 4 章 18 处 `\TODO{}`、`experiments/` 缺失等）。**送审前必须用不带 `--scaffold` 的命令复跑并清零。**
- **Gate 4 NOTICE**：`thesis_project/.human_review.json` 不存在。这是**设计如此**——AI 不能给自己签字；
  送审前必须由真人在终端执行 `zhaw gate4 bupt_isac_workflow/thesis_project --confirm-review --reviewer <你的名字>`，
  签署后逐章 SHA-256 会被写入，之后改一个字签名即失效。

## 2. 证据链完整性（Grounding Gate）

```
$ zhaw grounding bupt_isac_workflow/survey/literature_comparison_matrix.md \
                 --pdf-dir bupt_isac_workflow/literature
[*] Summary: 0 FAILURES, 0 WARNINGS.
[OK] Grounding Gate PASSED.
```

- 文献池：**11 篇 PDF**（`bupt_isac_workflow/literature/`）。
- 矩阵：**8 行**，每行的 `证据溯源` 列都指向真实存在的 PDF 文件名 + 真实页码区间。
- 校验方式：PyMuPDF 物理打开 PDF → 比对页数是否够 → 在该页范围内搜特征词。
  页码越界、PDF 缺失、文件名不存在，任意一条即 FAIL 并作废整张矩阵。
- 历史事故记录：删掉 5 篇 PDF 后该门禁确实 FAIL 了（Row1 声称 pp.1-7 但 [04] 只剩 6 页；Row3 声称 pp.1-8 但 [02] 只剩 6 页），
  从 commit `2758826` 恢复 PDF 后重新 PASS。**门禁拦住了自己仓库的漂移，这是它有效的最好证据。**

## 3. 交付物实测

| 交付物 | 路径 | 页数 | 体积 |
| :--- | :--- | :---: | ---: |
| 学位论文 PDF | `bupt_isac_workflow/thesis_project/main.pdf` | 32 | 375.6 KB |
| 组会 Beamer PDF | `bupt_isac_workflow/survey/seminar_presentation.pdf` | 14 | 437.0 KB |
| Word 导出 | `bupt_isac_workflow/thesis_project/thesis.docx` | — | 51.9 KB |

编译质量（`logs/06_compile.log`）：XeLaTeX **0 error / 0 Severe Overfull / 0 Undefined References**。

## 4. 对抗验证（14/14 PASS）

`zhaw selftest` 用 14 个"故意造假"的用例证明门禁真的会拦，而不是只会说 PASS：

| # | 攻击向量 | 期望 | 实测 |
| :---: | :--- | :--- | :---: |
| 1 | 伪造 DOI `10.9999/fake.test.2026` | FAIL | PASS |
| 2 | 真 DOI + 篡改标题（相似度 < 0.85） | FAIL | PASS |
| 3 | 签署后篡改章节 .tex（哈希失配） | FAIL | PASS |
| 4 | 占位审稿人"北京大学研究生/导师复核组" | FAIL | PASS |
| 5 | 无 CSV 支撑的量化断言（23.5% / 35.2 dB） | FAIL | PASS |
| 6 | PDF 缺页 / 页码越界（14 页 PDF 声称 pp.1-999） | FAIL | PASS |
| 7 | PDF 落地页 4 重熔断（<40KB、缺 fitz、导航词、标题相似度<0.5） | 全部 REJECT | PASS |
| 8 | Markdown `**` 残留 + TODO 泄漏进终稿 | FAIL | PASS |
| 9 | **CSV 存在但不含该数字（41.7 dB vs CSV 28.53 dB）** | FAIL | PASS |
| 10 | **引用已撤稿论文（合成 Crossref 缓存 `is-retracted-by`）** | FAIL | PASS |
| 11 | **数学恒等式写错（`2 + 2 = 5`）** | FAIL | PASS |

第 9 条是本次新增的：修复了旧 Gate 2 "只要存在任意 CSV 就全部放行"的漏洞。
现在每个数字都要落进某个 CSV 单元格（支持四舍五入与百分比/小数换算），并报告 `文件:行号`。

第 10、11 条对应两项新接入能力：撤稿检测（Crossref `relation.is-retracted-by` / `update-to`）
与 sympy 符号恒等式验证（`simplify(lhs - rhs) == 0`，只对确定的非零差值判 FAIL，不产生假阳性）。

## 5. 诚实缺口清单（这些没做完，就是没做完）

1. **论文正文只有 8,547 汉字**（`chapters/` 全量统计），硕士常规 3–5 万字 → 还差约 3/4。
2. **第 4 章有 18 处 `\TODO{}`**（`chap04_experiments.tex`，共 79 行）：三线表里是 `待填真实数据 / 待填 / 待测`。
3. **没有 `experiments/*.csv`**：所以 Gate 2 目前只能证明"没有自由漂浮的数字"，还不能证明"数字是对的"。
   真实实验跑完后，用 `inject_experiment_data.py` 把 CSV 注入三线表（带 `.meta.json` 硬件/重复次数/seed + SHA256）。
4. **Gate 4 未签署**：这是唯一必须由人完成的一步，任何自动化都不应替代。
5. **组会 PPT 14 页**：目标 15–20 页，还差 1–6 页。

## 6. 复现命令（逐条可粘贴）

```powershell
# 0. 环境自检：Python / PyMuPDF / XeLaTeX / 7 个门禁脚本是否就位
zhaw doctor

# 1. 门禁自身有没有被改坏（14 个对抗用例，零网络）
zhaw selftest

# 2. 引文取证（--offline 走本地 Crossref 缓存）
zhaw gate1 bupt_isac_workflow/thesis_project --offline

# 3. 数据溯源
zhaw gate2 bupt_isac_workflow/thesis_project --scaffold

# 4. 国标合规
zhaw gate3 bupt_isac_workflow/thesis_project --scaffold

# 5. 真人签字状态（送审前换成 --confirm-review）
zhaw gate4 bupt_isac_workflow/thesis_project --scaffold

# 6. 四门禁串跑 + 生成 gate_summary.json
zhaw check bupt_isac_workflow/thesis_project --scaffold --offline

# 7. 文献页码物理取证
zhaw grounding bupt_isac_workflow/survey/literature_comparison_matrix.md `
               --pdf-dir bupt_isac_workflow/literature

# 8. 重新编译（严格模式：overfull > 5pt 或未定义引用即失败）
zhaw compile bupt_isac_workflow/thesis_project
```

CI（`.github/workflows/quality-gates.yml`）在 Ubuntu / Windows / macOS 三平台 × Python 3.12 上重跑
`doctor → selftest → gate1..4 → check → grounding`，任何一条红即 PR 红。

## 7. 版本变更记录

| 日期 | 变更 |
| :--- | :--- |
| 2026-09（旧版） | 宣称 11 PDF / 16 维矩阵 0 FAIL / 32 条 Crossref OK —— 当时为真 |
| 2026-10-19 | 5 篇 PDF 被删 → grounding FAIL ×2；本报告重写为可复现格式 |
| 2026-10-19 | 从 `2758826` 恢复 11 篇 PDF → grounding 重新 PASS |
| 2026-10-19 | Gate 2 升级为 CSV 单元格级溯源；对抗用例 8 → 11 |
| 2026-10-20 | 接入撤稿检测 / sympy 符号验证 / SciencePlots；盲审产物排除与机构指纹清理；开题硬检查；对抗用例 11 → 14 |
| 2026-10-19 | 接入撤稿检测与 sympy 符号验证；SciencePlots 学术版式；22 个子命令全生命周期实测（见 `CAPABILITY_REPORT.md`） |
