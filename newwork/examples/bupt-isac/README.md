# 示例 · 低空经济场景下的通感一体化（ISAC）

这是 `newwork` 工作流的一次**完整跑通记录**：以 11 篇本地 PDF 为唯一证据源，产出
「文献阅读对比表 + 方向调研报告 + 组会汇报 PPT」，并在中间环节把一份规则明确的
重复性劳动派给 **MiMo Desktop** 作为子代理执行。

## 输入

`input/literature/` —— 11 篇 PDF（2024 年 1 篇、2025 年 3 篇、2026 年 7 篇），
另有 `literature_manifest.json`、`reading_plan.md`、`references_broad.bib`。

> 这些文件**复制自**原项目 `…/pidemo/bupt_isac_workflow/literature/`（原项目未改动）。
> 精读池原有 12 篇，其中 1 篇因付费墙未下载到本地，故为 11 篇。

## 产出（`deliverables/`）

| 文件 | 说明 |
| :-- | :-- |
| `literature_table.json` | **唯一数据源**：11 篇 × 15 字段 + meta |
| `build_table.py` | 由 JSON 渲染出下面两个文件 |
| `文献阅读对比表格.md` | 4 张主题表 + 逐篇 15 字段卡片（≈54 KB） |
| `文献阅读对比表格.xlsx` | 15 列，冻结表头、自动换行 |
| `方向调研报告.md` | 7 节：概述 / 四阶段脉络 / 五类方法 / 8 篇代表文献 / 对比（5 已解决 vs 7 未解决）/ 5 挑战→5 切入点 / 总结 |
| `研一SCI可行性简报.md` | 面向「北邮研一通信工程学生发 SCI 三/二区」的可行性结论与路线图 |
| `ISAC方向汇报/ISAC方向汇报.pptx` | **15 页**学术风组会 PPT（含 `STORY.md` 叙事稿与 `slides/` 源文件） |

## 中间产物（`work/`）

| 文件 | 说明 |
| :-- | :-- |
| `pdftext/*.txt` | 11 篇 PDF 的全文抽取（`<<<PAGE n>>>` 分页） |
| `digest.md` / `evidence.md` | 精读阶段的摘录与证据台账 |
| `extract_pdfs.py` / `build_digest.py` / `build_evidence.py` | 生成上述文件的本例脚本 |
| `mimo_metadata_audit.md` | **MiMo 子代理回执**：元数据抽取表（11 行） |
| `mimo_audit_verification.md` | 主代理对 MiMo 回执的**逐条交叉核对结论**（44/44 一致） |
| `verify_mimo_audit.py` | 生成上表的核对脚本（三方比对） |

## 派给 MiMo 的子任务（已跑通）

- **任务**：从 11 个全文 `.txt` 中抽取「文件名 / arXiv 编号 / 年份 / 标题 / 页数」→ 一张 Markdown 表。
- **为什么派**：纯规则抽取、重复 11 次、无需任何判断 —— 典型的高 token、低智力劳动。
- **brief**：`briefs/mimo-metadata-audit.md`（自包含 + 绝对路径 + 格式锁死 + 明确禁止项）。
- **执行**：`scripts/orchestrate_mimo.py --brief-file … --out … --workspace …`
- **回执**：`work/mimo_metadata_audit.md` —— 11 行，格式完全合规，自带总计行。
- **核对**：`work/verify_mimo_audit.py` 三方比对（MiMo 回执 / `literature_table.json` / `pdftext` 页码真值）
  → `work/mimo_audit_verification.md`。
- **结论**：**44 / 44 项一致，0 不一致 → 采信。**

**实测时延**：总 **≈15 分钟**，其中有一段 **≈9 分钟**的无事件静默期（`16:48:56 → 16:57:38`）。
桥接脚本的 900s 超时先到，但 MiMo 内部已把任务标记 `done`，回执完整。
→ 教训已写回 `docs/01-workflow.md` §四：**加心跳、调大超时、超时后先读一次会话历史**。

## 关键数字（均可回溯 `work/pdftext/` 原文）

| 编号 | 结果 |
| :-- | :-- |
| [2] | 定位误差 −61.1% / −22.8% / −9.0%；速度误差 −59.9% / −29.1% / −12.0% |
| [8] | 跟踪阶段省约 25 dB 功率；引用的 5G-A 现网感知资源开销 10%–20% |
| [10] | RAA 成本低于 HBF 的 1% |
| [12] | LoS 主导区部分信道信息低约 10 dB |
| [7] | LAMBDA 在 5% 样本下达 PCK@16 = 0.8512 |

## 核心论点

低空 ISAC 的核心研究逻辑是一条**「三重折中求解链」**：感知精度 ⇌ 通信速率 ⇌ 系统开销。
领域当前最缺的不是新算法，而是**可比性**（感知指标互不统一 + 全链路无实测）——这正是博士生的切入点。

## 如何重跑

```bash
PY="<python>"; NW="<newwork>"; EX="$NW/examples/bupt-isac"

$PY "$NW/skills/phd-literature-review/scripts/extract_pdfs.py" \
    --src "$EX/input/literature" --out "$EX/work/pdftext" --libs "$NW/libs/site-packages" \
    --engine auto

$PY "$NW/skills/phd-literature-review/scripts/build_table.py" \
    --json "$EX/deliverables/literature_table.json" --out-dir "$EX/deliverables" \
    --libs "$NW/libs/site-packages"

# 接地门禁（硬关卡）：11/11 论文、96 条定量断言全部可在原文定位
$PY "$NW/skills/phd-literature-review/scripts/verify_grounding.py" \
    --table-json "$EX/deliverables/literature_table.json" --pdftext "$EX/work/pdftext"

$PY "$NW/scripts/orchestrate_mimo.py" \
    --brief-file "$EX/briefs/mimo-metadata-audit.md" \
    --out "$EX/work/mimo_metadata_audit.md" \
    --workspace "C:/Users/24560/Desktop/study/pidemo" \
    --timeout 1800 --heartbeat 60

# 核对 MiMo 回执
$PY "$EX/work/verify_mimo_audit.py"
```

## PPT 入场动画

`deliverables/ISAC方向汇报/ISAC方向汇报.pptx` 已加入克制型入场动画：**9 页 / 23 个效果**。

| 页面 | 效果 |
| :-- | :-- |
| P1 封面 | 淡入 ×3（主标题 / 副标题 / 落款） |
| P3、P6、P12 篇章扉页 | **缩放出现**（巨型数字）+ 淡入 ×2 |
| P9、P10、P11 代表文献页 | **缩放出现** ×2（两个大号 KPI 数字） |
| P13 对比总结 | 淡入 ×2（左右栏标题） |
| P15 总结 | 淡入 ×3（标题 / 链式说明 / 金句） |

其余密集正文页（目录、方向定位、三重矛盾、四阶段、五类方法、挑战页）**保持静态**，避免"每页都在动"的廉价感。
时序：**每页点 1 次**，其余效果自动级联（间隔 300 ms）；淡入 600 ms、缩放 500 ms。

```bash
EX="$NW/examples/bupt-isac/work"
PY="<python>"

# 复核落盘动画（纯 zip 解析，只读）
$PY "$NW/scripts/inspect_anim.py" "$NW/examples/bupt-isac/deliverables/ISAC方向汇报/ISAC方向汇报.pptx"

# 重新施加动画计划（内置幂等守卫：目标页已有动画会拒绝执行）
$PY "$EX/apply_animations.py" --file-id "<file_id>" --dry-run

# 回滚到无动画版本
cp "$EX/backup/ISAC方向汇报.pre-anim.pptx" \
   "$NW/examples/bupt-isac/deliverables/ISAC方向汇报/ISAC方向汇报.pptx"
```

原理与踩坑见 `docs/05-ppt-animations.md`。

## 纪律声明

本示例全部内容基于 `input/literature/` 下 11 篇本地 PDF 全文；凡原文未给出者标注「文献未说明」；
未引入任何池外文献的结论充当本池证据；未给出任何具体期刊名称、影响因子或分区数值。

**已通过接地门禁**：`verify_grounding.py --table-json` 核对 11/11 篇论文、96 条定量断言，
0 FAILURES、0 WARNINGS（标题可定位 / arXiv 号存在 / 每个数字都能在原文中找到）。
反向验证：注入假数字与假 arXiv 号会被拦下并返回退出码 1。
