# -*- coding: utf-8 -*-
"""Generate the RIS thesis figures from the CSV files produced by sim_ris.py.

Reuses the project's own academic style helper
(``.agents/skills/thesis-latex-writer/scripts/plot_academic_curves.py``) so the
figures match ``zhaw``'s SciencePlots configuration, and adds the log axes a
plain ``plot_academic_curves.py`` call cannot express.

Label rule (learned the hard way): never put CJK and ``$...$`` in the same
string -- matplotlib hands the whole string to mathtext, whose STIX font set
has no CJK glyphs, so the Chinese turns into tofu boxes.  Math symbols are
written as Unicode (``√``, ``²``, ``N_R``) instead.

Run:  py -3.12 make_ris_figures.py
"""
from __future__ import annotations

import csv
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
STYLE_SCRIPT = os.path.join(
    ROOT, ".agents", "skills", "thesis-latex-writer", "scripts",
    "plot_academic_curves.py")
FIG_DIR = os.path.abspath(os.path.join(HERE, "..", "figures"))

STYLES = {
    "proposed": dict(color="#1f4e79", marker="o", ls="-", lw=1.6, ms=4.6),
    "random_ris": dict(color="#c00000", marker="s", ls="--", lw=1.3, ms=4.4),
    "no_ris": dict(color="#7f7f7f", marker="^", ls="-.", lw=1.3, ms=4.6),
    "mrt_equal": dict(color="#2e8b57", marker="d", ls=":", lw=1.3, ms=4.2),
}


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
    pdf = os.path.join(FIG_DIR, stem + ".pdf")
    png = os.path.join(FIG_DIR, stem + ".png")
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] {pdf}")


def fig_convergence(plt) -> None:
    rows = read_csv("convergence.csv")
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    ax.plot(col(rows, "iteration", int), col(rows, "sum_rate"),
            **STYLES["proposed"])
    ax.set_xlabel("交替优化迭代次数")
    ax.set_ylabel("系统和速率 (bps/Hz)")
    ax.set_title("交替优化收敛过程")
    ax.grid(True, which="both", alpha=0.3)
    save(fig, plt, "fig_ris_convergence")


def fig_rate_pmax(plt) -> None:
    rows = read_csv("rate_pmax.csv")
    x = col(rows, "p_max_dbm")
    labels = {
        "proposed": "所提交替优化 + 相位量化",
        "random_ris": "随机相移 RIS",
        "no_ris": "无 RIS（仅 BS 波束赋形）",
        "mrt_equal": "等功率 MRT",
    }
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    for key in ("proposed", "random_ris", "no_ris", "mrt_equal"):
        ax.plot(x, col(rows, key), label=labels[key], **STYLES[key])
    ax.set_xlabel("基站发射功率上限 (dBm)")
    ax.set_ylabel("系统和速率 (bps/Hz)")
    ax.set_title("和速率随发射功率的变化")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="upper left", fontsize=7.5)
    save(fig, plt, "fig_ris_rate_pmax")


def fig_rate_n(plt) -> None:
    rows = read_csv("rate_n.csv")
    x = col(rows, "n_ris", int)
    labels = {
        "proposed": "所提方案",
        "random_ris": "随机相移 RIS",
        "no_ris": "无 RIS",
    }
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    for key in ("proposed", "random_ris", "no_ris"):
        ax.plot(x, col(rows, key), label=labels[key], **STYLES[key])
    ax.set_xscale("log", base=2)
    ax.set_xticks(x)
    ax.set_xticklabels([str(v) for v in x])
    ax.set_xlabel("RIS 反射单元数 N")
    ax.set_ylabel("系统和速率 (bps/Hz)")
    ax.set_title("和速率随 RIS 规模的变化")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="upper left", fontsize=7.5)
    save(fig, plt, "fig_ris_rate_n")


def fig_quantization(plt) -> None:
    rows = [r for r in read_csv("quantization.csv") if r["bits"] != "continuous"]
    cont = [r for r in read_csv("quantization.csv") if r["bits"] == "continuous"][0]
    x = col(rows, "bits", int)
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    ax.plot(x, col(rows, "sum_rate"), label="离散相移（最优投影）",
            **STYLES["proposed"])
    ax.axhline(float(cont["sum_rate"]), color="#c00000", ls="--", lw=1.3,
               label="连续相移上界")
    ax.set_xlabel("相移量化比特数 b")
    ax.set_ylabel("系统和速率 (bps/Hz)")
    ax.set_title("相移量化对和速率的影响")
    ax.set_xticks(x)
    ax.set_xticklabels([str(v) for v in x])
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="lower right", fontsize=7.5)
    save(fig, plt, "fig_ris_quantization")


def fig_pilot(plt) -> None:
    rows = read_csv("pilot.csv")
    x = col(rows, "overhead_ratio")
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    ax.semilogy(x, col(rows, "nmse_fixed_prefix"), label="固定前缀导频",
                **STYLES["no_ris"])
    ax.semilogy(x, col(rows, "nmse_random_subset"), label="随机子集导频",
                **STYLES["proposed"])
    ax.semilogy(x, col(rows, "nmse_oracle_subset"), label="已知支撑集下界",
                **STYLES["random_ris"])
    ax.semilogy(x, col(rows, "nmse_theory_random"), label="LS 理论值 σ²/(T·P)",
                **STYLES["mrt_equal"])
    ax.set_xlabel("导频开销比例 T/N")
    ax.set_ylabel("级联信道 NMSE")
    ax.set_title("信道估计精度随导频开销的变化")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="upper right", fontsize=6.6, framealpha=0.92)
    save(fig, plt, "fig_ris_pilot")


def fig_crlb(plt) -> None:
    rows = read_csv("crlb.csv")
    x = col(rows, "snr_db")
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    ax.semilogy(x, col(rows, "nmse_ls"), label="LS 估计实测 NMSE",
                **STYLES["proposed"])
    ax.semilogy(x, col(rows, "crlb"), label="无偏估计 CRLB",
                **STYLES["random_ris"])
    ax.set_xlabel("导频信噪比 (dB)")
    ax.set_ylabel("级联信道 NMSE")
    ax.set_title("LS 估计与 CRLB 的贴合程度")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="lower left", fontsize=7.5)
    save(fig, plt, "fig_ris_crlb")


def main() -> int:
    # 后端必须在应用样式之前定好：matplotlib.use() 在 pyplot 已导入后会重置部分
    # rcParams，放在 setup_academic_style() 之后会把中文字体回退掉。
    import matplotlib
    matplotlib.use("Agg")
    load_style()
    import matplotlib.pyplot as plt

    fig_convergence(plt)
    fig_rate_pmax(plt)
    fig_rate_n(plt)
    fig_quantization(plt)
    fig_pilot(plt)
    fig_crlb(plt)
    print("[DONE] 6 figures written to", FIG_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
