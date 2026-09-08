# 全局数学符号与记号规范契约 (Global Mathematical Notation Ledger)

**适用范围**：北京大学 085402 通信工程硕士学位论文《面向高速时变信道的轻量化自适应信源信道联合语义通信机制研究》  
**规范依据**：GB/T 7713.1-2006、GB/T 3102.11-1993（物理科学和技术中使用的数学符号）  
**执行原则**：本协议为所有后续分块独立撰写小节（`chap03_sec01.tex` ~ `chap03_sec04.tex`）的**第一硬性输入契约**。各小节内部严禁擅自更换变量字母或量纲体系。

---

## 1. 字体排版与数学风格约定

| 类别 | 排版语法 | 示例 | 规范说明 |
| :--- | :--- | :--- | :--- |
| **标量 (Scalar)** | 斜体 `$x, \gamma, \sigma$` | $K, P, \sigma_n^2$ | 用于表示维数、功率、信噪比与噪声方差等单值标量 |
| **向量 (Vector)** | 粗斜体 `\bm{x}` | $\bm{x}, \bm{z}, \bm{m}, \bm{y}$ | 统一使用小写粗斜体表示连续/离散特征向量 |
| **矩阵 (Matrix)** | 粗体大写 `\bm{W}` | $\bm{W}_1, \bm{W}_2, \bm{H}$ | 统一使用大写粗斜体表示网络权重矩阵与信道矩阵 |
| **集合 (Set)** | 花体/黑板粗体 `\mathcal{S}` | $\mathcal{S}_{\text{QAM}}, \mathbb{R}, \mathbb{C}$ | 用于表示数字星座点集合、实数集与复数集 |
| **算子与期望** | 直体 `\mathbb{E}, \mathrm{Tr}` | $\mathbb{E}[\cdot], \nabla_{\bm{\theta}}, \|\cdot\|_2$ | 期望、微分算子与范数符号采用直体 |

---

## 2. 核心物理通信与系统变量字典

| 符号 | LaTeX 记号 | 维度 / 空间 | 物理量纲 | 物理含义与定义约束 |
| :---: | :--- | :--- | :---: | :--- |
| $\bm{x}$ | `\bm{x}` | $\mathbb{R}^{C \times H \times W}$ | 无量纲 (像素强度归一化) | 发送端输入的信源图像样本（$C$ 通道, 高 $H$, 宽 $W$） |
| $\bm{z}$ | `\bm{z}` | $\mathbb{R}^K$ | 潜在特征流形 | 深度编码器输出的未经信道功率归一化的连续特征向量 |
| $K$ | `$K$` | $\mathbb{Z}^+$ | 维数 | 经编码后的信道传输符号总维数 |
| $\rho$ | `\rho` | $\mathbb{R}^+$ | 维/像素 | 带宽压缩比 (Bandwidth Compression Ratio, CBR): $\rho = \frac{K}{C \cdot H \cdot W}$ |
| $P$ | `$P$` | $\mathbb{R}^+$ | 瓦特 (W) | 发送端允许的最大平均符号发射功率 (默认归一化为 $P=1$) |
| $\tilde{\bm{z}}$ | `\tilde{\bm{z}}` | $\mathbb{R}^K$ | 符号幅度 | 满足平均功率约束的物理信道发射符号：$\tilde{\bm{z}} = \sqrt{KP} \frac{\bm{z}}{\|\bm{z}\|_2}$ |
| $\bm{h}(t)$ | `\bm{h}(t)` | $\mathbb{C}^K$ | 信道增益 | 3GPP TDL-D 多径快时变信道冲激响应系数向量 |
| $f_d$ | `$f_d$` | $\mathbb{R}^+$ | 赫兹 (Hz) | 车辆高速移动诱发的最大多普勒频移扩展：$f_d = \frac{v \cdot f_c}{c}$ |
| $\bm{n}$ | `\bm{n}` | $\mathbb{C}^K$ | 噪声电压 | 加性复高斯白噪声：$\bm{n} \sim \mathcal{CN}(0, \sigma_n^2 \bm{I}_K)$ |
| $\sigma_n^2$ | `\sigma_n^2` | $\mathbb{R}^+$ | 瓦特 (W) | 信道高斯白噪声方差 |
| $\gamma$ | `\gamma` | $\mathbb{R}$ | 分贝 (dB) | 瞬时接收信噪比：$\gamma = 10 \log_{10} \frac{P}{\sigma_n^2}$ |
| $\bm{m}$ | `\bm{m}` | $[0, 1]^K$ | 门控掩码 | DCGU 门控子网络输出的连续通道剪枝掩码向量 |
| $\bm{z}_{\text{pruned}}$ | `\bm{z}_{\text{pruned}}` | $\mathbb{R}^K$ | 剪枝特征 | 经软松弛门控过滤后的潜在特征：$\bm{z}_{\text{pruned}} = \bm{z} \odot \bm{m}$ |
| $\bm{y}$ | `\bm{y}` | $\mathbb{C}^K$ | 接收信号 | 接收端射频前端采集的受污染信道符号向量：$\bm{y} = \bm{h} \odot \tilde{\bm{z}} + \bm{n}$ |
| $\hat{\bm{h}}$ | `\hat{\bm{h}}` | $\mathbb{C}^K$ | CSI 估计值 | 接收端经导频信道估计得到的信道状态信息 |
| $\hat{\bm{x}}$ | `\hat{\bm{x}}` | $\mathbb{R}^{C \times H \times W}$ | 重构信源 | 接收端深度语义解码器输出的重构图像矩阵 |

---

## 3. 神经网络参数与损失函数记号

| 符号 | LaTeX 记号 | 所属模块 | 物理含义 |
| :---: | :--- | :--- | :--- |
| $\bm{\theta}$ | `\bm{\theta}` | 发送端编码器 $f_{\bm{\theta}}$ | 包含多层非线性特征抽取卷积核与自注意力投影参数 |
| $\bm{\phi}$ | `\bm{\phi}` | 接收端解码器 $g_{\bm{\phi}}$ | 包含信道均衡估计补偿层与反卷积重构网络参数 |
| $\bm{W}_1, \bm{W}_2$ | `\bm{W}_1, \bm{W}_2` | 动态门控子网络 DCGU | 信噪比感知 MLP 的线性投影权重矩阵 |
| $\mathcal{L}_{\text{dist}}$ | `\mathcal{L}_{\text{dist}}` | 重构失真项 | 图像均方误差损失 (MSE): $\frac{1}{CHW} \|\bm{x} - \hat{\bm{x}}\|_2^2$ |
| $\mathcal{L}_{\text{sparse}}$ | `\mathcal{L}_{\text{sparse}}` | 稀疏性正则项 | 门控通道活跃度约束: $\frac{1}{K} \sum_{i=1}^K m_i$ |
| $\mathcal{L}_{\text{perceptual}}$ | `\mathcal{L}_{\text{perceptual}}` | 高阶感知损失 | 基于深度特征空间的 LPIPS 语义失真度量 |
| $\lambda_1, \lambda_2$ | `\lambda_1, \lambda_2` | 超参数平衡系数 | 稀疏惩罚项权重与感知损失加权标量 |

---

## 4. 跨章节引用接口规范
- **第一章引用接口**：引言中提出的“深衰落下信噪比失配”对应本表中的 $\gamma$ 动态扰动与门控 $\bm{m}$；
- **第三章推导接口**：第三章必须严格以此表变量为基准，展开公式推导，公式中出现的每一个新变量（如李雅普诺夫函数 $V(t)$）必须在正文中立即定义；
- **第四章实验接口**：第四章实验参数（如 $P=1$, $f_d=389\text{ Hz}$, $K=256$）必须严格与本表对应。
