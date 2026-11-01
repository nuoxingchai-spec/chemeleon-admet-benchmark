"""Coverage of the deployment models under contaminated vs clean calibration.

Same three deploy seeds, same ensemble probabilities. The early-stopping (es)
slice is carved from train at scaffold level, so calibrating on it reuses the
selection split; the global validation split (calib) is never seen during
training or early stopping and is scaffold-disjoint from test.
"""
from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
cs = import_module("11_conformal_scaffold")

DATA = ROOT / "data" / "chemprop_deploy"
RUNS = ROOT / "runs" / "deploy"
REPORTS = ROOT / "reports"
GLOBAL = ROOT / "data" / "processed" / "global_split.csv"
SEEDS = (1, 2, 42)
ALPHAS = (0.10, 0.20)
BOOT = 5000
BOOT_SEED = 20261101


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return float(centre - half), float(centre + half)


def load_split(endpoint: str, split: str) -> tuple[np.ndarray, np.ndarray, pd.Series]:
    truth = pd.read_csv(DATA / endpoint / f"{split}.csv")[["inchikey", "y"]]
    probs = []
    for seed in SEEDS:
        pred = pd.read_csv(RUNS / f"{endpoint}_s{seed}" / f"pred_{split}.csv")
        pred = pred.rename(columns={"y": "p"})
        merged = truth.merge(pred[["inchikey", "p"]], on="inchikey", how="left")
        if merged["p"].isna().any():
            raise ValueError(f"missing predictions for {endpoint}/{split}/s{seed}")
        probs.append(merged["p"].to_numpy(float))
    return np.mean(probs, axis=0), truth["y"].to_numpy(int), truth["inchikey"]


def scaffold_cluster_ci(hit: np.ndarray, groups: pd.Series, seed: int) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    uniq = groups.unique()
    index = {g: np.flatnonzero(groups.to_numpy() == g) for g in uniq}
    vals = np.empty(BOOT)
    for b in range(BOOT):
        pick = rng.choice(len(uniq), len(uniq), replace=True)
        idx = np.concatenate([index[uniq[j]] for j in pick])
        vals[b] = hit[idx].mean()
    return float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))


def evaluate(cal_p, cal_y, test_p, test_y, groups, alpha: float) -> dict:
    q = cs.q_standard(cs.conformal_scores(cal_p, cal_y), alpha)
    coverage, set_size = cs.coverage_sets(test_p, test_y, q)
    n = len(test_y)
    k = int(round(coverage * n))
    lo, hi = wilson(k, n)
    grid = np.stack([1 - test_p, test_p], axis=1)
    hit = ((1 - grid) <= q + 1e-12)[np.arange(n), test_y]
    clo, chi = scaffold_cluster_ci(hit, groups, BOOT_SEED)
    return {
        "alpha": alpha,
        "nominal": 1 - alpha,
        "q": q,
        "coverage": coverage,
        "wilson": [lo, hi],
        "cluster_bootstrap": [clo, chi],
        "set_size": set_size,
    }


def main() -> None:
    endpoint = "ames"
    split = {s: load_split(endpoint, s) for s in ("es", "calib", "test")}
    scaf = pd.read_csv(GLOBAL, encoding="utf-8-sig")
    scaf = scaf[scaf["endpoint"] == endpoint].set_index("inchikey")["scaffold_key"]
    groups = split["test"][2].map(scaf)
    if groups.isna().any():
        raise ValueError("test inchikey missing from global split")

    es_p, es_y, _ = split["es"]
    cal_p, cal_y, _ = split["calib"]
    test_p, test_y, _ = split["test"]

    out = {
        "endpoint": endpoint,
        "model": "deploy CheMeleon (fit / es / calib / test), 3-seed ensemble",
        "n": {k: len(v[1]) for k, v in split.items()},
        "auc": {k: float(roc_auc_score(v[1], v[0])) for k, v in split.items()},
        "brier": {k: float(brier_score_loss(v[1], v[0])) for k, v in split.items()},
        "calibration": {},
        "note": ("Within-model contrast: es reuses the early-stopping split; "
                 "calib is the global validation split, untouched by training "
                 "and by early stopping and scaffold-disjoint from test."),
    }
    for alpha in ALPHAS:
        out["calibration"][f"alpha_{alpha:.2f}"] = {
            "es_to_test": evaluate(es_p, es_y, test_p, test_y, groups, alpha),
            "calib_to_test": evaluate(cal_p, cal_y, test_p, test_y, groups, alpha),
        }
    (REPORTS / "deploy_clean_calibration.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
