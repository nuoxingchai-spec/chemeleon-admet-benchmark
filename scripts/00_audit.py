"""P0 audit: standardize the local hERG SI, check overlap with TDC, and identify split types."""
import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem.MolStandardize import rdMolStandardize
from rdkit.Chem.Scaffolds import MurckoScaffold

RDLogger.DisableLog("rdApp.*")

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "mp6b00471_si_001.xlsx"
TDC = ROOT / "data" / "external" / "tdc"
OUT = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
OUT.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)

CHOOSER = rdMolStandardize.LargestFragmentChooser()
UNCHARGER = rdMolStandardize.Uncharger()


def standardize(smiles: str) -> dict:
    smiles = str(smiles).strip()
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"status": "invalid"}
    try:
        mol = CHOOSER.choose(mol)
        mol = UNCHARGER.uncharge(mol)
    except Exception:
        return {"status": "standardize_failed"}
    std = Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)
    try:
        ik = Chem.MolToInchiKey(mol)
    except Exception:
        ik = ""
    try:
        scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=mol, includeChirality=False)
    except Exception:
        scaffold = ""
    return {
        "status": "ok",
        "smiles_std": std,
        "inchikey": ik,
        "inchikey_skeleton": ik[:14] if len(ik) >= 14 else "",
        "murcko": scaffold if scaffold else "ACYCLIC",
    }


def load_local() -> pd.DataFrame:
    raw = pd.read_excel(RAW, sheet_name="Final", header=None)
    hdr = raw.index[raw[0].astype(str).str.strip() == "No"][0]
    df = raw.iloc[hdr + 2 :, :7].copy()
    df.columns = ["No", "SMILES", "Name", "pIC50", "Class", "SetI", "SetII"]
    df["No"] = pd.to_numeric(df["No"], errors="coerce")
    df = df[df["No"].notna()].copy()
    df["No"] = df["No"].astype(int)
    df["Name"] = df["Name"].fillna("").astype(str).str.strip()
    df["pIC50"] = pd.to_numeric(df["pIC50"].replace("NA", None), errors="coerce")
    df["Class"] = pd.to_numeric(df["Class"], errors="coerce").astype("Int64")
    df = df[df["Class"].notna()].copy()
    df["Class"] = df["Class"].astype(int)
    df["SMILES"] = df["SMILES"].astype(str).str.strip()
    std = df["SMILES"].map(standardize)
    for key in ["status", "smiles_std", "inchikey", "inchikey_skeleton", "murcko"]:
        df[key] = [d.get(key) for d in std]
    return df


def load_tdc(name: str) -> pd.DataFrame:
    df = pd.read_csv(TDC / f"{name}.tab", sep="\t")
    df.columns = ["Drug_ID", "SMILES", "Y"]
    df["SMILES"] = df["SMILES"].astype(str).str.strip()
    std = df["SMILES"].map(standardize)
    for key in ["status", "smiles_std", "inchikey", "inchikey_skeleton", "murcko"]:
        df[key] = [d.get(key) for d in std]
    df["Y"] = pd.to_numeric(df["Y"], errors="coerce")
    return df


def scaffold_overlap(train: pd.DataFrame, test: pd.DataFrame) -> dict:
    tr = set(train["murcko"])
    te = set(test["murcko"])
    covered = len(te & tr)
    per_compound = test["murcko"].isin(tr).mean()
    return {
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "train_scaffolds": len(tr),
        "test_scaffolds": len(te),
        "test_scaffolds_seen_in_train": covered,
        "test_scaffold_coverage": round(float(covered / len(te)), 4) if te else None,
        "test_compounds_with_seen_scaffold_frac": round(float(per_compound), 4),
    }


local = load_local()
herg = load_tdc("herg")
dili = load_tdc("dili")
ames = load_tdc("ames")

summary = {
    "local": {
        "rows": int(len(local)),
        "invalid_smiles": int((local["status"] != "ok").sum()),
        "unique_full_inchikey": int(local["inchikey"].nunique()),
        "duplicate_inchikey_rows": int(len(local) - local["inchikey"].nunique()),
        "class_counts": {str(k): int(v) for k, v in local["Class"].value_counts().sort_index().items()},
        "pIC50_available": int(local["pIC50"].notna().sum()),
        "pIC50_missing": int(local["pIC50"].isna().sum()),
        "class0_pIC50_max": float(local.loc[local["Class"] == 0, "pIC50"].max()),
        "class1_pIC50_min": float(local.loc[local["Class"] == 1, "pIC50"].min()),
        "salts_or_mixtures": int(local["SMILES"].str.contains(r"\.", regex=True).sum()),
        "charged": int(local["SMILES"].str.contains(r"\[.*[+-]\]", regex=True).sum()),
        "split_I": {str(k): int(v) for k, v in local["SetI"].value_counts().items()},
        "split_II": {str(k): int(v) for k, v in local["SetII"].value_counts().items()},
    },
    "tdc_herg": {
        "rows": int(len(herg)),
        "invalid_smiles": int((herg["status"] != "ok").sum()),
        "unique_full_inchikey": int(herg["inchikey"].nunique()),
        "class_counts": {str(k): int(v) for k, v in herg["Y"].value_counts().sort_index().items()},
    },
    "overlap_local_vs_tdc_herg": {},
    "split_types": {},
    "other_endpoints": {},
}

local_keys = set(local["inchikey_skeleton"]) - {""}
herg_keys = set(herg["inchikey_skeleton"]) - {""}
local_full = set(local["inchikey"]) - {""}
herg_full = set(herg["inchikey"]) - {""}

overlap = {
    "skeleton_overlap_local_in_tdc": len(local_keys & herg_keys),
    "skeleton_overlap_tdc_in_local": len(herg_keys & local_keys),
    "full_overlap_local_in_tdc": len(local_full & herg_full),
    "local_coverage_by_tdc": round(len(local_keys & herg_keys) / len(local_keys), 4),
    "tdc_coverage_by_local": round(len(herg_keys & local_keys) / len(herg_keys), 4),
}
summary["overlap_local_vs_tdc_herg"] = overlap

local["in_tdc"] = local["inchikey_skeleton"].isin(herg_keys)
herg["in_local"] = herg["inchikey_skeleton"].isin(local_keys)
for col in ["SetI", "SetII"]:
    summary["overlap_local_vs_tdc_herg"][f"local_in_tdc_by_{col}"] = {
        str(k): int(v) for k, v in local.groupby(col)["in_tdc"].sum().items()
    }

for tag, tr_label, te_label in [
    ("SetI", "Training I", "Test I"),
    ("SetII", "Training II", "Test II"),
]:
    tr = local[local[tag] == tr_label]
    te = local[local[tag] == te_label]
    ext = local[local[tag] == "External validation"]
    summary["split_types"][tag] = {
        "train": scaffold_overlap(tr, tr),
        "test_vs_train": scaffold_overlap(tr, te),
        "external_vs_train": scaffold_overlap(tr, ext),
        "compound_overlap_train_test": int(len(set(tr["inchikey"]) & set(te["inchikey"]))),
    }
    # avoid storing self-overlap noise
    summary["split_types"][tag].pop("train", None)

for name, df in [("dili", dili), ("ames", ames)]:
    summary["other_endpoints"][name] = {
        "rows": int(len(df)),
        "invalid_smiles": int((df["status"] != "ok").sum()),
        "unique_full_inchikey": int(df["inchikey"].nunique()),
        "duplicate_rows": int(len(df) - df["inchikey"].nunique()),
        "class_counts": {str(k): int(v) for k, v in df["Y"].value_counts().sort_index().items()},
        "acyclic": int((df["murcko"] == "ACYCLIC").sum()),
    }

local.to_csv(OUT / "herg_local_standardized.csv", index=False, encoding="utf-8-sig")
herg.to_csv(OUT / "tdc_herg_standardized.csv", index=False, encoding="utf-8-sig")
dili.to_csv(OUT / "tdc_dili_standardized.csv", index=False, encoding="utf-8-sig")
ames.to_csv(OUT / "tdc_ames_standardized.csv", index=False, encoding="utf-8-sig")
(REPORTS / "p0_audit.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

print(json.dumps(summary, indent=2, ensure_ascii=False))
