"""Deduplicate the three endpoints and build one scaffold-disjoint global split."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "splits").mkdir(exist_ok=True)

FRACS = {"train": 0.8, "valid": 0.1, "test": 0.1}


def dedup(df: pd.DataFrame, endpoint: str) -> tuple[pd.DataFrame, dict]:
    rows = []
    dropped_conflict = 0
    for key, g in df.groupby("inchikey", sort=False):
        counts = g["y"].value_counts()
        if len(counts) > 1:
            dropped_conflict += 1
            continue
        y = int(counts.index[0])
        has_pic50 = "pIC50" in g.columns
        p = g["pIC50"].median() if has_pic50 else np.nan
        p_spread = (
            (g["pIC50"].max() - g["pIC50"].min())
            if has_pic50 and g["pIC50"].notna().any()
            else np.nan
        )
        orig_external = False
        for col in ["SetI", "SetII"]:
            if col in g.columns:
                orig_external = orig_external or bool((g[col] == "External validation").any())
        rows.append(
            {
                "endpoint": endpoint,
                "inchikey": key,
                "smiles_std": g["smiles_std"].iloc[0],
                "murcko": g["murcko"].iloc[0],
                "y": y,
                "pIC50": p,
                "pIC50_available": bool(g["pIC50"].notna().any()) if "pIC50" in g.columns else False,
                "pIC50_spread": p_spread,
                "n_source_rows": len(g),
                "orig_external": orig_external,
                "orig_setI": g["SetI"].iloc[0] if "SetI" in g.columns else "",
                "orig_setII": g["SetII"].iloc[0] if "SetII" in g.columns else "",
            }
        )
    out = pd.DataFrame(rows)
    info = {
        "endpoint": endpoint,
        "raw_rows": int(len(df)),
        "unique_inchikey": int(df["inchikey"].nunique()),
        "label_conflict_groups_dropped": int(dropped_conflict),
        "modeling_rows": int(len(out)),
        "class_counts": {str(k): int(v) for k, v in out["y"].value_counts().sort_index().items()},
        "pIC50_available": int(out["pIC50_available"].sum()),
        "scaffolds": int(out["murcko"].nunique()),
        "acyclic": int((out["murcko"] == "ACYCLIC").sum()),
    }
    return out, info


def scaffold_key(row) -> str:
    # acyclic molecules must each get their own group, otherwise one giant ACYCLIC bin dominates a split
    if row["murcko"] == "ACYCLIC":
        return "ACYCLIC:" + row["inchikey"]
    return row["murcko"]


def global_scaffold_split(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = df.copy()
    # the same InChIKey can yield different Murcko scaffolds when represented as different tautomers;
    # force one canonical scaffold per compound so it cannot land in two splits
    canon = df.groupby("inchikey")["murcko"].agg(
        lambda s: sorted(s.value_counts().items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    )
    df["murcko"] = df["inchikey"].map(canon)
    df["scaffold_key"] = df.apply(scaffold_key, axis=1)
    items = []
    for key, g in df.groupby("scaffold_key", sort=False):
        items.append((key, len(g), int(g["y"].sum())))
    items.sort(key=lambda x: (-x[1], -x[2], x[0]))

    total = len(df)
    total_pos = int(df["y"].sum())
    targets = {s: FRACS[s] * total for s in FRACS}
    pos_targets = {s: FRACS[s] * total_pos for s in FRACS}
    cur = {s: 0 for s in FRACS}
    cur_pos = {s: 0 for s in FRACS}
    assignment = {}

    for key, n, pos in items:
        best_score, best_split = None, None
        for s in FRACS:
            comp_ratio = (cur[s] + n) / targets[s]
            pos_ratio = (cur_pos[s] + pos) / max(pos_targets[s], 1.0)
            score = comp_ratio + 0.3 * pos_ratio
            if best_score is None or score < best_score:
                best_score, best_split = score, s
        assignment[key] = best_split
        cur[best_split] += n
        cur_pos[best_split] += pos

    df["split"] = df["scaffold_key"].map(assignment)

    checks = {
        "scaffold_disjoint": bool(
            df.groupby("scaffold_key")["split"].nunique().max() == 1
        ),
        "compound_disjoint": bool(df.groupby("inchikey")["split"].nunique().max() == 1),
        "split_counts": {s: int((df["split"] == s).sum()) for s in FRACS},
        "split_positives": {s: int(df.loc[df["split"] == s, "y"].sum()) for s in FRACS},
    }
    return df, checks


def main():
    herg = pd.read_csv(OUT / "herg_local_standardized.csv", encoding="utf-8-sig")
    dili = pd.read_csv(OUT / "tdc_dili_standardized.csv", encoding="utf-8-sig")
    ames = pd.read_csv(OUT / "tdc_ames_standardized.csv", encoding="utf-8-sig")
    herg = herg.rename(columns={"Class": "y"})
    dili = dili.rename(columns={"Y": "y"})
    ames = ames.rename(columns={"Y": "y"})
    dili["pIC50"] = np.nan
    ames["pIC50"] = np.nan

    frames, infos = [], []
    for endpoint, df in [("herg", herg), ("dili", dili), ("ames", ames)]:
        d, info = dedup(df, endpoint)
        frames.append(d)
        infos.append(info)
    data = pd.concat(frames, ignore_index=True)
    data, checks = global_scaffold_split(data)

    per_endpoint = {}
    for endpoint in ["herg", "dili", "ames"]:
        sub = data[data["endpoint"] == endpoint]
        per_endpoint[endpoint] = {
            "split_counts": {s: int((sub["split"] == s).sum()) for s in FRACS},
            "split_positives": {s: int(sub.loc[sub["split"] == s, "y"].sum()) for s in FRACS},
            "pIC50_in_train": int(sub.loc[sub["split"] == "train", "pIC50_available"].sum()),
        }
        sub.drop(columns=["scaffold_key"]).to_csv(
            OUT / "splits" / f"{endpoint}_splits.csv", index=False, encoding="utf-8-sig"
        )
    data.to_csv(OUT / "global_split.csv", index=False, encoding="utf-8-sig")

    manifest = {"endpoints": infos, "global_checks": checks, "per_endpoint": per_endpoint,
                "fractions": FRACS, "algorithm": "deterministic greedy scaffold partition, acyclic compounds unique"}
    (REPORTS / "p0_split_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
