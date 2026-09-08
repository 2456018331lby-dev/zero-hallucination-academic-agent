---
name: citation-auditor
description: >-
  学术引文逐条审计门禁（Citation Verification Gate）。对 LaTeX 工程中的全部参考文献
  （.bib 条目与 thebibliography 环境中的 \bibitem）执行 DOI→CrossRef 官方元数据回填比对：
  核验作者姓集合、标题、年份、卷期页码与 DOI 归属。任何作者张冠李戴、卷期页错配、
  查无此文献的条目一律 FAIL。核心铁律：禁止大模型凭参数记忆撰写 author 字段，
  所有引文字段必须以 Crossref/OpenAlex API 回填结果为准。
  这是学位论文送审前的第一道强制门禁（P0），审计不通过则禁止编译送审版。
metadata:
  version: "1.0.0"
  domain: academic-integrity
  role: citation-forensics-auditor
  scope: citation-verification, doi-lookup, bibliography-audit, gbt7714
  triggers: 引文核验, 文献校验, 参考文献检查, citation check, verify references, doi audit
---

# 引文审计门禁 (Citation Auditor Gate)

针对学位论文与学术手稿参考文献层的**事实性审计**工具。解决大模型写作最危险的事故模式：
引文字段（作者、卷期页）凭记忆生成而非来自权威数据源，导致"虚构作者名""同 DOI 配错作者"
等学术不端级错误。

---

## 为什么必须有这道门（事故案例）

对 demo 工程 `references.bib` 的 6 条文献实测：
- `zhang2025d2`（D²-JSCC, JSAC 2025, DOI 10.1109/JSAC.2025.3531546）：真实作者为
  Jianhao Huang, Kai Yuan, Chuan Huang, Kaibin Huang；工程内写成虚构的
  "Zhang Tian-Hao, Wu Si-Rui, Chen Wei, Niyato, Shen Xuemin"，并杜撰了中文名"张天浩"。
- `kang2024semantic`（DOI 10.1109/TWC.2023.3349330）：真实作者为
  Zhonghao Lyu, Guangxu Zhu, Jie Xu；工程内写成了完全无关的七人名单。
- 其余 4 条存在姓名首字母伪造、卷期页错配等问题。
- **6/6 条目全部存在事实性错误**，而全部条目的 DOI/标题均可被 Crossref 正确解析。

结论：DOI 与标题往往是对的（来自检索），作者与卷期页是模型脑补的。因此本门禁的比对
策略是"以 DOI 为锚，回填官方元数据，逐字段比对"。

---

## 环境前置条件

运行本门禁工具链前，请确保安装平台依赖环境：

```bash
pip install -r requirements.txt
```

## 使用方法

```bash
# 审计整个工程（自动发现 *.bib 与 .tex 中的 thebibliography）
python scripts/check_citations.py <工程路径>

# 输出结构化报告并指定缓存
python scripts/check_citations.py <工程路径> --json citation_audit.json

# 离线模式（只使用上次缓存的 Crossref 响应，不出网）
python scripts/check_citations.py <工程路径> --offline

# 严格模式：WARN 也判失败（送审前建议开启）
python scripts/check_citations.py <工程路径> --strict
```

退出码：`0` 全部通过；`1` 存在 FAIL；`2` 严格模式下存在 WARN。
**在 run_quality_gates.py 编排中，本门禁 FAIL 时禁止执行送审版编译与 docx 导出。**

---

## 审计规则（字段级判定）

| 字段 | 比对方式 | 判级 |
| :--- | :--- | :--- |
| 标题 | 与 Crossref 标题做序列相似度（阈值 0.85） | < 0.85 → FAIL（疑似张冠李戴） |
| 作者姓集合 | 解析条目姓序列，与 Crossref 作者 family name 序列比对 | 首作者姓不一致或前缀错配 → FAIL |
| 年份 | 与 Crossref issued date 比对 | 不一致 → FAIL |
| 卷/期/页 | 与 Crossref volume/issue/page 规范化比对 | 有数据且不一致 → FAIL；单侧缺失 → WARN |
| DOI 归属 | 无 DOI 条目按标题检索 Crossref | 检索无命中 → FAIL（查无此文献） |
| 引用完整性 | `\cite` 键 vs 定义键集合 | 悬空引用/未引用条目 → WARN |
| 双源重复 | 同时存在 .bib 与 thebibliography | WARN（应单一事实源） |

---

## 工作流铁律（写作者必须遵守）

1. **禁止凭记忆写 author 字段**：任何新增引文，先由本工具检索 DOI，用回填的官方元数据
   生成条目；查不到的文献（含 arXiv 预印本）必须在条目旁加 `% UNVERIFIED` 注释，
   且默认按 FAIL 处理。
2. **单一事实源**：一篇论文只允许 `.bib + BibTeX` 或 `thebibliography` 之一；
   混用视为结构违规。
3. **送审前全量重审**：引文池任何增删改后必须重跑本门禁并归档 JSON 报告。

---

## 缓存与网络礼貌

- 请求头带 `mailto` 联系方式进入 Crossref polite pool；条目间 0.3s 限速；
- 响应按 DOI/标题缓存于工程 `.citation_cache.json`，重复审计零网络开销；
- `--offline` 模式仅消费缓存，供无网环境复跑。

---

> **四副本同步铁律**：本技能为多平台工作流资产。平台开发者在 `.agents/skills/` 对本技能源码或文档做任何改动后，必须运行 `python .agents/skills/sync_skills.py` 保持 Gemini/Codex/Claude 三大全局镜像区完全一致。
