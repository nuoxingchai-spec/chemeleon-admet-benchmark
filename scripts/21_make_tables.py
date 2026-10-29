"""Generate LNCS booktabs tables from frozen result CSVs."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "reports"
OUT = ROOT / "paper" / "tables"
EP = {"herg": "hERG", "dili": "DILI", "ames": "Ames"}


def f3(x):
    return "NaN" if pd.isna(x) else f"{x:.3f}"


def f2(x):
    return "NaN" if pd.isna(x) else f"{x:.2f}"


def pval(p):
    return "$<$0.001" if p < 0.001 else f"{p:.3f}"


def ci(lo, hi):
    return f"[{f3(lo)}, {f3(hi)}]"


def pm(mean, sd):
    return f"{f3(mean)} $\\pm$ {f3(sd)}"


def wilson(k, n, z=1.96):
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return center - half, center + half


def wrap(label, caption, body, colspec, size="\\small", colsep="4pt"):
    return "\n".join([
        "\\begin{table}[htbp]",
        "\\centering",
        size,
        f"\\setlength{{\\tabcolsep}}{{{colsep}}}",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        f"\\begin{{tabular}}{{{colspec}}}",
        "\\toprule",
        body,
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
        "",
    ])


def t2_compact():
    base = pd.read_csv(R / "baselines_classical.csv")
    runs = pd.read_csv(R / "chemprop_runs.csv")
    specs = [
        ("rf", "RF", "---"),
        ("chemprop_none", "Scratch", "318{,}307"),
        ("chemprop_matched", "Matched", "9{,}329{,}247"),
        ("chemprop_chemeleon", "CheMeleon", "9{,}329{,}247"),
    ]
    lines = []
    for model, label, params in specs:
        cells = []
        for ep in ["herg", "dili", "ames"]:
            b = base[(base.endpoint == ep) & (base.split == "test")]
            c = runs[(runs.endpoint == ep) & (runs.split == "test")]
            if model in b.model.values:
                r = b[b.model == model].iloc[0]
                cells.append(f"{f3(r['auc'])} ({f3(r['ece'])})")
            else:
                g = c[c.model == model]
                cells.append(f"{f3(g['auc'].mean())} ({f3(g['ece'].mean())})")
        lines.append(f"{label} & {params} & " + " & ".join(cells) + " \\\\")
    body = "\n".join([
        "Model & Params & hERG & DILI & Ames \\\\",
        "\\midrule",
        *lines,
    ])
    cap = ("Test-set AUC (ECE) on the global scaffold-disjoint split. Chemprop rows are "
           "means over three seeds, classical baselines a single fit, and all rows use the "
           "same split and training budget.")
    (OUT / "t2_compact.tex").write_text(wrap("tab:main", cap, body, "lrrrr"), encoding="utf-8")


def t3_capacity():
    ctrl = pd.read_csv(R / "control_contrast.csv")
    pair_order = [("chemeleon", "matched", "CheMeleon--matched"),
                  ("matched", "scratch", "matched--scratch"),
                  ("chemeleon", "scratch", "CheMeleon--scratch")]
    lines = []
    for i, ep in enumerate(["herg", "dili", "ames"]):
        if i:
            lines.append("\\midrule")
        for a, b, label in pair_order:
            r = ctrl[(ctrl.endpoint == ep) & (ctrl.model_a == a) & (ctrl.model_b == b)]
            if r.empty:
                continue
            r = r.iloc[0]
            lines.append(
                f"{EP[ep]} & {label} & {int(r['seeds_a'])}/{int(r['seeds_b'])} & "
                f"{f3(r['d_auc'])} {ci(r['d_auc_lo'], r['d_auc_hi'])} & {pval(r['d_auc_p'])} & "
                f"{f3(r['d_ece'])} & {f3(r['d_brier'])} \\\\"
            )
    body = "\n".join([
        "Endpoint & Contrast & Seeds & $\\Delta$AUC [95\\% CI] & $p$ & $\\Delta$ECE & $\\Delta$Brier \\\\",
        "\\midrule",
        *lines,
    ])
    cap = ("Appendix: capacity-controlled paired contrasts ($A$--$B$) on seed-ensemble "
           "probabilities (paired bootstrap, 2000 resamples). Matched has the same "
           "2048$\\times$6 encoder as CheMeleon (9,329,247 parameters) but random "
           "initialisation; scratch is 300$\\times$3. Negative $\\Delta$ECE/$\\Delta$Brier "
           "favour $A$.")
    (OUT / "t3_capacity.tex").write_text(wrap("tab:capacity", cap, body, "llrrrrr", "\\footnotesize", "2.5pt"), encoding="utf-8")


def t6_coverage():
    cf = pd.read_csv(R / "conformal_holdout.csv")
    schemes = [("random50", "Random 50/50"),
               ("scaffold50", "Scaffold 50/50"),
               ("valid_to_test", "Valid$\\to$test")]
    models = [("chemeleon", "CheMeleon"), ("scratch", "Scratch")]

    def lines_for(ep):
        out = []
        for sc, label in schemes:
            for model, name in models:
                r = cf[(cf.endpoint == ep) & (cf.model == model) & (cf.scheme == sc)]
                if r.empty:
                    out.append(f"{label} & {name} & -- & -- & -- \\\\")
                    continue
                r = r.iloc[0]
                cov = float(r["coverage"])
                if sc == "valid_to_test":
                    n = int(r["n_test"])
                    lo, hi = wilson(round(cov * n), n)
                else:
                    lo, hi = float(r["coverage_lo"]), float(r["coverage_hi"])
                out.append(f"{label} & {name} & {f3(cov)} & [{f3(lo)}, {f3(hi)}] & {f3(r['set_size'])} \\\\")
        return out

    body = "\n".join([
        "Calibration/evaluation split & Model & Coverage & 95\\% interval & Set size \\\\",
        "\\midrule",
        *lines_for("ames"),
    ])
    cap = ("Ames split-conformal coverage at $\\alpha=0.10$ (nominal 0.90). Random 50/50 "
           "is the exchangeable control; scaffold 50/50 simulates deployment shift; both "
           "repeat the split 200 times (percentile interval). Valid$\\to$test is the "
           "deployed protocol (Wilson interval).")
    (OUT / "t6_coverage.tex").write_text(wrap("tab:coverage", cap, body, "llrrr", "\\small"), encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t2_compact()
    t3_capacity()
    t6_coverage()
    print("wrote", sorted(p.name for p in OUT.glob("*.tex")))


if __name__ == "__main__":
    main()
