"""Analyse the 300-epoch hERG matched/scratch controls against the main matrix."""
import importlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
rb = importlib.import_module("32_robustness")

RUNS_LONG = ROOT / "runs" / "chemprop_long"
SEEDS = (42, 1, 2)
N_BOOT = 5000
SEED = 20261030


def load_long(arm: str) -> pd.DataFrame:
    frames = []
    for seed in SEEDS:
        path = RUNS_LONG / f"herg_{arm}_s{seed}" / "pred_test.csv"
        part = pd.read_csv(path)[["inchikey", "y"]].rename(columns={"y": f"p{seed}"})
        if part["inchikey"].duplicated().any():
            raise ValueError(f"duplicate inchikey in {path}")
        frames.append(part.set_index("inchikey"))
    merged = pd.concat(frames, axis=1, join="outer")
    if merged.isna().any().any():
        raise ValueError(f"{arm}: missing predictions")
    pcols = [f"p{s}" for s in SEEDS]
    out = merged[pcols].mean(axis=1).rename("p").reset_index()
    base = rb.load_ensemble("herg", "chemeleon")[["inchikey", "y", "scaffold_key"]]
    out = base.merge(out, on="inchikey", how="left")
    if out["p"].isna().any():
        raise ValueError(f"{arm}: test compounds without predictions")
    return out


def best_epochs(arm: str) -> list[int]:
    epochs = []
    for seed in SEEDS:
        log = RUNS_LONG / f"herg_{arm}_s{seed}" / "train.log"
        matches = re.findall(r"best-epoch=(\d+)-val_roc", log.read_text(encoding="utf-8", errors="ignore"))
        epochs.append(int(matches[-1]) if matches else -1)
    return epochs


def main():
    base = rb.load_ensemble("herg", "chemeleon")
    y = base["y"].to_numpy(dtype=int)
    groups = base["scaffold_key"].to_numpy()
    probs = {}
    arms = {}
    for arm in ("matched_long", "scratch_long"):
        df = load_long(arm)
        if df["inchikey"].tolist() != base["inchikey"].tolist():
            raise ValueError(f"{arm}: order mismatch")
        p = df["p"].to_numpy(dtype=float)
        probs[arm] = p
        seed_aucs = []
        for seed in SEEDS:
            part = pd.read_csv(RUNS_LONG / f"herg_{arm}_s{seed}" / "pred_test.csv")[["inchikey", "y"]].rename(columns={"y": "p"})
            part = base[["inchikey", "y"]].merge(part, on="inchikey", how="left")
            seed_aucs.append(roc_auc_score(part["y"], part["p"]))
        m = rb.point_metrics(y, p)
        arms[arm] = {
            **m,
            "auc_seed_mean": float(np.mean(seed_aucs)),
            "auc_seed_sd": float(np.std(seed_aucs, ddof=1)),
            "best_epochs": best_epochs(arm),
            "n_seeds": len(SEEDS),
        }

    for name in ("matched", "scratch"):
        probs[f"primary_{name}"] = rb.load_ensemble("herg", name)["p"].to_numpy(dtype=float)
    probs["chemeleon"] = base["p"].to_numpy(dtype=float)

    contrasts = []
    pairs = [
        ("chemeleon", "matched_long"),
        ("matched_long", "scratch_long"),
        ("primary_matched", "matched_long"),
        ("primary_scratch", "scratch_long"),
    ]
    for a, b in pairs:
        for level, g in (("compound", None), ("scaffold", groups)):
            r = rb.contrast(y, probs[a], probs[b], g, N_BOOT, SEED)
            contrasts.append({"A": a, "B": b, "level": level,
                              "n_units": int(len(y) if g is None else len(np.unique(g))), **r})

    out = {"arms": arms, "contrasts": contrasts}
    (ROOT / "reports" / "long_budget.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    pd.DataFrame(contrasts).to_csv(ROOT / "reports" / "long_budget_contrasts.csv", index=False)
    print(json.dumps(arms, indent=2))
    print(pd.DataFrame(contrasts).to_string(index=False))


if __name__ == "__main__":
    main()
