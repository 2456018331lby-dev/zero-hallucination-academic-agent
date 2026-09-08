#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_academic_curves.py - Publication-Quality Academic Vector Curve Generator

Generates publication-ready figures conforming to IEEE/GB academic standards:
- Serif typography (Times New Roman / DejaVu Serif)
- High-contrast, colorblind-friendly distinct palettes and markers
- Clean gridlines, publication font sizes, and high-DPI vector PDF/PNG output
- Zero hardcoded fake curves: strictly requires external CSV data input.
"""

import os
import sys
import csv
import argparse
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    HAS_PLOT_DEPS = True
except ImportError:
    HAS_PLOT_DEPS = False

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# IEEE / Nature color-blind friendly palette
ACADEMIC_COLORS = [
    "#0072B2",  # Deep Blue
    "#D55E00",  # Vermilion
    "#009E73",  # Bluish Green
    "#CC79A7",  # Reddish Purple
    "#E69F00",  # Orange
    "#56B4E9",  # Sky Blue
    "#F0E442",  # Yellow
    "#000000",  # Black
]

ACADEMIC_MARKERS = ['o', 's', '^', 'D', 'v', 'p', '*', 'x']
ACADEMIC_LINESTYLES = ['-', '--', '-.', ':', '-', '--', '-.', ':']


def setup_academic_style():
    plt.rcParams.update({
        'font.family': 'serif',
        'font.serif': ['Times New Roman', 'DejaVu Serif', 'SimSun'],
        'mathtext.fontset': 'stix',
        'font.size': 11,
        'axes.labelsize': 12,
        'axes.titlesize': 13,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'legend.fontsize': 10,
        'legend.framealpha': 0.9,
        'figure.titlesize': 14,
        'lines.linewidth': 2.0,
        'lines.markersize': 6,
        'axes.grid': True,
        'grid.linestyle': '--',
        'grid.alpha': 0.5,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight'
    })


def plot_curves_from_csv(
    csv_path,
    x_col,
    y_cols,
    series_labels=None,
    xlabel=None,
    ylabel=None,
    title=None,
    output_pdf=None,
    output_png=None,
    figsize=(6.5, 4.5)
):
    if not os.path.exists(csv_path):
        print(f"[-] Input CSV file not found: {csv_path}", file=sys.stderr)
        return False

    with open(csv_path, "r", encoding="utf-8-sig") as fp:
        reader = csv.reader(fp)
        rows = [r for r in reader if r and any(cell.strip() for cell in r)]

    if len(rows) < 2:
        print("[-] CSV must have at least header and one row of data", file=sys.stderr)
        return False

    headers = [h.strip() for h in rows[0]]
    data_rows = rows[1:]

    # 解析 x 列索引
    try:
        x_idx = int(x_col) if str(x_col).isdigit() else headers.index(x_col)
    except ValueError:
        print(f"[-] x-column '{x_col}' not found in headers: {headers}", file=sys.stderr)
        return False

    # 解析 y 列索引
    y_indices = []
    for y in y_cols:
        try:
            idx = int(y) if str(y).isdigit() else headers.index(y.strip())
            y_indices.append(idx)
        except ValueError:
            print(f"[-] y-column '{y}' not found in headers: {headers}", file=sys.stderr)
            return False

    # 提取 x 数值
    x_vals = []
    for r in data_rows:
        try:
            x_vals.append(float(r[x_idx].strip()))
        except ValueError:
            continue

    if not x_vals:
        print("[-] No valid numerical data found in x-column", file=sys.stderr)
        return False

    # 提取各 y 曲线数据
    series_data = []
    for yi in y_indices:
        y_vals = []
        for r in data_rows:
            try:
                y_vals.append(float(r[yi].strip()))
            except ValueError:
                y_vals.append(np.nan)
        series_data.append(y_vals)

    # 绘图
    setup_academic_style()
    fig, ax = plt.subplots(figsize=figsize)

    for i, (yi, y_data) in enumerate(zip(y_indices, series_data)):
        label = series_labels[i] if series_labels and i < len(series_labels) else headers[yi]
        color = ACADEMIC_COLORS[i % len(ACADEMIC_COLORS)]
        marker = ACADEMIC_MARKERS[i % len(ACADEMIC_MARKERS)]
        linestyle = ACADEMIC_LINESTYLES[i % len(ACADEMIC_LINESTYLES)]
        ax.plot(x_vals, y_data, label=label, color=color, marker=marker, linestyle=linestyle)

    ax.set_xlabel(xlabel or headers[x_idx])
    ax.set_ylabel(ylabel or "Metric")
    if title:
        ax.set_title(title)
    ax.legend(loc="best", frameon=True)

    plt.tight_layout()

    if output_pdf:
        os.makedirs(os.path.dirname(os.path.abspath(output_pdf)), exist_ok=True)
        plt.savefig(output_pdf, format="pdf")
        print(f"[OK] Generated academic vector PDF chart: {output_pdf}")

    if output_png:
        os.makedirs(os.path.dirname(os.path.abspath(output_png)), exist_ok=True)
        plt.savefig(output_png, format="png", dpi=300)
        print(f"[OK] Generated high-DPI raster PNG chart: {output_png}")

    plt.close()
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot academic curves from CSV")
    parser.add_argument("--csv", required=True, help="Input CSV data file")
    parser.add_argument("--x", required=True, help="Column name or index for X axis")
    parser.add_argument("--y", required=True, help="Comma-separated column names or indices for Y axis")
    parser.add_argument("--series", default="", help="Comma-separated custom legend labels")
    parser.add_argument("--xlabel", default="", help="Label for X axis")
    parser.add_argument("--ylabel", default="", help="Label for Y axis")
    parser.add_argument("--title", default="", help="Chart title")
    parser.add_argument("--output-pdf", default="academic_curve.pdf", help="Output PDF file path")
    parser.add_argument("--output-png", default=None, help="Output PNG file path (optional)")

    args = parser.parse_args()

    if not HAS_PLOT_DEPS:
        print("[-] [依赖缺失] matplotlib 或 numpy 未安装，无法生成学术矢量图表。", file=sys.stderr)
        print("    请运行安装命令: pip install -r .agents/skills/requirements.txt (或: pip install matplotlib numpy)", file=sys.stderr)
        sys.exit(1)
    y_cols = [c.strip() for c in args.y.split(",") if c.strip()]
    labels = [s.strip() for s in args.series.split(",") if s.strip()] if args.series else None

    success = plot_curves_from_csv(
        args.csv,
        args.x,
        y_cols,
        series_labels=labels,
        xlabel=args.xlabel or None,
        ylabel=args.ylabel or None,
        title=args.title or None,
        output_pdf=args.output_pdf,
        output_png=args.output_png
    )
    sys.exit(0 if success else 1)
