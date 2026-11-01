"""Cluster-robust contrasts, multiplicity control, and a complete metric table."""
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
RUNS = ROOT / "runs" / "chemprop"
REPORTS = ROOT / "reports"
SEEDS = (42, 1, 2)
MODELS = ("chemeleon", "matched", "scratch")
CONTRASTS = (("chemeleon", "matched"), ("matched", "scratch"), ("chemeleon", "scratch"))
CLASSICAL_DIR = ROOT / "runs" / "classical"
CLASSICAL_BEST = {"herg": "logreg", "dili": "rf", "ames": "rf"}


def ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (p >= lo) & (p < hi if hi < 1 else p <= hi)
        if mask.sum() == 0:
            continue
        total += mask.mean() * abs(y[mask].mean() - p[mask].mean())
    return float(total)


def load_test(endpoint: str) -> pd.DataFrame:
    df = pd.read_csv(SPLIT, encoding="utf-8-sig")
    te = df[(df["endpoint"] == endpoint) & (df["split"] == "test")].copy()
    return te[["inchikey", "y", "scaffold_key"]].reset_index(drop=True)


def load_ensemble(endpoint: str, model: str, seeds=SEEDS) -> pd.DataFrame:
    frames = []
    for seed in seeds:
        path = RUNS / f"{endpoint}_{model}_s{seed}" / "pred_test.csv"
        if not path.exists():
            raise FileNotFoundError(path)
        part = pd.read_csv(path)[["inchikey", "y"]].rename(columns={"y": f"p{seed}"})
        if part["inchikey"].duplicated().any():
            raise ValueError(f"duplicate inchikey in {path}")
        frames.append(part.set_index("inchikey"))
    merged = pd.concat(frames, axis=1, join="outer")
    if merged.isna().any().any():
        missing = merged[merged.isna().any(axis=1)]
        raise ValueError(f"{endpoint}/{model}: missing predictions for\n{missing.head()}")
    pcols = [f"p{s}" for s in seeds]
    out = merged[pcols].mean(axis=1).rename("p").reset_index()
    test = load_test(endpoint)
    out = test.merge(out, on="inchikey", how="left")
    if out["p"].isna().any():
        raise ValueError(f"{endpoint}/{model}: test compounds without predictions")
    return out


def point_metrics(y: np.ndarray, p: np.ndarray) -> dict:
    pred = (p >= 0.5).astype(int)
    return {
        "n": int(len(y)),
        "pos": int(y.sum()),
        "auc": float(roc_auc_score(y, p)),
        "pr_auc": float(average_precision_score(y, p)),
        "acc": float((pred == y).mean()),
        "mcc": float(matthews_corrcoef(y, pred)),
        "brier": float(brier_score_loss(y, p)),
        "ece": ece(y, p),
    }


def resample_indices(groups: np.ndarray | None, n: int, rng) -> np.ndarray:
    if groups is None:
        return rng.integers(0, n, n)
    uniq = np.unique(groups)
    picked = rng.choice(uniq, len(uniq), replace=True)
    return np.concatenate([np.where(groups == g)[0] for g in picked])


def contrast(
    y: np.ndarray,
    p_a: np.ndarray,
    p_b: np.ndarray,
    groups: np.ndarray | None,
    n_boot: int,
    seed: int,
) -> dict:
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(n_boot):
        idx = resample_indices(groups, len(y), rng)
        yy = y[idx]
        if len(np.unique(yy)) < 2:
            continue
        diffs.append(roc_auc_score(yy, p_a[idx]) - roc_auc_score(yy, p_b[idx]))
    d = np.asarray(diffs)
    lo, hi = np.percentile(d, [2.5, 97.5])
    p = 2.0 * min(float((d <= 0).mean()), float((d >= 0).mean()))
    return {
        "delta": float(d.mean()),
        "ci_low": float(lo),
        "ci_high": float(hi),
        "p": float(min(1.0, p)),
        "n_boot_ok": int(len(d)),
    }


def bh(pvals: np.ndarray) -> np.ndarray:
    p = np.asarray(pvals, dtype=float)
    order = np.argsort(p)
    ranked = p[order]
    m = len(p)
    q = ranked * m / np.arange(1, m + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty_like(q)
    out[order] = np.minimum(q, 1.0)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-boot", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=20261030)
    args = ap.parse_args()

    metric_rows = []
    contrast_rows = []

    classical = pd.read_csv(REPORTS / "baselines_classical.csv", encoding="utf-8-sig")
    classical = classical[classical["split"] == "test"]

    for endpoint in ("herg", "dili", "ames"):
        probs = {}
        for model in MODELS:
            df = load_ensemble(endpoint, model)
            y = df["y"].to_numpy(dtype=int)
            p = df["p"].to_numpy(dtype=float)
            probs[model] = (df, y, p)
            m = point_metrics(y, p)
            metric_rows.append({"endpoint": endpoint, "model": f"chemprop_{model}",
                                "seeds": len(SEEDS), "source": "seed ensemble", **m})
        drop_paths = [
            RUNS / f"{endpoint}_matched_dropout_s{seed}" / "pred_test.csv"
            for seed in SEEDS
        ]
        if all(path.exists() for path in drop_paths):
            df = load_ensemble(endpoint, "matched_dropout")
            y = df["y"].to_numpy(dtype=int)
            p = df["p"].to_numpy(dtype=float)
            probs["matched_dropout"] = (df, y, p)
            m = point_metrics(y, p)
            metric_rows.append({"endpoint": endpoint, "model": "chemprop_matched_dropout",
                                "seeds": len(SEEDS), "source": "seed ensemble", **m})

        base = probs["chemeleon"][0]
        groups = base["scaffold_key"].to_numpy()
        y = base["y"].to_numpy(dtype=int)
        for a, b in CONTRASTS:
            df_a, _, p_a = probs[a]
            df_b, _, p_b = probs[b]
            if not (df_a["inchikey"].tolist() == df_b["inchikey"].tolist() == base["inchikey"].tolist()):
                raise ValueError(f"order mismatch for {endpoint} {a}/{b}")
            for level, g in (("compound", None), ("scaffold", groups)):
                r = contrast(y, p_a, p_b, g, args.n_boot, args.seed)
                contrast_rows.append({
                    "endpoint": endpoint,
                    "contrast": f"{a}-{b}",
                    "level": level,
                    "n_units": int(len(y) if g is None else len(np.unique(g))),
                    "family": "capacity",
                    **r,
                })
        if "matched_dropout" in probs:
            df_b, _, p_b = probs["matched_dropout"]
            if not (df_b["inchikey"].tolist() == base["inchikey"].tolist()):
                raise ValueError(f"order mismatch for {endpoint} matched_dropout")
            for level, g in (("compound", None), ("scaffold", groups)):
                r = contrast(y, probs["chemeleon"][2], p_b, g, args.n_boot, args.seed)
                contrast_rows.append({
                    "endpoint": endpoint,
                    "contrast": "chemeleon-matched_dropout",
                    "level": level,
                    "n_units": int(len(y) if g is None else len(np.unique(g))),
                    "family": "dropout",
                    **r,
                })

        best = CLASSICAL_BEST[endpoint]
        cdf = pd.read_csv(CLASSICAL_DIR / f"{endpoint}_{best}_test.csv")
        cdf = base[["inchikey", "y", "scaffold_key"]].merge(
            cdf[["inchikey", "p"]], on="inchikey", how="left"
        )
        if cdf["p"].isna().any():
            raise ValueError(f"{endpoint}: classical test compounds without predictions")
        p_c = cdf["p"].to_numpy(dtype=float)
        for level, g in (("compound", None), ("scaffold", groups)):
            r = contrast(y, probs["chemeleon"][2], p_c, g, args.n_boot, args.seed)
            contrast_rows.append({
                "endpoint": endpoint,
                "contrast": f"chemeleon-classical_{best}",
                "level": level,
                "n_units": int(len(y) if g is None else len(np.unique(g))),
                "family": "classical",
                **r,
            })

    # Classical baselines: metrics only (predictions are not persisted), one fit each.
    for _, row in classical.iterrows():
        metric_rows.append({
            "endpoint": row["endpoint"],
            "model": f"classical_{row['model']}",
            "seeds": 1,
            "source": "single fit",
            "n": int(row["n"]),
            "pos": int(row["pos"]),
            "auc": float(row["auc"]),
            "pr_auc": float(row["pr_auc"]),
            "acc": float(row["acc"]),
            "mcc": float(row["mcc"]),
            "brier": float(row["brier"]),
            "ece": float(row["ece"]),
        })

    metrics = pd.DataFrame(metric_rows)
    contrasts = pd.DataFrame(contrast_rows)

    # Multiplicity within each family and resampling level.
    for family, size in (("capacity", 9), ("classical", 3)):
        for level in ("compound", "scaffold"):
            mask = (contrasts["family"] == family) & (contrasts["level"] == level)
            if mask.sum() == 0:
                continue
            p = contrasts.loc[mask, "p"].to_numpy()
            if len(p) != size:
                raise ValueError(f"{family}/{level}: expected {size} tests, got {len(p)}")
            contrasts.loc[mask, "p_bonferroni"] = np.minimum(p * len(p), 1.0)
            contrasts.loc[mask, "q_bh"] = bh(p)

    metrics.to_csv(REPORTS / "main_metrics.csv", index=False)
    contrasts.to_csv(REPORTS / "cluster_bootstrap.csv", index=False)
    print(metrics.to_string(index=False))
    print()
    print(contrasts.to_string(index=False))


if __name__ == "__main__":
    main()
