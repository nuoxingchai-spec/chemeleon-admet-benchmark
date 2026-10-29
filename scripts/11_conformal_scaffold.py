"""Scaffold-aware conformal prediction and calibration under scaffold shift.

Valid split = calibration, test split = evaluation. Variants:
  standard        global split-conformal quantile
  cluster         Mandrian by Butina cluster of Murcko scaffolds (shrunk to global)
  swc             scaffold-similarity-weighted conformal quantile
  difficulty      Mandrian by novelty bin (1 - max Tanimoto to train)
Reports marginal coverage, per-cluster coverage spread, set size, and
risk-coverage / AURC for the calibrated probabilities.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import AllChem
from rdkit.ML.Cluster import Butina
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from metrics import ece  # noqa: E402

RDLogger.DisableLog("rdApp.*")

RUNS = ROOT / "runs" / "chemprop"
REPORTS = ROOT / "reports"
DATA = ROOT / "data" / "processed" / "global_split.csv"


def logit(p, eps=1e-6):
    p = np.clip(p, eps, 1 - eps)
    return np.log(p / (1 - p))


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def fp_of(smiles: str):
    mol = Chem.MolFromSmiles(smiles) if isinstance(smiles, str) else None
    if mol is None:
        return None
    return AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)


def sim_matrix(test_fps, cal_fps) -> np.ndarray:
    out = np.zeros((len(test_fps), len(cal_fps)), dtype=np.float32)
    for i, ft in enumerate(test_fps):
        if ft is None:
            continue
        out[i] = DataStructs.BulkTanimotoSimilarity(ft, cal_fps)
    return out


def load_ensemble(endpoint: str, model: str) -> dict:
    dirs = sorted(RUNS.glob(f"{endpoint}_{model}_s*"))
    dirs = [d for d in dirs if (d / "preds.json").exists()]
    if not dirs:
        raise FileNotFoundError(f"no runs for {endpoint}/{model}")
    ps, ys = {}, {}
    used = []
    lens = {}
    for d in dirs:
        j = json.loads((d / "preds.json").read_text())
        ok = True
        for split in ["valid", "test"]:
            p = np.array(j["splits"][split]["p"], dtype=float)
            y = np.array(j["splits"][split]["y"], dtype=int)
            if split in lens and lens[split] != len(p):
                ok = False
                break
        if not ok:
            continue
        for split in ["valid", "test"]:
            p = np.array(j["splits"][split]["p"], dtype=float)
            y = np.array(j["splits"][split]["y"], dtype=int)
            lens[split] = len(p)
            ps.setdefault(split, []).append(p)
            ys[split] = y
        used.append(d.name)
    return {
        "valid": {"p": np.mean(ps["valid"], axis=0), "y": ys["valid"],
                  "sigma": np.std(ps["valid"], axis=0)},
        "test": {"p": np.mean(ps["test"], axis=0), "y": ys["test"],
                 "sigma": np.std(ps["test"], axis=0)},
        "runs": used,
    }


def scaffolds(endpoint: str, inchikeys: list[str]) -> list[str]:
    g = pd.read_csv(DATA, encoding="utf-8-sig")
    sub = g[g["endpoint"] == endpoint].set_index("inchikey")
    return [sub.loc[k, "murcko"] if k in sub.index else "ACYCLIC" for k in inchikeys]


def get_inchikeys(endpoint: str, split: str) -> list[str]:
    df = pd.read_csv(ROOT / "data" / "chemprop" / endpoint / f"{split}.csv")
    return df["inchikey"].tolist()


def conformal_scores(p, y):
    return 1.0 - np.where(y == 1, p, 1.0 - p)


def q_standard(scores, alpha):
    n = len(scores)
    k = min(int(np.ceil((n + 1) * (1 - alpha))), n)
    return float(np.sort(scores)[k - 1])


def q_weighted(scores, w, alpha):
    order = np.argsort(scores)
    s, ww = scores[order], w[order]
    cw = np.cumsum(ww) / ww.sum()
    idx = np.searchsorted(cw, 1 - alpha)
    if idx >= len(s):
        return float(s[-1])
    return float(s[idx])


def coverage_sets(p, y, q):
    grid = np.stack([1 - p, p], axis=1)
    in_set = (1.0 - grid) <= q + 1e-12
    return float(in_set[np.arange(len(y)), y].mean()), float(in_set.sum(axis=1).mean())


def cluster_labels(cal_fps, cutoff=0.4, min_size=25):
    n = len(cal_fps)
    dists = []
    for i in range(1, n):
        sims = DataStructs.BulkTanimotoSimilarity(cal_fps[i], cal_fps[:i])
        dists.extend([1.0 - s for s in sims])
    clust = Butina.ClusterData(dists, n, cutoff, isDistData=True, reordering=True)
    lab = np.full(n, -1, dtype=int)
    for k, members in enumerate(clust):
        for m in members:
            lab[m] = k
    return lab


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoints", nargs="+", default=["herg", "dili", "ames"])
    ap.add_argument("--models", nargs="+", default=["chemeleon", "scratch"])
    ap.add_argument("--alpha", type=float, default=0.1)
    ap.add_argument("--out", default="reports/conformal_scaffold.csv")
    args = ap.parse_args()

    rows = []
    selective = []
    for endpoint in args.endpoints:
        ik_val = get_inchikeys(endpoint, "valid")
        ik_te = get_inchikeys(endpoint, "test")
        sc_val = scaffolds(endpoint, ik_val)
        sc_te = scaffolds(endpoint, ik_te)
        # scaffold similarity uses the scaffold itself; acyclic falls back to the molecule
        g = pd.read_csv(DATA, encoding="utf-8-sig")
        sub = g[g["endpoint"] == endpoint].set_index("inchikey")
        mol_val = [sub.loc[k, "smiles_std"] if k in sub.index else "" for k in ik_val]
        mol_te = [sub.loc[k, "smiles_std"] if k in sub.index else "" for k in ik_te]
        scaf_val = [s if s != "ACYCLIC" else m for s, m in zip(sc_val, mol_val)]
        scaf_te = [s if s != "ACYCLIC" else m for s, m in zip(sc_te, mol_te)]
        fp_cal = [fp_of(s) for s in scaf_val]
        fp_te = [fp_of(s) for s in scaf_te]
        S = sim_matrix(fp_te, fp_cal)
        # novelty vs the training set
        ik_tr = get_inchikeys(endpoint, "train")
        fp_tr = [fp_of(s if s != "ACYCLIC" else sub.loc[k, "smiles_std"])
                 for k, s in zip(ik_tr, scaffolds(endpoint, ik_tr))]
        d_cal = 1.0 - np.array([max(DataStructs.BulkTanimotoSimilarity(f, fp_tr)) if f else 0.0
                                for f in fp_cal])
        d_te = 1.0 - np.array([max(DataStructs.BulkTanimotoSimilarity(f, fp_tr)) if f else 0.0
                               for f in fp_te])

        for model in args.models:
            ens = load_ensemble(endpoint, model)
            p_cal, y_cal = ens["valid"]["p"], ens["valid"]["y"]
            p_te, y_te = ens["test"]["p"], ens["test"]["y"]
            s_cal = conformal_scores(p_cal, y_cal)

            # ---- calibrators fitted on valid ----
            t_glob = 1.0
            best = np.inf
            for t in np.geomspace(0.05, 20, 300):
                nll = log_loss(y_cal, np.clip(sigmoid(logit(p_cal) / t), 1e-6, 1 - 1e-6), labels=[0, 1])
                if nll < best:
                    t_glob, best = float(t), nll
            # difficulty-conditional temperature: log T = a + b * d
            best_ab, best_nll = (0.0, 0.0), np.inf
            for a in np.linspace(-1.5, 1.5, 31):
                for b in np.linspace(-2.0, 2.0, 41):
                    T = np.exp(a + b * d_cal)
                    q = sigmoid(logit(p_cal) / T)
                    nll = log_loss(y_cal, np.clip(q, 1e-6, 1 - 1e-6), labels=[0, 1])
                    if nll < best_nll:
                        best_ab, best_nll = (float(a), float(b)), nll
            a, b = best_ab
            p_cal_dc = sigmoid(logit(p_cal) / np.exp(a + b * d_cal))
            p_te_dc = sigmoid(logit(p_te) / np.exp(a + b * d_te))

            cal_versions = {
                "raw": (p_cal, p_te),
                "temperature": (sigmoid(logit(p_cal) / t_glob), sigmoid(logit(p_te) / t_glob)),
                "diff_temp": (p_cal_dc, p_te_dc),
            }

            # ---- conformal variants (on raw scores) ----
            q_std = q_standard(s_cal, args.alpha)
            cov_std, sz_std = coverage_sets(p_te, y_te, q_std)

            lab = cluster_labels(fp_cal)
            test_cluster = np.argmax(S, axis=1) if S.size else np.zeros(len(p_te), dtype=int)
            test_cluster = lab[test_cluster] if S.size else np.zeros(len(p_te), dtype=int)
            q_cl = {}
            for k in np.unique(lab):
                q_cl[k] = q_standard(s_cal[lab == k], args.alpha) if (lab == k).sum() >= 25 else q_std
            q_te_cl = np.array([q_cl[k] for k in test_cluster])
            grid = np.stack([1 - p_te, p_te], axis=1)
            in_cl = (1.0 - grid) <= q_te_cl[:, None] + 1e-12
            cov_cl = float(in_cl[np.arange(len(y_te)), y_te].mean())
            sz_cl = float(in_cl.sum(axis=1).mean())
            cluster_cov = {}
            for k in np.unique(test_cluster):
                m = test_cluster == k
                cluster_cov[int(k)] = (int(m.sum()), float(in_cl[m][np.arange(m.sum()), y_te[m]].mean()))
            big = {k: v for k, (m, v) in cluster_cov.items() if m >= 10}
            if big:
                tot = sum(cluster_cov[k][0] for k in big)
                mad = sum(cluster_cov[k][0] * abs(cluster_cov[k][1] - (1 - args.alpha)) for k in big) / tot
                min_cov = min(big.values())
                max_cov = max(big.values())
            else:
                mad = min_cov = max_cov = np.nan

            w = np.power(S + 0.05, 2)
            q_te_swc = np.array([q_weighted(s_cal, w[i], args.alpha) for i in range(len(p_te))])
            in_swc = (1.0 - grid) <= q_te_swc[:, None] + 1e-12
            cov_swc = float(in_swc[np.arange(len(y_te)), y_te].mean())
            sz_swc = float(in_swc.sum(axis=1).mean())

            edges = np.quantile(d_cal, [0.25, 0.5, 0.75])
            bin_cal = np.digitize(d_cal, edges)
            bin_te = np.digitize(d_te, edges)
            q_bin = {}
            for k in range(4):
                q_bin[k] = q_standard(s_cal[bin_cal == k], args.alpha) if (bin_cal == k).sum() >= 25 else q_std
            q_te_bin = np.array([q_bin[k] for k in bin_te])
            in_bin = (1.0 - grid) <= q_te_bin[:, None] + 1e-12
            cov_bin = float(in_bin[np.arange(len(y_te)), y_te].mean())
            sz_bin = float(in_bin.sum(axis=1).mean())

            # difficulty-normalized conformal: nonconformity divided by an uncertainty scale
            sig_cal, sig_te = ens["valid"]["sigma"], ens["test"]["sigma"]
            med_sig = float(np.median(sig_cal + 0.01)) or 1.0
            med_nov = float(np.median(d_cal + 0.02)) or 1.0
            scales = {
                "norm_sigma": ((sig_cal + 0.01) / med_sig, (sig_te + 0.01) / med_sig),
                "norm_combo": (
                    0.5 * (sig_cal + 0.01) / med_sig + 0.5 * (d_cal + 0.02) / med_nov,
                    0.5 * (sig_te + 0.01) / med_sig + 0.5 * (d_te + 0.02) / med_nov,
                ),
            }
            norm_res = {}
            for sname, (sc_cal, sc_te) in scales.items():
                q_n = q_standard(s_cal / sc_cal, args.alpha)
                in_n = (1.0 - grid) / sc_te[:, None] <= q_n + 1e-12
                norm_res[sname] = (float(in_n[np.arange(len(y_te)), y_te].mean()),
                                   float(in_n.sum(axis=1).mean()))

            for name, (pc, pt) in cal_versions.items():
                conf = np.maximum(pt, 1 - pt)
                order = np.argsort(-conf, kind="stable")
                err = ((pt >= 0.5).astype(int) != y_te)[order]
                n = len(y_te)
                ks = np.arange(20, n + 1)
                risks = np.array([err[:k].mean() for k in ks])
                cov = ks / n
                if name == "raw":
                    scores = {
                        "confidence": conf,
                        "neg_sigma": -sig_te,
                        "neg_novelty": -d_te,
                        "combo": conf / max(conf.std(), 1e-6) - sig_te / max(sig_te.std(), 1e-6)
                        - d_te / max(d_te.std(), 1e-6),
                    }
                    aurc = {}
                    for sname, score in scores.items():
                        o = np.argsort(-score, kind="stable")
                        e = ((pt >= 0.5).astype(int) != y_te)[o]
                        aurc[sname] = float(np.mean([e[:k].mean() for k in ks]))
                        selective.append({
                            "endpoint": endpoint, "model": model, "score": sname,
                            "n": n, "aurc": aurc[sname],
                            "risk_at_80": float(e[: int(n * 0.8)].mean()),
                            "risk_at_90": float(e[: int(n * 0.9)].mean()),
                        })
                    rng = np.random.default_rng(3)
                    deltas = {k: [] for k in scores if k != "confidence"}
                    for _ in range(500):
                        idx = rng.integers(0, n, n)
                        if len(np.unique(y_te[idx])) < 2:
                            continue
                        bb = {}
                        for sname, score in scores.items():
                            o = np.argsort(-score[idx], kind="stable")
                            e = ((pt[idx] >= 0.5).astype(int) != y_te[idx])[o]
                            kk = np.arange(20, len(idx) + 1)
                            bb[sname] = np.mean([e[:k].mean() for k in kk])
                        for k in deltas:
                            deltas[k].append(bb[k] - bb["confidence"])
                    for k, v in deltas.items():
                        v = np.array(v)
                        selective.append({
                            "endpoint": endpoint, "model": model, "score": f"delta_{k}",
                            "n": n, "aurc": float(aurc[k] - aurc["confidence"]),
                            "risk_at_80": float(np.percentile(v, 2.5)),
                            "risk_at_90": float(np.percentile(v, 97.5)),
                        })
                rows.append({
                    "endpoint": endpoint,
                    "model": model,
                    "runs": "|".join(ens["runs"]),
                    "calibration": name,
                    "n_cal": len(y_cal),
                    "n_test": n,
                    "auc": float(roc_auc_score(y_te, pt)),
                    "brier": float(brier_score_loss(y_te, pt)),
                    "ece": ece(y_te, pt),
                    "log_loss": float(log_loss(y_te, np.clip(pt, 1e-6, 1 - 1e-6), labels=[0, 1])),
                    "aurc": float(risks.mean()),
                    "risk_at_80": float(risks[np.argmin(np.abs(cov - 0.8))]),
                    "risk_at_90": float(risks[np.argmin(np.abs(cov - 0.9))]),
                    "conformal": "standard",
                    "coverage": cov_std,
                    "set_size": float(sz_std),
                })
                for cname, cov_v, sz_v, extra in [
                    ("cluster", cov_cl, sz_cl, cluster_cov),
                    ("swc", cov_swc, sz_swc, {}),
                    ("difficulty", cov_bin, sz_bin, {}),
                    ("norm_sigma", norm_res["norm_sigma"][0], norm_res["norm_sigma"][1], {}),
                    ("norm_combo", norm_res["norm_combo"][0], norm_res["norm_combo"][1], {}),
                ]:
                    rows.append({
                        "endpoint": endpoint, "model": model, "runs": "|".join(ens["runs"]),
                        "calibration": name, "n_cal": len(y_cal), "n_test": n,
                        "auc": float(roc_auc_score(y_te, pt)),
                        "brier": float(brier_score_loss(y_te, pt)),
                        "ece": ece(y_te, pt),
                        "log_loss": float(log_loss(y_te, np.clip(pt, 1e-6, 1 - 1e-6), labels=[0, 1])),
                        "aurc": float(risks.mean()),
                        "risk_at_80": float(risks[np.argmin(np.abs(cov - 0.8))]),
                        "risk_at_90": float(risks[np.argmin(np.abs(cov - 0.9))]),
                        "conformal": cname,
                        "coverage": cov_v,
                        "set_size": float(sz_v),
                        "min_cluster_coverage": min_cov,
                        "max_cluster_coverage": max_cov,
                        "cluster_coverage_mad": mad,
                        "n_clusters_test": len(cluster_cov),
                    })
            print(f"{endpoint}/{model}: std cov={cov_std:.3f} sz={sz_std:.3f} | "
                  f"cluster cov={cov_cl:.3f} sz={sz_cl:.3f} mad={mad:.3f} | swc cov={cov_swc:.3f} | "
                  f"diff cov={cov_bin:.3f} | ECE raw={ece(y_te, p_te):.3f} "
                  f"T={t_glob:.2f} dc=({a:.2f},{b:.2f}) -> {ece(y_te, p_te_dc):.3f}", flush=True)

    out = pd.DataFrame(rows)
    out_path = ROOT / args.out
    if out_path.exists():
        old = pd.read_csv(out_path)
        keys = ["endpoint", "model", "calibration", "conformal"]
        old = old[~old.set_index(keys).index.isin(out.set_index(keys).index)]
        out = pd.concat([old, out], ignore_index=True)
    out.to_csv(out_path, index=False)
    sel = pd.DataFrame(selective)
    sel.to_csv(ROOT / "reports" / "selective.csv", index=False)
    print(f"wrote {out_path} ({len(out)} rows) and reports/selective.csv ({len(sel)} rows)")


if __name__ == "__main__":
    main()
