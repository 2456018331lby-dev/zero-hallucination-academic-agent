# -*- coding: utf-8 -*-
"""低空 ISAC 论文仿真：CRB 验证 / Pareto 前沿 / 子载波与 PAPR / 收敛 / 轨迹。

本脚本生成论文第 4 章引用的全部数值（experiments/*.csv）。
运行：py -3.12 experiments/sim_bupt.py
"""
from __future__ import annotations

import csv
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RNG = np.random.default_rng(20261019)

# ---------------------------------------------------------------- 系统参数
FC_HZ = 28e9
BW_HZ = 100e6
DF_HZ = 120e3
M_SC = 1024
N_T = 32
N_R = 16
K = 4
U = 2
P_MAX_DBM = 35.0
P_MAX_W = 10.0 ** ((P_MAX_DBM - 30.0) / 10.0)
NOISE_DBM_TOTAL = -94.0          # 100 MHz 全带热噪声 (-174 dBm/Hz + 80 dB)
SIGMA2 = 10.0 ** ((NOISE_DBM_TOTAL - 30.0) / 10.0) / M_SC   # 单子载波噪声
V_MAX = 25.0
H_UAV = 100.0
D_MIN = 10.0
D_MAX = 3000.0
D_REF = 500.0
THETA_T = math.radians(25.0)
# |alpha|^2 @ D_REF：由雷达方程标定
#   P_r/P_t = G_t*G_r*lambda^2*RCS / ((4pi)^3 R^4)
#   = 32*32*(0.0107)^2*1 / (1984 * 500^4) ~= 9.5e-16
ALPHA2 = 9.5e-16
N_SYM = 16
RICE_K_DB = 10.0
# 边缘用户（d = D_MAX）在满功率单子载波下 SNR = 10 dB
EDGE_SNR_DB = 10.0
BETA_EDGE = 10.0 ** (EDGE_SNR_DB / 10.0) * SIGMA2 / P_MAX_W
GAMMAS_DB = [0.0, 2.0, 4.0, 6.0, 8.0, 10.0]


def db(x):
    return 10.0 * math.log10(x)


# ---------------------------------------------------------------- 阵列与 CRB
def ula(n, angle, spacing=0.5):
    idx = np.arange(n)
    return np.exp(1j * 2 * np.pi * spacing * idx * math.sin(angle)) / math.sqrt(n)


def ula_derivative(n, angle, spacing=0.5):
    idx = np.arange(n)
    return 1j * 2 * np.pi * spacing * idx * math.cos(angle) * ula(n, angle, spacing)


def perpendicular_energy(n, angle, spacing=0.5):
    a = ula(n, angle, spacing)
    da = ula_derivative(n, angle, spacing)
    proj = da - a * (a.conj() @ da)
    return float(np.real(proj.conj() @ proj))


def crb_theta(gain, n_r=N_R, theta=THETA_T, n_sym=N_SYM, sigma2=SIGMA2, alpha2=ALPHA2):
    """角度估计 CRB（未知复幅度 nuisance 已投影消除）。"""
    if gain <= 0:
        return float("inf")
    fisher = 2.0 * alpha2 * n_sym * perpendicular_energy(n_r, theta) / sigma2 * gain
    return 1.0 / fisher


def alpha2_at(distance):
    """双程路损：alpha^2(d) = alpha^2(D_REF) * (D_REF/d)^4。"""
    return ALPHA2 * (D_REF / max(distance, 1.0)) ** 4


def validate_crb(n_r, snr_db=20.0, trials=400, n_sym=32, theta=THETA_T):
    sigma2 = 1.0
    alpha2 = 10.0 ** (snr_db / 10.0) * sigma2
    alpha = math.sqrt(alpha2)
    gain = 1.0
    crb = 1.0 / (2.0 * alpha2 * n_sym * perpendicular_energy(n_r, theta) / sigma2 * gain)
    grid = np.linspace(theta - 0.02, theta + 0.02, 4001)
    b = np.array([ula(n_r, g) for g in grid])
    errs = np.empty(trials)
    rng = np.random.default_rng(1000 + int(n_r))
    for t in range(trials):
        s = math.sqrt(gain / 2.0) * (rng.standard_normal(n_sym)
                                     + 1j * rng.standard_normal(n_sym))
        n = math.sqrt(sigma2 / 2.0) * (rng.standard_normal((n_r, n_sym))
                                       + 1j * rng.standard_normal((n_r, n_sym)))
        y = alpha * np.outer(ula(n_r, theta), s) + n
        corr = np.abs(b.conj() @ (y @ s.conj()))
        errs[t] = grid[int(np.argmax(corr))] - theta
    return math.sqrt(crb), float(np.sqrt(np.mean(errs ** 2)))


# ---------------------------------------------------------------- 信道与波束
def comm_channels(rng, k=K, n_t=N_T):
    angles = np.sort(rng.uniform(-math.pi / 3, math.pi / 3, k))
    dist = rng.uniform(300.0, D_MAX, k)
    pathloss = BETA_EDGE * (D_MAX / dist) ** 2
    kappa = 10.0 ** (RICE_K_DB / 10.0)
    h = np.empty((k, n_t), dtype=complex)
    for i in range(k):
        los = ula(n_t, angles[i]).conj()  # 行向量信道 h_i = a(theta_i)^H，故 y = h x
        nlos = (rng.standard_normal(n_t) + 1j * rng.standard_normal(n_t)) / math.sqrt(2)
        nlos /= np.linalg.norm(nlos)
        h[i] = math.sqrt(pathloss[i]) * (math.sqrt(kappa / (kappa + 1)) * los
                                         + math.sqrt(1.0 / (kappa + 1)) * nlos)
    return h, angles, dist


def zf_beamformers(h):
    gram = h @ h.conj().T
    w = h.conj().T @ np.linalg.inv(gram)
    for i in range(w.shape[1]):
        w[:, i] /= np.linalg.norm(w[:, i])
    return w


def mmse_beamformers(h, p, p_s, w_s, sigma2=SIGMA2):
    k, n_t = h.shape
    out = np.empty((n_t, k), dtype=complex)
    for i in range(k):
        r = sigma2 * np.eye(n_t) + p_s * np.outer(w_s, w_s.conj())
        for j in range(k):
            if j != i:
                # h_j^H h_j = outer(conj(h_j), h_j)
                r = r + p[j] * np.outer(h[j].conj(), h[j])
        v = np.linalg.solve(r, h[i].conj())  # MMSE 权向量正比于 R^{-1} h_i^H
        out[:, i] = v / np.linalg.norm(v)
    return out


def sensing_beam(theta=THETA_T):
    return ula(N_T, theta)


def total_gain(w_comm, p, p_s, w_s, theta=THETA_T):
    a = ula(N_T, theta)
    g = p_s * abs(a.conj() @ w_s) ** 2
    for i in range(w_comm.shape[1]):
        g += p[i] * abs(a.conj() @ w_comm[:, i]) ** 2
    return float(np.real(g))


def min_power_zf(h, w, gamma, p_s, w_s):
    p = np.empty(h.shape[0])
    for i in range(h.shape[0]):
        sig = abs(h[i] @ w[:, i]) ** 2
        itf = SIGMA2 + p_s * abs(h[i] @ w_s) ** 2
        p[i] = gamma * itf / sig
    return p


def mmse_fixed_point(h, gamma, p_s, w_s, iters=200, init_frac=0.02,
                     project=True):
    """MMSE 波束 + Yates 功率控制的交替迭代（SCA-BCD 内层）。

    从低功率起点出发，Yates 迭代的发送功率单调递增收敛到不动点（标准结论）。
    project=True 时每次更新后做和功率预算投影，保证轨迹始终可行。
    """
    k = h.shape[0]
    budget = P_MAX_W - p_s
    p = np.full(k, init_frac * budget / k)
    trace = []
    w = mmse_beamformers(h, p, p_s, w_s)
    for _ in range(iters):
        w = mmse_beamformers(h, p, p_s, w_s)
        new_p = np.empty(k)
        for i in range(k):
            sig = abs(h[i] @ w[:, i]) ** 2
            itf = SIGMA2 + p_s * abs(h[i] @ w_s) ** 2
            for j in range(k):
                if j != i:
                    itf += p[j] * abs(h[i] @ w[:, j]) ** 2
            new_p[i] = gamma * itf / sig
        p = new_p
        if project and p.sum() > budget:
            p *= budget / p.sum()
        total = float(p.sum())
        rate = 0.0
        for i in range(k):
            sig = abs(h[i] @ w[:, i]) ** 2
            itf = SIGMA2 + p_s * abs(h[i] @ w_s) ** 2
            for j in range(k):
                if j != i:
                    itf += p[j] * abs(h[i] @ w[:, j]) ** 2
            rate += math.log2(1.0 + p[i] * sig / itf)
        trace.append(dict(total_power=total, sum_rate=rate))
        if len(trace) > 3 and abs(trace[-1]["total_power"] - trace[-2]["total_power"]) \
                <= 1e-9 * max(1.0, abs(total)):
            break
    return p, w, trace


def _max_feasible_gamma(h, p_s, w_s, lo_db=-10.0, hi_db=30.0, steps=24):
    """二分找 Yates 不动点仍在和功率预算内的最大目标 SINR（dB）。"""
    budget = P_MAX_W - p_s
    lo, hi = lo_db, hi_db
    for _ in range(steps):
        mid = 0.5 * (lo + hi)
        p, _, tr = mmse_fixed_point(h, 10.0 ** (mid / 10.0), p_s, w_s,
                                    iters=120, project=False)
        if tr and tr[-1]["total_power"] <= budget:
            lo = mid
        else:
            hi = mid
    return lo


# ---------------------------------------------------------------- A：CRB 验证
def exp_crb_validation():
    rows = []
    for n_r in (8, 12, 16, 24, 32):
        th, mc = validate_crb(n_r)
        rows.append(dict(n_r=n_r, crb_std=th, mc_rmse=mc, ratio=mc / th))
    _write("crb_validation.csv", rows)
    return rows


# ---------------------------------------------------------------- B：Pareto
def exp_pareto():
    h, angles, dist = comm_channels(np.random.default_rng(20261019))
    w_zf = zf_beamformers(h)
    w_s = sensing_beam()
    k = h.shape[0]
    sig = np.array([abs(h[i] @ w_zf[:, i]) ** 2 for i in range(k)])
    leak = np.array([abs(h[i] @ w_s) ** 2 for i in range(k)])

    # 通信为中心时可达的最大 gamma：p_i = gamma*SIGMA2/sig_i，故解析可得
    inv = SIGMA2 / np.maximum(sig, 1e-300)
    base = float(np.sum(inv))
    gamma_max = P_MAX_W / base if base > 0 else 1.0
    if not np.isfinite(gamma_max) or gamma_max <= 1.0:
        gamma_max = 1.0

    # 纯感知（无通信同频干扰、满功率）时的感知增益：时隙划分与雷达为中心共用
    gain_sensing_only = total_gain(w_zf, np.zeros(k), P_MAX_W, w_s)

    rows = []
    for g_db in GAMMAS_DB:
        gamma = 10.0 ** (g_db / 10.0)
        # 通信为中心：p_s = 0
        p = min_power_zf(h, w_zf, gamma, 0.0, w_s)
        if p.sum() <= P_MAX_W * 1.0001:
            gain = total_gain(w_zf, p, 0.0, w_s)
            rows.append(dict(scheme="Comm-centric", gamma_db=g_db,
                             rate=k * math.log2(1.0 + gamma), crb=crb_theta(gain),
                             total_power=float(p.sum()), sensing_power=0.0, gain=gain))
        # 所提：总功率预算内最大化 a^H R_x a（一维闭式，含 p_s 抬高通信功率的耦合）
        a_comm = float(np.sum(gamma * SIGMA2 / sig))
        slope = 1.0 + gamma * float(np.sum(leak / sig))
        p_s = max(0.0, (P_MAX_W - a_comm) / slope)
        p2 = min_power_zf(h, w_zf, gamma, p_s, w_s)
        total2 = float(p2.sum()) + p_s
        if total2 <= P_MAX_W * 1.0001:
            gain2 = total_gain(w_zf, p2, p_s, w_s)
            rows.append(dict(scheme="Proposed", gamma_db=g_db,
                             rate=k * math.log2(1.0 + gamma), crb=crb_theta(gain2),
                             total_power=total2, sensing_power=p_s, gain=gain2))
        # 时隙划分：eta 比例时间做通信（满功率），(1-eta) 做感知（满功率）
        # 平均 Fisher 信息 = (1-eta) * FI(P_MAX) => CRB_ts = CRB(P_MAX)/(1-eta)
        eta = (k * math.log2(1.0 + gamma)) / (k * math.log2(1.0 + gamma_max))
        # eta -> 1 时感知占空比趋于 0，CRB 发散；占空比 < 5% 的方案不具工程意义
        if eta < 0.95:
            duty = 1.0 - eta
            rows.append(dict(scheme="Time-sharing", gamma_db=g_db,
                             rate=k * math.log2(1.0 + gamma),
                             crb=crb_theta(gain_sensing_only) / duty,
                             total_power=P_MAX_W,
                             sensing_power=duty * P_MAX_W,
                             gain=gain_sensing_only))
    rows.append(dict(scheme="Radar-centric", gamma_db="", rate=0.0,
                     crb=crb_theta(gain_sensing_only), total_power=P_MAX_W,
                     sensing_power=P_MAX_W, gain=gain_sensing_only))
    _write("pareto.csv", rows)

    grid = np.linspace(-math.pi / 2, math.pi / 2, 361)
    pat = []
    for g in grid:
        av = ula(N_T, g)
        entry = dict(angle_deg=math.degrees(g))
        for i in range(k):
            entry[f"comm{i + 1}_db"] = db(abs(av.conj() @ w_zf[:, i]) ** 2 + 1e-30)
        entry["sensing_db"] = db(abs(av.conj() @ w_s) ** 2 + 1e-30)
        pat.append(entry)
    _write("beampattern.csv", pat)
    return rows, angles, dist, gamma_max


# ---------------------------------------------------------------- C：子载波 / PAPR
def exp_subcarrier():
    """频域划分：rho 比例子载波专职感知，其余承载通信。"""
    h, angles, dist = comm_channels(np.random.default_rng(20261019))
    w_zf = zf_beamformers(h)
    w_s = sensing_beam()
    gamma = 10.0 ** (9.0 / 10.0)
    p = min_power_zf(h, w_zf, gamma, 0.0, w_s)
    rows = []
    for rho in [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60]:
        n_sens = int(round(rho * M_SC))
        n_comm = M_SC - n_sens
        p_sens = rho * P_MAX_W
        p_comm_scale = (1.0 - rho) * P_MAX_W / max(float(p.sum()), 1e-12)
        p_comm = p * min(p_comm_scale, 1.0)
        gain = total_gain(w_zf, p_comm, p_sens, w_s)
        rate = (n_comm / M_SC) * K * math.log2(1.0 + gamma)
        rows.append(dict(rho=rho, n_sensing=n_sens, n_comm=n_comm, rate=rate,
                         crb=crb_theta(gain), gain=gain,
                         sensing_power=p_sens,
                         comm_power=float(p_comm.sum())))
    # 派生列：以全通信（rho=0）为基准的 CRB 改善倍数与速率保留比例，
    # 供正文直接引用（避免读者自行除算产生分歧）。
    base_crb = rows[0]["crb"]
    base_rate = rows[0]["rate"]
    for r in rows:
        r["crb_improvement"] = base_crb / r["crb"]
        r["rate_ratio"] = r["rate"] / base_rate
    _write("subcarrier.csv", rows)
    return rows


def exp_papr(n_fft=256, oversample=4, n_sym=1200, n_reserved=16, iters=60,
             target_db=6.0):
    """PAPR CCDF：普通 OFDM vs 预留子载波（TR）峰均比抑制。

    TR 迭代：clip 出超过目标门限的峰 -> 只保留预留子载波上的投影 -> 从时域减掉，
    并每轮归一化功率（否则削峰会把总功率抬高，CCDF 比较失去意义）。
    """
    rng = np.random.default_rng(7)
    n_os = n_fft * oversample
    half = n_fft // 2
    res = np.zeros(n_fft, dtype=bool)
    res[rng.choice(n_fft, n_reserved, replace=False)] = True

    def grid_to_time(v):
        x = np.zeros(n_os, dtype=complex)
        x[:half] = v[:half]
        x[n_os - (n_fft - half):] = v[half:]
        return np.fft.ifft(x) * math.sqrt(n_os)

    def time_to_grid(e):
        ef = np.fft.fft(e) / math.sqrt(n_os)
        v = np.zeros(n_fft, dtype=complex)
        v[:half] = ef[:half]
        v[half:] = ef[n_os - (n_fft - half):]
        return v

    def papr_db(x):
        p = np.abs(x) ** 2
        return db(p.max() / p.mean())

    papr_plain, papr_tr = [], []
    for _ in range(n_sym):
        sym = (rng.integers(0, 2, n_fft) * 2 - 1
               + 1j * (rng.integers(0, 2, n_fft) * 2 - 1)) / math.sqrt(2)
        xf = np.zeros(n_fft, dtype=complex)
        xf[~res] = sym[~res]
        x = grid_to_time(xf)
        papr_plain.append(papr_db(x))

        p_avg = float(np.mean(np.abs(x) ** 2))
        thr = math.sqrt(p_avg * 10.0 ** (target_db / 10.0))
        y = x.copy()
        for _ in range(iters):
            e = np.clip(np.abs(y) - thr, 0.0, None) * np.exp(1j * np.angle(y))
            cg = time_to_grid(e)
            cf = np.zeros(n_fft, dtype=complex)
            cf[res] = cg[res]
            y = y - 0.9 * grid_to_time(cf)
            y *= math.sqrt(p_avg / float(np.mean(np.abs(y) ** 2)))
        papr_tr.append(papr_db(y))

    rows = []
    for target in np.arange(3.0, 12.01, 0.25):
        rows.append(dict(papr_db=round(float(target), 2),
                         ccdf_plain=float(np.mean(np.array(papr_plain) > target)),
                         ccdf_tr=float(np.mean(np.array(papr_tr) > target))))
    _write("papr.csv", rows)
    return rows, float(np.mean(papr_plain)), float(np.mean(papr_tr))


def _sum_rate(h, w, p, p_s, w_s):
    """给定波束与功率时的可达和速率（bit/s/Hz）。"""
    k = h.shape[0]
    total = 0.0
    for i in range(k):
        sig = abs(h[i] @ w[:, i]) ** 2
        itf = SIGMA2 + p_s * abs(h[i] @ w_s) ** 2
        for j in range(k):
            if j != i:
                itf += p[j] * abs(h[i] @ w[:, j]) ** 2
        total += math.log2(1.0 + p[i] * sig / itf)
    return total


def _drdp(h, w, p, p_s, w_s, i):
    """和速率对第 i 个用户功率的偏导（用于坐标上升）。"""
    k = h.shape[0]
    ln2 = math.log(2.0)
    sig_i = abs(h[i] @ w[:, i]) ** 2
    itf_i = SIGMA2 + p_s * abs(h[i] @ w_s) ** 2
    for j in range(k):
        if j != i:
            itf_i += p[j] * abs(h[i] @ w[:, j]) ** 2
    grad = sig_i / ((itf_i + p[i] * sig_i) * ln2)
    for j in range(k):
        if j == i:
            continue
        sig_j = abs(h[j] @ w[:, j]) ** 2
        itf_j = SIGMA2 + p_s * abs(h[j] @ w_s) ** 2
        for m in range(k):
            if m != j:
                itf_j += p[m] * abs(h[j] @ w[:, m]) ** 2
        grad -= p[j] * sig_j * abs(h[j] @ w[:, i]) ** 2 \
            / (itf_j * (itf_j + p[j] * sig_j) * ln2)
    return grad


# ---------------------------------------------------------------- D：收敛
def exp_convergence(iters=60):
    """交替优化（MMSE 波束 + 功率投影梯度）的和速率收敛轨迹。

    每轮先按当前功率更新 MMSE 波束，再沿和速率对功率的梯度做
    Armijo 回溯线搜索并投影回和功率预算；回溯保证和速率单调不减。
    """
    h, angles, dist = comm_channels(np.random.default_rng(20261019))
    w_s = sensing_beam()
    p_s = 0.3 * P_MAX_W
    budget = P_MAX_W - p_s
    k = h.shape[0]
    p = np.full(k, budget / k)
    w = mmse_beamformers(h, p, p_s, w_s)
    rate = _sum_rate(h, w, p, p_s, w_s)
    trace = [dict(total_power=float(p.sum()), sum_rate=float(rate))]
    step0 = 0.2 * budget
    for _ in range(iters):
        w = mmse_beamformers(h, p, p_s, w_s)
        grad = np.array([_drdp(h, w, p, p_s, w_s, i) for i in range(k)])
        gmax = float(np.max(np.abs(grad)))
        if gmax <= 0.0:
            break
        direction = (grad - grad.mean()) / gmax
        step = step0
        improved = False
        for _ in range(40):
            cand = np.maximum(p + step * direction, 0.0)
            if cand.sum() > budget:
                cand *= budget / cand.sum()
            cand_rate = _sum_rate(h, w, cand, p_s, w_s)
            if cand_rate > rate:
                improved = True
                break
            step *= 0.5
        if not improved:
            break
        p, rate = cand, cand_rate
        step0 = min(2.0 * step, 0.5 * budget)
        trace.append(dict(total_power=float(p.sum()), sum_rate=float(rate)))
        if len(trace) > 2 and abs(trace[-1]["sum_rate"] - trace[-2]["sum_rate"]) \
                <= 1e-10 * max(1.0, abs(rate)):
            break
    rows = [dict(iteration=i + 1, total_power=float(t["total_power"]),
                 sum_rate=float(t["sum_rate"])) for i, t in enumerate(trace)]
    _write("convergence.csv", rows)
    return rows


# ---------------------------------------------------------------- E：轨迹
def exp_trajectory(n_slot=30, dt=1.0, v_target=8.0):
    """两架无人机各自跟踪一个地面目标：最小化各时隙 PCRB。

    目标函数 -sum log(alpha^2(d_n) * G) 关于位置是凸的（-log 复合凸），
    速度约束为凸，故用 SLSQP 直接求解；基线为绕目标匀速盘旋。
    """
    from scipy.optimize import minimize

    tgt0 = np.array([[0.0, 600.0], [400.0, 900.0]])
    starts = np.array([[-300.0, 300.0], [700.0, 300.0]])   # 距目标约 400 m
    vels = np.array([[v_target, 0.0], [0.0, -v_target]])
    tgt = np.stack([np.stack([tgt0[u] + vels[u] * dt * n for n in range(n_slot)])
                    for u in range(U)])          # (U, N, 2)
    v_lim = V_MAX * dt

    def dist3(q, n, u):
        return math.sqrt(H_UAV ** 2 + float(np.sum((q - tgt[u, n]) ** 2)))

    def obj_u(x, u):
        q = x.reshape(n_slot, 2)
        val = 0.0
        for n in range(n_slot):
            d = dist3(q[n], n, u)
            # -log(alpha2(d) * P_MAX) = -log(alpha2) - log(P_MAX)
            val -= math.log(alpha2_at(d) * P_MAX_W)
        return val

    def cons_u(x, u):
        q = x.reshape(n_slot, 2)
        c = [v_lim ** 2 - np.sum((q[0] - starts[u]) ** 2)]
        for n in range(1, n_slot):
            c.append(v_lim ** 2 - np.sum((q[n] - q[n - 1]) ** 2))
        return np.array(c)

    q_opt = np.empty((U, n_slot, 2))
    for u in range(U):
        x0 = np.repeat(starts[u][None, :], n_slot, axis=0).reshape(-1)
        res = minimize(obj_u, x0, args=(u,), method="SLSQP",
                       constraints=[{"type": "ineq", "fun": cons_u, "args": (u,)}],
                       options=dict(maxiter=500, ftol=1e-10))
        q_opt[u] = res.x.reshape(n_slot, 2)

    # 基线：绕各自目标匀速盘旋（半径 250 m），保证对比公平
    radius = 250.0
    ang = np.linspace(0, 2 * math.pi, n_slot, endpoint=False)
    q_cir = np.stack([np.stack([tgt[u, :, 0] + radius * np.cos(ang),
                               tgt[u, :, 1] + radius * np.sin(ang)], axis=1)
                      for u in range(U)], axis=0)

    rows = []
    for n in range(n_slot):
        for u in range(U):
            d_opt = dist3(q_opt[u, n], n, u)
            d_cir = dist3(q_cir[u, n], n, u)
            rows.append(dict(
                slot=n + 1, uav=u + 1,
                x_opt=float(q_opt[u, n, 0]), y_opt=float(q_opt[u, n, 1]),
                x_circ=float(q_cir[u, n, 0]), y_circ=float(q_cir[u, n, 1]),
                dist_opt=d_opt, dist_circ=d_cir,
                crb_opt=crb_theta(P_MAX_W, alpha2=alpha2_at(d_opt)),
                crb_circ=crb_theta(P_MAX_W, alpha2=alpha2_at(d_cir)),
                target_x=float(tgt[u, n, 0]), target_y=float(tgt[u, n, 1])))
    _write("trajectory.csv", rows)
    return rows


# ---------------------------------------------------------------- 工具
def _write(name, rows):
    if not rows:
        return
    path = os.path.join(HERE, name)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        for r in rows:
            wr.writerow({k: (f"{v:.6g}" if isinstance(v, float) else v)
                         for k, v in r.items()})
    print(f"[+] {name}: {len(rows)} rows")


def write_params():
    h, angles, dist = comm_channels(np.random.default_rng(20261019))
    rows = [dict(
        fc_hz=FC_HZ, bw_hz=BW_HZ, df_hz=DF_HZ, m_sc=M_SC, n_t=N_T, n_r=N_R, k_user=K,
        u_uav=U, p_max_dbm=P_MAX_DBM, noise_dbm=NOISE_DBM_TOTAL,
        noise_dbm_per_sc=10.0 * math.log10(SIGMA2 * 1e3),
        v_max=V_MAX,
        h_uav=H_UAV, d_min=D_MIN, d_max=D_MAX, d_ref=D_REF,
        theta_deg=math.degrees(THETA_T), alpha2=ALPHA2, n_sym=N_SYM,
        rice_k_db=RICE_K_DB, beta_edge=BETA_EDGE, sigma2=SIGMA2, p_max_w=P_MAX_W,
        user_angles_deg=";".join(f"{math.degrees(a):.2f}" for a in angles),
        user_dist_m=";".join(f"{d:.1f}" for d in dist),
        seed=20261019,
    )]
    _write("params.csv", rows)


def main():
    print("=== bupt ISAC simulation ===")
    write_params()
    for r in exp_crb_validation():
        print(f"  N_r={r['n_r']:2d} sqrt(CRB)={r['crb_std']:.6g} "
              f"MC={r['mc_rmse']:.6g} ratio={r['ratio']:.4f}")
    exp_pareto()
    exp_subcarrier()
    _, mp, mt = exp_papr(n_sym=20000)
    print(f"  mean PAPR: plain={mp:.2f} dB, TR={mt:.2f} dB")
    exp_convergence()
    exp_trajectory()
    print("=== done ===")


if __name__ == "__main__":
    main()
