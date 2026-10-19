# newwork — 主从协作科研工作流（主代理决策 · MiMo 执行）

一个**自包含**的工作区。它把两件事打包在一起：

1. **一条博士级文献调研流水线**：本地 PDF → ①15 字段文献阅读对比表 ②7 节方向调研报告 ③15 页学术风组会 PPT，全程可溯源、不编造。
2. **一套主从编排模式**：主代理（WorkBuddy / 你）负责决策、分解与最终交付物；**MiMo Desktop 作为子代理**承担规则明确、提示词清晰的重复性劳动（批量抽取、文件遍历、资料查找）。

设计目标是**可复现、可移植**：换一台机器、换一个人（或另一个 AI）接手，读完本文件即可运行。

> 🎓 **刚上研究生、只想知道"我该说什么话"？** 直接看 **`docs/06-playbook.md`（科研场景 AI 指挥手册）**——
> 里面按「组会汇报 / 开题调研 / 写论文 / 复现实验 / 日常杂活」给了可以直接复制粘贴的指令模板。

---

## 30 秒看懂分工

| 角色 | 负责 | 不负责 |
| :-- | :-- | :-- |
| **主代理（orchestrator）** | 目标定义、任务分解、所有判断与取舍、证据核对、最终产物 | 不做可由明确规则描述的重复劳动 |
| **MiMo Desktop（subagent）** | 规则明确的重复性劳动：批量抽取、逐文件遍历、格式化、资料查找 | 不做判断、不决定选题、不写最终结论 |

**判断一个子任务该不该派给 MiMo**：能否用一段不含歧义的规则写清楚「输入 → 输出」？能 → 派出去；不能 → 自己留着做。

---

## 目录结构

```
newwork/
├─ README.md                       ← 你在这里（总入口）
├─ docs/
│  ├─ 01-workflow.md               主从协作工作流：怎么把子任务派给 MiMo
│  ├─ 02-mimo-bridge-api.md        MiMo Desktop 本地 API 逆向笔记（路由/限制）
│  ├─ 03-literature-pipeline.md    文献调研三件套规范（15 字段 / 7 节 / 15 页 PPT）
│  ├─ 04-related-assets.md         ⚠️ 与既有 `.agents/skills/` 的重复与差异（务必读）
│  ├─ 05-ppt-animations.md         PPT 入场动画：SDK 限制、timing XML 后处理、坑
│  └─ 06-playbook.md           ★ 研究生科研场景 AI 指挥手册（组会/调研/写论文怎么下指令）
├─ skills/                         ★ 唯一源（source of truth）
│  ├─ phd-literature-review/       个人级 skill：本地文献 → 表 + 报告 + PPT
│  │  ├─ SKILL.md
│  │  ├─ scripts/extract_pdfs.py     抽取（--engine auto|academic|pypdf）
│  │  ├─ scripts/academic_extractor.py  双栏清洗（移植自 .agents/skills/，需 PyMuPDF）
│  │  ├─ scripts/verify_grounding.py    接地门禁（移植并增强：表模式 + 矩阵模式）
│  │  ├─ scripts/build_table.py      Markdown + XLSX 渲染
│  │  └─ references/ppt-storyboard.md
│  └─ mimo-desktop-bridge/         个人级 skill：驱动 MiMo Desktop
│     ├─ SKILL.md
│     ├─ mimo_bridge.py            纯标准库 CLI 桥接
│     └─ examples/                 逆向过程留下的探针脚本与记录
├─ scripts/
│  ├─ install_skills.py            把 skills/ 同步安装到 ~/.workbuddy/skills/
│  ├─ litpool_fetch.py         ★ 文献池入口：OpenAlex / HAL 检索 → 下载 OA PDF + 记录来源
│  ├─ orchestrate_mimo.py          主从编排入口：把 brief 派给 MiMo 并回收结果
│  ├─ inspect_anim.py              只读：导出每页 <p:timing> 动画结构（纯 zip 解析）
│  └─ retime_animations.py         改写 timing：click → after-previous 级联 + 收短时长
├─ libs/site-packages/             隔离依赖（pypdf、pymupdf、openpyxl）——可再生，见下文
└─ examples/
   ├─ bupt-isac/                   实例一：低空经济 ISAC（arXiv 池）
   └─ otfs-isac/                   实例二：OTFS-ISAC（非 arXiv 池 + MiMo 并行两批）
```

---

## 快速开始

> 下文用 `NN` 代表 Python 解释器路径、`NW` 代表本目录（`…/pidemo/newwork`）。

### 0）准备依赖（隔离安装，不污染全局）

```bash
python -m pip install --target "NW/libs/site-packages" pypdf openpyxl
python -m pip install --target "NW/libs/site-packages" pymupdf   # 推荐：双栏清洗 + 物理页码门禁
```

> `pymupdf` 不是必需，但装上它 `extract_pdfs.py --engine auto` 会自动切换到双栏清洗
> （`pypdf` 会把双栏论文的左右栏交错在一起，是最容易导致"读错"的条件）。

### 0b）手头还没有 PDF？先用 `litpool_fetch.py` 建一个文献池

流水线的入口脚本。它从 **OpenAlex**（`is_oa:true`）与 **HAL 检索 API** 发现开放获取论文，
下载 PDF 并写一份**来源清单**（`manifest.json`：每条记录 query / host / DOI / 排除原因）。

```bash
# 发现 + 下载；--append 可增量补充且续编号
$PY "NW/scripts/litpool_fetch.py" \
    --query "OTFS integrated sensing and communication" \
    --filter "title_and_abstract.search:OTFS OR delay-Doppler OR AFDM" \
    --out "$EX/input/literature" --min-year 2021 --limit 14 \
    --deny-host arxiv.org --deny-host www.mdpi.com

# 只看候选来源分布、不下载（用来判断哪些 host 可达）
$PY "NW/scripts/litpool_fetch.py" --query "..." --out "$EX/input/literature" --probe-hosts
```

必读的实务经验（都在 `examples/otfs-isac/TOPIC.md` §四有原样记录）：

- **`--filter` 很关键**：纯关键词检索会把卫星 / THz / 引力波等离题论文拖进来；
  加 `title_and_abstract.search:<关键词>` 强制切题。
- **HAL 的全文本下载已被 Anubis 机器人门挡住**（`/document` 返回 `Making sure you're not a bot!` HTML）。
  HAL 的**检索 API 仍可用**，所以 HAL 只当"发现源"，下载交给其它 host。
- 下载走 `urlopen` 时脚本已内置 **系统证书库**上下文（`_ssl_ctx()`），
  否则 `hal.science`、`orbilu.uni.lu` 等会报 `CERTIFICATE_VERIFY_FAILED`。
- **必须自己核对下载到的 PDF 与本条目是否同一篇**：`litpool_fetch.py` 只保证 URL 可达，
  不保证内容对得上。实例二里就抓到 1 篇标题与正文完全不符的（`[28]`），已排除。

### 1）安装/刷新 skill

```bash
python "NW/scripts/install_skills.py"              # 全部
python "NW/scripts/install_skills.py" --only phd-literature-review
python "NW/scripts/install_skills.py" --dry-run    # 只看会做什么
```

> `skills/` 是**唯一源**；`~/.workbuddy/skills/` 只是安装副本。
> 改了 skill 后重跑一次即可生效（新会话才加载）。

### 2）跑一遍文献调研流水线（以示例为例）

```bash
PY="C:/Users/24560/.workbuddy/binaries/python/versions/3.13.12/python.exe"
EX="NW/examples/bupt-isac"

# a) 抽取 PDF 全文（auto：有 PyMuPDF 就走双栏清洗，否则回落 pypdf）
$PY "NW/skills/phd-literature-review/scripts/extract_pdfs.py" \
    --src "$EX/input/literature" --out "$EX/work/pdftext" \
    --libs "NW/libs/site-packages" --engine auto

# b) 渲染对比表（Markdown + XLSX）
$PY "NW/skills/phd-literature-review/scripts/build_table.py" \
    --json "$EX/deliverables/literature_table.json" \
    --out-dir "$EX/deliverables" --libs "NW/libs/site-packages"

# c) 接地门禁（硬关卡：每条定量断言都必须能在原文找到；退出码 1 = 不通过）
$PY "NW/skills/phd-literature-review/scripts/verify_grounding.py" \
    --table-json "$EX/deliverables/literature_table.json" \
    --pdftext "$EX/work/pdftext"
```

### 3）把一个子任务派给 MiMo

```bash
$PY "NW/scripts/orchestrate_mimo.py" \
    --brief-file "$EX/briefs/mimo-metadata-audit.md" \
    --out "$EX/work/mimo_metadata_audit.md" \
    --workspace "C:/Users/24560/Desktop/study/pidemo" \
    --timeout 1800 --heartbeat 60
```

前提：**MiMo Desktop 正在运行**，且本工作区里已有一个会话（API 不能新建会话）。
脚本会自动挑选 `directory` 等于 `--workspace` 的会话；也可用 `--session` 显式指定。

> ⏱ **它很慢，但没卡死**：实测一次 11 文件的字段抽取耗时 **≈15 分钟**，中间有长达 **9 分钟**的无事件空档。
> `--heartbeat` 会定期打印 `[heartbeat] alive Ns / Ms` 供你判断存活；结束时脚本会报告
> `idle`（正常）/ `timeout`（可能被截断）/ `closed` / `error`。
> 详见 `docs/01-workflow.md` §四。

### 4）构建 PPT

见 `docs/03-literature-pipeline.md` 与 `skills/phd-literature-review/references/ppt-storyboard.md`
（用 `tencent-pptx` skill 的 `slidep` CLI；`--project` 必须传**绝对、正斜杠**路径）。

### 5）给做好的 PPT 加入场动画（可选）

```bash
$PY "NW/scripts/inspect_anim.py" "deck.pptx"              # 看当前每页动画
$PY "NW/scripts/retime_animations.py" "deck.pptx" --check  # 看会改成什么样
$PY "NW/scripts/retime_animations.py" "deck.pptx" --stagger 300 --fade-ms 600
```

> 本地 editor SDK 只能产出"点击触发 + 1000 ms 淡入"，**无法表达"上一动画之后"**，
> 所以必须先由 SDK 加效果、再用脚本改写 `<p:timing>`。
> 完整流程、XML 细节与踩坑见 **`docs/05-ppt-animations.md`**。

---

## 给"另一个 AI"的接手指南

1. **先读** `docs/01-workflow.md`（分工与编排）→ `docs/03-literature-pipeline.md`（产物规范）。
2. **硬约束（不可违反）**：所有内容必须来自用户本地文献；缺失写「文献未说明」；**绝不编造**题目/作者/期刊/实验数据。
3. **别相信仓库里任何现成的对比表**——示例里 `…/survey/literature_comparison_matrix.md`（在**原项目**里）数据是错的，必须从 PDF 重建。
4. **改 skill 请改 `skills/` 下的**，然后 `install_skills.py` 同步；不要直接改 `~/.workbuddy/skills/`。
5. **`libs/site-packages/` 是产物不是源码**，可随时删除并用第 0 步重建。

---

## 两个跑通的实例

| | 实例一 `examples/bupt-isac` | 实例二 `examples/otfs-isac` |
| :-- | :-- | :-- |
| 选题 | 低空经济场景下的通感一体化（ISAC） | 高机动低空场景下的时延-多普勒域（OTFS）通感一体化 |
| 与前一实例的关系 | — | 同一主线的**相邻分支**：把战场从 OFDM 家族换到 OTFS 家族 |
| 文献池 | 本地已有 11 篇（arXiv 预印本为主） | `litpool_fetch.py` 采得 **39 篇**（非 arXiv：IEEE/Springer/TechRxiv/机构库） |
| 深读 | 11 篇 | 12 篇（`[04][05][06][20][23][25][30][34][35][37][38][39]`） |
| MiMo 用法 | 单会话，1 批元数据审计 | **两会话并行**：batch1 / batch2 各 6 篇 |
| 接地门禁 | 通过 | **12/12 通过**（gate 抓到 1 处 DOI 只在登记库、不在正文，已改记 `venue_note`） |
| 产物 | 表 + 报告 + 15 页 PPT（含动画）+ 可行性简报 | 表 + 报告 + 15 页 PPT |
| 独有的方法论收获 | PPT timing XML 的改写法 | 文献池采集脚本、非 arXiv/多机构库版式的抽取、**并行派发 MiMo** |

实例二的对照价值：它检验了流水线在**换主题、换来源（无 arXiv）、换版式（多机构库作者稿）**时是否仍然成立——
结论是成立，但暴露了两个必须由人兜住的环节：**下载条目与正文的一致性**、以及**登记库 DOI 不等于正文可核对**。



- **✅ 与既有技能族的重复已合并（方案 A，2026-09-14）**：`phd-literature-review` 为主干，
  已把 `.agents/skills/phd-literature-survey` 的 `verify_grounding.py`（接地门禁）与
  `academic_extractor.py`（双栏清洗）**移植并增强**。`.agents/skills/` 下**未修改或删除任何文件**。
  触发词边界：文献调研/组会汇报/开题 → 用本工作区的 skill；只有需要 Markdown/Marp 幻灯片时才回落
  `phd-literature-survey`。详见 `docs/04-related-assets.md` §三。
- **MiMo 本地 API 不能新建/删除会话**，只能驱动 UI 里已存在的会话；提交内容会写入用户真实会话历史并消耗额度。详见 `docs/02-mimo-bridge-api.md`。
- MiMo 会话若不在「完全访问权限」下，遇到工具调用会**阻塞等待人工点击**，脚本会一直等到 timeout。派活前先确认权限。
- 定量结论必须能在 `work/pdftext/` 的原文里检索到，否则不得进入交付物。
