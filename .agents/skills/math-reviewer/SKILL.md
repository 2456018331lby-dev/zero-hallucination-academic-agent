---
name: math-reviewer
description: >-
  数学严谨度与理论形式化推导审查助手。针对工科/理科学位论文中的形式化建模、符号契约一致性、定理陈述与证明强度匹配、
  以及算法底层假设冲突（如 STE 有偏梯度 vs 无偏 SGD 假设）执行自动化机检与形式化推导复核。
metadata:
  version: "1.0.0"
  domain: academic-math-rigor
  role: theoretical-mathematics-auditor
  scope: math-verification, notation-contract, theorem-strength, assumption-consistency
  triggers: 检查数学推导, 符号表一致性, 定理证明检查, math review, notation check, verify proof
---

# 数学严谨度与理论证明审查助手 (Math Reviewer Skill)

针对学术学位论文与工科手稿中理论建模与数学证明的**严谨性与相容性机检工具**。
避免大模型在撰写数学章节时产生的经典软肋：
1. **定理陈述与证明强度错配**：陈述宣称“以概率 1 / 几乎必然收敛”，实际证明却仅推导了均方/期望上界 $\mathbb{E}[\|\nabla \mathcal{L}\|^2] \le \mathcal{O}(1/\sqrt{T})$；
2. **假设与组件冲突**：假定随机梯度无偏估计，却采用直通估计器（STE）进行离散不可导反向传播，造成理论自相矛盾；
3. **符号漂移**：跨章节私自定义同名不同义或不同名同义的张量记号，破坏全局符号契约。

---

## 核心审查维度

| 检查维度 | 判定逻辑 | 修复指引 |
|---|---|---|
| **符号契约对齐** | 核对正文中的张量符号是否在 `notation_table.md` 统一登记 | 统一至契约表，避免跨章节漂移 |
| **流水线唯一性** | 检查正文数据流是否严格遵循全局唯一 pipeline 定义 | 各章节仅引用该主流程，禁止私自重组 |
| **定理证明强度匹配** | 检测是否存在“以概率 1 收敛”而仅证明了期望收敛的脱节 | 引入 Robbins-Siegmund 超鞅引理，或修正定理为期望收敛 |
| **算法假设冲突** | 检测是否存在 STE 直通估计器与“无偏梯度估计”假设共存 | 改为有界偏差随机梯度假设（Bounded Gradient Bias） |

---

## 使用方法

```bash
# 审计当前 LaTeX 工程的数学推导与符号契约
python scripts/check_math.py <工程路径> [--notation notation_table.md]
```

---

> **四副本同步铁律**：本技能为多平台工作流资产。平台开发者在 `.agents/skills/` 对本技能源码或文档做任何改动后，必须运行 `python .agents/skills/sync_skills.py` 保持 Gemini/Codex/Claude 三大全局镜像区完全一致。
