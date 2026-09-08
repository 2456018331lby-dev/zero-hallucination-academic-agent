# 组会/开题文献汇报 PPT 模板 (Marp Presentation Template)

本模板提供符合 Marp 规范的学术汇报幻灯片代码。可在 VS Code 安装 Marp for VS Code 插件一键导出为 PPTX 或 PDF，也可直接用于投屏汇报。

---

```markdown
---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  section {
    font-family: 'Segoe UI', 'PingFang SC', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 22px;
    padding: 36px 48px;
    background-color: #f8fafc;
    color: #1e293b;
  }
  h1 {
    color: #0f172a;
    font-size: 38px;
    border-bottom: 2px solid #2563eb;
    padding-bottom: 8px;
    margin-bottom: 24px;
  }
  h2 {
    color: #1d4ed8;
    font-size: 28px;
    margin-bottom: 16px;
  }
  h3 {
    color: #334155;
    font-size: 24px;
  }
  table {
    font-size: 16px;
    width: 100%;
  }
  th {
    background-color: #e2e8f0;
    color: #0f172a;
  }
  .highlight {
    color: #2563eb;
    font-weight: bold;
  }
  footer {
    font-size: 13px;
    color: #64748b;
  }
---

<!-- _class: lead -->
# [研究方向名称]：文献调研与前沿综述
### 组会文献分享 / 博士课题开题准备

**汇报人**：博士研究生 · [姓名]  
**指导教师**：[导师姓名]  
**实验室**：[实验室/课题组名称]  
**日期**：2026年

---

## 汇报大纲 (Agenda)

1. **研究背景与问题定义** (Background & Motivation)
2. **领域发展脉络与演进** (Chronological Evolution)
3. **主流技术分类与体系** (Taxonomy & Paradigms)
4. **代表性前沿论文精读** (Deep Dive into Core Papers)
5. **横向对比与核心突破** (Comparative Analysis)
6. **未解难题与博士切入点** (Challenges & Proposed Topics)

---

## 1. 研究背景与核心科学问题

- **核心矛盾**：
  - 现有模型在处理 [特定输入] 时，由于 [理论/算力瓶颈]，导致 [关键缺陷]。
- **为什么该问题至关重要**：
  - **理论层面**：关乎 [表征空间紧致性 / 泛化下界保证 / 因果解耦]。
  - **工程层面**：直接制约了 [自动驾驶 / 具身智能 / 边缘实时推断] 的可靠落地。
- **典型失效模式**：
  - 传统 SOTA 方法在 [分布偏移/长尾噪声] 条件下性能大幅滑坡。

<!-- Note: 汇报时控制在 1.5 分钟内，迅速让导师和组内同学建立对该问题痛点的直观感知。 -->

---

## 2. 领域技术发展脉络 (Timeline)

- **第一阶段：传统启发式与浅层学习 (2015-2018)**
  - 依赖人工先验特征，模型泛化空间受限，难以应对复杂多变输入。
- **第二阶段：经典深度神经网络主导 (2019-2022)**
  - CNN / 基础 Transformer 架构大幅提升表征上限，但计算开销与显存消耗急剧膨胀。
- **第三阶段：前沿生成式/自监督/稀疏注意力范式 (2023-至今)**
  - 走向扩散模型 (Diffusion) / 状态空间模型 (SSM) / 稀疏路由架构，兼顾扩展律 (Scaling) 与计算能效。

<!-- Note: 强调技术演进的动力：从关注“精度提升”逐步转向“泛化性、计算效率与理论可解释性”。 -->

---

## 3. 技术分类体系 (Methodology Taxonomy)

- **类别 1：[基于网络结构创新的轻量化范式]**
  - 代表作：Paper A (NeurIPS 2024), Paper B (ICML 2023)
  - 优势：端侧低延迟，推理极快；局限：对小目标细粒度表征能力受限。
- **类别 2：[基于自监督对比与跨域对齐范式]**
  - 代表作：Paper C (CVPR 2024), Paper D (ICLR 2023)
  - 优势：无监督数据利用率极高；局限：训练收敛周期较长，算力开销大。
- **类别 3：[基于因果解耦与不确定性估计范式]**
  - 代表作：Paper E (TPAMI 2024), Paper F (NeurIPS 2023)
  - 优势：分布外抗噪能力强；局限：数学建模复杂，优化超参数敏感。

---

## 4. 重点文献精读 1: [Paper Title A]

- **文献信息**：Zhang et al. (*NeurIPS 2024*, Stanford)
- **核心动机**：解决高分辨率图像生成中注意力矩阵的 $\mathcal{O}(N^2)$ 计算瓶颈。
- **核心方法设计**：
  - 提出 Exemplar 稀疏路由注意力机制，利用动态聚类 Token 降低冗余度。
  - 联合优化目标：$\mathcal{L}_{total} = \mathcal{L}_{diff} + \gamma \mathcal{L}_{sparse}$。
- **关键实验证据**：
  - ImageNet 256x256 上 FID 降至 2.15，吞吐提升 2.3 倍，显存降低 45%。
- **学术评价与局限**：
  - 优点：工程极其优美，消融实验无懈可击。
  - 短板：聚类敏感度较高；极小物体易丢失细节；*文献未说明学习率预热策略*。

<!-- Note: 先肯定其机理创新（为什么聪明），再从学术严谨性角度指出其隐藏的缺陷（为什么能被我们改进）。 -->

---

## 5. 重点文献精读 2: [Paper Title B]

- **文献信息**：Wang et al. (*ICML 2023*, MIT)
- **核心动机**：真实世界连续分布偏移导致表征空间漂移崩溃。
- **核心方法设计**：
  - 构造对称式跨域对比损失，引入正交约束投影矩阵消除特征纠缠。
- **关键实验证据**：
  - CIFAR-100-C 鲁棒误差率降至 31.4% (下降 3.8%)。
- **学术评价与局限**：
  - 优点：数学证明完备，无需目标域未标注数据。
  - 短板：预训练需 800 epochs，冷启动算力成本高昂。

---

## 6. 横向文献对比矩阵 (Comparative Summary)

| 代表方法 | 核心范式 | 参数量 / 算力 | 监督信号需求 | OOD 泛化 | 核心痛点 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Method A** | 稀疏路由 | 中等 (A100 可跑) | 纯自监督 | 中等 | 细粒度定位弱 |
| **Method B** | 正交解耦 | 庞大 (8 卡集群) | 弱监督 | 强 | 训练收敛缓慢 |
| **Method C** | 扩散隐空间 | 适中 | 条件多模态 | 极强 | 采样步数较多 |

---

## 7. 领域现状：已解决 vs 未解决

### 学术界已较好解决的问题 (Solved)
- 标准 Benchmark 上的经验平均精度已趋近饱和。
- 大规模基础预训练模型的主干特征提取能力成熟。

### 依然悬而未决的技术死结 (Unresolved)
- 极端分布外 (OOD) 与长尾场景下的抗虚假关联能力依然脆弱。
- 理论泛化误差界（Generalization Bound）缺乏紧致证明。
- 实时部署与长上下文推理的资源开销矛盾尚未根本化解。

---

## 8. 博士生选题建议与课题切入点

### 拟定博士课题选题：[选题暂定名称]
- **学术动机 (Why)**：
  - 现有 Method A 虽实现稀疏加速，但在边界模糊处存在表征坍塌；Method B 虽解耦鲁棒但代价高昂。
- **核心科学假设 (Hypothesis)**：
  - 引入因果约束引导稀疏路由分配，可在几乎不增加计算量的前提下抵御虚假特征干扰。
- **拟定技术路线 (How)**：
  1. 以开源 SOTA 为 Baseline 搭建统一测试基准。
  2. 构造因果引导的稀疏路由层，推导反事实对比目标。
  3. 系统设计严密消融实验与 OOD 压力测试。
- **近期落地规划**：
  - 2 周内完成 Baseline 复现；1 个月内跑通原型验证 (Proof-of-Concept)。

---

<!-- _class: lead -->
# Thank You!
### 请各位老师与同门批评指正！

**Q & A 讨论环节**
```
