"""Analyse the second hERG scaffold split: seed-mean AUC and cluster-robust contrasts."""
from __future__ import annotations

import json
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
SPLIT = ROOT / "data" / "processed" / "second_split" / "herg_all.csv"
RUNS = ROOT / "runs" / "chemprop_second"
REPORTS = ROOT / "reports"
SEEDS = (42, 1, 2)
ARMS = ("chemeleon", "matched", "scratch")


def ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (p >= lo) & (p < hi if hi < 1 else p <= hi)
        if mask.sum() == 0:
            continue
        total += mask.mean() * abs(y[mask].mean() - p[mask].mean())
    return float(total)


def load_arm(arm: str, truth: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    frames = []
    for seed in SEEDS:
        path = RUNS / f"herg_{arm}_s{seed}" / "pred_test.csv"
        df = pd.read_csv(path)[["inchikey", "y"]].rename(columns={"y": f"p{seed}"})
        frames.append(df.set_index("inchikey"))
    merged = pd.concat(frames, axis=1, join="outer")
    if merged.isna().any().any():
        raise ValueError(f"{arm}: missing predictions across seeds")
    merged["p"] = merged[[f"p{s}" for s in SEEDS]].mean(axis=1)
    out = truth[["inchikey", "y", "scaffold_key"]].merge(
        merged[["p"]].reset_index(), on="inchikey", how="left"
    )
    if out["p"].isna().any():
        raise ValueError(f"{arm}: test compounds without predictions")
    return out["y"].to_numpy(dtype=int), out["p"].to_numpy(dtype=float)


def contrast(y, p_a, p_b, groups, n_boot=5000, seed=20261030):
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(n_boot):
        if groups is None:
            idx = rng.integers(0, len(y), len(y))
        else:
            uniq = np.unique(groups)
            picked = rng.choice(uniq, len(uniq), replace=True)
            idx = np.concatenate([np.where(groups == g)[0] for g in picked])
        if len(np.unique(y[idx])) < 2:
            continue
        diffs.append(roc_auc_score(y[idx], p_a[idx]) - roc_auc_score(y[idx], p_b[idx]))
    d = np.asarray(diffs)
    lo, hi = np.percentile(d, [2.5, 97.5])
    p = 2.0 * min(float((d <= 0).mean()), float((d >= 0).mean()))
    return {"delta": float(d.mean()), "ci_low": float(lo), "ci_high": float(hi),
            "p": float(min(1.0, p)), "n_boot_ok": int(len(d))}


def main() -> None:
    df = pd.read_csv(SPLIT, encoding="utf-8-sig")
    truth = df[(df["endpoint"] == "herg") & (df["split"] == "test")].reset_index(drop=True)
    y = truth["y"].to_numpy(dtype=int)
    groups = truth["scaffold_key"].to_numpy()
    report = {
        "split": {"n": int(len(y)), "pos": int(y.sum()),
                  "scaffolds": int(len(np.unique(groups)))},
        "arms": {},
        "contrasts": {},
    }
    probs = {}
    for arm in ARMS:
        y_arm, p = load_arm(arm, truth)
        per_seed = []
        for seed in SEEDS:
            part = pd.read_csv(RUNS / f"herg_{arm}_s{seed}" / "pred_test.csv")
            part = truth[["inchikey", "y"]].merge(
                part[["inchikey", "y"]].rename(columns={"y": "p"}), on="inchikey"
            )
            per_seed.append(roc_auc_score(part["y"], part["p"]))
        probs[arm] = (y_arm, p)
        report["arms"][arm] = {
            "auc_ensemble": float(roc_auc_score(y_arm, p)),
            "auc_seed_mean": float(np.mean(per_seed)),
            "auc_seed_sd": float(np.std(per_seed, ddof=1)),
            "pr_auc": float(average_precision_score(y_arm, p)),
            "mcc": float(matthews_corrcoef(y_arm, (p >= 0.5).astype(int))),
            "brier": float(brier_score_loss(y_arm, p)),
            "ece": ece(y_arm, p),
        }
    for a, b in (("chemeleon", "matched"), ("matched", "scratch"), ("chemeleon", "scratch")):
        ya, pa = probs[a]
        yb, pb = probs[b]
        if not np.array_equal(ya, yb):
            raise ValueError("label order mismatch")
        for level, g in (("compound", None), ("scaffold", groups)):
            report["contrasts"][f"{a}-{b}/{level}"] = contrast(ya, pa, pb, g)
    REPORTS.joinpath("second_split_results.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
