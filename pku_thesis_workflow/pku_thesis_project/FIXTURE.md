# 夹具工程：故意保留缺陷的门禁回归靶子

**这个工程不是一篇待完成的学位论文，而是 `zhaw` 四道门禁的回归测试夹具（fixture）。**

它被刻意做成「看起来像论文、实际上一身病」的样子，用来验证门禁系统能不能抓住真实写作中最危险的那类问题。**低分是预期结果，不是待办事项**；把它的数据填满、分数刷高，等于把测试用例删掉了。

## 它故意保留了哪些缺陷

| 缺陷 | 位置 | 应该被谁抓住 | 抓住时的表现 |
| --- | --- | --- | --- |
| 编造的量化结论（无实验支撑） | `chapters/chap01_intro.tex:20`「提升高达 3.8dB」 | Gate 2 数据溯源 | `FAIL`：claim 无法在 `experiments/*.csv` 中找到对应单元格 |
| 完全没有实验目录 | 缺 `experiments/` | Gate 2 | `FAIL`：no experiments/*.csv exists |
| 第 4 章整章占位 | `chapters/chap04_experiments.tex` 22 处 `\TODO{}` | Gate 3 / audit | `\TODO{}` 残留计数 > 0 |
| 参考文献严重不足 | `references.bib` 6 条 | Gate 3 | `WARNING`：6 < 60 |
| 无人签署 | 缺 `.human_review.json` | Gate 4 | `FAIL`：需真人签名与章节哈希绑定 |
| 接地矩阵字段缺失 | `survey/` 矩阵 row 6 缺 `evidence` 字段 | Grounding | `FAIL`：missing 'evidence' field |

## 为什么保留它

1. **门禁的价值只能用「它抓住过什么」来证明。** 一个 100 分的工程证明不了门禁有用；一个 24 分的工程配上「为什么扣分」的清单才能。
2. **它是防回归的。** 任何一次修改 `check_citations.py` / `run_quality_gates.py` / `check_thesis_compliance.py`，都必须确认这些缺陷仍然被抓住；抓不住了就是门禁被改坏了。
3. **它是写作时的反面教材。** 研究生第一次写论文时最常犯的错，就是先编一个「提升 3.8dB」再去找实验凑——这个夹具把后果直接摆在眼前。

## 怎么用它

```bash
# 应该看到 Gate 2 FAIL（假数据）、Gate 3 FAIL（文献不足）、Gate 4 FAIL（未签）
py -3.12 -m zhaw audit pku_thesis_workflow/pku_thesis_project

# 脚手架模式下 Gate 2 会放行占位符，但假数据依然应该被抓住
py -3.12 -m zhaw check pku_thesis_workflow/pku_thesis_project --scaffold --offline
```

`zhaw audit` 检测到本文件后会在报告顶部打出夹具警告，并说明低分是预期结果。

## 真正的论文工程在哪

- `bupt_isac_workflow/thesis_project` —— 北邮 085402 通感一体化（主生产工程）
- `ris_thesis_workflow/ris_thesis_project` —— RIS 辅助通信（第二生产工程）

这两个工程才是应该被补全、被审计、被送审的对象。本夹具**不要**被填满。
