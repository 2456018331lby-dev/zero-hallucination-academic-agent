# 第三方依赖许可证清单 / Third-Party Licenses

本仓库**自身代码**采用 MIT 许可证（见 `LICENSE`）。
本文件列出运行时依赖与可选依赖的许可证，以及由此产生的分发义务。
清单中的版本号为实测安装版本（2026-10 校验），许可证取自 PyPI / GitHub 官方声明。

## 一、运行时必需依赖

| 依赖 | 版本 | 许可证 | 对本项目的实际影响 |
|---|---|---|---|
| `pymupdf` (PyMuPDF) | 1.28.2 | **AGPL-3.0-or-later** 或 Artifex 商业许可（双许可） | **重点**：见下方「AGPL 义务」 |

## 二、可选依赖（`pip install -e ".[full]"`）

| 依赖 | 版本 | 许可证 | 用途 |
|---|---|---|---|
| `python-docx` | ≥1.1.0 | MIT | LaTeX → Word 降级导出 |
| `matplotlib` | ≥3.8.0 | PSF-based (matplotlib license) | 学术曲线绘制 |
| `numpy` | ≥1.26.0 | BSD-3-Clause | 数值计算 |
| `scienceplots`（建议） | 2.2.2 | MIT | IEEE / Science 期刊版式（缺失时自动回退到内置 rcParams） |
| `sympy`（建议） | 1.14.0 | BSD-3-Clause | 数学门禁的符号恒等式验证（缺失时自动回退到正则检查） |

## 三、外部 CLI 工具（非 Python 依赖，独立进程调用）

| 工具 | 许可证 | 调用方式 | 是否传染 |
|---|---|---|---|
| `xelatex` (MiKTeX / TeX Live) | LPPL / 各发行版 | `subprocess` 独立进程 | 否 |
| `pandoc` | **GPL-2.0** | `subprocess` 独立进程 | **否**（进程隔离，不 import） |
| `git` | GPL-2.0 | `subprocess` 独立进程 | 否 |
| `marp-cli`（可选，PPT） | MIT | 独立进程 | 否 |

## 四、AGPL 义务（重要）

`pymupdf` 是 AGPL-3.0 与 Artifex 商业许可的双许可软件。它被本项目的
`academic_extractor.py`、`verify_grounding.py`、`export_to_word.py` 直接 import，
因此**本工具运行时构成 AGPL 意义上的「组合作品」**。据此：

1. **自己用、校内用、不对外分发**：无额外义务。这也是本项目的主要使用场景。
2. **对外分发**（发 wheel、打 exe、放 Docker 镜像给他人、SaaS 化）：
   - 要么整体以 **AGPL-3.0** 发布，并向使用者提供完整对应源码；
   - 要么向 **Artifex** 购买商业许可（https://artifex.com/licensing/）。
3. **仅分发本仓库源码、让用户自己 `pip install`**：本仓库代码仍是 MIT，
   依赖由用户自行安装并各自遵守其许可证——这是最省事的分发方式。

> 结论：**不要把 `pymupdf` 打进你自己的发布物里**。本仓库历史上
> `newwork/libs/` 曾 vendored 过 50.7 MB 依赖（已删除），删除的原因之一就是
> 避免无意中把 AGPL 代码随仓库一起分发。

## 五、明确不引入的依赖及原因

| 项目 | 许可证 | 不引入原因 |
|---|---|---|
| `hallucinator` | AGPL-3.0-or-later | Rust 二进制、无 pip 包，且 AGPL 传染 |
| `jackfiled/BUPTBachelorThesis` | GPL-3.0 | 模板会传染 |
| `Nerlci/BUPTBachelorThesis` | 无 LICENSE 文件 | 默认保留所有权利，不可用 |
| `MinerU` | Apache-2.0 + 附加条款 | 4 GB 模型 + 商业阈值条款 |
| `Lean 4` / `Rocq` | Apache-2.0 / LGPL-2.1 | 形式化成本以月计，学位论文不适用 |
| `DVC` / `MLflow` / `Sacred` / `Hydra` | Apache-2.0 / MIT | 体量远超需求，`compute_sha256()` 已够 |

## 六、本仓库内嵌的第三方数据

| 内容 | 许可证 | 位置 |
|---|---|---|
| GB/T 7714-2015 参考文献格式规则（人工重写实现） | 无（自行实现，非复制 CSL 文件） | `thesis-latex-writer/scripts/check_thesis_compliance.py` |
| 文献池 PDF（arXiv / 开放获取预印本，33 个文件） | 各自原始许可（arXiv 非独占分发许可等） | `*/literature*/` |

> 文献池 PDF 仅用于本地接地门禁（`zhaw grounding`）取证与人工阅读，
> 不属于本项目代码，也不改变本项目代码的许可证。若对外分发本仓库，
> 建议将 `*/literature*/` 从发布物中剔除（它们体积大且与工具能力无关）。

---

维护约定：新增任何 `dependencies` 或 `optional-dependencies` 时，必须同步更新本表；
CI 不检查许可证，靠 code review 保证。
