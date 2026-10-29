"""Capacity-controlled contrast: CheMeleon vs same-architecture random-init (2048x6)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from metrics import ece  # noqa: E402

RUNS = ROOT / "runs" / "chemprop"
OUT = ROOT / "reports" / "control_contrast.csv"
PATTERNS = {
    "chemeleon": "{ep}_chemeleon_s*",
    "matched": "{ep}_matched_s*",
    "matched_dropout": "{ep}_matched_dropout_s*",
    "scratch": "{ep}_scratch_s*",
}
CONTRASTS = [
    ("chemeleon", "matched"),
    ("chemeleon", "matched_dropout"),
    ("chemeleon", "scratch"),
    ("matched", "scratch"),
]


def load_seeds(ep: str, model: str) -> dict[int, np.ndarray]:
    out = {}
    for d in sorted(RUNS.glob(PATTERNS[model].format(ep=ep))):
        f = d / "preds.json"
        if not f.exists():
            continue
        j = json.loads(f.read_text())
        seed = int(j["seed"])
        out[seed] = np.array(j["splits"]["test"]["p"], dtype=float)
    return out


def paired(y, pa, pb, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    d = {"auc": [], "ece": [], "brier": []}
    for _ in range(n):
        idx = rng.integers(0, len(y), len(y))
        if len(np.unique(y[idx])) < 2:
            continue
        d["auc"].append(roc_auc_score(y[idx], pa[idx]) - roc_auc_score(y[idx], pb[idx]))
        d["ece"].append(ece(y[idx], pa[idx]) - ece(y[idx], pb[idx]))
        d["brier"].append(brier_score_loss(y[idx], pa[idx]) - brier_score_loss(y[idx], pb[idx]))
    res = {}
    for k, v in d.items():
        v = np.array(v)
        res[f"d_{k}"] = float(v.mean())
        res[f"d_{k}_lo"] = float(np.percentile(v, 2.5))
        res[f"d_{k}_hi"] = float(np.percentile(v, 97.5))
        res[f"d_{k}_p"] = float(2 * min((v <= 0).mean(), (v >= 0).mean()))
    return res


def main():
    data = pd.read_csv(ROOT / "data/processed/global_split.csv", encoding="utf-8-sig")
    rows = []
    for ep in ["herg", "dili", "ames"]:
        y = data[(data.endpoint == ep) & (data.split == "test")]["y"].to_numpy()
        ens, info = {}, {}
        for model in PATTERNS:
            seeds = load_seeds(ep, model)
            seeds = {s: p for s, p in seeds.items() if len(p) == len(y)}
            if not seeds:
                continue
            ens[model] = np.mean(list(seeds.values()), axis=0)
            info[model] = {
                "n_seeds": len(seeds),
                "single_auc_mean": float(np.mean([roc_auc_score(y, p) for p in seeds.values()])),
                "single_auc_sd": float(np.std([roc_auc_score(y, p) for p in seeds.values()])),
            }
            for s_txt in seeds:
                run_dir = RUNS / (PATTERNS[model].format(ep=ep).rstrip("*") + str(s_txt))
                ref = json.loads((run_dir / "preds.json").read_text())
                assert np.array_equal(np.array(ref["splits"]["test"]["y"]), y), f"y mismatch {ep} {model} s{s_txt}"
        if "chemeleon" not in ens:
            continue
        for a, b in CONTRASTS:
            if a not in ens or b not in ens:
                continue
            rows.append({
                "endpoint": ep, "model_a": a, "model_b": b, "n": int(len(y)),
                "seeds_a": info[a]["n_seeds"], "seeds_b": info[b]["n_seeds"],
                "single_auc_mean_a": info[a]["single_auc_mean"],
                "single_auc_sd_a": info[a]["single_auc_sd"],
                "single_auc_mean_b": info[b]["single_auc_mean"],
                "single_auc_sd_b": info[b]["single_auc_sd"],
                "auc_a": float(roc_auc_score(y, ens[a])),
                "auc_b": float(roc_auc_score(y, ens[b])),
                "ece_a": ece(y, ens[a]),
                "ece_b": ece(y, ens[b]),
                **paired(y, ens[a], ens[b]),
            })
        print(ep, {k: v["n_seeds"] for k, v in info.items()}, flush=True)

    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    cols = ["endpoint", "model_a", "model_b", "seeds_a", "seeds_b", "auc_a", "auc_b",
            "d_auc", "d_auc_lo", "d_auc_hi", "d_auc_p", "d_ece", "d_ece_lo", "d_ece_hi", "d_brier"]
    print(out[cols].to_string(index=False))


if __name__ == "__main__":
    main()
