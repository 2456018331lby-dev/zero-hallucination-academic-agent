# 6G RIS 辅助无线通信与信道估计全局数学符号契约表 (Notation Contract)

为杜绝跨章节数学符号漂移、量纲冲突以及矩阵向量维度不匹配，根据工科博士学位论文标准规范，制定本工程全局数学符号统一契约。后续所有 LaTeX 章节推导必须严格对齐本表。

---

## 1. 标量与系统维度契约

| 符号 (Symbol) | 物理含义 (Physical Meaning) | 默认范围 / 典型取值 | 出现章节 |
| :--- | :--- | :--- | :--- |
| $M$ | 基站 (BS) 发射天线数 | $M \ge 1$（多天线，如 8, 16, 64） | 第 1, 2, 3, 4 章 |
| $N$ | 可重构智能表面 (RIS) 反射微元总数 | $N \gg 1$（大规模阵列，如 64, 128, 256） | 第 1, 2, 3, 4 章 |
| $K$ | 接收端单天线移动用户总数 | $K \ge 1$（多用户场景，如 2, 4, 8） | 第 1, 2, 3, 4 章 |
| $P_{\max}$ | 基站端最大发射总功率预算 | $P_{\max} > 0$（dBm 或 mW） | 第 3, 4 章 |
| $\sigma_k^2$ | 用户 $k$ 处接收机复高斯加性白噪声方差 | $\sigma_k^2 > 0$（通常归一化或依信噪比设定） | 第 3, 4 章 |
| $\gamma_k$ | 用户 $k$ 处的接收信号与干扰加噪声比 (SINR) | $\gamma_k \ge 0$ | 第 3, 4 章 |
| $\theta_n$ | RIS 第 $n$ 个反射单元的相移角 | $\theta_n \in [0, 2\pi)$ | 第 2, 3, 4 章 |
| $\beta_n$ | RIS 第 $n$ 个反射单元的幅度反射系数 | $\beta_n \in [0, 1]$（理想无源反射通常设为 1） | 第 2, 3, 4 章 |
| $\tau$ | 下行/上行信道估计导频序列时隙长度 | $\tau \ge K(N+1)$ | 第 3, 4 章 |
| $R_{\mathrm{sum}}$ | 多用户可达加权和速率 (Sum Rate) | 单位：$\mathrm{bps/Hz}$ | 第 3, 4 章 |

---

## 2. 向量与矩阵空间契约

| 符号 (Symbol) | 维度空间 (Dimension) | 物理含义与数学定义 |
| :--- | :--- | :--- |
| $\bm{x} \in \mathbb{C}^{M \times 1}$ | 向量 | 基站端多天线发射信号向量：$\bm{x} = \sum_{k=1}^K \bm{w}_k s_k$，满足 $\mathbb{E}[\|\bm{x}\|^2] \le P_{\max}$ |
| $s_k \in \mathbb{C}$ | 标量 | 发送给用户 $k$ 的归一化独立数据符号，满足 $\mathbb{E}[|s_k|^2]=1, \mathbb{E}[s_k s_j^*]=0 (k \neq j)$ |
| $\bm{w}_k \in \mathbb{C}^{M \times 1}$ | 向量 | 基站面向用户 $k$ 的有源发射波束赋形预编码向量 |
| $\bm{W} \in \mathbb{C}^{M \times K}$ | 矩阵 | 基站全用户发射预编码矩阵：$\bm{W} = [\bm{w}_1, \bm{w}_2, \dots, \bm{w}_K]$ |
| $\bm{h}_{d,k}^H \in \mathbb{C}^{1 \times M}$ | 向量（共轭转置） | 基站至用户 $k$ 的直连无线信道向量（Direct Link Channel） |
| $\bm{G} \in \mathbb{C}^{N \times M}$ | 矩阵 | 基站至可重构智能表面 (RIS) 的多径/视距信道响应矩阵（BS-to-RIS Link） |
| $\bm{h}_{r,k}^H \in \mathbb{C}^{1 \times N}$ | 向量（共轭转置） | RIS 至用户 $k$ 的反射反射信道向量（RIS-to-User Link） |
| $\bm{\Theta} \in \mathbb{C}^{N \times N}$ | 对角对阵 | RIS 相移调控对角矩阵：$\bm{\Theta} = \mathrm{diag}(\beta_1 e^{j\theta_1}, \dots, \beta_N e^{j\theta_N})$ |
| $\bm{v} \in \mathbb{C}^{N \times 1}$ | 向量 | RIS 无源反射波束向量：$\bm{v} = [v_1, \dots, v_N]^T = [\beta_1 e^{j\theta_1}, \dots, \beta_N e^{j\theta_N}]^T$，满足 $|v_n| \le 1$ |
| $\bm{H}_{\mathrm{casc},k} \in \mathbb{C}^{N \times M}$ | 矩阵 | 基站通过 RIS 经过反射到达用户 $k$ 的级联信道矩阵：$\bm{H}_{\mathrm{casc},k} = \mathrm{diag}(\bm{h}_{r,k}^H) \bm{G}$ |
| $\bm{n} \in \mathbb{C}^{K \times 1}$ | 向量 | 多用户端独立同分布复高斯白噪声：$n_k \sim \mathcal{CN}(0, \sigma_k^2)$ |
| $\bm{\Phi} \in \mathbb{C}^{\tau \times N}$ | 矩阵 | 信道估计阶段 RIS 导频反射相移图案设计矩阵（DFT 或哈达玛正交码本） |

---

## 3. 数学定理与算法符号契约

1. **等效复合信道向量**：
   $$\bm{h}_k^H(\bm{\Theta}) = \bm{h}_{d,k}^H + \bm{h}_{r,k}^H \bm{\Theta} \bm{G} = \bm{h}_{d,k}^H + \bm{v}^H \bm{H}_{\mathrm{casc},k}$$
2. **用户 $k$ 接收 SINR**：
   $$\gamma_k(\bm{W}, \bm{v}) = \frac{|\bm{h}_k^H(\bm{\Theta})\bm{w}_k|^2}{\sum_{j \neq k}^K |\bm{h}_k^H(\bm{\Theta})\bm{w}_j|^2 + \sigma_k^2}$$
3. **主被动联合优化目标函数**：
   $$\max_{\bm{W}, \bm{v}} \sum_{k=1}^K \log_2\left(1 + \gamma_k(\bm{W}, \bm{v})\right) \quad \text{s.t.} \quad \sum_{k=1}^K \|\bm{w}_k\|^2 \le P_{\max}, \quad |v_n| = 1, \forall n=1,\dots,N$$
4. **交替优化 (AO) 子问题解耦**：
   - 子问题 1（固定 $\bm{v}$ 求解 $\bm{W}$）：凸分式规划 (WMMSE / FP)；
   - 子问题 2（固定 $\bm{W}$ 求解 $\bm{v}$）：半正定松弛 (SDR) 或黎曼流形共轭梯度法 (Riem-CG)。
