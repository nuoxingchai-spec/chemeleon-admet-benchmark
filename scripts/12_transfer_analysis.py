"""Decompose hERG external transfer: shared-scaffold vs novel-scaffold Karim compounds,
novelty bins, local threshold sensitivity (40 uM vs 10 uM), and reverse transfer.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import AllChem, rdFingerprintGenerator
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from metrics import ece  # noqa: E402

RDLogger.DisableLog("rdApp.*")
REPORTS = ROOT / "reports"
GEN = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)


def bv(smiles):
    mol = Chem.MolFromSmiles(smiles) if isinstance(smiles, str) else None
    return AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048) if mol else None


def arr(smiles):
    mol = Chem.MolFromSmiles(smiles) if isinstance(smiles, str) else None
    out = np.zeros(2048, dtype=np.float32)
    if mol is not None:
        out[:] = np.asarray(GEN.GetFingerprint(mol), dtype=np.float32)
    return out


def max_sim(f, refs):
    return max(DataStructs.BulkTanimotoSimilarity(f, refs)) if f is not None and refs else 0.0


def main():
    g = pd.read_csv(ROOT / "data/processed/global_split.csv", encoding="utf-8-sig")
    h = g[g["endpoint"] == "herg"].copy()
    h["scaf_ref"] = h["murcko"].where(h["murcko"] != "ACYCLIC", h["smiles_std"])
    train = h[h["split"] == "train"]
    ref_fp = [bv(s) for s in train["scaf_ref"]]
    local_scaf = set(h["murcko"])

    karim = pd.read_csv(ROOT / "data/processed/karim_standardized.csv", encoding="utf-8-sig")
    karim = karim[~karim["in_local"]].copy()
    karim["scaf_ref"] = karim["murcko"].where(karim["murcko"] != "ACYCLIC", karim["smiles_std"])
    karim["shared_scaffold"] = karim["murcko"].isin(local_scaf)
    karim["novelty"] = [1.0 - max_sim(bv(s), ref_fp) for s in karim["scaf_ref"]]

    rows = []
    runs = {
        "chemeleon_original": ROOT / "runs/chemprop/herg_chemeleon_s42/pred_external_all.csv",
    }
    for name, path in runs.items():
        if not path.exists():
            print(f"skip missing {path}")
            continue
        pred = pd.read_csv(path).rename(columns={"y": "p"})[["inchikey", "p"]]
        d = karim.merge(pred, on="inchikey", how="inner")
        for label, mask in [("all", np.ones(len(d), bool)),
                            ("shared_scaffold", d["shared_scaffold"].to_numpy()),
                            ("novel_scaffold", ~d["shared_scaffold"].to_numpy())]:
            sub = d[mask]
            rows.append({"model": name, "subset": label, "n": len(sub), "pos": int(sub["y"].sum()),
                         "auc": roc_auc_score(sub["y"], sub["p"]),
                         "mean_p": float(sub["p"].mean()), "ece": ece(sub["y"].to_numpy(), sub["p"].to_numpy())})
        d["novelty_bin"] = pd.qcut(d["novelty"], 5, labels=False)
        for b, sub in d.groupby("novelty_bin"):
            rows.append({"model": name, "subset": f"novelty_Q{int(b) + 1}", "n": len(sub),
                         "pos": int(sub["y"].sum()), "auc": roc_auc_score(sub["y"], sub["p"]),
                         "mean_p": float(sub["p"].mean()), "ece": ece(sub["y"].to_numpy(), sub["p"].to_numpy())})

    # local threshold sensitivity: same compounds, labels at 40 uM vs 10 uM
    for run in sorted((ROOT / "runs/chemprop").glob("herg_chemeleon_s*")):
        pj = run / "preds.json"
        if not pj.exists():
            continue
        js = json.loads(pj.read_text())
        keys = pd.read_csv(ROOT / "data/chemprop/herg/test.csv")["inchikey"]
        pred = pd.DataFrame({"inchikey": keys, "p": js["splits"]["test"]["p"]})
        d = pred.merge(h[h["split"] == "test"][["inchikey", "pIC50", "y"]], on="inchikey")
        d = d.dropna(subset=["pIC50"])
        y10 = (d["pIC50"] >= 5.0).astype(int)
        rows.append({"model": f"chemeleon_local({run.name})", "subset": "local_test_40uM",
                     "n": len(d), "pos": int(d["y"].sum()), "auc": roc_auc_score(d["y"], d["p"]),
                     "mean_p": float(d["p"].mean()), "ece": ece(d["y"].to_numpy(), d["p"].to_numpy())})
        rows.append({"model": f"chemeleon_local({run.name})", "subset": "local_test_10uM",
                     "n": len(d), "pos": int(y10.sum()), "auc": roc_auc_score(y10, d["p"]),
                     "mean_p": float(d["p"].mean()), "ece": ece(y10.to_numpy(), d["p"].to_numpy())})

    # reverse transfer: Karim-trained RF -> local test
    ext = pd.read_csv(ROOT / "data/chemprop/herg_aligned/external_clean.csv")
    X = np.vstack([arr(s) for s in ext["smiles"]])
    rf = RandomForestClassifier(n_estimators=500, n_jobs=-1, random_state=42,
                                class_weight="balanced").fit(X, ext["y"].to_numpy())
    for split, tag in [("test", "local_test_40uM"), ("test", "local_test_10uM")]:
        t = pd.read_csv(ROOT / f"data/chemprop/herg/{split}.csv")
        p = rf.predict_proba(np.vstack([arr(s) for s in t["smiles"]]))[:, 1]
        d = pd.DataFrame({"inchikey": t["inchikey"], "p": p}).merge(
            h[h["split"] == split][["inchikey", "pIC50"]], on="inchikey").dropna(subset=["pIC50"])
        if tag.endswith("40uM"):
            y = h.set_index("inchikey").loc[d["inchikey"], "y"].to_numpy()
        else:
            y = (d["pIC50"] >= 5.0).astype(int).to_numpy()
        rows.append({"model": "rf_karim_trained", "subset": f"reverse_{tag}", "n": len(d),
                     "pos": int(y.sum()), "auc": roc_auc_score(y, d["p"]),
                     "mean_p": float(d["p"].mean()), "ece": ece(y, d["p"].to_numpy())})

    out = pd.DataFrame(rows)
    out.to_csv(REPORTS / "external_transfer.csv", index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
