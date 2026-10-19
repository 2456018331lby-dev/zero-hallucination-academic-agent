# examples/otfs-isac — 实例二：高机动低空场景下的 OTFS 通感一体化

`newwork` 工作流的**第二个实例**。用途有两个：① 给用户的论文提供一条与既有 ISAC 工作**相邻但不同**的方向；
② 用一批全新数据检验流水线能否复现——特别是**换来源（无 arXiv）、换版式（多机构库作者稿）、并行派发 MiMo** 之后。

选题理由见 [`TOPIC.md`](./TOPIC.md)。

---

## 产物在哪

| 产物 | 路径 |
| :-- | :-- |
| 15 字段文献阅读对比表（Markdown） | `deliverables/文献阅读对比表格.md` |
| 同上（XLSX，15 列冻结表头） | `deliverables/文献阅读对比表格.xlsx` |
| 表的单一数据源 | `deliverables/literature_table.json` |
| 7 节方向调研报告 | `deliverables/方向调研报告.md` |
| 15 页组会 PPT（含 23 个入场动画） | `deliverables/OTFS-ISAC方向汇报/OTFS-ISAC方向汇报.pptx` |
| PPT 分镜与页面表 | `deliverables/OTFS-ISAC方向汇报/STORY.md` |

## 中间产物

| 内容 | 路径 |
| :-- | :-- |
| 文献池（39 篇 PDF） | `input/literature/` |
| 来源清单（含排除原因） | `input/manifest.json` |
| 抽取出的全文（39 个 `.txt`，双栏清洗） | `work/pdftext/` |
| MiMo 两批的输入切片 | `work/mimo_batch1/`、`work/mimo_batch2/` |
| MiMo 两批的回执 | `work/mimo_batch1_result.md`、`work/mimo_batch2_result.md` |
| MiMo 回执交叉核对记录 | `work/mimo_verification.md` |
| PPT 动画脚本与页信息导出 | `work/apply_animations.py`、`work/dump_pages.py` |
| PPT 无动画备份 | `work/backup/…pre-anim.pptx` |

---

## 复现步骤（照抄即可）

```bash
NW="…/pidemo/newwork"; EX="$NW/examples/otfs-isac"
PY="C:/Users/24560/.workbuddy/binaries/python/versions/3.13.12/python.exe"

# 1) 采池（可选；已采好，见 input/manifest.json）
$PY "$NW/scripts/litpool_fetch.py" \
    --query "OTFS integrated sensing and communication" \
    --filter "title_and_abstract.search:OTFS OR delay-Doppler OR AFDM" \
    --out "$EX/input/literature" --min-year 2021 --limit 14 \
    --deny-host arxiv.org --deny-host www.mdpi.com --deny-host hal.science

# 2) 抽取全文（双栏引擎）
$PY "$NW/skills/phd-literature-review/scripts/extract_pdfs.py" \
    --src "$EX/input/literature" --out "$EX/work/pdftext" \
    --libs "$NW/libs/site-packages" --engine academic

# 3) 渲染对比表
$PY "$NW/skills/phd-literature-review/scripts/build_table.py" \
    --json "$EX/deliverables/literature_table.json" --out-dir "$EX/deliverables" \
    --libs "$NW/libs/site-packages"

# 4) 接地门禁（硬关卡）
$PY "$NW/skills/phd-literature-review/scripts/verify_grounding.py" \
    --table-json "$EX/deliverables/literature_table.json" --pdftext "$EX/work/pdftext"
# -> 11/11 PASSED, exit 0

# 5) 并行派发 MiMo 两批（两个不同会话，互不干扰）
$PY "$NW/scripts/orchestrate_mimo.py" --brief-file "$EX/briefs/mimo-batch1.md" \
    --out "$EX/work/mimo_batch1_result.md" --workspace "…/pidemo" --timeout 3000
$PY "$NW/scripts/orchestrate_mimo.py" --brief-file "$EX/briefs/mimo-batch2.md" \
    --out "$EX/work/mimo_batch2_result.md" --session "<第二个会话 id>" --timeout 3000

# 6) PPT + 动画（见 docs/05-ppt-animations.md）
```

---

## 与实例一的差异（这次新踩出来的）

| 环节 | 实例一 | 实例二 | 结论 |
| :-- | :-- | :-- | :-- |
| 文献来源 | 现成 11 篇 arXiv 预印本 | `litpool_fetch.py` 采 39 篇，OpenAlex + HAL | 池子能自动建，但**必须人工核对条目与正文一致** |
| 版式 | arXiv 单栏模板 | IEEE/Springer/TechRxiv/机构库作者稿 | `--engine academic` 全部搞定；作者稿常**不带 DOI 页眉** |
| MiMo | 单会话 1 批 | **两会话 2 批并行** | 并行有效：batch2 仅 231 s 完成，与 batch1 重叠执行 |
| 门禁 | 一次通过 | 抓到 1 处：DOI 只在登记库、不在正文 | 登记库元数据 ≠ 正文可核对，需记 `venue_note` |
| 交叉核对 | 未发现表内错误 | **抓到表内 1 处作者张冠李戴**（[39]）＋**发现 [30] 整篇漏项** | MiMo 回执值得逐条对，它确实能查出人的笔误与漏项 |

### 三个必须记牢的坑

1. **`litpool_fetch.py` 只保证 URL 可达，不保证内容对得上。** 实例里 `[28]` 的 PDF 正文是一篇
   完全无关的经济学论文（OTFS/delay-Doppler 词频为 0）——这是**下载条目错配**，只能靠人抽查发现。
2. **HAL 全文本下载已被 Anubis 机器人门挡住**（`/document` 返回 `Making sure you're not a bot!` HTML）。
   HAL 的**检索 API 仍可用**，所以 HAL 只当发现源。manifest 里那批
   `reason = "download failed: not a PDF (got b'<!doctype html>…')"` 就是它。
3. **arXiv 不可达是最大的取样偏差**：OTFS-ISAC 恰是 arXiv 上的活跃方向，本池只能用
   IEEE/Springer/机构库替代。这个限制必须写进任何基于本池的结论里。
4. **"派发清单"与"最终表"会对不上。** 这次两批共 12 篇交给 MiMo，但组装 `literature_table.json`
   时漏掉了 `[30]`（表里只剩 11 篇），而报告与 PPT 的分类表却已引用 `[30]`——出现"表 11 篇、
   正文引 12 篇"的自相矛盾。是 MiMo 的 batch1 回执（含 `[30]`）触发复核才补回。
   **落盘前务必比对「派发清单的条目集合」与「最终表的条目集合」。**
