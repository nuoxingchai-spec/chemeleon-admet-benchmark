"""Classical ECFP4 baselines on the cleaned global scaffold split."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem import rdFingerprintGenerator
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    matthews_corrcoef,
    roc_auc_score,
)

RDLogger.DisableLog("rdApp.*")
ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
GEN = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)


def fp(smiles: str) -> np.ndarray:
    mol = Chem.MolFromSmiles(smiles)
    arr = np.zeros((2048,), dtype=np.float32)
    if mol is not None:
        arr[:] = np.asarray(GEN.GetFingerprint(mol), dtype=np.float32)
    return arr


def ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (p >= lo) & (p < hi if hi < 1 else p <= hi)
        if mask.sum() == 0:
            continue
        total += mask.mean() * abs(y[mask].mean() - p[mask].mean())
    return float(total)


def bootstrap_auc(y: np.ndarray, p: np.ndarray, n: int = 1000, seed: int = 42):
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n):
        idx = rng.integers(0, len(y), len(y))
        if len(np.unique(y[idx])) < 2:
            continue
        vals.append(roc_auc_score(y[idx], p[idx]))
    if not vals:
        return (float("nan"), float("nan"))
    return tuple(float(v) for v in np.percentile(vals, [2.5, 97.5]))


def metrics(y, p, threshold=0.5):
    pred = (p >= threshold).astype(int)
    lo, hi = bootstrap_auc(y, p)
    return {
        "n": int(len(y)),
        "pos": int(y.sum()),
        "auc": float(roc_auc_score(y, p)),
        "auc_ci_low": lo,
        "auc_ci_high": hi,
        "pr_auc": float(average_precision_score(y, p)),
        "acc": float(accuracy_score(y, pred)),
        "mcc": float(matthews_corrcoef(y, pred)),
        "brier": float(brier_score_loss(y, p)),
        "ece": ece(y, p),
    }


def main():
    data = pd.read_csv(ROOT / "data" / "processed" / "global_split.csv", encoding="utf-8-sig")
    rows = []
    for endpoint in ["herg", "dili", "ames"]:
        sub = data[data["endpoint"] == endpoint].copy()
        x = np.vstack([fp(s) for s in sub["smiles_std"]])
        y = sub["y"].to_numpy()
        tr = sub["split"].to_numpy() == "train"
        for split_name in ["valid", "test"]:
            te = sub["split"].to_numpy() == split_name
            models = {
                "rf": RandomForestClassifier(
                    n_estimators=500, n_jobs=-1, random_state=42, class_weight="balanced"
                ),
                "histgb": HistGradientBoostingClassifier(
                    max_iter=400, learning_rate=0.06, max_leaf_nodes=31,
                    l2_regularization=1.0, random_state=42, class_weight="balanced"
                ),
                "logreg": LogisticRegression(
                    max_iter=3000, C=1.0, class_weight="balanced", n_jobs=-1
                ),
            }
            for name, model in models.items():
                model.fit(x[tr], y[tr])
                p = model.predict_proba(x[te])[:, 1]
                m = metrics(y[te], p)
                m.update({"endpoint": endpoint, "model": name, "split": split_name})
                rows.append(m)
                print(json.dumps(m, ensure_ascii=False))

    df = pd.DataFrame(rows)[
        ["endpoint", "model", "split", "n", "pos", "auc", "auc_ci_low", "auc_ci_high",
         "pr_auc", "acc", "mcc", "brier", "ece"]
    ]
    df.to_csv(REPORTS / "baselines_classical.csv", index=False, encoding="utf-8-sig")
    (REPORTS / "baselines_classical.json").write_text(
        df.to_json(orient="records", indent=2, force_ascii=False), encoding="utf-8"
    )
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
