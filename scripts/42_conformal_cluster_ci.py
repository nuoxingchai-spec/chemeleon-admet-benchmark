"""Cluster-robust CIs for the deployed (valid->test) conformal coverage."""
from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
cs = import_module("11_conformal_scaffold")

ALPHA = 0.10
N_BOOT = 5000
SEED = 20261031
OUT = ROOT / "reports" / "conformal_cluster_ci.json"


def coverage_indicators(endpoint: str, model: str) -> tuple[np.ndarray, np.ndarray, float]:
    d = cs.load_ensemble(endpoint, model)
    pv, yv = d["valid"]["p"], d["valid"]["y"]
    pt, yt = d["test"]["p"], d["test"]["y"]
    s_cal = 1.0 - np.where(yv == 1, pv, 1.0 - pv)
    q = cs.q_standard(s_cal, ALPHA)
    ind = ((1.0 - np.where(yt == 1, pt, 1.0 - pt)) <= q + 1e-12).astype(float)
    return ind, yt, q


def boot_ci(ind: np.ndarray, groups: np.ndarray, rng: np.random.Generator) -> dict:
    compound, cluster = [], []
    uniq = np.unique(groups)
    for _ in range(N_BOOT):
        idx = rng.integers(0, len(ind), len(ind))
        compound.append(ind[idx].mean())
        picked = rng.choice(uniq, len(uniq), replace=True)
        idx = np.concatenate([np.where(groups == g)[0] for g in picked])
        cluster.append(ind[idx].mean())
    c = np.asarray(compound)
    s = np.asarray(cluster)
    return {
        "coverage": float(ind.mean()),
        "compound_ci": [float(np.percentile(c, 2.5)), float(np.percentile(c, 97.5))],
        "scaffold_ci": [float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5))],
    }


def main() -> None:
    out = {}
    for endpoint in ["ames"]:
        inchikeys = cs.get_inchikeys(endpoint, "test")
        groups = np.array(cs.scaffolds(endpoint, inchikeys))
        for model in ["chemeleon", "scratch", "matched"]:
            ind, _, q = coverage_indicators(endpoint, model)
            rng = np.random.default_rng(SEED)
            res = boot_ci(ind, groups, rng)
            res.update({"endpoint": endpoint, "model": model, "n": int(len(ind)),
                        "n_scaffolds": int(len(np.unique(groups))),
                        "alpha": ALPHA, "q": float(q), "n_boot": N_BOOT, "seed": SEED})
            out[f"{endpoint}/{model}"] = res
            print(endpoint, model, json.dumps(res))
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
