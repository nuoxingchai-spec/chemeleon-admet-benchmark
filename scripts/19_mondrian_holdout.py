"""Does cluster-Mondrian conformal help when calibration is exchangeable with evaluation?

Ames only (the only endpoint with enough calibration points). Repeated scaffold-grouped
50/50 splits of the test set; standard split conformal vs Butina-cluster Mondrian.
"""
import sys
from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import DataStructs, RDLogger

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
cs = import_module("11_conformal_scaffold")

RDLogger.DisableLog("rdApp.*")
R = ROOT / "reports"
ALPHA = 0.10
REPEATS = 100
MIN_CLUSTER_CAL = 25
MIN_CLUSTER_EVAL = 10


def split_scaffold(groups, n, rng):
    idx_by_group = {}
    for i, g in enumerate(groups):
        idx_by_group.setdefault(g, []).append(i)
    keys = list(idx_by_group)
    mask = np.zeros(n, dtype=bool)
    size, target = 0, n // 2
    for k in rng.permutation(len(keys)):
        mask[idx_by_group[keys[k]]] = True
        size += len(idx_by_group[keys[k]])
        if size >= target:
            break
    return np.where(mask)[0], np.where(~mask)[0]


def cluster_stats(cov_mask, labels):
    out = []
    for lab in np.unique(labels):
        m = labels == lab
        if m.sum() >= MIN_CLUSTER_EVAL:
            out.append((m.sum(), cov_mask[m].mean()))
    if not out:
        return float("nan"), float("nan")
    w = np.array([o[0] for o in out], dtype=float)
    c = np.array([o[1] for o in out], dtype=float)
    mad = float((w / w.sum() * np.abs(c - np.average(c, weights=w))).sum())
    return float(c.min()), mad


def cover(p, y, q):
    grid = np.stack([1 - p, p], axis=1)
    return ((1.0 - grid) <= q + 1e-12)[np.arange(len(y)), y]


def main():
    data = pd.read_csv(ROOT / "data/processed/global_split.csv", encoding="utf-8-sig")
    te = data[(data.endpoint == "ames") & (data.split == "test")]
    y = te["y"].to_numpy()
    groups = [g if isinstance(g, str) and g else "ACYCLIC" for g in te["murcko"]]
    smiles = te["smiles_std"].tolist()
    scaf = [g if g != "ACYCLIC" else s for g, s in zip(groups, smiles)]
    fp_all = [cs.fp_of(s) for s in scaf]
    n = len(y)

    rows = []
    for model in ["chemeleon", "scratch"]:
        try:
            ens = cs.load_ensemble("ames", model)
        except FileNotFoundError:
            continue
        p = np.asarray(ens["test"]["p"], dtype=float)
        assert np.array_equal(np.asarray(ens["test"]["y"]), y), model
        rng = np.random.default_rng(1)
        reps = []
        for _ in range(REPEATS):
            cal, ev = split_scaffold(groups, n, rng)
            q_std = cs.q_standard(cs.conformal_scores(p[cal], y[cal]), ALPHA)
            cov_std = cover(p[ev], y[ev], q_std)
            in0s = p[ev] <= q_std + 1e-12
            in1s = (1.0 - p[ev]) <= q_std + 1e-12
            size_std = float((in0s.astype(int) + in1s.astype(int)).mean())

            lab = cs.cluster_labels([fp_all[i] for i in cal], cutoff=0.4)
            S = cs.sim_matrix([fp_all[i] for i in ev], [fp_all[i] for i in cal])
            ev_lab = lab[np.argmax(S, axis=1)]
            counts = {k: int((lab == k).sum()) for k in np.unique(lab)}
            q_cluster = {}
            for k in counts:
                if counts[k] >= MIN_CLUSTER_CAL:
                    s = cs.conformal_scores(p[cal][lab == k], y[cal][lab == k])
                    q_cluster[k] = cs.q_standard(s, ALPHA)
                else:
                    q_cluster[k] = q_std
            q_ev = np.array([q_cluster[k] for k in ev_lab])
            in0 = p[ev] <= q_ev + 1e-12
            in1 = (1.0 - p[ev]) <= q_ev + 1e-12
            covered = np.where(y[ev] == 1, in1, in0)
            size_mon = float((in0.astype(int) + in1.astype(int)).mean())

            large = {k for k in counts if counts[k] >= MIN_CLUSTER_CAL}
            frac_large = float(np.mean([k in large for k in ev_lab]))

            min_std, mad_std = cluster_stats(cov_std, ev_lab)
            min_mon, mad_mon = cluster_stats(covered, ev_lab)
            reps.append({
                "cov_std": float(cov_std.mean()), "size_std": size_std,
                "cov_mon": float(covered.mean()), "size_mon": size_mon,
                "min_std": min_std, "min_mon": min_mon,
                "mad_std": mad_std, "mad_mon": mad_mon,
                "n_clusters": len(counts),
                "n_large_clusters": len(large),
                "frac_eval_large": frac_large,
            })
        d = pd.DataFrame(reps)
        row = {"endpoint": "ames", "model": model, "repeats": len(d)}
        for c in ["cov_std", "size_std", "cov_mon", "size_mon", "min_std", "min_mon",
                  "mad_std", "mad_mon", "n_clusters", "n_large_clusters", "frac_eval_large"]:
            row[c] = float(d[c].mean())
        for a, b in [("cov_mon", "cov_std"), ("size_mon", "size_std"), ("min_mon", "min_std"), ("mad_mon", "mad_std")]:
            diff = d[a] - d[b]
            row[f"d_{a}"] = float(diff.mean())
            row[f"d_{a}_lo"] = float(np.percentile(diff, 2.5))
            row[f"d_{a}_hi"] = float(np.percentile(diff, 97.5))
        rows.append(row)
        print(model, {k: round(v, 3) for k, v in row.items() if isinstance(v, float)}, flush=True)

    out = pd.DataFrame(rows)
    out.to_csv(R / "conformal_mondrian_holdout.csv", index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
