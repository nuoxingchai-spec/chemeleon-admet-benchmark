"""Prepare the Karim hERG external set and a threshold-aligned local training set.

Karim et al. labels hERG blockade at 10 uM (pIC50 >= 5); the local SI labels at
~40 uM (pIC50 >= 4.41). A model trained on local labels is therefore evaluated
against a different decision boundary, so we (a) exclude local compounds in the
4.4-5.0 gray zone and retrain, and (b) keep the original model as a sensitivity
analysis. Karim has no pIC50 column, so no gray zone can be removed on that side.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem.MolStandardize import rdMolStandardize
from rdkit.Chem.Scaffolds import MurckoScaffold

RDLogger.DisableLog("rdApp.*")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"
CP = ROOT / "data" / "chemprop"
REPORTS = ROOT / "reports"
CHOOSER = rdMolStandardize.LargestFragmentChooser()
UNCHARGER = rdMolStandardize.Uncharger()


def standardize(smiles):
    mol = Chem.MolFromSmiles(str(smiles).strip())
    if mol is None:
        return None
    try:
        mol = UNCHARGER.uncharge(CHOOSER.choose(mol))
    except Exception:
        return None
    std = Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)
    try:
        ik = Chem.MolToInchiKey(mol)
    except Exception:
        return None
    try:
        scaf = MurckoScaffold.MurckoScaffoldSmiles(mol=mol, includeChirality=False)
    except Exception:
        scaf = ""
    return {"smiles_std": std, "inchikey": ik, "murcko": scaf or "ACYCLIC"}


def prep_karim():
    raw = pd.read_csv(ROOT / "data/external/tdc/herg_karim.tab", sep="\t")
    rows = []
    for _, r in raw.iterrows():
        s = standardize(r["Drug"])
        if s is None:
            continue
        rows.append({"inchikey": s["inchikey"], "smiles_std": s["smiles_std"],
                     "murcko": s["murcko"], "y": int(r["Y"])})
    df = pd.DataFrame(rows)
    n_std = len(df)
    conflict = 0
    keep = []
    for key, g in df.groupby("inchikey", sort=False):
        if g["y"].nunique() > 1:
            conflict += 1
            continue
        keep.append(g.iloc[0])
    out = pd.DataFrame(keep).reset_index(drop=True)
    return raw, df, out, {"raw_rows": int(len(raw)), "standardized": int(n_std),
                          "unique_after_dedup": int(len(out)), "label_conflict_dropped": int(conflict),
                          "positives": int(out["y"].sum()), "negatives": int((out["y"] == 0).sum())}


def main():
    raw, std_all, karim, info = prep_karim()
    g = pd.read_csv(OUT / "global_split.csv", encoding="utf-8-sig")
    herg = g[g["endpoint"] == "herg"]
    local_keys = set(herg["inchikey"])
    local_skel = {k[:14] for k in local_keys}
    karim_full = set(karim["inchikey"])
    karim_skel = {k[:14] for k in karim_full}
    overlap_full = karim_full & local_keys
    overlap_skel = karim_skel & local_skel
    karim["in_local"] = karim["inchikey"].isin(local_keys)
    karim["in_local_skeleton"] = karim["inchikey"].str[:14].isin(local_skel)
    karim.to_csv(OUT / "karim_standardized.csv", index=False, encoding="utf-8-sig")

    # threshold-aligned local labels: positive pIC50>=5, negative pIC50<=4.4
    h = herg.copy()
    keep = ((h["y"] == 1) & (h["pIC50"] >= 5.0)) | ((h["y"] == 0) & (h["pIC50"] <= 4.4))
    aligned = h[keep].copy()
    aligned["y_orig"] = aligned["y"]
    aligned["y"] = np.where(aligned["pIC50"] >= 5.0, 1, 0)
    outdir = CP / "herg_aligned"
    outdir.mkdir(parents=True, exist_ok=True)
    for split in ["train", "valid", "test"]:
        part = aligned[aligned["split"] == split][["smiles_std", "y", "inchikey"]].rename(
            columns={"smiles_std": "smiles"})
        part.to_csv(outdir / f"{split}.csv", index=False)
    # external evaluation sets: Karim minus local compounds; clean also drops local scaffolds
    local_scaf = set(herg["murcko"])
    ext_all = karim[~karim["in_local"]][["smiles_std", "y", "inchikey"]].rename(
        columns={"smiles_std": "smiles"})
    ext_clean = karim[~karim["in_local"] & ~karim["murcko"].isin(local_scaf)][
        ["smiles_std", "y", "inchikey"]].rename(columns={"smiles_std": "smiles"})
    ext_all.to_csv(CP / "herg_aligned" / "external_all.csv", index=False)
    ext_clean.to_csv(CP / "herg_aligned" / "external_clean.csv", index=False)

    manifest = {
        "karim": info,
        "overlap": {
            "full_inchikey_with_local_herg": int(len(overlap_full)),
            "skeleton_with_local_herg": int(len(overlap_skel)),
            "karim_rows_removed": int(karim["in_local"].sum()),
            "karim_rows_sharing_local_scaffold": int(karim["murcko"].isin(local_scaf).sum()),
            "external_all_rows": int(len(ext_all)),
            "external_all_positives": int(ext_all["y"].sum()),
            "external_clean_rows": int(len(ext_clean)),
            "external_clean_positives": int(ext_clean["y"].sum()),
        },
        "threshold_alignment": {
            "rule": "positive pIC50>=5.0, negative pIC50<=4.4, gray 4.4-5.0 and missing pIC50 dropped",
            "local_rows_before": int(len(h)),
            "local_rows_after": int(len(aligned)),
            "dropped_gray": int(((h["pIC50"] > 4.4) & (h["pIC50"] < 5.0)).sum()),
            "dropped_missing_pIC50": int(h["pIC50"].isna().sum()),
            "per_split": {s: int((aligned["split"] == s).sum()) for s in ["train", "valid", "test"]},
            "per_split_pos": {s: int(aligned.loc[aligned["split"] == s, "y"].sum())
                              for s in ["train", "valid", "test"]},
        },
        "original_local_threshold_note": "local y = pIC50 >= 4.4089 (40 uM); 83 positives in 4.41-5.0",
    }
    (REPORTS / "p3_external_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
