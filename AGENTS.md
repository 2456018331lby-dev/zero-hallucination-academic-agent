# AGENTS.md — 给下一个 AI Agent 的使用说明书

> 这份文件是写给**接手这个仓库的 AI** 的，不是写给人的。人看 [README.md](README.md)。
> 读完这一页，你应该能在 10 分钟内跑通全流程，并且知道**哪些事绝对不要做**。

---

## 0. 三十秒定位

这个仓库不是「AI 帮你写论文」的工具，是**一套让论文里每个字都能被查的质量门禁**。

- 它**不生成内容**，它**验证内容**：数字必须能追到 CSV 单元格，引文必须能追到 Crossref 记录，页码必须能在本地 PDF 里打开看到。
- 它面向**中文学位论文**：GB/T 7713.1-2006 + GB/T 7714-2015，不是 IEEE/ACM 模板。
- 它的主入口是 `zhaw` 命令行（29 个子命令），**不要绕过它直接调 `scripts/` 里的脚本**——除非你在改门禁本身。

一句话：**别的工具负责写得快，这个仓库负责写不假。**

---

## 1. 先跑这三条（任何任务之前）

```powershell
cd <repo>
py -3.12 -m pip install -e ".[full]"   # 首次
zhaw doctor                            # 环境体检，应输出 RESULT: READY
zhaw selftest                          # 17 项对抗测试，应输出 17/17 PASSED
```

`selftest` 不过，说明**门禁本身坏了**，此时任何审计结论都不可信，先修门禁。

> 只用 `py -3.12`，不要用裸 `python`（本机 PATH 上的 `python` 是 WindowsApps 占位符）。

---

## 2. 仓库地图：哪些是资产，哪些是噪声

| 路径 | 是什么 | AI 该不该动 |
|---|---|---|
| `zhaw/` | **唯一入口**，29 子命令的 CLI 实现 | ✅ 要改就改这里 |
| `.agents/skills/` | **核心资产**，8 个技能 + 17 项对抗测试 | ✅ 门禁逻辑在这里 |
| `bupt_isac_workflow/` | 主力工程（北邮 085402 ISAC 双交付） | ⚠️ 只在用户要求时改内容 |
| `ris_thesis_workflow/` | 验收夹具（证明门禁可复用） | ⚠️ 同上 |
| `pku_thesis_workflow/` | 初号机 / 反面教材（曾整体编造数据） | ❌ 当历史标本，别「修好」它 |
| `newwork/` | 组会流水线 + MiMo Desktop 桥 + 39 篇论文样例 | ⚠️ 独立子系统，非核心 |
| `_demo/` | 演示与实测产物（已 gitignore） | ✅ 随便删 |
| `_attic/` | 历史噪声归档（Claude 汉化补丁、ADS 脚本等） | ❌ 不要恢复 |
| `docs/` | 使用文档 | ✅ 可补 |

**权威性排序**（哪个文档说的算）：

1. `zhaw` 命令的**实时输出** —— 永远最权威
2. [CAPABILITY_REPORT.md](CAPABILITY_REPORT.md) —— 最近一次全量实测
3. [PROJECT_AUDIT_REPORT.md](PROJECT_AUDIT_REPORT.md) —— 问题清单与修复状态
4. `bupt_isac_workflow/E2E_VERIFICATION_REPORT.md` —— 单工程端到端记录
5. `newwork/docs/` —— 用户本人写的科研手册（理念来源，非实现说明）

**冲突时以 1 为准，并顺手把 2–4 改对。**

---

## 3. 二十九个命令速查

### 环境与自检
```powershell
zhaw doctor                     # 环境体检
zhaw selftest                   # 17 项对抗测试
```

### 四道门禁（可单独跑）
```powershell
zhaw gate1 <工程> [--offline]        # 引文 vs Crossref（含撤稿检测）
zhaw gate2 <工程> [--scaffold]       # 数据溯源：数字必须在 experiments/*.csv 里
zhaw gate3 <工程> [--scaffold] [--min-bib 60]   # GB/T 合规
zhaw gate4 <工程> [--scaffold]       # 真人签字状态（AI 签不了）
zhaw check  <工程> [--scaffold] [--offline]     # 四门禁串跑，fail-fast
zhaw grounding <矩阵.md> --pdf-dir <PDF目录>     # 物理打开 PDF 核验页码
```

### 写作与产物
```powershell
zhaw new <目录> --kind thesis|proposal --title ... --author ...   # 从零脚手架
zhaw proposal <目录> [--check]      # 开题报告（六章配额）
zhaw figures <工程> [--caption ..] [--label ..]   # CSV → 学术图 + 表格片段
zhaw bib <工程> [--offline]         # Crossref 回填 .bib
zhaw math <工程>                    # 符号契约 + sympy 恒等式验证
zhaw compile <工程>                 # xelatex 编译并解析日志
zhaw docx <工程>                    # LaTeX → Word（pandoc 优先，无则降级）
```

### 汇报与交付
```powershell
zhaw seminar <矩阵.md> --topic "..." --out-dir <目录> --compile   # 组会 Beamer
zhaw defense <工程> --out-dir <目录> --compile                    # 答辩 deck + 讲稿 + Q&A
zhaw audit <工程> [--offline] [--scaffold]    # 可交付度打分（0–100）
zhaw progress <工程>                          # 字数/占位符/图表/文献进度
zhaw anonymize <工程> --out <目录> --force     # 盲审版（去姓名/学号/致谢）
zhaw archive <工程> --out-dir <目录> --name <名>  # 归档 zip + sha256 manifest
```

### 全流程剧本与周期汇报（从 0 写一篇论文用这组）
```powershell
zhaw flow                             # 列出 11 个场景剧本（lit/group/proposal/paper/submit/revision/defense/blind/midterm/weekly/archive）
zhaw flow show paper                  # 看某个剧本的逐步 SOP（哪些能自动、哪些必须人工）
zhaw flow run paper --project <工程> --out <目录>   # 生成该剧本的 runbook md
zhaw flow status paper --project <工程>             # 按产物是否存在算完成度 + 下一步
zhaw read <PDF目录> --out <目录> [--limit N] [--digest]   # 批量读 PDF → 阅读卡 + 矩阵 + gaps + 综述草稿
zhaw submit <工程> --venue ieee-tvt --out <目录>    # 投稿前 11 项机检 + cover letter + checklist
zhaw review <工程> [--venue ieee-tvt] --out <目录>  # 自审（MAJOR/MINOR）
zhaw rebuttal <审稿意见.md> --out <目录>            # 按 Reviewer 切分 → 逐条回复骨架
zhaw midterm <工程> --out <目录> [--target 30000]   # 中期检查报告（字数/文献/图件缺口）
zhaw weekly <工程> --out <目录> [--days 7]          # 周报（git 提交 + 字数增量 + 门禁状态快照）
```

> `zhaw flow` 只给 SOP 和清单，**不代写正文**；标 `[人工]` 的步骤永远不会被自动标完成。

> 三个等价写法：`zhaw xxx` = `py -3.12 -m zhaw xxx` = 直接调 `scripts/xxx.py`。
> **优先用第一种**，因为只有 CLI 会统一处理退出码与编码。

---

## 4. 五个典型任务剧本

### A. 用户说「我有一批 PDF，下周组会要汇报」

```powershell
# 1. 先确认矩阵里的页码是真的
zhaw grounding <矩阵.md> --pdf-dir <PDF目录>
#    0 FAIL 才能往下走；FAIL 说明矩阵在编页码

# 2. 生成 16 页 Beamer + 讲稿
zhaw seminar <矩阵.md> --topic "课题方向" --out-dir <目录> --compile
```
产出：`seminar_presentation.pdf`（约 16 页）、`seminar_notes.md`、`seminar_outline.md`。

### B. 用户说「帮我改论文第 4 章 / 检查这章有没有问题」

```powershell
zhaw check <工程> --offline      # 四门禁
zhaw math  <工程>                # 数学推导
zhaw audit <工程>                # 打分 + 缺口清单
zhaw progress <工程>             # 还差多少字、多少 TODO
```
**先看 audit 的缺口清单再动笔**。第 4 章的数字必须来自 `experiments/*.csv`，否则 Gate 2 必 FAIL。

### C. 用户说「要交盲审版了」

```powershell
zhaw anonymize <工程> --out <盲审目录> --force
zhaw compile   <盲审目录>                 # 必须重新编译！
```
**盲审版必须重新编译**——`anonymize` 会排除所有编译产物（PDF/DOCX 里含真实姓名），只保留 `figures/*.pdf`。
交付前读 `LEAKS.md`，里面列了机器管不了的 6 类人工项。

### D. 用户说「开个新课题 / 新的本科毕设」

```powershell
zhaw new <目录> --kind thesis --title "..." --author "..." --student-id "..." `
    --institute "..." --major "..." --direction "..." --advisor "..."
zhaw compile <目录>       # 应 0 错误
zhaw audit   <目录> --offline --scaffold
```
本科毕设只需改两处：模板换成本科版、`--min-bib 15`（硕士硬线是 60）。

### E. 用户说「老师给了一批文献，我要从头写一篇论文」

```powershell
zhaw flow show paper                      # 先看 11 步 SOP，知道哪步是人工
zhaw read <PDF目录> --out <目录> --digest  # 读文献 → 阅读卡/矩阵/gaps/综述草稿
zhaw new <目录> --kind thesis --title ... # 建工程
zhaw flow run paper --project <目录> --out <目录>   # 生成 runbook，按步执行
zhaw midterm <目录> --out <目录>           # 中期：字数/文献/图件缺口
zhaw weekly  <目录> --out <目录>           # 每周一次，记录增量
zhaw submit  <目录> --venue ieee-tvt --out <目录>  # 投稿前机检
zhaw review  <目录> --venue ieee-tvt --out <目录>  # 自审
```
**注意**：`flow` 只给清单和 SOP，正文、创新点、实验设计仍然只能人写；它保证的是「不漏步」和「每步有产物可查」。

---

## 5. 铁律：AI 绝对不能做的六件事

1. **不许凭参数记忆写 `author` 字段。** 必须 `zhaw bib` / Crossref 回填。这是本项目的第一铁律。
2. **不许自己签 Gate 4。** `.human_review.json` 有占位符检测，AI 自签会被拦截；签字只能由用户本人跑 `zhaw gate4 ... --confirm-review --reviewer <真名>`。
3. **不许手改 `.citation_cache.json`** 来「修」Gate 1。缓存是证据，改缓存=伪造证据。
4. **不许把 `--scaffold` 当成「让门禁通过」的开关。** 它的语义是「这是脚手架，我承认有占位符」，只能用于未完成的稿子；正式交付必须不带它跑。
5. **不许新增依赖而不查许可证。** `pymupdf` 是 AGPL-3.0（见 [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)），再引入 AGPL/GPL 库会污染整个仓库的 MIT 声明。
6. **不许在没有 `experiments/*.csv` 的情况下宣称「数据已核验」。** 没有 CSV，Gate 2 结构性无法 PASS——这是设计，不是 bug。

---

## 6. 产物长什么样（2026-10-19 实测）

| 命令 | 产物 | 实测规模 |
|---|---|---|
| `zhaw new` + `compile` | 完整学位论文脚手架 | 32 页 / 375.3 KB / 0 错误 |
| `zhaw seminar` | 组会 Beamer | 16 页 / 243 KB |
| `zhaw defense` | 答辩 deck + 讲稿 + Q&A | 约 20 页 / 82 KB |
| `zhaw anonymize` + `compile` | 盲审版 | 30 页 / 371 KB，姓名/学号/导师/致谢 **零命中** |
| `zhaw archive` | zip + manifest | 约 1 MB / 31 文件 |
| `zhaw audit` | 可交付度报告 md + json | 0–100 分 + 缺口清单 |
| `zhaw progress` | 进度表 | 汉字数 / TODO 处 / 图表数 / 文献数 |

---

## 7. 出问题怎么查

| 现象 | 先查什么 |
|---|---|
| `zhaw` 命令不存在 | `py -3.12 -m pip install -e .` 是否成功；用 `py -3.12 -m zhaw` 兜底 |
| 中文输出乱码 | 终端编码；CLI 已 `reconfigure(encoding="utf-8")`，若仍乱码用 `py -3.12 -m zhaw` |
| Gate 1 全 FAIL | 是否加了 `--offline` 而缓存为空；先联网跑一次填充缓存 |
| Gate 2 全 FAIL | 工程里有没有 `experiments/*.csv`；数字是否与 CSV 一致（容差 0.5%） |
| Gate 3 FAIL | `--min-bib` 阈值；GB/T 格式；参考文献是否 ≥ 阈值 |
| 编译失败但 PDF 存在 | LaTeX 常见「退出码非 0 但产出 PDF」；看 `main.log` 里的 Error 行 |
| 组会 deck 空白 | `seminar` 第一个参数是**矩阵 md 文件**，不是工程目录 |

---

## 8. 改代码时的约定

- Python 3.12，**只用标准库 + `pymupdf`**（+ 可选 `sympy`/`matplotlib`/`scienceplots`/`python-docx`）。
- 所有门禁返回 `{"status": "PASS"|"NOTICE"|"FAIL", "details": [...]}`，`NOTICE` 表示「脚手架模式下的已知缺口」，**不等于失败**。
- 新门禁必须配一条对抗用例写进 `.agents/skills/tests/test_gates.py`，并在 `run_selftest.py` 的 `TEST_SPECS` 注册——否则 CI 不会跑它。
- 改完跑：`zhaw selftest` → `zhaw check bupt_isac_workflow/thesis_project --scaffold --offline` → 三平台 CI。
- 提交前 `git status` 必须干净；`_demo/`、`_attic/`、`_ci_*/` 都已 gitignore。

---

## 9. 一句话交接

> 你要做的不是「帮用户写论文」，是「让用户写的东西经得起查」。
> 任何声称「已验证」的结论，都必须能落到一条命令的输出上。
