"""Analyse the second scaffold split for hERG, DILI, and Ames."""
from __future__ import annotations

import argparse
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
SPLIT = ROOT / "data" / "processed" / "global_split.csv"
DATA = ROOT / "data" / "chemprop_second"
RUNS = ROOT / "runs" / "chemprop_second"
REPORTS = ROOT / "reports"
SEEDS = (42, 1, 2)
ARMS = ("chemeleon", "matched", "scratch")
ENDPOINTS = ("herg", "dili", "ames")


def ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (p >= lo) & (p < hi if hi < 1 else p <= hi)
        if mask.sum() == 0:
            continue
        total += mask.mean() * abs(y[mask].mean() - p[mask].mean())
    return float(total)


def contrast(y, p_a, p_b, groups, n_boot=5000, seed=20261031):
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


def truth_for(endpoint: str) -> pd.DataFrame:
    truth = pd.read_csv(DATA / endpoint / "test.csv", encoding="utf-8-sig")[["smiles", "y", "inchikey"]]
    split = pd.read_csv(SPLIT, encoding="utf-8-sig")
    split = split[split["endpoint"] == endpoint][["inchikey", "scaffold_key"]]
    out = truth.merge(split, on="inchikey", how="left", validate="one_to_one")
    if out["scaffold_key"].isna().any():
        raise ValueError(f"{endpoint}: missing scaffold keys")
    return out


def load_arm(endpoint: str, arm: str, truth: pd.DataFrame):
    frames = []
    for seed in SEEDS:
        path = RUNS / f"{endpoint}_{arm}_s{seed}" / "pred_test.csv"
        df = pd.read_csv(path)[["inchikey", "y"]].rename(columns={"y": f"p{seed}"})
        if df["inchikey"].duplicated().any():
            raise ValueError(f"duplicate inchikey in {path}")
        frames.append(df.set_index("inchikey"))
    merged = pd.concat(frames, axis=1, join="outer")
    if merged.isna().any().any():
        raise ValueError(f"{endpoint}/{arm}: missing predictions across seeds")
    merged["p"] = merged[[f"p{s}" for s in SEEDS]].mean(axis=1)
    out = truth[["inchikey", "y"]].merge(merged[["p"]].reset_index(), on="inchikey", how="left")
    if out["p"].isna().any():
        raise ValueError(f"{endpoint}/{arm}: test compounds without predictions")
    return out["y"].to_numpy(dtype=int), out["p"].to_numpy(dtype=float)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoints", default=",".join(ENDPOINTS))
    ap.add_argument("--tag", default="second_split_all_results")
    args = ap.parse_args()
    endpoints = tuple(x.strip() for x in args.endpoints.split(",") if x.strip())
    report = {}
    rows = []
    for endpoint in endpoints:
        truth = truth_for(endpoint)
        y = truth["y"].to_numpy(dtype=int)
        groups = truth["scaffold_key"].to_numpy()
        probs = {}
        report[endpoint] = {
            "split": {"n": int(len(y)), "pos": int(y.sum()),
                      "scaffolds": int(len(np.unique(groups)))},
            "arms": {},
            "contrasts": {},
        }
        for arm in ARMS:
            y_arm, p = load_arm(endpoint, arm, truth)
            per_seed = []
            for seed in SEEDS:
                part = pd.read_csv(RUNS / f"{endpoint}_{arm}_s{seed}" / "pred_test.csv")
                part = truth[["inchikey", "y"]].merge(
                    part[["inchikey", "y"]].rename(columns={"y": "p"}), on="inchikey"
                )
                per_seed.append(roc_auc_score(part["y"], part["p"]))
            probs[arm] = (y_arm, p)
            report[endpoint]["arms"][arm] = {
                "auc_ensemble": float(roc_auc_score(y_arm, p)),
                "auc_seed_mean": float(np.mean(per_seed)),
                "auc_seed_sd": float(np.std(per_seed, ddof=1)),
                "pr_auc": float(average_precision_score(y_arm, p)),
                "mcc": float(matthews_corrcoef(y_arm, (p >= 0.5).astype(int))),
                "brier": float(brier_score_loss(y_arm, p)),
                "ece": ece(y_arm, p),
            }
            rows.append({"endpoint": endpoint, "arm": arm, **report[endpoint]["arms"][arm]})
        for a, b in (("chemeleon", "matched"), ("matched", "scratch"), ("chemeleon", "scratch")):
            ya, pa = probs[a]
            yb, pb = probs[b]
            if not np.array_equal(ya, yb):
                raise ValueError(f"{endpoint}: label order mismatch")
            for level, g in (("compound", None), ("scaffold", groups)):
                report[endpoint]["contrasts"][f"{a}-{b}/{level}"] = contrast(ya, pa, pb, g)
    (REPORTS / f"{args.tag}.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    pd.DataFrame(rows).to_csv(REPORTS / f"{args.tag}_metrics.csv", index=False)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
