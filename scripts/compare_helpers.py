"""Shared helpers for paired model comparisons."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from metrics import ece  # noqa: E402

RUNS = ROOT / "runs" / "chemprop"


def load_run(tag: str, endpoint: str) -> pd.DataFrame:
    run_dir = RUNS / tag
    pred = pd.read_csv(run_dir / "pred_test.csv")
    is_multi = (run_dir / "preds.json").exists() and '"endpoint": "multitask"' in (
        run_dir / "preds.json"
    ).read_text(encoding="utf-8")
    if is_multi:
        labels = pd.read_csv(ROOT / "data" / "chemprop" / "multitask" / "test.csv")
        pred = pred[["inchikey", endpoint]].rename(columns={endpoint: "p"}).merge(
            labels[["inchikey", endpoint]].rename(columns={endpoint: "y"}), on="inchikey"
        )
    else:
        labels = pd.read_csv(ROOT / "data" / "chemprop" / endpoint / "test.csv")
        pred = pred[["inchikey", "y"]].rename(columns={"y": "p"}).merge(
            labels[["inchikey", "y"]], on="inchikey"
        )
    return pred.dropna().sort_values("inchikey").reset_index(drop=True)


def paired_bootstrap(y, pa, pb, n=2000, seed=42):
    rng = np.random.default_rng(seed)
    d_auc, d_ece, d_brier = [], [], []
    for _ in range(n):
        idx = rng.integers(0, len(y), len(y))
        if len(np.unique(y[idx])) < 2:
            continue
        d_auc.append(roc_auc_score(y[idx], pa[idx]) - roc_auc_score(y[idx], pb[idx]))
        d_ece.append(ece(y[idx], pa[idx]) - ece(y[idx], pb[idx]))
        d_brier.append(brier_score_loss(y[idx], pa[idx]) - brier_score_loss(y[idx], pb[idx]))
    out = {}
    for name, vals in [("auc", d_auc), ("ece", d_ece), ("brier", d_brier)]:
        vals = np.array(vals)
        lo, hi = np.percentile(vals, [2.5, 97.5])
        p = 2 * min((vals <= 0).mean(), (vals >= 0).mean())
        out[f"d_{name}"] = float(np.mean(vals))
        out[f"d_{name}_ci_low"] = float(lo)
        out[f"d_{name}_ci_high"] = float(hi)
        out[f"d_{name}_p"] = float(min(p, 1.0))
    return out
