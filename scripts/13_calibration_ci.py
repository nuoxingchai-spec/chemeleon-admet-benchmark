"""Calibration with paired bootstrap CIs, including pooled ECE across endpoints.

Post-hoc calibrators are fitted on the valid split (also used for early stopping;
this is disclosed and makes coverage estimates optimistic, not pessimistic).
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from metrics import ece  # noqa: E402

RUNS = ROOT / "runs" / "chemprop"


def logit(p, eps=1e-6):
    p = np.clip(p, eps, 1 - eps)
    return np.log(p / (1 - p))


def temperature_fit(p, y):
    z = logit(p)
    best_t, best_nll = 1.0, np.inf
    for t in np.geomspace(0.05, 20.0, 400):
        q = 1.0 / (1.0 + np.exp(-z / t))
        nll = log_loss(y, np.clip(q, 1e-6, 1 - 1e-6), labels=[0, 1])
        if nll < best_nll:
            best_t, best_nll = float(t), nll
    return best_t


def ece_equal_mass(y, p, bins=10):
    order = np.argsort(p)
    chunks = np.array_split(order, bins)
    total = 0.0
    for c in chunks:
        if len(c) == 0:
            continue
        total += len(c) / len(y) * abs(y[c].mean() - p[c].mean())
    return float(total)


def load_ensemble(endpoint, model):
    dirs = [d for d in sorted(RUNS.glob(f"{endpoint}_{model}_s*")) if (d / "preds.json").exists()]
    if not dirs:
        return None
    ps, ys, lens = {}, {}, {}
    used = []
    for d in dirs:
        j = json.loads((d / "preds.json").read_text())
        ok = all(s not in lens or lens[s] == len(j["splits"][s]["p"]) for s in ["valid", "test"])
        if not ok:
            continue
        for s in ["valid", "test"]:
            ps.setdefault(s, []).append(np.array(j["splits"][s]["p"], dtype=float))
            ys[s] = np.array(j["splits"][s]["y"], dtype=int)
            lens[s] = len(j["splits"][s]["p"])
        used.append(d.name)
    return {s: {"p": np.mean(ps[s], axis=0), "y": ys[s]} for s in ["valid", "test"]}, used


def fit_apply(p_val, y_val, p_te):
    t = temperature_fit(p_val, y_val)
    platt = LogisticRegression(C=1e6, solver="lbfgs").fit(logit(p_val).reshape(-1, 1), y_val)
    iso = IsotonicRegression(out_of_bounds="clip").fit(p_val, y_val)
    return {
        "raw": p_te,
        "temperature": 1.0 / (1.0 + np.exp(-logit(p_te) / t)),
        "platt": platt.predict_proba(logit(p_te).reshape(-1, 1))[:, 1],
        "isotonic": iso.predict(p_te),
    }, t


def paired_delta(y, pa, pb, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    da, db = [], []
    for _ in range(n):
        idx = rng.integers(0, len(y), len(y))
        if len(np.unique(y[idx])) < 2:
            continue
        da.append(ece(y[idx], pa[idx]))
        db.append(ece(y[idx], pb[idx]))
    d = np.array(da) - np.array(db)
    return float(np.mean(d)), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)), \
        float(2 * min((d <= 0).mean(), (d >= 0).mean()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reports/calibration_ci.csv")
    ap.add_argument("--boot", type=int, default=2000)
    args = ap.parse_args()

    rows = []
    pooled = {}
    for endpoint in ["herg", "dili", "ames"]:
        for model in ["chemeleon", "scratch"]:
            ens = load_ensemble(endpoint, model)
            if ens is None:
                print(f"skip {endpoint}/{model}")
                continue
            (cal, used) = ens
            pv, yv = cal["valid"]["p"], cal["valid"]["y"]
            pt, yt = cal["test"]["p"], cal["test"]["y"]
            variants, t = fit_apply(pv, yv, pt)
            pooled.setdefault(model, []).append((yt, variants))
            base = variants["raw"]
            for name, p in variants.items():
                d_ece = d_brier = d_nll = (np.nan, np.nan, np.nan, np.nan)
                if name != "raw":
                    d_ece = paired_delta(yt, p, base, args.boot)
                    br = []
                    rng = np.random.default_rng(1)
                    for _ in range(args.boot):
                        idx = rng.integers(0, len(yt), len(yt))
                        br.append(brier_score_loss(yt[idx], p[idx]) - brier_score_loss(yt[idx], base[idx]))
                    br = np.array(br)
                    d_brier = (float(br.mean()), float(np.percentile(br, 2.5)),
                               float(np.percentile(br, 97.5)),
                               float(2 * min((br <= 0).mean(), (br >= 0).mean())))
                rows.append({
                    "endpoint": endpoint, "model": model, "seeds": len(used), "calibrator": name,
                    "n": len(yt), "auc": roc_auc_score(yt, p),
                    "brier": brier_score_loss(yt, p),
                    "nll": log_loss(yt, np.clip(p, 1e-6, 1 - 1e-6), labels=[0, 1]),
                    "ece": ece(yt, p), "ece_eqmass": ece_equal_mass(yt, p),
                    "d_ece_vs_raw": d_ece[0], "d_ece_lo": d_ece[1], "d_ece_hi": d_ece[2],
                    "d_ece_p": d_ece[3],
                    "d_brier_vs_raw": d_brier[0], "d_brier_lo": d_brier[1],
                    "d_brier_hi": d_brier[2], "d_brier_p": d_brier[3],
                    "temperature": t,
                })
            print(f"{endpoint}/{model}: n={len(yt)} seeds={len(used)} T={t:.2f} "
                  f"ECE raw={ece(yt, base):.3f} -> T {ece(yt, variants['temperature']):.3f} "
                  f"iso {ece(yt, variants['isotonic']):.3f}", flush=True)

    out = pd.DataFrame(rows)
    out.to_csv(ROOT / args.out, index=False)

    # pooled: resample within endpoint so endpoint composition stays fixed
    prows = []
    for model, parts in pooled.items():
        rng = np.random.default_rng(7)
        names = list(parts[0][1].keys())
        ece_d = {k: [] for k in names}
        for _ in range(args.boot):
            ys, ps = [], {k: [] for k in names}
            for yt, variants in parts:
                idx = rng.integers(0, len(yt), len(yt))
                ys.append(yt[idx])
                for k in names:
                    ps[k].append(variants[k][idx])
            y_all = np.concatenate(ys)
            base_ece = ece(y_all, np.concatenate(ps["raw"]))
            for k in names:
                ece_d[k].append(ece(y_all, np.concatenate(ps[k])))
        y_all = np.concatenate([yt for yt, _ in parts])
        p_all = {k: np.concatenate([v[k] for _, v in parts]) for k in names}
        for k in names:
            d = np.array(ece_d[k]) - np.array(ece_d["raw"])
            prows.append({"model": model, "calibrator": k, "n_pooled": len(y_all),
                          "ece_pooled": ece(y_all, p_all[k]),
                          "d_ece_pooled": float(np.mean(d)),
                          "d_ece_lo": float(np.percentile(d, 2.5)),
                          "d_ece_hi": float(np.percentile(d, 97.5))})
    pooled_df = pd.DataFrame(prows)
    pooled_df.to_csv(ROOT / "reports/calibration_pooled.csv", index=False)
    print("\nPooled (bootstrap within endpoint):")
    print(pooled_df.to_string(index=False))


if __name__ == "__main__":
    main()
