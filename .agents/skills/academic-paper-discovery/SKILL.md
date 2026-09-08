---
name: academic-paper-discovery
description: >-
  前沿学术文献智能发掘助手。依据用户给出的研究主题、关键词或技术痛点，自主检索顶会/顶刊高引论文
  （对接 OpenAlex 与 arXiv，依据顶级期刊与会议学术声誉、引用速率与出版年份综合加权），自动下载开源 (OA) PDF 全文，
  并生成结构化分流清单（区分已就绪全文与需校园网补充的付费论文），为后续深度调研与综述提供权威文献池。
metadata:
  version: "1.0.0"
  domain: academic-research
  role: literature-retrieval-specialist
  scope: paper-discovery, citation-analysis, open-access-download
  triggers: 找论文, 查找前沿文献, 推荐顶会论文, 文献检索, paper search, find papers
---

# 前沿学术文献智能发掘助手 (Academic Paper Discovery Assistant)

面向科研人员与研究生，用于在进入新课题时自动检索高价值、高影响力、前沿学术文献。
解决传统手动在 Google Scholar / DBLP 翻找效率低、无法批量下载开源全文、缺乏影响力统一打分等痛点。

---

## 核心功能与工作流

1. **多源开放学术 API 聚合**：
   - 聚合 **OpenAlex** (2.5亿+学术条目、包含引用数、DOI、期刊分类、OA链接)；
   - 聚合 **arXiv API** (覆盖近 1-2 年最新预印本与跨学科分类)。
2. **多维学术影响力打分算法**：
   $$\text{Score} = 0.40 \cdot \text{VenuePrestige} + 0.35 \cdot \log_{2.5}(\text{Citations} + 1) + 0.25 \cdot \text{Recency}$$
   - 自动加权通信/信号顶刊顶会（IEEE JSAC, TWC, TSP, COMST, TIT, ICC, GLOBECOM 等）与计算机顶刊顶会（CVPR, NeurIPS, ICML, ICLR, TPAMI, ISCA 等）。
3. **开源全文自动化抓取 (Open Access Downloader)**：
   - 对具有合法 OA 授权的论文，直接自动下载 PDF 到本地指定目录（如 `./literature/`）；
   - 下载器内置四重物理熔断（Fail-Closed 策略）：文件体积 < 40KB 拒收；缺 PyMuPDF 或页数 < 3 拒收；首页前 500 字符命中导航词拒收；首页文本与标题 NFKD 复合相似度（0.6 Token 覆盖率 + 0.4 局部窗口比对）< 0.50 拒收，坚决防止网页转储冒充论文本体。并在 `literature_manifest.json` 中留档 `pdf_verified` 状态。
4. **版权墙透明分流 (Paywall Triage)**：
   - 绝不伪造不存在的付费下载；
   - 针对 IEEE/Elsevier/Springer 等付费商业文献，生成清单并附带 DOI/官网直达链接，提示用户在校园网 VPN 下一键批量补齐。

---

## 环境前置条件

运行本技能检索与 PDF 落地页过滤下载工具链前，请确保安装依赖：

```bash
pip install -r requirements.txt
```

## 使用方法

直接在终端或对话中输入研究主题执行：

```bash
# 自动两级漏斗检索：广度池 50 篇生成 references_broad.bib，精读池 12 篇下载开源全文
python scripts/search_papers.py "semantic communications deep jscc" --dir "./literature" --broad-limit 50 --deep-limit 12

# 快速初筛模式（支持 --limit 别名）
python scripts/search_papers.py "diffusion model acceleration" --dir "./literature" --limit 15
```

执行后将自动生成：
- `./literature/`：已下载的 OA PDF 全文文件；
- `./literature/references_broad.bib`：GB/T 7714 规范的完整作者名与卷期页 BibTeX 数据库；
- `./literature/literature_manifest.json`：文献详细元数据；
- `./literature/reading_plan.md`：阅读与精读分流计划。

随后无缝移交至 `phd-literature-survey` 技能进行深度精读与依据校验。

---

> **四副本同步铁律**：本技能为多平台工作流资产。平台开发者在 `.agents/skills/` 对本技能源码或文档做任何改动后，必须运行 `python .agents/skills/sync_skills.py` 保持 Gemini/Codex/Claude 三大全局镜像区完全一致。
