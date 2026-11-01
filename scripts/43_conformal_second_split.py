"""Conformal coverage audit on the second Ames scaffold split.

Mirrors the primary protocol: calibrate on the early-stopping validation split
and evaluate on test, versus exchangeable 50/50 controls inside test.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs" / "chemprop_second"
DATA = ROOT / "data" / "chemprop_second"
SPLIT = ROOT / "data" / "processed" / "global_split.csv"
REPORTS = ROOT / "reports"
SEEDS = (42, 1, 2)
ARMS = ("chemeleon", "matched", "scratch")


def load_arm(endpoint: str, arm: str, split: str) -> pd.DataFrame:
    truth = pd.read_csv(DATA / endpoint / f"{split}.csv", encoding="utf-8-sig")[
        ["smiles", "y", "inchikey"]
    ]
    frames = []
    for seed in SEEDS:
        path = RUNS / f"{endpoint}_{arm}_s{seed}" / f"pred_{split}.csv"
        pred = pd.read_csv(path)[["inchikey", "y"]].rename(columns={"y": f"p{seed}"})
        if pred["inchikey"].duplicated().any():
            raise ValueError(f"duplicate inchikey in {path}")
        frames.append(pred.set_index("inchikey"))
    merged = pd.concat(frames, axis=1, join="outer")
    if merged.isna().any().any():
        raise ValueError(f"{endpoint}/{split}: missing predictions across seeds")
    merged["p"] = merged[[f"p{s}" for s in SEEDS]].mean(axis=1)
    out = truth.merge(merged[["p"]].reset_index(), on="inchikey", how="left")
    if out["p"].isna().any():
        raise ValueError(f"{endpoint}/{split}: compounds without predictions")
    scaf = pd.read_csv(SPLIT, encoding="utf-8-sig")
    scaf = scaf[scaf["endpoint"] == endpoint][["inchikey", "scaffold_key"]]
    out = out.merge(scaf, on="inchikey", how="left", validate="one_to_one")
    if out["scaffold_key"].isna().any():
        raise ValueError(f"{endpoint}/{split}: missing scaffold keys")
    return out


def scores(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    return 1.0 - np.where(y == 1, p, 1.0 - p)


def q_standard(s: np.ndarray, alpha: float) -> float:
    n = len(s)
    k = min(int(np.ceil((n + 1) * (1 - alpha))), n)
    return float(np.sort(s)[k - 1])


def coverage(p: np.ndarray, y: np.ndarray, q: float) -> tuple[float, float]:
    grid = np.stack([1 - p, p], axis=1)
    in_set = (1.0 - grid) <= q + 1e-12
    return float(in_set[np.arange(len(y)), y].mean()), float(in_set.sum(axis=1).mean())


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    p = k / n
    den = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return centre - half, centre + half


def split_halves(groups: np.ndarray, rng: np.random.Generator, by_group: bool):
    idx = np.arange(len(groups))
    if by_group:
        uniq = np.unique(groups)
        rng.shuffle(uniq)
        cal_groups = uniq[: len(uniq) // 2]
        cal = np.where(np.isin(groups, cal_groups))[0]
        ev = np.where(~np.isin(groups, cal_groups))[0]
    else:
        rng.shuffle(idx)
        cal, ev = idx[: len(idx) // 2], idx[len(idx) // 2 :]
    return cal, ev


def half_control(p, y, groups, rng, by_group, alpha, n_rep=200):
    cov, size = [], []
    for _ in range(n_rep):
        cal, ev = split_halves(groups, rng, by_group)
        if len(np.unique(y[cal])) < 2 or len(np.unique(y[ev])) < 2:
            continue
        q = q_standard(scores(p[cal], y[cal]), alpha)
        c, s = coverage(p[ev], y[ev], q)
        cov.append(c)
        size.append(s)
    cov = np.asarray(cov)
    return {
        "coverage": float(cov.mean()),
        "ci_low": float(np.percentile(cov, 2.5)),
        "ci_high": float(np.percentile(cov, 97.5)),
        "set_size": float(np.mean(size)),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="ames")
    ap.add_argument("--alpha", type=float, default=0.1)
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--tag", default="conformal_second_split")
    args = ap.parse_args()
    arms = tuple(x.strip() for x in args.arms.split(",") if x.strip())

    report = {"endpoint": args.endpoint, "alpha": args.alpha, "arms": {}}
    rows = []
    for arm in arms:
        valid = load_arm(args.endpoint, arm, "valid")
        test = load_arm(args.endpoint, arm, "test")
        yv = valid["y"].to_numpy(dtype=int)
        yt = test["y"].to_numpy(dtype=int)
        pv = valid["p"].to_numpy(dtype=float)
        pt = test["p"].to_numpy(dtype=float)
        g = test["scaffold_key"].to_numpy()
        q = q_standard(scores(pv, yv), args.alpha)
        cov, size = coverage(pt, yt, q)
        ci_low, ci_high = wilson(int(round(cov * len(yt))), len(yt))
        rand = half_control(pt, yt, g, np.random.default_rng(1), False, args.alpha)
        scaf = half_control(pt, yt, g, np.random.default_rng(2), True, args.alpha)
        report["arms"][arm] = {
            "valid_n": int(len(yv)),
            "test_n": int(len(yt)),
            "test_scaffolds": int(len(np.unique(g))),
            "valid_auc": float(roc_auc_score(yv, pv)),
            "test_auc": float(roc_auc_score(yt, pt)),
            "valid_brier": float(brier_score_loss(yv, pv)),
            "test_brier": float(brier_score_loss(yt, pt)),
            "deployed": {"coverage": cov, "wilson_low": ci_low, "wilson_high": ci_high,
                         "set_size": size, "q": q},
            "random_50_50": rand,
            "scaffold_50_50": scaf,
        }
        rows.append({
            "arm": arm,
            "valid_auc": report["arms"][arm]["valid_auc"],
            "test_auc": report["arms"][arm]["test_auc"],
            "valid_brier": report["arms"][arm]["valid_brier"],
            "test_brier": report["arms"][arm]["test_brier"],
            "coverage": cov,
            "coverage_low": ci_low,
            "coverage_high": ci_high,
            "set_size": size,
            "random_5050": rand["coverage"],
            "random_ci_low": rand["ci_low"],
            "random_ci_high": rand["ci_high"],
            "scaffold_5050": scaf["coverage"],
            "scaffold_ci_low": scaf["ci_low"],
            "scaffold_ci_high": scaf["ci_high"],
        })
    (REPORTS / f"{args.tag}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    pd.DataFrame(rows).to_csv(REPORTS / f"{args.tag}.csv", index=False)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
