"""Seed-level uncertainty, minimum detectable effects, and connectivity-level corpus exposure."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
PRETRAIN = ROOT / "data" / "external" / "chemeleon_pretrain" / "pretrain_inchikeys.csv"
SPLIT = ROOT / "data" / "processed" / "global_split.csv"
RUNS = ROOT / "runs" / "chemprop"
REPORTS = ROOT / "reports"
SEEDS = (42, 1, 2)
ENDPOINTS = ("herg", "dili", "ames")
ARMS = ("chemeleon", "matched", "scratch")
N_BOOT = 5000
BOOT_SEED = 20261101
Z_POWER = stats.norm.ppf(0.975) + stats.norm.ppf(0.80)


def load_seed_probs(endpoint: str, arm: str, truth: pd.DataFrame) -> dict[int, np.ndarray]:
    out = {}
    for seed in SEEDS:
        df = pd.read_csv(RUNS / f"{endpoint}_{arm}_s{seed}" / "pred_test.csv")
        merged = truth[["inchikey"]].merge(
            df.set_index("inchikey")["y"].rename("p").reset_index(), on="inchikey", how="left"
        )
        if merged["p"].isna().any():
            raise ValueError(f"{endpoint}/{arm}/s{seed}: missing predictions")
        out[seed] = merged["p"].to_numpy(dtype=float)
    return out


def bootstrap_delta(y, p_a, p_b, groups=None, n_boot=N_BOOT, seed=BOOT_SEED):
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(n_boot):
        if groups is None:
            idx = rng.integers(0, len(y), len(y))
        else:
            uniq = np.unique(groups)
            picked = rng.choice(uniq, len(uniq), replace=True)
            idx = np.concatenate([np.where(groups == x)[0] for x in picked])
        if len(np.unique(y[idx])) < 2:
            continue
        diffs.append(roc_auc_score(y[idx], p_a[idx]) - roc_auc_score(y[idx], p_b[idx]))
    d = np.asarray(diffs)
    lo, hi = np.percentile(d, [2.5, 97.5])
    p = 2.0 * min(float((d <= 0).mean()), float((d >= 0).mean()))
    return {
        "delta": float(roc_auc_score(y, p_a) - roc_auc_score(y, p_b)),
        "ci_low": float(lo),
        "ci_high": float(hi),
        "p": float(min(1.0, p)),
        "boot_sd": float(d.std(ddof=1)),
        "mde_80": float(Z_POWER * d.std(ddof=1)),
        "n_boot": int(len(d)),
    }


def main() -> None:
    pretrain = pd.read_csv(PRETRAIN, dtype=str)["inchikey"]
    keys = set(pretrain)
    conn = set(pretrain.str[:14])
    split = pd.read_csv(SPLIT, encoding="utf-8-sig")
    report: dict = {"seed_level": {}, "power": {}, "connectivity_overlap": {},
                    "connectivity_subset": {}, "exact_subset": {}}

    for endpoint in ENDPOINTS:
        truth = split[(split["endpoint"] == endpoint) & (split["split"] == "test")][
            ["inchikey", "y", "scaffold_key"]
        ].reset_index(drop=True)
        y = truth["y"].to_numpy(dtype=int)
        groups = truth["scaffold_key"].to_numpy()
        seed_probs = {arm: load_seed_probs(endpoint, arm, truth) for arm in ARMS}
        ens = {arm: np.mean([seed_probs[arm][s] for s in SEEDS], axis=0) for arm in ARMS}

        seed_entry = {}
        for a, b in (("chemeleon", "matched"), ("chemeleon", "scratch"), ("matched", "scratch")):
            deltas = []
            for s in SEEDS:
                deltas.append(
                    float(roc_auc_score(y, seed_probs[a][s]) - roc_auc_score(y, seed_probs[b][s]))
                )
            arr = np.asarray(deltas)
            half = float(stats.t.ppf(0.975, len(arr) - 1) * arr.std(ddof=1) / np.sqrt(len(arr)))
            seed_entry[f"{a}-{b}"] = {
                "per_seed": deltas,
                "mean": float(arr.mean()),
                "sd": float(arr.std(ddof=1)),
                "t_ci_low": float(arr.mean() - half),
                "t_ci_high": float(arr.mean() + half),
            }
        report["seed_level"][endpoint] = seed_entry

        power_entry = {}
        for a, b in (("chemeleon", "matched"), ("chemeleon", "scratch"), ("matched", "scratch")):
            power_entry[f"{a}-{b}"] = {
                "compound": bootstrap_delta(y, ens[a], ens[b], None),
                "scaffold": bootstrap_delta(y, ens[a], ens[b], groups),
            }
        report["power"][endpoint] = power_entry

        ikeys = truth["inchikey"].astype(str)
        exact = ikeys.isin(keys).to_numpy()
        conn_mask = ikeys.str[:14].isin(conn).to_numpy()
        report["connectivity_overlap"][endpoint] = {
            "n": int(len(ikeys)),
            "exact": int(exact.sum()),
            "exact_frac": float(exact.mean()),
            "connectivity": int(conn_mask.sum()),
            "connectivity_frac": float(conn_mask.mean()),
            "connectivity_clean": int((~conn_mask).sum()),
            "connectivity_clean_pos": int(y[~conn_mask].sum()),
            "connectivity_clean_scaffolds": int(len(np.unique(groups[~conn_mask]))),
        }
        keep = ~conn_mask
        if keep.sum() >= 10 and y[keep].sum() >= 2:
            entry = {"n": int(keep.sum()), "pos": int(y[keep].sum()),
                     "auc": {arm: float(roc_auc_score(y[keep], ens[arm][keep])) for arm in ARMS}}
            keep_keys = ("delta", "ci_low", "ci_high", "p")
            yk, gk = y[keep], groups[keep]
            for a, b in (("chemeleon", "matched"), ("chemeleon", "scratch")):
                comp = bootstrap_delta(yk, ens[a][keep], ens[b][keep], None)
                scaf = bootstrap_delta(yk, ens[a][keep], ens[b][keep], gk)
                entry[f"{a}-{b}"] = {
                    "compound": {k: comp[k] for k in keep_keys},
                    "scaffold": {k: scaf[k] for k in keep_keys},
                }
            report["connectivity_subset"][endpoint] = entry

        keep = ~exact
        if keep.sum() >= 10 and y[keep].sum() >= 2:
            entry = {"n": int(keep.sum()), "pos": int(y[keep].sum()),
                     "auc": {arm: float(roc_auc_score(y[keep], ens[arm][keep])) for arm in ARMS}}
            keep_keys = ("delta", "ci_low", "ci_high", "p")
            yk, gk = y[keep], groups[keep]
            for a, b in (("chemeleon", "matched"), ("chemeleon", "scratch")):
                comp = bootstrap_delta(yk, ens[a][keep], ens[b][keep], None)
                scaf = bootstrap_delta(yk, ens[a][keep], ens[b][keep], gk)
                entry[f"{a}-{b}"] = {
                    "compound": {k: comp[k] for k in keep_keys},
                    "scaffold": {k: scaf[k] for k in keep_keys},
                }
            report["exact_subset"][endpoint] = entry

    (REPORTS / "power_seed_exposure.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
