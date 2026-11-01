"""Audit overlap between the CheMeleon pretraining corpus and benchmark compounds,
and re-check the headline contrasts on non-overlapping test compounds."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
PRETRAIN = ROOT / "data" / "external" / "chemeleon_pretrain" / "pretrain_inchikeys.csv"
SPLIT = ROOT / "data" / "processed" / "global_split.csv"
RUNS = ROOT / "runs" / "chemprop"
SECOND = ROOT / "data" / "chemprop_second"
REPORTS = ROOT / "reports"
SEEDS = (42, 1, 2)
ENDPOINTS = ("herg", "dili", "ames")
ARMS = ("chemeleon", "matched", "scratch")


def contrast(y, p_a, p_b, mask, groups=None, n_boot=5000, seed=20261031):
    rng = np.random.default_rng(seed)
    y, p_a, p_b = y[mask], p_a[mask], p_b[mask]
    g = None if groups is None else groups[mask]
    diffs = []
    for _ in range(n_boot):
        if g is None:
            idx = rng.integers(0, len(y), len(y))
        else:
            uniq = np.unique(g)
            picked = rng.choice(uniq, len(uniq), replace=True)
            idx = np.concatenate([np.where(g == x)[0] for x in picked])
        if len(np.unique(y[idx])) < 2:
            continue
        diffs.append(roc_auc_score(y[idx], p_a[idx]) - roc_auc_score(y[idx], p_b[idx]))
    d = np.asarray(diffs)
    lo, hi = np.percentile(d, [2.5, 97.5])
    p = 2.0 * min(float((d <= 0).mean()), float((d >= 0).mean()))
    return {"delta": float(d.mean()), "ci_low": float(lo), "ci_high": float(hi),
            "p": float(min(1.0, p))}


def load_probs(endpoint: str, arm: str, truth: pd.DataFrame) -> np.ndarray:
    frames = []
    for seed in SEEDS:
        df = pd.read_csv(RUNS / f"{endpoint}_{arm}_s{seed}" / "pred_test.csv")
        frames.append(df.set_index("inchikey")["y"].rename(f"p{seed}"))
    merged = pd.concat(frames, axis=1)
    merged["p"] = merged[[f"p{s}" for s in SEEDS]].mean(axis=1)
    out = truth[["inchikey"]].merge(merged[["p"]].reset_index(), on="inchikey", how="left")
    if out["p"].isna().any():
        raise ValueError(f"{endpoint}/{arm}: missing predictions")
    return out["p"].to_numpy(dtype=float)


def main() -> None:
    keys = set(pd.read_csv(PRETRAIN, dtype=str)["inchikey"])
    split = pd.read_csv(SPLIT, encoding="utf-8-sig")
    report: dict = {"pretrain_unique_inchikeys": len(keys), "splits": {}, "contrasts": {}}

    for endpoint in ENDPOINTS:
        part = split[split["endpoint"] == endpoint]
        entry = {}
        for name in ("train", "valid", "test"):
            frame = part[part["split"] == name]
            ikeys = frame["inchikey"].astype(str)
            exact = ikeys.isin(keys)
            skeleton = ikeys.str[:14].isin({k[:14] for k in keys})
            entry[name] = {
                "n": int(len(frame)),
                "exact_overlap": int(exact.sum()),
                "exact_frac": float(exact.mean()),
                "skeleton_overlap": int(skeleton.sum()),
                "skeleton_frac": float(skeleton.mean()),
            }
        report["splits"][endpoint] = entry

    report["second_split_test"] = {}
    for endpoint in ENDPOINTS:
        ikeys = pd.read_csv(SECOND / endpoint / "test.csv", encoding="utf-8-sig")["inchikey"].astype(str)
        exact = ikeys.isin(keys)
        report["second_split_test"][endpoint] = {
            "n": int(len(ikeys)),
            "exact_overlap": int(exact.sum()),
            "exact_frac": float(exact.mean()),
        }

    ext_path = ROOT / "data" / "chemprop" / "herg_aligned" / "external_clean.csv"
    if ext_path.exists():
        ikeys = pd.read_csv(ext_path, encoding="utf-8-sig")["inchikey"].astype(str)
        report["karim_external_clean"] = {
            "n": int(len(ikeys)),
            "exact_overlap": int(ikeys.isin(keys).sum()),
        }

    pooled = split[split["split"] == "test"]["inchikey"].astype(str).drop_duplicates()
    report["pooled_test"] = {
        "n": int(pooled.nunique()),
        "exact_overlap": int(pooled.isin(keys).sum()),
        "exact_frac": float(pooled.isin(keys).mean()),
    }

    for endpoint in ENDPOINTS:
        truth = split[(split["endpoint"] == endpoint) & (split["split"] == "test")][
            ["inchikey", "y", "scaffold_key"]
        ].reset_index(drop=True)
        y = truth["y"].to_numpy(dtype=int)
        groups = truth["scaffold_key"].to_numpy()
        overlap = truth["inchikey"].astype(str).isin(keys).to_numpy()
        keep = ~overlap
        probs = {arm: load_probs(endpoint, arm, truth) for arm in ARMS}
        entry = {
            "n_test": int(len(y)),
            "n_nonoverlap": int(keep.sum()),
            "pos_nonoverlap": int(y[keep].sum()),
            "scaffolds_nonoverlap": int(len(np.unique(groups[keep]))),
            "full_auc": {arm: float(roc_auc_score(y, probs[arm])) for arm in ARMS},
        }
        if keep.sum() >= 10 and y[keep].sum() >= 2:
            entry["subset_auc"] = {arm: float(roc_auc_score(y[keep], probs[arm][keep])) for arm in ARMS}
            for a, b in (("chemeleon", "matched"), ("chemeleon", "scratch")):
                entry[f"{a}-{b}"] = {
                    "compound": contrast(y, probs[a], probs[b], keep),
                    "scaffold": contrast(y, probs[a], probs[b], keep, groups),
                }
        report["contrasts"][endpoint] = entry

    (REPORTS / "pretrain_overlap.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
