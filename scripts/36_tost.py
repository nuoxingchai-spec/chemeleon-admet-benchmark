"""TOST equivalence tests for the capacity contrasts (90% bootstrap intervals)."""
import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
rb = importlib.import_module("32_robustness")

MARGIN = 0.06
N_BOOT = 5000
SEED = 20261030
ENDPOINTS = ("herg", "dili", "ames")
CONTRASTS = (("chemeleon", "matched"), ("chemeleon", "scratch"))


def main():
    rows = []
    for endpoint in ENDPOINTS:
        base = rb.load_ensemble(endpoint, "chemeleon")
        y = base["y"].to_numpy(dtype=int)
        groups = base["scaffold_key"].to_numpy()
        for a, b in CONTRASTS:
            df_a = rb.load_ensemble(endpoint, a)
            df_b = rb.load_ensemble(endpoint, b)
            if not (df_a["inchikey"].tolist() == df_b["inchikey"].tolist()
                    == base["inchikey"].tolist()):
                raise ValueError(f"order mismatch {endpoint} {a}/{b}")
            p_a = df_a["p"].to_numpy(dtype=float)
            p_b = df_b["p"].to_numpy(dtype=float)
            delta = float(roc_auc_score(y, p_a) - roc_auc_score(y, p_b))
            for level, g in (("compound", None), ("scaffold", groups)):
                rng = np.random.default_rng(SEED)
                draws = []
                for _ in range(N_BOOT):
                    idx = rb.resample_indices(g, len(y), rng)
                    yy = y[idx]
                    if len(np.unique(yy)) < 2:
                        continue
                    draws.append(roc_auc_score(yy, p_a[idx]) - roc_auc_score(yy, p_b[idx]))
                d = np.asarray(draws)
                lo, hi = np.percentile(d, [5, 95])
                equivalent = bool(lo > -MARGIN and hi < MARGIN)
                p_tost = float(max((d <= -MARGIN).mean(), (d >= MARGIN).mean()))
                rows.append({
                    "endpoint": endpoint,
                    "contrast": f"{a}-{b}",
                    "level": level,
                    "n_units": int(len(y) if g is None else len(np.unique(g))),
                    "delta": delta,
                    "ci90_low": float(lo),
                    "ci90_high": float(hi),
                    "margin": MARGIN,
                    "equivalent": equivalent,
                    "p_tost": p_tost,
                })
                print(rows[-1], flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(ROOT / "reports" / "tost.csv", index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
