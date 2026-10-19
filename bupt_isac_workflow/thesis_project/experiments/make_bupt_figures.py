# -*- coding: utf-8 -*-
"""由 sim_bupt.py 产出的 CSV 生成第 4 章全部图件。

复用项目自带的学术样式（SciencePlots / IEEE 风格）：
``.agents/skills/thesis-latex-writer/scripts/plot_academic_curves.py``。
图件标签一律使用「中文 + Unicode 数学符号」，**不使用** ``$...$`` ——
含 ``$`` 的字符串会被 matplotlib 整串交给 mathtext（STIX 字体，无中文字形），
中文会变成方块。

Run:  py -3.12 make_bupt_figures.py
"""
from __future__ import annotations

import csv
import importlib.util
import os
import sys

import matplotlib

matplotlib.use("Agg")  # 必须在加载样式（其内部 import pyplot）之前

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
STYLE_SCRIPT = os.path.join(
    ROOT, ".agents", "skills", "thesis-latex-writer", "scripts",
    "plot_academic_curves.py")
FIG_DIR = os.path.abspath(os.path.join(HERE, "..", "figures"))


def load_style():
    spec = importlib.util.spec_from_file_location("_zhaw_plot", STYLE_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_zhaw_plot"] = mod
    spec.loader.exec_module(mod)
    mod.setup_academic_style("ieee")
    return mod


def read_csv(name: str) -> list[dict]:
    with open(os.path.join(HERE, name), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def col(rows, key, cast=float):
    return [cast(r[key]) for r in rows]


def save(fig, plt, stem: str) -> None:
    os.makedirs(FIG_DIR, exist_ok=True)
    for ext in ("pdf", "png"):
        path = os.path.join(FIG_DIR, f"{stem}.{ext}")
        fig.savefig(path, dpi=300, bbox_inches="tight")
        print(f"[+] {path}")
    plt.close(fig)


def fig_pareto(plt) -> None:
    rows = read_csv("pareto.csv")
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    styles = {
        "Comm-centric": dict(marker="o", label="通信为中心"),
        "Proposed": dict(marker="s", label="所提联合优化"),
        "Time-sharing": dict(marker="^", label="时隙划分"),
    }
    for scheme, st in styles.items():
        pts = [r for r in rows if r["scheme"] == scheme]
        pts.sort(key=lambda r: float(r["rate"]))
        ax.semilogy(col(pts, "rate"), col(pts, "crb"),
                    linestyle="-", markersize=5, **st)
    radar = [r for r in rows if r["scheme"] == "Radar-centric"][0]
    ax.semilogy([0.0], [float(radar["crb"])], marker="*", markersize=11,
                linestyle="none", label="雷达为中心")
    ax.set_xlabel("目标可达和速率 (bps/Hz)")
    ax.set_ylabel("角度估计 CRB (rad²)")
    ax.set_title("等速率下的感知 CRB 对比")
    ax.grid(True, which="both", alpha=0.35)
    ax.legend(fontsize=8, loc="best")
    save(fig, plt, "fig_isac_pareto_curve")


def fig_subcarrier(plt) -> None:
    rows = read_csv("subcarrier.csv")
    rho = col(rows, "rho")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 3.0))
    ax1.plot(rho, col(rows, "rate"), marker="o", markersize=4)
    ax1.set_xlabel("感知子载波占比 ρ")
    ax1.set_ylabel("通信和速率 (bps/Hz)")
    ax1.grid(True, alpha=0.35)
    ax2.semilogy(rho, col(rows, "crb"), marker="s", markersize=4)
    ax2.set_xlabel("感知子载波占比 ρ")
    ax2.set_ylabel("角度估计 CRB (rad²)")
    ax2.grid(True, which="both", alpha=0.35)
    fig.suptitle("频域划分：速率与感知精度的权衡")
    save(fig, plt, "fig_subcarrier_tradeoff")


def fig_papr(plt) -> None:
    rows = read_csv("papr.csv")
    fig, ax = plt.subplots(figsize=(5.0, 3.4))
    ax.semilogy(col(rows, "papr_db"), col(rows, "ccdf_plain"),
                label="普通 OFDM")
    ax.semilogy(col(rows, "papr_db"), col(rows, "ccdf_tr"),
                linestyle="--", label="预留子载波峰均比抑制")
    ax.set_xlabel("PAPR 门限 (dB)")
    ax.set_ylabel("CCDF")
    ax.set_title("PAPR 互补累积分布")
    ax.grid(True, which="both", alpha=0.35)
    ax.legend(fontsize=8)
    save(fig, plt, "fig_papr_ccdf")


def fig_convergence(plt) -> None:
    rows = read_csv("convergence.csv")
    fig, ax = plt.subplots(figsize=(5.0, 3.4))
    ax.plot(col(rows, "iteration"), col(rows, "sum_rate"),
            marker="o", markersize=5)
    ax.set_xlabel("交替优化迭代次数")
    ax.set_ylabel("通信和速率 (bps/Hz)")
    ax.set_title("所提算法的收敛轨迹")
    ax.grid(True, alpha=0.35)
    save(fig, plt, "fig_convergence")


def fig_crb_validation(plt) -> None:
    rows = read_csv("crb_validation.csv")
    crb = col(rows, "crb_std")
    mc = col(rows, "mc_rmse")
    fig, ax = plt.subplots(figsize=(4.6, 3.8))
    lo = min(min(crb), min(mc)) * 0.7
    hi = max(max(crb), max(mc)) * 1.4
    ax.loglog([lo, hi], [lo, hi], linestyle="--", linewidth=1.0,
              label="完全一致参考线")
    ax.loglog(crb, mc, marker="o", markersize=6, linestyle="none",
              label="蒙特卡洛均方根误差")
    for r in rows:
        ax.annotate(f"N_R={r['n_r']}", (float(r["crb_std"]), float(r["mc_rmse"])),
                    textcoords="offset points", xytext=(6, -10), fontsize=7)
    ax.set_xlabel("闭式解 √CRB (rad)")
    ax.set_ylabel("蒙特卡洛 RMSE (rad)")
    ax.set_title("CRB 闭式解与蒙特卡洛互验")
    ax.grid(True, which="both", alpha=0.35)
    ax.legend(fontsize=8, loc="upper left")
    save(fig, plt, "fig_crb_validation")


def fig_beampattern(plt) -> None:
    rows = read_csv("beampattern.csv")
    ang = col(rows, "angle_deg")
    fig, ax = plt.subplots(figsize=(5.4, 3.4))
    for i in range(1, 5):
        key = f"comm{i}_db"
        if key in rows[0]:
            ax.plot(ang, col(rows, key), linewidth=1.1,
                    label=f"通信波束 {i}")
    ax.plot(ang, col(rows, "sensing_db"), linewidth=1.6, linestyle="--",
            label="感知波束")
    ax.set_xlabel("方位角 (°)")
    ax.set_ylabel("归一化阵列增益 (dB)")
    ax.set_title("发射波束方向图")
    ax.set_ylim(-60, 3)
    ax.grid(True, alpha=0.35)
    ax.legend(fontsize=7, ncol=2, loc="lower center")
    save(fig, plt, "fig_beampattern")


def fig_trajectory(plt) -> None:
    rows = read_csv("trajectory.csv")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.4, 3.6))

    # 左图：几何轨迹。目标本身随时间移动，故画成折线而非散点
    tgt_pts = {}
    for r in rows:
        tgt_pts[float(r["slot"])] = (float(r["target_x"]), float(r["target_y"]))
    slots = sorted(tgt_pts)
    ax1.plot([tgt_pts[s][0] for s in slots],
             [tgt_pts[s][1] for s in slots],
             color="k", linestyle=":", linewidth=1.2, label="目标运动轨迹")
    for uav, color in ((1, "C0"), (2, "C1")):
        pts = [r for r in rows if int(r["uav"]) == uav]
        ax1.plot(col(pts, "x_circ"), col(pts, "y_circ"), color=color,
                 linestyle="none", marker=".", markersize=3, alpha=0.45,
                 label=f"无人机 {uav}（盘旋基线）")
        ax1.plot(col(pts, "x_opt"), col(pts, "y_opt"), color=color,
                 linewidth=1.6, label=f"无人机 {uav}（优化轨迹）")
    ax1.set_xlabel("x 坐标 (m)")
    ax1.set_ylabel("y 坐标 (m)")
    ax1.set_title("(a) 轨迹几何")
    ax1.grid(True, alpha=0.35)
    ax1.legend(fontsize=6.5, loc="best")

    # 右图：各时隙的 CRB（优化轨迹 vs 盘旋基线）
    for uav, color in ((1, "C0"), (2, "C1")):
        pts = [r for r in rows if int(r["uav"]) == uav]
        ax2.semilogy(col(pts, "slot"), col(pts, "crb_opt"), color=color,
                     marker="o", markersize=3, label=f"无人机 {uav}（优化）")
        ax2.semilogy(col(pts, "slot"), col(pts, "crb_circ"), color=color,
                     linestyle="--", linewidth=1.0, alpha=0.6,
                     label=f"无人机 {uav}（盘旋基线）")
    ax2.set_xlabel("时隙序号")
    ax2.set_ylabel("角度估计 CRB (rad²)")
    ax2.set_title("(b) 逐时隙感知精度")
    ax2.grid(True, which="both", alpha=0.35)
    ax2.legend(fontsize=6.5, loc="best")
    save(fig, plt, "fig_uav_trajectory_pcrb")


def main() -> None:
    style = load_style()
    plt = style.plt
    fig_pareto(plt)
    fig_subcarrier(plt)
    fig_papr(plt)
    fig_convergence(plt)
    fig_crb_validation(plt)
    fig_beampattern(plt)
    fig_trajectory(plt)
    print("=== figures done ===")


if __name__ == "__main__":
    main()
