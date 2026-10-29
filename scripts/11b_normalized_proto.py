"""Quick check: does normalizing conformal scores by uncertainty/novelty fix under-coverage?"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import AllChem

RDLogger.DisableLog("rdApp.*")
ROOT = Path(__file__).resolve().parents[1]
G = pd.read_csv(ROOT / "data/processed/global_split.csv", encoding="utf-8-sig")


def fp(smiles):
    mol = Chem.MolFromSmiles(smiles) if isinstance(smiles, str) else None
    return AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048) if mol else None


def q_level(scores, alpha):
    n = len(scores)
    return np.sort(scores)[min(int(np.ceil((n + 1) * (1 - alpha))), n) - 1]


for ep in ["herg", "dili", "ames"]:
    sub = G[G.endpoint == ep].set_index("inchikey")
    tr_keys = pd.read_csv(ROOT / f"data/chemprop/{ep}/train.csv")["inchikey"]
    fp_tr = [fp(sub.loc[k, "smiles_std"] if sub.loc[k, "murcko"] == "ACYCLIC" else sub.loc[k, "murcko"])
             for k in tr_keys]
    runs = sorted((ROOT / "runs/chemprop").glob(f"{ep}_chemeleon_s*"))
    js = [json.loads((r / "preds.json").read_text()) for r in runs]
    data = {}
    for split in ["valid", "test"]:
        P = np.array([j["splits"][split]["p"] for j in js])
        y = np.array(js[0]["splits"][split]["y"])
        keys = pd.read_csv(ROOT / f"data/chemprop/{ep}/{split}.csv")["inchikey"]
        scaf = [sub.loc[k, "murcko"] if sub.loc[k, "murcko"] != "ACYCLIC" else sub.loc[k, "smiles_std"]
                for k in keys]
        d = np.array([1 - max(DataStructs.BulkTanimotoSimilarity(fp(s), fp_tr)) if fp(s) else 0.0
                      for s in scaf])
        data[split] = {"p": P.mean(0), "sig": P.std(0), "y": y, "d": d}
    c, t = data["valid"], data["test"]
    print(f"\n{ep}: ncal={len(c['y'])} ntest={len(t['y'])} "
          f"sigma {c['sig'].mean():.3f}/{t['sig'].mean():.3f} "
          f"novelty {c['d'].mean():.3f}/{t['d'].mean():.3f}")
    for alpha in (0.1, 0.05):
        for label, sc, st in [
            ("plain", np.ones(len(c["y"])), np.ones(len(t["y"]))),
            ("sigma", (c["sig"] + 0.01) / np.median(c["sig"] + 0.01),
             (t["sig"] + 0.01) / np.median(c["sig"] + 0.01)),
            ("novelty", (c["d"] + 0.02) / np.median(c["d"] + 0.02),
             (t["d"] + 0.02) / np.median(c["d"] + 0.02)),
            ("combo", 0.5 * (c["sig"] + 0.01) / np.median(c["sig"] + 0.01) + 0.5 * (c["d"] + 0.02) / np.median(c["d"] + 0.02),
             0.5 * (t["sig"] + 0.01) / np.median(c["sig"] + 0.01) + 0.5 * (t["d"] + 0.02) / np.median(c["d"] + 0.02)),
        ]:
            base = (1 - np.where(c["y"] == 1, c["p"], 1 - c["p"])) / sc
            q = q_level(base, alpha)
            sets = (1 - np.stack([1 - t["p"], t["p"]], 1)) / st[:, None] <= q + 1e-12
            cov = sets[np.arange(len(t["y"])), t["y"]].mean()
            print(f"  a={alpha:.2f} {label:8s} cov={cov:.3f} size={sets.sum(1).mean():.3f}")
