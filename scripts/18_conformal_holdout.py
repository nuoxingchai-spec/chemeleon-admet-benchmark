"""Is the conformal under-coverage caused by scaffold shift or by a small calibration set?

Held-out experiment on the test split:
  - random 50/50 split (exchangeable): conformal coverage should be ~1-alpha by construction
  - scaffold-grouped 50/50 split: mimics deployment shift between calibration and evaluation
  - valid -> test (the original protocol) for reference
"""
import sys
from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
cs = import_module("11_conformal_scaffold")

R = ROOT / "reports"
ALPHA = 0.10
REPEATS = 200


def split_random(n, rng):
    perm = rng.permutation(n)
    h = n // 2
    return perm[:h], perm[h:]


def split_scaffold(groups, n, rng):
    idx_by_group = {}
    for i, g in enumerate(groups):
        idx_by_group.setdefault(g, []).append(i)
    keys = list(idx_by_group)
    target = n // 2
    mask = np.zeros(n, dtype=bool)
    size = 0
    for k in rng.permutation(len(keys)):
        mask[idx_by_group[keys[k]]] = True
        size += len(idx_by_group[keys[k]])
        if size >= target:
            break
    return np.where(mask)[0], np.where(~mask)[0]


def main():
    data = pd.read_csv(ROOT / "data/processed/global_split.csv", encoding="utf-8-sig")
    ref = pd.read_csv(R / "conformal_scaffold.csv")
    ref = ref[(ref.calibration == "raw") & (ref.conformal == "standard")]

    rows = []
    for ep in ["herg", "dili", "ames"]:
        te_rows = data[(data.endpoint == ep) & (data.split == "test")]
        y_ref = te_rows["y"].to_numpy()
        groups = [g if isinstance(g, str) and g else "ACYCLIC" for g in te_rows["murcko"]]

        for model in ["chemeleon", "scratch", "matched"]:
            try:
                ens = cs.load_ensemble(ep, model)
            except FileNotFoundError:
                continue
            p = np.asarray(ens["test"]["p"], dtype=float)
            y = np.asarray(ens["test"]["y"], dtype=int)
            if len(p) != len(y_ref) or not np.array_equal(y, y_ref):
                print(f"skip {ep}/{model}: label/order mismatch", flush=True)
                continue
            n = len(y)
            rng = np.random.default_rng(0)
            for scheme in ["random50", "scaffold50"]:
                covs, sizes, cals, evals = [], [], [], []
                for _ in range(REPEATS):
                    if scheme == "random50":
                        cal, ev = split_random(n, rng)
                    else:
                        cal, ev = split_scaffold(groups, n, rng)
                    if len(cal) < 10 or len(ev) < 10:
                        continue
                    q = cs.q_standard(cs.conformal_scores(p[cal], y[cal]), ALPHA)
                    c, s = cs.coverage_sets(p[ev], y[ev], q)
                    covs.append(c)
                    sizes.append(s)
                    cals.append(len(cal))
                    evals.append(len(ev))
                covs = np.array(covs)
                sizes = np.array(sizes)
                rows.append({
                    "endpoint": ep, "model": model, "scheme": scheme,
                    "repeats": len(covs), "n_test": n,
                    "cal_size": float(np.mean(cals)), "eval_size": float(np.mean(evals)),
                    "coverage": float(covs.mean()),
                    "coverage_lo": float(np.percentile(covs, 2.5)),
                    "coverage_hi": float(np.percentile(covs, 97.5)),
                    "coverage_sd": float(covs.std(ddof=0)),
                    "set_size": float(sizes.mean()),
                    "set_size_lo": float(np.percentile(sizes, 2.5)),
                    "set_size_hi": float(np.percentile(sizes, 97.5)),
                })
            rr = ref[(ref.endpoint == ep) & (ref.model == model)]
            if len(rr):
                r0 = rr.iloc[0]
                rows.append({
                    "endpoint": ep, "model": model, "scheme": "valid_to_test",
                    "repeats": 1, "n_test": int(r0["n_test"]),
                    "cal_size": np.nan, "eval_size": float(r0["n_test"]),
                    "coverage": float(r0["coverage"]),
                    "coverage_lo": np.nan, "coverage_hi": np.nan, "coverage_sd": np.nan,
                    "set_size": float(r0["set_size"]),
                    "set_size_lo": np.nan, "set_size_hi": np.nan,
                })
            print(ep, model, "done", flush=True)

    out = pd.DataFrame(rows)
    out.to_csv(R / "conformal_holdout.csv", index=False)
    print(out.to_string(index=False))

    gaps = []
    for ep in ["herg", "dili", "ames"]:
        for model in ["chemeleon", "scratch", "matched"]:
            try:
                ens = cs.load_ensemble(ep, model)
            except FileNotFoundError:
                continue
            rec = {"endpoint": ep, "model": model,
                   "auc_valid": roc_auc_score(ens["valid"]["y"], ens["valid"]["p"]),
                   "auc_test": roc_auc_score(ens["test"]["y"], ens["test"]["p"]),
                   "brier_valid": brier_score_loss(ens["valid"]["y"], ens["valid"]["p"]),
                   "brier_test": brier_score_loss(ens["test"]["y"], ens["test"]["p"]),
                   "mean_p_test": float(np.mean(ens["test"]["p"])),
                   "frac_gt90_test": float(np.mean(np.asarray(ens["test"]["p"]) > 0.9)),
                   "base_rate_test": float(np.mean(ens["test"]["y"])),
                   "n_valid": len(ens["valid"]["y"]), "n_test": len(ens["test"]["y"])}
            gaps.append(rec)
    pd.DataFrame(gaps).to_csv(R / "valid_test_gap.csv", index=False)


if __name__ == "__main__":
    main()
