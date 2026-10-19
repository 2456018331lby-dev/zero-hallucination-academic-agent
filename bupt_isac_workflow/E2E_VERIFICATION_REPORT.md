# 端到端验证报告 · bupt_isac_workflow

> **本报告记录的是当前工作区的实测结果，不是历史快照。**
> 历史快照（2026-09 旧版：32 页 / 8,547 汉字 / 18 处 `\TODO{}` / 16 篇文献）在当时那个
> commit 上是真的，但工程随后被完整补全，旧数字已全部作废。
> 判断「哪个说的算」的唯一依据是 `zhaw` 命令的实时输出。

---

## 1. 元数据

| 项目 | 值 |
|---|---|
| 工程路径 | `bupt_isac_workflow/thesis_project` |
| 课题 | 面向低空智联网的无人机通感一体化（ISAC）波形设计与感知辅助通信资源管理 |
| 学位 | 北京邮电大学 信息与通信工程学院 · 电子信息（`085402`）硕士 |
| 模板 | GB/T 7713.1-2006 + GB/T 7714-2015 |
| 验证时间 | 2026-10-19 |

---

## 2. 交付物实测

| 交付物 | 路径 | 实测 |
|---|---|---|
| 学位论文 PDF | `thesis_project/main.pdf` | **72 页 / 759.5 KB**（777,775 字节） |
| 论文正文 | `chapters/*.tex` | **30,038 汉字**，`\TODO{}` **0 处** |
| 组会 Beamer | `survey/seminar_presentation.pdf` | 14 页 16:9，含 `\note{}` 逐字讲稿 |
| 仿真数据 | `experiments/*.csv` | **8 个 CSV**（`sim_bupt.py` 产出） |
| 学术图件 | `figures/*.pdf` | **7 张**（`make_bupt_figures.py` 产出） |
| 参考文献 | `chapters/references.tex` | **62 条**手写 `\thebibliography`（不走 bibtex） |
| 文献池 | `literature/*.pdf` | 11 篇开源 OA PDF |
| 对比矩阵 | `survey/literature_comparison_matrix.md` | 8 行 × 16 列，接地门禁 **0 FAIL / 0 WARN** |
| 执行日志 | `logs/00_selftest.log` ~ `06_compile.log` | 7 份原始终端记录 |

---

## 3. 编译结果

```
zhaw compile bupt_isac_workflow/thesis_project
→ LaTeX Errors: 0
→ Severe Overfull: 0
→ Undefined Refs: 0
→ main.pdf: 72 页 / 759.5 KB
```

日志里仍有 **2 处 < 5pt 的 overfull**（`chap01` 与 `chap03` 各一处），属中文字距微调级别，
不影响版面；工具按 5pt 阈值不计为 severe。

---

## 4. 四道门禁

| 门禁 | 结果 | 证据 |
|---|---|---|
| Gate 1 引文取证 | **PASS** | 62/62 条命中 Crossref，`FAIL=0`，`WARN=0` |
| Gate 2 数据溯源 | **PASS** | 全部量化断言解析到 `experiments/*.csv` 单元格（容差 0.5%） |
| Gate 3 国标合规 | **PASS** | `0 ERROR(s), 0 WARNING(s)` |
| Gate 4 真人签署 | **FAIL（设计如此）** | `.human_review.json` 不存在；AI 不能代签 |

`zhaw check --scaffold --offline` → **Overall PASS，退出码 0**；
`zhaw check --offline`（不带 scaffold）→ **Overall FAIL，退出码 1**，失败点只有 Gate 4。

---

## 5. 可交付度评分

```
zhaw audit bupt_isac_workflow/thesis_project
→ 可交付度 82.5 / 100
```

| 维度 | 得分 | 依据 |
|---|:---:|---|
| 门禁通过率 | 75.0（权重 0.30） | 3/4 PASS，未过 Gate 4 |
| 正文完成度 | 100.0（0.25） | 30,038 汉字 / 目标 30,000 |
| 数据可溯源 | 100.0（0.15） | `experiments/*.csv` 存在且断言逐格命中 |
| 参考文献量 | 100.0（0.10） | 62 条 / 目标 60 |
| 真人签署 | 0.0（0.10） | 未签署 |
| 脚手架残留 | 100.0（0.10） | 0 处 `\TODO{}` |

**扣掉的 17.5 分全部落在「没人签字」这一项上**——这是本项目唯一无法自动化的环节。

---

## 6. 对抗自测

```
zhaw selftest → 17/17 PASS
```

17 项覆盖：编造 DOI、标题篡改、无 CSV 的量化断言、数字与 CSV 对不上、中文数字绕过、
页数超出被引 PDF、下载器熔断、Markdown 与 `\TODO` 残留、签字后章节被改、占位签名、
撤稿论文引用、sympy 反证恒等式、盲审版残留编译产物、页眉/元数据/正文残留校名、
审计门禁计数聚合错误、`--out` 污染 CWD、夹具工程被误读。

---

## 7. 诚实缺口清单

1. **Gate 4 未签署**：送审前必须由真人在终端执行
   `zhaw gate4 bupt_isac_workflow/thesis_project --confirm-review --reviewer <真名>`。
2. **SDR 基准未实现**：仿真用「ZF + 匹配感知波束 + 一维闭式功率分配 + MMSE 不动点」的
   可实现方案替代 SDR/SCA-BCD。正文已如实声明未实现 SDR 对比，**没有编造 SDR 数字**；
   根因是本机未安装 `cvxpy`，且 SDR 升维后变量规模达百万量级。
3. **`literature/` 的 11 篇 PDF 与正文被引的 62 篇不相交**：接地门禁证明的是
   「矩阵里那 11 篇确实写了那些话」，不等于「论文引的 62 篇都被读过」——两件事不要混为一谈。
4. **图件的物理合理性未逐图复核**：7 张图由 `make_bupt_figures.py` 从 CSV 生成，
   数据列可对应到具体 CSV；但趋势是否符合物理预期仍需人眼过一遍。
5. **30,038 汉字是「达到硕士常规下限」**，不是「写得足够好」。
   字数达标与学术质量是两件事，后者只能由导师与评阅人判断。

---

## 8. 复现命令

```powershell
cd <repo>

zhaw doctor
zhaw selftest

# 重跑仿真与图件（约 1-2 分钟）
py -3.12 bupt_isac_workflow/thesis_project/experiments/sim_bupt.py
py -3.12 bupt_isac_workflow/thesis_project/experiments/make_bupt_figures.py

zhaw check bupt_isac_workflow/thesis_project --scaffold --offline
zhaw compile bupt_isac_workflow/thesis_project
zhaw audit bupt_isac_workflow/thesis_project
```

---

## 9. 版本历史

| 版本 | 状态 | 说明 |
|---|---|---|
| 2026-09 初版 | **已作废** | 32 页 / 8,547 汉字 / 18 处 `\TODO{}` / 16 篇文献 / `experiments/` 缺失 |
| 2026-10-19 本版 | **当前** | 72 页 / 30,038 汉字 / 0 TODO / 62 条文献 / 8 CSV + 7 图 / 四门禁 3 PASS + Gate 4 FAIL / audit 82.5 |
