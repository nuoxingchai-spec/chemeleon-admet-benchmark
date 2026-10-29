"""Paired comparison of the CheMeleon seed ensemble against the strongest classical baseline."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem import rdFingerprintGenerator
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from metrics import ece  # noqa: E402

RDLogger.DisableLog("rdApp.*")
GEN = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
RUNS = ROOT / "runs" / "chemprop"


def fp(smiles):
    mol = Chem.MolFromSmiles(smiles)
    out = np.zeros(2048, dtype=np.float32)
    if mol is not None:
        out[:] = np.asarray(GEN.GetFingerprint(mol), dtype=np.float32)
    return out


def paired(y, pa, pb, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    d_auc, d_ece = [], []
    for _ in range(n):
        idx = rng.integers(0, len(y), len(y))
        if len(np.unique(y[idx])) < 2:
            continue
        d_auc.append(roc_auc_score(y[idx], pa[idx]) - roc_auc_score(y[idx], pb[idx]))
        d_ece.append(ece(y[idx], pa[idx]) - ece(y[idx], pb[idx]))
    out = {}
    for name, v in [("auc", d_auc), ("ece", d_ece)]:
        v = np.array(v)
        out[f"d_{name}"] = float(v.mean())
        out[f"d_{name}_lo"] = float(np.percentile(v, 2.5))
        out[f"d_{name}_hi"] = float(np.percentile(v, 97.5))
        out[f"d_{name}_p"] = float(2 * min((v <= 0).mean(), (v >= 0).mean()))
    return out


def main():
    data = pd.read_csv(ROOT / "data/processed/global_split.csv", encoding="utf-8-sig")
    rows = []
    for ep in ["herg", "dili", "ames"]:
        sub = data[data.endpoint == ep]
        x = np.vstack([fp(s) for s in sub["smiles_std"]])
        y = sub["y"].to_numpy()
        tr = sub["split"].to_numpy() == "train"
        te = sub["split"].to_numpy() == "test"
        ys = y[te]
        klass = {}
        for name, model in {
            "rf": RandomForestClassifier(n_estimators=500, n_jobs=-1, random_state=42,
                                         class_weight="balanced"),
            "histgb": HistGradientBoostingClassifier(max_iter=400, learning_rate=0.06,
                                                     max_leaf_nodes=31, l2_regularization=1.0,
                                                     random_state=42, class_weight="balanced"),
            "logreg": LogisticRegression(max_iter=3000, C=1.0, class_weight="balanced"),
        }.items():
            model.fit(x[tr], y[tr])
            klass[name] = model.predict_proba(x[te])[:, 1]
        best_name = max(klass, key=lambda k: roc_auc_score(ys, klass[k]))

        dirs = [d for d in sorted(RUNS.glob(f"{ep}_chemeleon_s*")) if (d / "preds.json").exists()]
        ens = np.mean([json.loads((d / "preds.json").read_text())["splits"]["test"]["p"] for d in dirs], axis=0)
        rows.append({"endpoint": ep, "comparison": f"chemeleon_vs_{best_name}",
                     "n": int(te.sum()), "auc_chemprop": roc_auc_score(ys, ens),
                     "auc_classical": roc_auc_score(ys, klass[best_name]),
                     "n_seeds": len(dirs), **paired(ys, ens, klass[best_name])})
        print(rows[-1], flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(ROOT / "reports" / "classical_vs_chemprop.csv", index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
