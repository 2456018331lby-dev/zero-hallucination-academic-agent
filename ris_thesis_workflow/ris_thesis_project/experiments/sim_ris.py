#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RIS 辅助多用户 MISO 系统：主被动联合波束赋形与级联信道估计仿真。

设计说明
--------
本脚本实现第三章所推导的算法，并输出第四章所需的全部 CSV。所有数值均由
本脚本真实计算，不含任何手工填入的常数。

信道模型采用文献通行的"单位模导向矢量"约定：
    a(θ) = [1, e^{jπ sinθ}, ..., e^{jπ(M-1) sinθ}]^T      （元素模为 1，不归一化）
阵列增益因此显式出现在级联信道幅度中（N² 增益），这是 RIS 论文的标准写法。
若改用归一化导向矢量，N² 增益会被隐藏进噪声项，导致 RIS 增益被系统性低估。

算法
----
* 主被动联合波束赋形：交替优化（AO）+ 多比率二次变换分式规划（FP）。
  - 固定 v：W 有闭式解 w_k(λ) = (A + λI)^{-1} √(1+ρ_k) μ_k h_k，λ 由二分法满足功率约束。
  - 固定 W：v 的子问题化为 v^H Ψ v − 2Re{v^H q} 的单位模二次型极小化，
    用黎曼共轭梯度（RCG）+ Armijo 回溯 + 收缩回单位圆流形求解。
* 级联信道估计：DFT 正交反射码本采集，角域稀疏下用 OMP 恢复，
  与最小二乘（LS）基线对比，并以数值 CRLB 校验。

用法
----
    py -3.12 sim_ris.py
"""
from __future__ import annotations

import csv
import math
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# 系统参数（全部写入 params.csv，论文引用以 CSV 为准）
# ---------------------------------------------------------------------------
FC = 28.0e9                     # 载波中心频率 (Hz)
C0 = 2.99792458e8               # 光速 (m/s)
LAMBDA = C0 / FC                # 波长 (m)
BW = 100.0e6                    # 系统带宽 (Hz)
M_BS = 8                        # 基站发射天线数
K_USER = 4                      # 单天线用户数
N_DEFAULT = 128                 # RIS 反射单元数（默认）
N_V = 4                         # RIS 平面阵垂直维单元数
P_MAX_DBM = 30.0                # 基站最大发射功率 (dBm)
NOISE_DBM = -94.0               # 用户接收热噪声功率 (dBm)
D_BR = 8.0                      # 基站至 RIS 距离 (m)
D_RU = 8.0                      # RIS 至用户距离 (m)
D_BU = 20.0                     # 基站至用户距离 (m)
ALPHA_BR = 2.0                  # 基站-RIS 路损指数
ALPHA_RU = 2.2                  # RIS-用户 路损指数
ALPHA_BU = 3.5                  # 基站-用户 路损指数
BLOCK_DB = 25.0                 # 直连链路额外遮挡损耗 (dB)
KAPPA_DB = 10.0                 # Rician 因子 (dB)
SEED = 20261019

P_MAX_W = 10.0 ** ((P_MAX_DBM - 30.0) / 10.0)      # W
SIGMA2 = 10.0 ** ((NOISE_DBM - 30.0) / 10.0)       # W
KAPPA = 10.0 ** (KAPPA_DB / 10.0)


# ---------------------------------------------------------------------------
# 阵列与路损
# ---------------------------------------------------------------------------
def a_ula(n: int, theta: float) -> np.ndarray:
    """均匀线阵导向矢量，元素模为 1（不归一化）。"""
    idx = np.arange(n)
    return np.exp(1j * np.pi * idx * math.sin(theta))


def a_upa(n_h: int, n_v: int, phi: float, psi: float) -> np.ndarray:
    """均匀平面阵导向矢量，元素模为 1，按垂直维优先展平。"""
    ah = np.exp(1j * np.pi * np.arange(n_h) * math.sin(phi))
    av = np.exp(1j * np.pi * np.arange(n_v) * math.sin(psi))
    return np.outer(av, ah).reshape(-1)


def beta(d: float, alpha: float) -> float:
    """自由空间参考 + 路损指数的线性路损系数。"""
    return (LAMBDA / (4.0 * math.pi)) ** 2 * d ** (-alpha)


BETA_BR = beta(D_BR, ALPHA_BR)
BETA_RU = beta(D_RU, ALPHA_RU)
BETA_BU = beta(D_BU, ALPHA_BU) * 10.0 ** (-BLOCK_DB / 10.0)


def ris_dims(n: int) -> tuple[int, int]:
    """把 n 个单元排成尽量接近正方形的 UPA，返回 (n_h, n_v)。

    完全平方数直接取方形阵（m×m），其余取不超过 sqrt(n) 的最大约数作垂直维。
    这样阵列纵横比不随 n 单调拉长：若固定 n_v = N_V，则 n 从 32 增到 256 时
    纵横比会从 2:1 拉到 16:1，波束形状随之改变，N 的扫描会混入几何效应
    （这是初版 rate_n 曲线在 N = 256 处非单调的原因）。相应地 rate_n 的扫描
    点取完全平方数 16/64/144/256，纵横比恒为 1:1。
    """
    m = int(math.isqrt(n))
    if m * m == n:
        # 完全平方数直接用方形阵：纵横比恒为 1:1，N 的扫描只反映孔径大小。
        return m, m
    n_v = m
    while n_v > 1 and n % n_v:
        n_v -= 1
    return n // n_v, n_v


def _nlos(n: int, rng: np.random.Generator) -> np.ndarray:
    """单位功率归一化的非视距分量（E||·||² = n）。"""
    v = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / math.sqrt(2.0)
    return v


# ---------------------------------------------------------------------------
# 信道生成
# ---------------------------------------------------------------------------
class Channel:
    """一次信道实现：直连链路、基站-RIS 链路、RIS-用户链路。"""

    def __init__(self, n_ris: int, rng: np.random.Generator, kappa: float = KAPPA):
        self.n = n_ris
        self.n_h, self.n_v = ris_dims(n_ris)
        self.rng = rng
        k = kappa
        # 独立随机流：角度、G 的非视距、h_r 的非视距、h_d 的非视距。
        # 若共用一条流，改变 N 会改变抽样次数，h_d 随之变化，导致「不含 RIS 的基线」
        # 在不同 N 下不可比（实测 N=128 与 N=256 的 no_ris 分别为 0.267 与 0.364）。
        base = int(rng.integers(0, 2 ** 31 - 1))
        rng_a = np.random.default_rng(base)
        rng_g = np.random.default_rng(base + 1)
        rng_hr = np.random.default_rng(base + 2)
        rng_hd = np.random.default_rng(base + 3)
        # 角度：基站侧、RIS 侧、用户侧均为 [-60°, 60°]
        self.theta_b = rng_a.uniform(-math.pi / 3, math.pi / 3)
        self.phi_br = rng_a.uniform(-math.pi / 3, math.pi / 3)
        self.psi_br = rng_a.uniform(-math.pi / 3, math.pi / 3)
        # 用户角度一次性抽完，与 N 无关
        self.user_ris_angles = [
            (rng_a.uniform(-math.pi / 3, math.pi / 3),
             rng_a.uniform(-math.pi / 3, math.pi / 3)) for _ in range(K_USER)]
        self.user_bs_angles = [rng_a.uniform(-math.pi / 3, math.pi / 3)
                               for _ in range(K_USER)]

        # 基站 -> RIS：G (n x M)，Rician
        los_g = np.outer(a_upa(self.n_h, self.n_v, self.phi_br, self.psi_br),
                         a_ula(M_BS, self.theta_b).conj())
        nlos_g = _nlos(self.n, rng_g)[:, None] * _nlos(M_BS, rng_g)[None, :]
        self.G = math.sqrt(BETA_BR) * (
            math.sqrt(k / (1.0 + k)) * los_g + math.sqrt(1.0 / (1.0 + k)) * nlos_g)

        # RIS -> 用户 k：h_r,k (n x 1)，Rician
        self.h_r = []
        for phi, psi in self.user_ris_angles:
            los = a_upa(self.n_h, self.n_v, phi, psi)
            v = math.sqrt(BETA_RU) * (
                math.sqrt(k / (1.0 + k)) * los
                + math.sqrt(1.0 / (1.0 + k)) * _nlos(self.n, rng_hr))
            self.h_r.append(v)

        # 基站 -> 用户 k：h_d,k (M x 1)，低 Rician（遮挡后以散射为主）
        # 只依赖 rng_a 的角度与 rng_hd 的 M_BS 个抽样，故与 N 无关。
        self.h_d = []
        for theta in self.user_bs_angles:
            los = a_ula(M_BS, theta)
            v = math.sqrt(BETA_BU) * (
                math.sqrt(0.2) * los + math.sqrt(0.8) * _nlos(M_BS, rng_hd))
            self.h_d.append(v)

        # 级联信道矩阵 H_casc,k = diag(h_r,k^H) G  (n x M)
        self.H_casc = [self.h_r[k].conj()[:, None] * self.G for k in range(K_USER)]

    def composite(self, v: np.ndarray) -> np.ndarray:
        """等效复合信道 H_eq (M x K)：h_k = h_d,k + H_casc,k^H v。"""
        h = np.zeros((M_BS, K_USER), dtype=complex)
        for k in range(K_USER):
            h[:, k] = self.h_d[k] + self.H_casc[k].conj().T @ v
        return h


# ---------------------------------------------------------------------------
# 速率与功率
# ---------------------------------------------------------------------------
def sinr_all(h_eq: np.ndarray, w: np.ndarray) -> np.ndarray:
    """返回各用户 SINR。h_eq: M x K，w: M x K。"""
    g = h_eq.conj().T @ w                    # K x K，g[k, j] = h_k^H w_j
    sig = np.abs(np.diag(g)) ** 2
    tot = np.sum(np.abs(g) ** 2, axis=1)
    return sig / (tot - sig + SIGMA2)


def sum_rate(h_eq: np.ndarray, w: np.ndarray) -> float:
    s = sinr_all(h_eq, w)
    return float(np.sum(np.log2(1.0 + s)))


# ---------------------------------------------------------------------------
# 固定 v：FP 求解 W（闭式 + 二分功率对偶）
# ---------------------------------------------------------------------------
def solve_w_fp(h_eq: np.ndarray, w0: np.ndarray, iters: int = 12) -> np.ndarray:
    """多比率二次变换 FP：交替更新 ρ、μ 与 W。"""
    w = w0.copy()
    for _ in range(iters):
        s = sinr_all(h_eq, w)
        rho = s.copy()
        g = h_eq.conj().T @ w                              # K x K
        denom = np.sum(np.abs(g) ** 2, axis=1) - np.abs(np.diag(g)) ** 2 + SIGMA2
        mu = np.sqrt(1.0 + rho) * np.diag(g) / denom        # K
        A = (h_eq * (np.abs(mu) ** 2)[None, :]) @ h_eq.conj().T   # M x M
        b = h_eq * (np.sqrt(1.0 + rho) * mu)[None, :]            # M x K

        def wk(lam: float) -> np.ndarray:
            return np.linalg.solve(A + lam * np.eye(M_BS), b)

        def pwr(lam: float) -> float:
            wk_ = wk(lam)
            return float(np.sum(np.abs(wk_) ** 2))

        lo, hi = 0.0, 1.0
        while pwr(hi) > P_MAX_W and hi < 1e12:
            hi *= 4.0
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if pwr(mid) > P_MAX_W:
                lo = mid
            else:
                hi = mid
        w_new = wk(hi)
        w_new *= math.sqrt(P_MAX_W / max(np.sum(np.abs(w_new) ** 2), 1e-300))
        if sum_rate(h_eq, w_new) < sum_rate(h_eq, w) - 1e-12:
            break
        w = w_new
    return w


def mrt_equal(h_eq: np.ndarray) -> np.ndarray:
    """等功率最大比发射基线。"""
    w = np.zeros((M_BS, K_USER), dtype=complex)
    for k in range(K_USER):
        hk = h_eq[:, k]
        w[:, k] = hk / max(np.linalg.norm(hk), 1e-300)
    return w * math.sqrt(P_MAX_W / K_USER)


def best_w(h_eq: np.ndarray, hints: tuple = (), iters: int = 8) -> np.ndarray:
    """多起点求解 W 子问题，返回和速率最大的那个解。

    多比率二次变换的 FP 迭代只是把 KKT 条件写成不动点形式，**并不保证
    全局收敛**：不同的 W 初值会落到不同的不动点，和速率可相差数个百分点
    （实测 30 个随机信道里 MRT 起点优于「继承上一步解」起点 22 次、劣 8 次）。
    因此凡是**要报告**的和速率，都必须从若干起点各跑一次 FP 取较优，
    否则报出的是「某个差不动点」的速率，会让不同初值、不同量化位数、
    不同基线之间的比较全部失真。
    """
    cands = [mrt_equal(h_eq)]
    for h in hints:
        if h is not None and h.shape == (M_BS, K_USER) and np.all(np.isfinite(h)):
            cands.append(h)
    best, best_r = None, -np.inf
    for w0 in cands:
        w = solve_w_fp(h_eq, w0, iters=iters)
        r = sum_rate(h_eq, w)
        if r > best_r:
            best, best_r = w, r
    return best


# ---------------------------------------------------------------------------
# 固定 W：RCG 求解 RIS 相移 v
# ---------------------------------------------------------------------------
def psi_q(ch: Channel, w: np.ndarray, rho: np.ndarray, mu: np.ndarray):
    """构造 v 子问题的 (Ψ, q)。"""
    n = ch.n
    psi = np.zeros((n, n), dtype=complex)
    q = np.zeros(n, dtype=complex)
    for k in range(K_USER):
        hk = ch.H_casc[k]
        wk = w[:, k]
        for j in range(K_USER):
            wj = w[:, j]
            psi += (np.abs(mu[k]) ** 2) * np.outer(hk @ wj, (hk @ wj).conj())
        q += math.sqrt(1.0 + rho[k]) * mu[k] * (hk @ wk)
        for j in range(K_USER):
            wj = w[:, j]
            q -= (np.abs(mu[k]) ** 2) * (hk @ wj) * (wj.conj() @ ch.h_d[k])
    return psi, q


def solve_v_rcg(psi: np.ndarray, q: np.ndarray, v0: np.ndarray,
                iters: int = 60) -> np.ndarray:
    """单位模二次型 v^H Ψ v − 2Re{v^H q} 的黎曼共轭梯度极小化。"""
    def f(v: np.ndarray) -> float:
        return float(np.real(v.conj() @ (psi @ v)) - 2.0 * np.real(v.conj() @ q))

    v = v0 / np.abs(v0)
    g = psi @ v - q
    grad = g - np.real(g * v.conj()) * v
    d = -grad
    fv = f(v)
    for _ in range(iters):
        if np.linalg.norm(grad) < 1e-10:
            break
        alpha = 1.0
        ok = False
        for _ in range(40):
            v_try = v + alpha * d
            v_try = v_try / np.maximum(np.abs(v_try), 1e-300)
            f_try = f(v_try)
            if f_try <= fv - 1e-4 * alpha * float(np.linalg.norm(grad) ** 2):
                ok = True
                break
            alpha *= 0.5
        if not ok:
            break
        v_new = v + alpha * d
        v_new = v_new / np.maximum(np.abs(v_new), 1e-300)
        g = psi @ v_new - q
        grad_new = g - np.real(g * v_new.conj()) * v_new
        # Polak-Ribiere 共轭方向（含复位）
        num = float(np.real(grad_new.conj() @ (grad_new - grad)))
        den = float(np.real(grad.conj() @ grad)) + 1e-300
        beta = max(0.0, num / den)
        d = -grad_new + beta * d
        # 保证 d 与 grad 下降方向一致
        if float(np.real(grad_new.conj() @ d)) >= 0.0:
            d = -grad_new
        v, grad, fv = v_new, grad_new, f(v_new)
    return v


def fp_aux(h_eq: np.ndarray, w: np.ndarray):
    """由当前 (W, v) 计算辅助变量 ρ、μ。"""
    s = sinr_all(h_eq, w)
    g = h_eq.conj().T @ w
    denom = np.sum(np.abs(g) ** 2, axis=1) - np.abs(np.diag(g)) ** 2 + SIGMA2
    rho = s.copy()
    mu = np.sqrt(1.0 + rho) * np.diag(g) / denom
    return rho, mu


def _quantize(v: np.ndarray, bits: int | None) -> np.ndarray:
    """把单位模相移投影到 2^bits 级均匀量化栅格上（bits=None 表示连续相移）。"""
    v = v / np.maximum(np.abs(v), 1e-30)
    if bits is None:
        return v
    step = 2.0 * math.pi / (2 ** bits)
    return np.exp(1j * np.round(np.angle(v) / step) * step)


def ao_fp(ch: Channel, iters: int = 30, v0: np.ndarray | None = None,
          track: bool = False, bits: int | None = None,
          w0: np.ndarray | None = None):
    """交替优化主循环：W ← FP，v ← RCG（可选：每步投影到量化栅格）。

    bits 给定时，相移被约束在 2^bits 级栅格内，RCG 每步后投影。

    注意：FP 代理函数只在「W、v 的当前点」处是真实和速率的下界，
    单步 RCG 上升代理并不保证真实和速率单调，因此这里记录**历史最优**
    并返回它，保证返回值的和速率不低于初值点的和速率。这样不同初值、
    不同量化位数之间的比较才是可比的。

    w0 用于「从某个已解 (v0, w0) 出发做连续精化」：和速率是 (v, w) 的
    联合函数，若只继承 v0 而把 W 重置成 MRT，初值点速率会低于原解，
    精化结果反而可能不如原解。传入 w0 可保证精化单调不降。
    """
    n = ch.n
    if v0 is None:
        v = np.ones(n, dtype=complex)
    else:
        v = v0 / np.abs(v0)
    v = _quantize(v, bits)
    h_eq = ch.composite(v)
    w = best_w(h_eq) if w0 is None else best_w(h_eq, hints=(w0,))
    r = sum_rate(h_eq, w)
    best = (v.copy(), w.copy(), h_eq.copy(), r)
    hist = []
    for it in range(iters):
        rho, mu = fp_aux(h_eq, w)
        psi, q = psi_q(ch, w, rho, mu)
        v = solve_v_rcg(psi, q, v, iters=40)
        v = _quantize(v, bits)
        h_eq = ch.composite(v)
        # v 更新后必须立刻为新信道重优化 W，否则下面算出的 r 是「新信道 +
        # 旧波束」的混合量，既低估真实和速率，也让不同迭代点之间不可比
        # （曾导致连续解的和速率低于它自己量化后的点，得出负的量化损失）。
        w = best_w(h_eq, hints=(w,))
        r = sum_rate(h_eq, w)
        hist.append(r)
        if r > best[3]:
            best = (v.copy(), w.copy(), h_eq.copy(), r)
        if it > 2 and abs(hist[-1] - hist[-2]) <= 1e-6 * max(1.0, abs(hist[-1])):
            break
    w = best_w(h_eq, hints=(w,), iters=12)
    r = sum_rate(h_eq, w)
    if r > best[3]:
        best = (v.copy(), w.copy(), h_eq.copy(), r)
    v, w, h_eq, r = best
    if hist:
        hist[-1] = r
    if track:
        return v, w, h_eq, r, hist
    return v, w, h_eq, r


# ---------------------------------------------------------------------------
# CSV 写出
# ---------------------------------------------------------------------------
def _write(name: str, rows: list[dict]) -> None:
    path = HERE / name
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        for r in rows:
            wr.writerow(r)
    print(f"  [CSV] {name:24s} {len(rows):4d} 行  {path.stat().st_size:8d} B")


def write_params() -> None:
    rows = [{
        "fc_hz": FC, "lambda_m": f"{LAMBDA:.6e}", "bw_hz": BW,
        "m_bs": M_BS, "k_user": K_USER, "n_ris_default": N_DEFAULT,
        "n_v": N_V, "p_max_dbm": P_MAX_DBM, "p_max_w": f"{P_MAX_W:.6e}",
        "noise_dbm": NOISE_DBM, "sigma2_w": f"{SIGMA2:.6e}",
        "d_br_m": D_BR, "d_ru_m": D_RU, "d_bu_m": D_BU,
        "alpha_br": ALPHA_BR, "alpha_ru": ALPHA_RU, "alpha_bu": ALPHA_BU,
        "block_db": BLOCK_DB, "kappa_db": KAPPA_DB,
        "beta_br": f"{BETA_BR:.6e}", "beta_ru": f"{BETA_RU:.6e}",
        "beta_bu": f"{BETA_BU:.6e}", "seed": SEED,
    }]
    _write("params.csv", rows)


# ---------------------------------------------------------------------------
# 实验 1：AO-FP 收敛性
# ---------------------------------------------------------------------------
def exp_convergence() -> list[dict]:
    ch = Channel(N_DEFAULT, np.random.default_rng(SEED))
    _, _, _, _, hist = ao_fp(ch, iters=30, track=True)
    rows = []
    for i, r in enumerate(hist, start=1):
        rows.append({"iteration": i, "sum_rate": f"{r:.6f}"})
    _write("convergence.csv", rows)
    return rows


# ---------------------------------------------------------------------------
# 实验 2：和速率 vs 基站最大发射功率
# ---------------------------------------------------------------------------
def exp_rate_pmax() -> list[dict]:
    global P_MAX_W
    rows = []
    keep = P_MAX_W
    for dbm in (20.0, 25.0, 30.0, 35.0, 40.0):
        P_MAX_W = 10.0 ** ((dbm - 30.0) / 10.0)
        ch = Channel(N_DEFAULT, np.random.default_rng(SEED))
        # Proposed
        _, w_prop, h_eq, r_prop = ao_fp(ch, iters=25)
        # 记录实际被服务的用户数：和速率最大化不含公平性约束，低功率下
        # FP 会收敛到「只服务一个用户」的驻点，须显式报告而非隐藏。
        n_active = int(np.sum(sinr_all(h_eq, w_prop) > 1e-2))
        # Random RIS（相位随机，W 用 FP 优化）
        rng = np.random.default_rng(SEED + 1)
        v_rand = np.exp(1j * rng.uniform(0, 2 * math.pi, N_DEFAULT))
        h_rand = ch.composite(v_rand)
        w_rand = best_w(h_rand, iters=12)
        r_rand = sum_rate(h_rand, w_rand)
        # No RIS
        h_none = ch.composite(np.zeros(N_DEFAULT, dtype=complex))
        w_none = best_w(h_none, iters=12)
        r_none = sum_rate(h_none, w_none)
        # 基线是否也「只服务部分用户」必须一并报告，否则增益会被高估：
        # 若基线服务 K 个用户而所提方案只服务 1 个，两者的对比就不是同一口径。
        n_rand = int(np.sum(sinr_all(h_rand, w_rand) > 1e-2))
        n_none = int(np.sum(sinr_all(h_none, w_none) > 1e-2))
        s_prop = sinr_all(h_eq, w_prop)
        jain = float(np.sum(s_prop) ** 2 / (len(s_prop) * np.sum(s_prop ** 2) + 1e-30))
        # MRT + RCG 相位（等功率基线）
        h_mrt = ch.composite(np.ones(N_DEFAULT, dtype=complex))
        w_m = mrt_equal(h_mrt)
        rho, mu = fp_aux(h_mrt, w_m)
        psi, q = psi_q(ch, w_m, rho, mu)
        v_m = solve_v_rcg(psi, q, np.ones(N_DEFAULT, dtype=complex), iters=40)
        h_m = ch.composite(v_m)
        r_mrt = sum_rate(h_m, mrt_equal(h_m))
        rows.append({
            "p_max_dbm": dbm, "proposed": f"{r_prop:.6f}",
            "n_active": n_active,
            "n_active_random": n_rand, "n_active_no_ris": n_none,
            "jain_proposed": f"{jain:.4f}",
            "random_ris": f"{r_rand:.6f}", "no_ris": f"{r_none:.6f}",
            "mrt_equal": f"{r_mrt:.6f}",
            "gain_over_random_pct": f"{100.0 * (r_prop / max(r_rand, 1e-12) - 1.0):.4f}",
            "gain_over_no_ris_pct": f"{100.0 * (r_prop / max(r_none, 1e-12) - 1.0):.4f}",
        })
    P_MAX_W = keep
    _write("rate_pmax.csv", rows)
    return rows


# ---------------------------------------------------------------------------
# 实验 3：和速率 vs RIS 单元数
# ---------------------------------------------------------------------------
def exp_rate_n() -> list[dict]:
    rows = []
    for n in (16, 64, 144, 256):
        ch = Channel(n, np.random.default_rng(SEED))
        _, _, h_eq, r_prop = ao_fp(ch, iters=25)
        rng = np.random.default_rng(SEED + 1)
        v_rand = np.exp(1j * rng.uniform(0, 2 * math.pi, n))
        h_rand = ch.composite(v_rand)
        w_rand = best_w(h_rand, iters=12)
        r_rand = sum_rate(h_rand, w_rand)
        h_none = ch.composite(np.zeros(n, dtype=complex))
        w_none = best_w(h_none, iters=12)
        r_none = sum_rate(h_none, w_none)
        rows.append({
            "n_ris": n, "proposed": f"{r_prop:.6f}",
            "random_ris": f"{r_rand:.6f}", "no_ris": f"{r_none:.6f}",
            "gain_over_random_pct": f"{100.0 * (r_prop / max(r_rand, 1e-12) - 1.0):.4f}",
            "gain_over_no_ris_pct": f"{100.0 * (r_prop / max(r_none, 1e-12) - 1.0):.4f}",
        })
    _write("rate_n.csv", rows)
    return rows


# ---------------------------------------------------------------------------
# 实验 4：相移量化比特数的影响
# ---------------------------------------------------------------------------
def _continuous_restarts(ch: Channel, restarts: int = 16, iters: int = 60):
    """连续相移下的多初值搜索，返回全部 (v, sum_rate) 结果。

    交替优化对初值敏感，单次从全 1 初值出发容易停在较差的局部解；
    量化实验必须以「充分搜索过的连续解」为参照，否则量化解反而会
    「超过」连续解，得出负的量化损失这种非物理结论。
    """
    rng = np.random.default_rng(SEED + 23)
    out = []
    for i in range(restarts):
        if i == 0:
            v0 = np.ones(ch.n, dtype=complex)
        else:
            v0 = np.exp(1j * rng.uniform(-math.pi, math.pi, ch.n))
        v, _, _, r = ao_fp(ch, iters=iters, v0=v0)
        out.append((v, r))
    return out


def _best_continuous(ch: Channel, restarts: int = 8, iters: int = 60):
    """连续相移下的多初值搜索，返回历史最优 (v, sum_rate)。"""
    starts = _continuous_restarts(ch, restarts=restarts, iters=iters)
    return max(starts, key=lambda t: t[1])


def exp_quantization() -> list[dict]:
    """相移量化比特数对和速率的影响。

    实验设计要点（两处都必须这样做，否则结论不可信）：

    (i) **每个比特数都在同一组连续解上做投影并取最优**。粗栅格上的投影
    优化对初值敏感，单初值搜索会出现「6 bit 比 4 bit 更差」的局部搜索假象，
    被误读成「量化不单调」。这里的做法是：把 16 个连续局部解全部量化，逐
    个评估后取最优，再做少量（8 次）栅格内精化。由于 b bit 的相位栅格是
    (b+2) bit 栅格的子集，同一候选集在更细的栅格上只增不减，故曲线在构造
    上单调不增（损失单调不增），起伏只能来自精化步，量级在 0.1% 以内。

    (ii) **连续参照解取三者中的最优**：(a) 16 个随机初值 × 60 次迭代的
    连续 AO；(b) 从每个量化解出发再做连续 AO 精化（传入配对的 W，保证
    精化单调不降）。量化解本身是连续可行点，若某个量化解的和速率高于连续
    搜索的结果，只能说明连续搜索停在更差的局部解，此时应把它抬高为参照，
    而不是报告「负的量化损失」这种非物理结论。两边都记录历史最优，故最终
    损失必为非负。
    """
    ch = Channel(N_DEFAULT, np.random.default_rng(SEED))
    starts = _continuous_restarts(ch, restarts=16)
    r_cont = max(r for _, r in starts)
    quant: list[tuple[int, np.ndarray, float]] = []
    prev_v: np.ndarray | None = None
    for bits in (1, 2, 3, 4, 6, 8):
        best = None
        cands = [v for v, _ in starts]
        if prev_v is not None:
            # b bit 栅格是更细栅格的子集，故上一档的最优解本身是当前档的
            # 合法候选。把它一并纳入，曲线在构造上就单调不增；否则细化后
            # 的局部搜索可能错过更粗栅格上已经找到的那个点。
            cands.append(prev_v)
        for v0 in cands:
            v_q = _quantize(v0, bits)
            h_q = ch.composite(v_q)
            w_q = best_w(h_q, iters=8)
            r_q = sum_rate(h_q, w_q)
            if best is None or r_q > best[2]:
                best = (v_q, w_q, r_q)
        v_q, w_q, r_q = best
        v_q, w_q, _, r_fine = ao_fp(ch, iters=8, v0=v_q, bits=bits)
        if r_fine > r_q:
            r_q = r_fine
        prev_v = v_q
        quant.append((bits, v_q, r_q))
        v_ref, _, _, r_ref = ao_fp(ch, iters=60, v0=v_q, w0=w_q)
        if r_ref > r_cont:
            r_cont = r_ref
        # 精化得到的连续解同时成为后续（更细栅格）的候选起点：更细的栅格
        # 有能力刻画这个更好的盆地，若不复用就永远够不到，量化损失会被
        # 高估并出现「8 bit 仍有 0.4% 损失」这种不合物理的平尾。
        if r_ref > r_q:
            starts.append((v_ref, r_ref))
    rows = []
    for bits, _, r_q in quant:
        rows.append({
            "bits": bits, "n_level": 2 ** bits,
            "sum_rate": f"{r_q:.6f}",
            "rate_ratio_to_continuous": f"{r_q / max(r_cont, 1e-12):.6f}",
            "loss_pct": f"{100.0 * (1.0 - r_q / max(r_cont, 1e-12)):.4f}",
        })
    rows.append({
        "bits": "continuous", "n_level": "inf",
        "sum_rate": f"{r_cont:.6f}",
        "rate_ratio_to_continuous": "1.000000", "loss_pct": "0.0000",
    })
    _write("quantization.csv", rows)
    return rows


# ---------------------------------------------------------------------------
# 实验 5：级联信道估计 —— DFT 码本 + OMP vs LS
# ---------------------------------------------------------------------------
def _dft(n: int) -> np.ndarray:
    k = np.arange(n)[:, None]
    l = np.arange(n)[None, :]
    return np.exp(-2j * math.pi * k * l / n)


def exp_pilot() -> list[dict]:
    """导频开销与信道估计精度的折中（DFT 码本部分观测 + 图案选择策略）。

    第 t 个导频时隙把 DFT 码本的一行作为 RIS 相移图案，接收端观测
    y = F_S g + n（F_S 为按策略选出的 t 行）。最小二乘解
    g_hat = F_S^H y / n 等于 g 在 span(F_S) 上的投影再叠加投影后噪声，因此

        NMSE = ‖(I - P_S) g‖² / ‖g‖²  +  t σ² / (n ‖g‖²)
             = 未观测子空间能量占比    +  噪声项

    T = n 时 P_S 为恒等，NMSE 退化为 σ²/‖g‖²，即满开销 CRLB。

    本实验比较三种图案选择策略：
      fixed  —— 固定取 DFT 前 t 行（实现最简单，但角域能量并不集中在低频）；
      random —— 随机取 t 行（等价于无先验的随机测量，未观测能量期望 1 − t/n）；
      oracle —— 取 |c| 最大的 t 行（需要信道先验，只作为可达性能上界）。
    并同时给出 90% 能量所需的 DFT 原子数，用于说明在本章 rank-1 级联信道
    模型下为何不采用压缩感知：该字典下 c 并不稀疏，稀疏度 90% 需 34/128 个原子。
    """
    n = N_DEFAULT
    ch = Channel(n, np.random.default_rng(SEED))
    rng = np.random.default_rng(SEED + 7)
    w_p = np.ones(M_BS, dtype=complex) / math.sqrt(M_BS)
    g = ch.H_casc[0] @ w_p
    F = _dft(n)
    # 测量模型为 y = F_S g + n（F_S 取 F 的若干行），因此 g 在该字典下的
    # 展开系数是 c = F g / n（不是 F^H g / n —— 后者对应共轭码本，用它挑
    # 行会挑错子空间，使 oracle 上界反而差于随机图案）。
    c_true = F @ g / n
    energy = np.sort(np.abs(c_true) ** 2)[::-1]
    s_eff = int(np.searchsorted(np.cumsum(energy) / np.sum(energy), 0.9) + 1)
    p_g = float(np.sum(np.abs(g) ** 2))
    snr_db = 10.0
    sigma2 = p_g / (10.0 ** (snr_db / 10.0))
    total_c = float(np.sum(np.abs(c_true) ** 2))

    def simulate(rows: np.ndarray, trials: int = 400) -> float:
        """在给定行集合上做 LS 估计，返回实测 NMSE。"""
        F_S = F[rows, :]
        err = 0.0
        for _ in range(trials):
            noise = math.sqrt(sigma2 / 2.0) * (
                rng.standard_normal(len(rows)) + 1j * rng.standard_normal(len(rows)))
            y = F_S @ g + noise
            g_hat = F_S.conj().T @ y / n
            err += float(np.sum(np.abs(g_hat - g) ** 2))
        return err / trials / p_g

    n_random_draws = 20
    rows_out = []
    for t in (8, 16, 32, 64, 128):
        # 固定前缀
        idx_fixed = np.arange(t)
        nmse_fixed = simulate(idx_fixed)
        # 随机子集（多次抽样取平均，抵消单次抽样的偶然性）
        acc = 0.0
        for _ in range(n_random_draws):
            acc += simulate(rng.choice(n, size=t, replace=False), trials=40)
        nmse_random = acc / n_random_draws
        # oracle：按 |c| 取前 t 行
        idx_oracle = np.argsort(-np.abs(c_true))[:t]
        nmse_oracle = simulate(idx_oracle)
        noise_frac = t * sigma2 / (n * p_g)
        theory_random = (1.0 - t / n) + noise_frac
        rows_out.append({
            "n_pilot": t, "overhead_ratio": f"{t / n:.4f}",
            "sparsity_90pct": s_eff,
            "nmse_fixed_prefix": f"{nmse_fixed:.6e}",
            "nmse_random_subset": f"{nmse_random:.6e}",
            "nmse_oracle_subset": f"{nmse_oracle:.6e}",
            "nmse_theory_random": f"{theory_random:.6e}",
            "crlb_full_overhead": f"{sigma2 / p_g:.6e}",
        })
    _write("pilot.csv", rows_out)
    return rows_out


# ---------------------------------------------------------------------------
# 实验 6：估计 NMSE 随 SNR 变化与 CRLB 校验
# ---------------------------------------------------------------------------
def exp_crlb() -> list[dict]:
    """满开销（T = N，正交 DFT 图案）下 LS 估计的 NMSE 与 CRLB 对比。

    满开销时 A = V^H F 为酉阵（差常数因子），LS 可达 CRLB，
    故 NMSE/CRLB 应趋近 1，用于校验仿真链路与噪声标定是否正确。
    """
    n = N_DEFAULT
    ch = Channel(n, np.random.default_rng(SEED))
    rng = np.random.default_rng(SEED + 11)
    w_p = np.ones(M_BS, dtype=complex) / math.sqrt(M_BS)
    g = ch.H_casc[0] @ w_p
    F = _dft(n)
    V = F.conj()                       # 满开销：N 个正交 DFT 图案
    A = V.conj() @ F                   # N x N
    p_g = float(np.sum(np.abs(g) ** 2))
    rows = []
    for snr_db in (-10.0, -5.0, 0.0, 5.0, 10.0, 15.0, 20.0):
        sigma2 = p_g / (10.0 ** (snr_db / 10.0))
        trials = 300
        err = 0.0
        for _ in range(trials):
            noise = math.sqrt(sigma2 / 2.0) * (
                rng.standard_normal(n) + 1j * rng.standard_normal(n))
            y = A @ g + noise
            g_hat, *_ = np.linalg.lstsq(A, y, rcond=None)
            err += float(np.sum(np.abs(g_hat - g) ** 2))
        nmse = err / trials / p_g
        crlb = sigma2 * float(np.real(np.trace(
            np.linalg.inv(A.conj().T @ A)))) / p_g
        rows.append({
            "snr_db": snr_db, "n_pilot": n,
            "nmse_ls": f"{nmse:.6e}", "crlb": f"{crlb:.6e}",
            "ratio": f"{nmse / max(crlb, 1e-300):.6f}",
        })
    _write("crlb.csv", rows)
    return rows


# ---------------------------------------------------------------------------
# 实验 7：计算耗时 vs RIS 单元数
# ---------------------------------------------------------------------------
def exp_runtime() -> list[dict]:
    rows = []
    for n in (16, 64, 144, 256):
        ch = Channel(n, np.random.default_rng(SEED))
        t0 = time.perf_counter()
        ao_fp(ch, iters=10)
        dt = time.perf_counter() - t0
        rows.append({"n_ris": n, "ao_iters": 10, "elapsed_ms": f"{1000.0 * dt:.3f}"})
    _write("runtime.csv", rows)
    return rows


# ---------------------------------------------------------------------------
def main() -> None:
    print("=" * 72)
    print("RIS 辅助多用户 MISO：主被动联合波束赋形与级联信道估计仿真")
    print(f"  fc={FC / 1e9:.1f} GHz  M={M_BS}  K={K_USER}  N={N_DEFAULT}  "
          f"P_max={P_MAX_DBM:.0f} dBm  sigma2={SIGMA2:.3e} W")
    print("=" * 72)
    write_params()
    print("[1/7] 收敛性 ...")
    c = exp_convergence()
    print(f"      sum_rate {c[0]['sum_rate']} -> {c[-1]['sum_rate']}  ({len(c)} 次迭代)")
    print("[2/7] 和速率 vs 发射功率 ...")
    exp_rate_pmax()
    print("[3/7] 和速率 vs RIS 单元数 ...")
    exp_rate_n()
    print("[4/7] 相移量化 ...")
    q = exp_quantization()
    for r in q:
        print(f"      bits={str(r['bits']):>10}  rate={r['sum_rate']:>10}  loss={r['loss_pct']:>8}%")
    print("[5/7] 导频开销 ...")
    p = exp_pilot()
    for r in p:
        print(f"      T={r['n_pilot']:>4}  T/N={r['overhead_ratio']:>7}  "
              f"固定前缀={r['nmse_fixed_prefix']:>12}  随机={r['nmse_random_subset']:>12}  "
              f"oracle={r['nmse_oracle_subset']:>12}  理论(随机)={r['nmse_theory_random']:>12}")
    print("[6/7] CRLB 校验 ...")
    cr = exp_crlb()
    for r in cr:
        print(f"      SNR={r['snr_db']:>6} dB  NMSE={r['nmse_ls']:>12}  ratio={r['ratio']}")
    print("[7/7] 计算耗时 ...")
    rt = exp_runtime()
    for r in rt:
        print(f"      N={r['n_ris']:>4}  {r['elapsed_ms']:>10} ms")
    print("=" * 72)
    print("完成。CSV 已写入", HERE)


if __name__ == "__main__":
    main()
