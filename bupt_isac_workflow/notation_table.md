# 面向低空智联网的无人机通感一体化数学符号契约表 (Notation Contract)

## 1. 单源流水线定义 (Pipeline Definition)
基带波形生成 $\mathbf{X}$ -> 空地信道传输 $\mathbf{H}_c, \mathbf{H}_s$ -> 目标回波接收与匹配滤波 -> 联合波束赋形与轨迹交替优化 $\mathbf{W}, \mathbf{q}_u \to$ 性能评估与界限验证

## 2. 核心数学符号与物理含义规范

| 数学符号 | 符号定义与物理含义 | 维度 / 域 |
| :--- | :--- | :--- |
| $\mathbf{X}$ | 发射通感一体化预编码基带波形矩阵 | $\mathbb{C}^{N_t \times N_s}$ |
| $\mathbf{H}_c$ | 通信下行多输入多输出（MIMO）等效信道矩阵 | $\mathbb{C}^{K \times N_t}$ |
| $\mathbf{H}_s$ | 感知目标回波散射空间信道矩阵 | $\mathbb{C}^{N_r \times N_t}$ |
| $\mathrm{CRB}$ | 目标运动与位置参数估计的克拉美罗界矩阵 | $\mathbb{R}^{d \times d}$ |
| $\mathbf{J}$ | 费雪信息矩阵（Fisher Information Matrix, FIM） | $\mathbb{R}^{d \times d}$ |
| $\mathrm{SINR}_k$ | 第 $k$ 个通信用户的接收信干噪比 | $\mathbb{R}$ |
| $\sigma_c^2$ | 通信接收机加性复高斯白噪声方差 | $\mathbb{R}^+$ |
| $\sigma_s^2$ | 感知接收机加性复高斯白噪声方差 | $\mathbb{R}^+$ |
| $\mathbf{q}_u$ | 第 $u$ 架无人机的三维空间位置坐标向量 | $\mathbb{R}^{3 \times 1}$ |
| $V_{\max}$ | 无人机最大水平巡航线速度 | $\mathbb{R}^+$ |
| $P_{\max}$ | 系统发射总功率预算 | $\mathbb{R}^+$ |
| $\Delta f$ | OFDM 子载波间隔 | $\mathbb{R}^+$ |
| $M$ | OFDM 正交子载波总数 | $\mathbb{Z}^+$ |
| $N_t$ | 基站/无人机发射天线数 | $\mathbb{Z}^+$ |
| $N_r$ | 感知接收天线数 | $\mathbb{Z}^+$ |
| $K$ | 通信移动用户总数 | $\mathbb{Z}^+$ |
| $U$ | 协同无人机总数 | $\mathbb{Z}^+$ |
| $\mathbf{W}$ | 下行多用户通信预编码矩阵 | $\mathbb{C}^{N_t \times K}$ |
| $\mathbf{w}_s$ | 感知定向探测波束赋形向量 | $\mathbb{C}^{N_t \times 1}$ |
| $\alpha_k$ | 目标雷达散射截面积（RCS）及复反射系数 | $\mathbb{C}$ |
| $\theta_k$ | 目标相对于天线阵列的到达角（AoA） | $\mathbb{R}$ |
| $\tau_k$ | 目标信号往返传播时延 | $\mathbb{R}^+$ |
| $f_{D,k}$ | 目标运动引起的多普勒频移 | $\mathbb{R}$ |
| $R_{\mathrm{sum}}$ | 通信下行加权和速率 | $\mathbb{R}^+$ |
| $\Gamma_{\mathrm{th}}$ | 通信接收最低 SINR 门限要求 | $\mathbb{R}^+$ |
| $\mathbf{a}(\theta)$ | 均匀线阵（ULA）空间阵列导向矢量 | $\mathbb{C}^{N_t \times 1}$ |
| $\beta$ | 自由空间参考距离路径损耗系数 | $\mathbb{R}^+$ |
| $d_u$ | 无人机与目标之间的欧氏距离 | $\mathbb{R}^+$ |
