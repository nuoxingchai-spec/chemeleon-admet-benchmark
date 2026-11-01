"""Aggregate second-FM (ChemBERTa) arms and compute capacity contrasts."""
from __future__ import annotations

import argparse
import importlib
import json
import sys
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
sys.path.insert(0, str(ROOT / "scripts"))
rb = importlib.import_module("32_robustness")

SPLIT = ROOT / "data" / "processed" / "global_split.csv"
DATA = ROOT / "data" / "chemprop"
SEEDS = (42, 1, 2)
ENDPOINTS = ("herg", "dili", "ames")
ARMS = ("pretrained", "matched", "scratch")
N_BOOT = 5000
SEED = 20261031
MARGIN = 0.06


def ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (p >= lo) & (p < hi if hi < 1 else p <= hi)
        if mask.sum() == 0:
            continue
        total += mask.mean() * abs(y[mask].mean() - p[mask].mean())
    return float(total)


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


def load_base(endpoint: str) -> pd.DataFrame:
    test = pd.read_csv(DATA / endpoint / "test.csv", encoding="utf-8-sig")[["smiles", "y", "inchikey"]]
    split = pd.read_csv(SPLIT, encoding="utf-8-sig")
    split = split[split["endpoint"] == endpoint][["inchikey", "scaffold_key"]]
    out = test.merge(split, on="inchikey", how="left", validate="one_to_one")
    if out["scaffold_key"].isna().any():
        raise ValueError(f"{endpoint}: missing scaffold keys")
    return out


def load_ensemble(runs: Path, endpoint: str, arm: str):
    frames = []
    for seed in SEEDS:
        path = runs / f"{endpoint}_{arm}_s{seed}" / "pred_test.csv"
        part = pd.read_csv(path)[["inchikey", "y"]].rename(columns={"y": f"p{seed}"})
        if part["inchikey"].duplicated().any():
            raise ValueError(f"duplicate inchikey in {path}")
        frames.append(part.set_index("inchikey"))
    merged = pd.concat(frames, axis=1, join="outer")
    if merged.isna().any().any():
        raise ValueError(f"{endpoint}/{arm}: missing predictions")
    pcols = [f"p{s}" for s in SEEDS]
    out = merged[pcols].mean(axis=1).rename("p").reset_index()
    base = load_base(endpoint)
    out = base.merge(out, on="inchikey", how="left", validate="one_to_one")
    if out["p"].isna().any():
        raise ValueError(f"{endpoint}/{arm}: test compounds without predictions")
    return out


def seed_metrics(runs: Path, endpoint: str, arm: str) -> list[dict]:
    base = load_base(endpoint)
    out = []
    for seed in SEEDS:
        path = runs / f"{endpoint}_{arm}_s{seed}" / "pred_test.csv"
        part = pd.read_csv(path)[["inchikey", "y"]].rename(columns={"y": "p"})
        merged = base.merge(part, on="inchikey", how="left", validate="one_to_one")
        meta = json.loads((runs / f"{endpoint}_{arm}_s{seed}" / "metrics.json").read_text())
        out.append({
            "seed": seed,
            "auc": float(roc_auc_score(merged["y"], merged["p"])),
            "brier": float(brier_score_loss(merged["y"], merged["p"])),
            "ece": ece(merged["y"].to_numpy(), merged["p"].to_numpy()),
            "best_epoch": meta["best_epoch"],
            "best_valid_auc": meta["best_valid_auc"],
            "params": meta["params"],
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=str(ROOT / "runs" / "chemberta"))
    ap.add_argument("--tag", default="second_fm")
    ap.add_argument("--endpoints", default=",".join(ENDPOINTS))
    args = ap.parse_args()
    runs = Path(args.runs)
    endpoints = tuple(x.strip() for x in args.endpoints.split(",") if x.strip())

    results: dict[str, dict] = {}
    rows = []
    contrasts = []
    for endpoint in endpoints:
        ensembles = {}
        for arm in ARMS:
            df = load_ensemble(runs, endpoint, arm)
            ensembles[arm] = df["p"].to_numpy(dtype=float)
            sm = seed_metrics(runs, endpoint, arm)
            m = point_metrics(df["y"].to_numpy(dtype=int), ensembles[arm])
            results.setdefault(endpoint, {})[arm] = {
                **m,
                "auc_seed_mean": float(np.mean([x["auc"] for x in sm])),
                "auc_seed_sd": float(np.std([x["auc"] for x in sm], ddof=1)),
                "params": sm[0]["params"],
                "best_epochs": [x["best_epoch"] for x in sm],
                "seed_metrics": sm,
            }
            rows.append({"endpoint": endpoint, "arm": arm, **m,
                         "auc_seed_mean": results[endpoint][arm]["auc_seed_mean"],
                         "auc_seed_sd": results[endpoint][arm]["auc_seed_sd"],
                         "params": sm[0]["params"]})
        y = load_base(endpoint)["y"].to_numpy(dtype=int)
        groups = load_base(endpoint)["scaffold_key"].to_numpy()
        for a, b in (("pretrained", "matched"), ("matched", "scratch"), ("pretrained", "scratch")):
            for level, g in (("compound", None), ("scaffold", groups)):
                r = rb.contrast(y, ensembles[a], ensembles[b], g, N_BOOT, SEED)
                # 90% interval on the same draws, for TOST.
                rng = np.random.default_rng(SEED)
                diffs = []
                for _ in range(N_BOOT):
                    idx = rb.resample_indices(g, len(y), rng)
                    if len(np.unique(y[idx])) < 2:
                        continue
                    diffs.append(roc_auc_score(y[idx], ensembles[a][idx]) - roc_auc_score(y[idx], ensembles[b][idx]))
                d = np.asarray(diffs)
                lo90, hi90 = np.percentile(d, [5, 95])
                p_tost = max(float((d <= -MARGIN).mean()), float((d >= MARGIN).mean()))
                contrasts.append({
                    "endpoint": endpoint, "A": a, "B": b, "level": level,
                    "n_units": int(len(y) if g is None else len(np.unique(g))),
                    "delta": r["delta"], "ci_low": r["ci_low"], "ci_high": r["ci_high"],
                    "p": r["p"], "ci90_low": float(lo90), "ci90_high": float(hi90),
                    "equivalent": bool(lo90 > -MARGIN and hi90 < MARGIN),
                    "p_tost": float(p_tost),
                })

    out = {"runs": str(runs), "results": results, "contrasts": contrasts}
    (ROOT / "reports" / f"{args.tag}_results.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    pd.DataFrame(rows).to_csv(ROOT / "reports" / f"{args.tag}_metrics.csv", index=False)
    pd.DataFrame(contrasts).to_csv(ROOT / "reports" / f"{args.tag}_contrasts.csv", index=False)
    print(json.dumps(results, indent=2))
    print(pd.DataFrame(contrasts).to_string(index=False))


if __name__ == "__main__":
    main()
