"""Per-seed and seed-mean metrics for every neural arm on the test split."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    matthews_corrcoef,
    roc_auc_score,
)

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
SEEDS = (42, 1, 2)
ARMS = ("chemeleon", "matched", "matched_dropout", "scratch")


def ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (p >= lo) & (p < hi if hi < 1 else p <= hi)
        if mask.sum() == 0:
            continue
        total += mask.mean() * abs(y[mask].mean() - p[mask].mean())
    return float(total)


def score(y: np.ndarray, p: np.ndarray) -> dict:
    pred = (p >= 0.5).astype(int)
    return {
        "auc": float(roc_auc_score(y, p)),
        "pr_auc": float(average_precision_score(y, p)),
        "mcc": float(matthews_corrcoef(y, pred)),
        "brier": float(brier_score_loss(y, p)),
        "ece": ece(y, p),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=str(ROOT / "runs" / "chemprop"))
    ap.add_argument("--classical")
    ap.add_argument("--out", default=str(REPORTS / "seedmean_metrics.csv"))
    args = ap.parse_args()
    runs = Path(args.runs)

    rows = []
    for endpoint in ("herg", "dili", "ames"):
        for arm in ARMS:
            paths = [runs / f"{endpoint}_{arm}_s{s}" / "pred_test.csv" for s in SEEDS]
            if not all(p.exists() for p in paths):
                continue
            truth = pd.read_csv(
                ROOT / "data" / "processed" / "global_split.csv", encoding="utf-8-sig"
            )
            truth = truth[(truth["endpoint"] == endpoint) & (truth["split"] == "test")]
            per_seed = []
            for path in paths:
                df = pd.read_csv(path)[["inchikey", "y"]].rename(columns={"y": "p"})
                df = truth[["inchikey", "y"]].merge(df, on="inchikey", how="left")
                if df["p"].isna().any():
                    raise ValueError(f"{path}: missing predictions")
                per_seed.append(score(df["y"].to_numpy(dtype=int), df["p"].to_numpy()))
            arr = {k: np.array([m[k] for m in per_seed]) for k in per_seed[0]}
            rows.append({
                "endpoint": endpoint,
                "model": arm,
                "seeds": len(per_seed),
                **{f"{k}_mean": float(v.mean()) for k, v in arr.items()},
                **{f"{k}_sd": float(v.std(ddof=1)) for k, v in arr.items()},
            })
    if args.classical:
        df = pd.read_csv(args.classical, encoding="utf-8-sig")
        df = df[df["split"] == "test"]
        for endpoint in ("herg", "dili", "ames"):
            for _, r in df[df["endpoint"] == endpoint].iterrows():
                rows.append({
                    "endpoint": endpoint,
                    "model": f"classical_{r['model']}",
                    "seeds": 1,
                    "auc_mean": r["auc"], "auc_sd": np.nan,
                    "pr_auc_mean": r["pr_auc"], "pr_auc_sd": np.nan,
                    "mcc_mean": r["mcc"], "mcc_sd": np.nan,
                    "brier_mean": r["brier"], "brier_sd": np.nan,
                    "ece_mean": r["ece"], "ece_sd": np.nan,
                })
    out = pd.DataFrame(rows)
    out.to_csv(args.out, index=False, encoding="utf-8-sig")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
