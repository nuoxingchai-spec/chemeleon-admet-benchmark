"""Generate paper figures from final prediction artifacts (F1-F3)."""
import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from metrics import ece  # noqa: E402

cal = importlib.import_module("13_calibration_ci")
R = ROOT / "reports"
FIG = R / "figures"

BLUE = "#1f4e79"
ORANGE = "#c55a11"
GREEN = "#548235"
GRAY = "#7f7f7f"


def style():
    plt.rcParams.update({
        "font.family": "DejaVu Serif",
        "font.size": 9,
        "axes.labelsize": 10,
        "axes.titlesize": 10,
        "legend.fontsize": 8.5,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
        "savefig.bbox": "tight",
    })


def wilson(k, n, z=1.96):
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return center - half, center + half


def reliability(y, p, edges):
    idx = np.clip(np.digitize(p, edges) - 1, 0, len(edges) - 2)
    xs, ys, ns = [], [], []
    for b in range(len(edges) - 1):
        m = idx == b
        if m.sum() == 0:
            continue
        xs.append(p[m].mean())
        ys.append(y[m].mean())
        ns.append(int(m.sum()))
    return np.array(xs), np.array(ys), np.array(ns)


def fig1_reliability():
    (ens, used) = cal.load_ensemble("ames", "chemeleon")
    pv, yv = ens["valid"]["p"], ens["valid"]["y"]
    pt, yt = ens["test"]["p"], ens["test"]["y"]
    variants, _ = cal.fit_apply(pv, yv, pt)
    (ens_s, used_s) = cal.load_ensemble("ames", "scratch")
    p_scratch = ens_s["test"]["p"]

    edges = np.linspace(0, 1, 11)
    fig, (ax, axh) = plt.subplots(
        2, 1, figsize=(4.6, 3.5), sharex=True, height_ratios=[3.2, 1.0]
    )
    ax.plot([0, 1], [0, 1], ls="--", lw=0.8, color="0.55", zorder=1)
    for p, label, color, marker in [
        (variants["raw"], "CheMeleon raw", BLUE, "o"),
        (variants["platt"], "CheMeleon Platt", ORANGE, "s"),
        (p_scratch, "scratch raw", GRAY, "^"),
    ]:
        xs, ys, _ = reliability(yt, p, edges)
        ax.plot(xs, ys, marker=marker, ms=3.2, lw=1.1, color=color, label=label)
    ax.set_ylabel("Observed positive rate")
    ax.set_title("Ames reliability (seed ensemble, test n=732)")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(0.03, 0.93,
            f"ECE: raw {ece(yt, variants['raw']):.3f}, "
            f"Platt {ece(yt, variants['platt']):.3f}, "
            f"scratch {ece(yt, p_scratch):.3f}",
            fontsize=8.2)
    ax.legend(loc="lower right", frameon=False)

    _, _, ns = reliability(yt, variants["raw"], edges)
    centers = (edges[:-1] + edges[1:]) / 2
    axh.bar(centers, ns, width=0.08, color="0.75", edgecolor="0.4", lw=0.4)
    axh.set_ylabel("Count")
    axh.set_xlabel("Predicted probability (CheMeleon raw)")
    axh.set_xlim(0, 1)

    fig.align_ylabels((ax, axh))
    fig.savefig(FIG / "fig1_reliability_ames.pdf")
    fig.savefig(FIG / "fig1_reliability_ames.png", dpi=300)
    plt.close(fig)
    return used, used_s


def fig2_coverage():
    cf = pd.read_csv(R / "conformal_holdout.csv")
    cf = cf[(cf.endpoint == "ames") & (cf.model.isin(["chemeleon", "scratch"]))]
    cf = cf[cf.scheme.isin(["random50", "scaffold50", "valid_to_test"])]
    labels = {
        "random50": "random 50/50\n(exchangeable)",
        "scaffold50": "scaffold-grouped\n50/50",
        "valid_to_test": "valid → test\n(deployed)",
    }
    schemes = ["random50", "scaffold50", "valid_to_test"]
    width = 0.36
    x = np.arange(len(schemes))

    fig, (axc, axs) = plt.subplots(1, 2, figsize=(5.2, 2.9))
    for j, (model, color, name) in enumerate(
        [("chemeleon", BLUE, "CheMeleon"), ("scratch", ORANGE, "scratch")]
    ):
        cov, lo, hi, size, slo, shi = [], [], [], [], [], []
        for sc in schemes:
            row = cf[(cf.model == model) & (cf.scheme == sc)].iloc[0]
            c = float(row["coverage"])
            cov.append(c)
            if sc == "valid_to_test":
                n = int(row["n_test"])
                a, b = wilson(round(c * n), n)
                lo.append(c - a)
                hi.append(b - c)
                size.append(float(row["set_size"]))
                slo.append(0.0)
                shi.append(0.0)
            else:
                lo.append(c - float(row["coverage_lo"]))
                hi.append(float(row["coverage_hi"]) - c)
                size.append(float(row["set_size"]))
                slo.append(size[-1] - float(row["set_size_lo"]))
                shi.append(float(row["set_size_hi"]) - size[-1])
        xpos = x + (j - 0.5) * width
        axc.bar(xpos, cov, width, yerr=[lo, hi], capsize=2, color=color,
                edgecolor="white", lw=0.5, label=name,
                error_kw={"lw": 0.8, "ecolor": "0.25"})
        axs.bar(xpos, size, width, yerr=[slo, shi],
                capsize=2, color=color, edgecolor="white", lw=0.5,
                error_kw={"lw": 0.8, "ecolor": "0.25"})

    axc.axhline(0.9, ls="--", lw=0.9, color="0.2")
    axc.text(2.42, 0.903, "nominal 0.90", fontsize=8, ha="right", va="bottom")
    axc.set_ylim(0.78, 0.95)
    axc.set_ylabel("Marginal coverage")
    axc.set_xticks(x)
    axc.set_xticklabels([labels[s] for s in schemes])
    axc.set_title("Ames coverage (α = 0.10)")

    axs.set_ylabel("Mean prediction-set size")
    axs.set_xticks(x)
    axs.set_xticklabels([labels[s] for s in schemes])
    axs.set_title("Ames set size")
    axs.set_ylim(1.0, 1.6)

    handles = [plt.Rectangle((0, 0), 1, 1, color=BLUE),
               plt.Rectangle((0, 0), 1, 1, color=ORANGE)]
    fig.legend(handles, ["CheMeleon", "scratch"], loc="lower center", ncol=2,
               frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(FIG / "fig2_coverage_protocol.pdf")
    fig.savefig(FIG / "fig2_coverage_protocol.png", dpi=300)
    plt.close(fig)


def fig3_lowdata():
    low = pd.read_csv(R / "lowdata.csv")
    agg = low.groupby(["model", "train_n"])["auc"].agg(["mean", "std"]).reset_index()
    series = [
        ("chemeleon", "CheMeleon", BLUE, "o", "-"),
        ("matched_dropout", "matched+dropout", ORANGE, "s", "-"),
        ("matched", "matched 2048×6", GREEN, "^", "--"),
        ("scratch", "scratch 300×3", GRAY, "D", "-"),
    ]
    fig, ax = plt.subplots(figsize=(4.4, 3.1))
    for model, label, color, marker, ls in series:
        d = agg[agg.model == model].sort_values("train_n")
        ax.errorbar(d.train_n, d["mean"], yerr=d["std"], marker=marker, ms=3.2,
                    lw=1.1, ls=ls, capsize=2, color=color, label=label)
    ax.set_xscale("log")
    ax.set_xticks([50, 100, 200, 400])
    ax.set_xticklabels(["50", "100", "200", "400"])
    ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    ax.set_xlabel("Training-set size n (hERG)")
    ax.set_ylabel("hERG test AUC (mean ± SD, 3 seeds)")
    ax.set_ylim(0.55, 0.95)
    ax.legend(loc="upper left", frameon=False)
    ax.annotate("n = 400: scratch catches up", xy=(396, 0.872), xytext=(225, 0.932),
                fontsize=7, va="top",
                arrowprops={"arrowstyle": "-", "lw": 0.6, "color": "0.4"})
    fig.savefig(FIG / "fig3_lowdata.pdf")
    fig.savefig(FIG / "fig3_lowdata.png", dpi=300)
    plt.close(fig)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    style()
    used, used_s = fig1_reliability()
    fig2_coverage()
    fig3_lowdata()
    print(f"fig1 seeds chemeleon={used} scratch={used_s}")
    print(f"wrote {FIG}")


if __name__ == "__main__":
    main()
