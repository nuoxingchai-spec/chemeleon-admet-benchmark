"""Build seed-2027 second scaffold-disjoint splits for DILI and Ames."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SPLIT = ROOT / "data" / "processed" / "global_split.csv"
OUT = ROOT / "data" / "chemprop_second"
REPORTS = ROOT / "reports"
FRACS = {"train": 0.8, "valid": 0.1, "test": 0.1}
# First seed in 2027..2040 whose size-only greedy split keeps validation/test
# positive rates within 0.05 of the endpoint rate.
SEEDS = {"dili": 2030, "ames": 2033}
POS_WEIGHT = 0.0


def build(endpoint: str, df: pd.DataFrame, seed: int) -> dict:
    sub = df[df["endpoint"] == endpoint].copy()
    scaffolds = (
        sub.groupby("scaffold_key")
        .agg(n=("y", "size"), pos=("y", "sum"))
        .reset_index()
    )
    rng = np.random.default_rng(seed)
    scaffolds = scaffolds.iloc[rng.permutation(len(scaffolds))].reset_index(drop=True)

    targets = {s: FRACS[s] * len(sub) for s in FRACS}
    pos_targets = {s: FRACS[s] * int(sub["y"].sum()) for s in FRACS}
    cur = {s: 0 for s in FRACS}
    cur_pos = {s: 0 for s in FRACS}
    assignment: dict[str, str] = {}
    for row in scaffolds.itertuples(index=False):
        best_score, best_split = None, None
        for s in FRACS:
            score = (cur[s] + row.n) / targets[s] + POS_WEIGHT * (
                (cur_pos[s] + row.pos) / max(pos_targets[s], 1.0)
            )
            if best_score is None or score < best_score:
                best_score, best_split = score, s
        assignment[row.scaffold_key] = best_split
        cur[best_split] += row.n
        cur_pos[best_split] += row.pos

    sub["split"] = sub["scaffold_key"].map(assignment)
    checks = {
        "scaffold_disjoint": bool(sub.groupby("scaffold_key")["split"].nunique().max() == 1),
        "compound_disjoint": bool(sub.groupby("inchikey")["split"].nunique().max() == 1),
        "split_counts": {s: int((sub["split"] == s).sum()) for s in FRACS},
        "split_positives": {s: int(sub.loc[sub["split"] == s, "y"].sum()) for s in FRACS},
        "n_compounds": int(len(sub)),
        "n_scaffolds": int(sub["scaffold_key"].nunique()),
    }
    if not checks["scaffold_disjoint"] or not checks["compound_disjoint"]:
        raise RuntimeError(f"{endpoint}: split is not disjoint: {checks}")
    for s in FRACS:
        part = sub[sub["split"] == s]
        if part["y"].nunique() < 2:
            raise RuntimeError(f"{endpoint}/{s}: one class: {checks}")

    out_dir = OUT / endpoint
    out_dir.mkdir(parents=True, exist_ok=True)
    for s in FRACS:
        part = sub[sub["split"] == s][["smiles_std", "y", "inchikey"]].rename(
            columns={"smiles_std": "smiles"}
        )
        part.to_csv(out_dir / f"{s}.csv", index=False)
    return {"endpoint": endpoint, "seed": seed, "checks": checks}


def main() -> None:
    df = pd.read_csv(SPLIT, encoding="utf-8-sig")
    manifests = [build(ep, df, SEEDS[ep]) for ep in ("dili", "ames")]
    path = REPORTS / "second_split_all_manifest.json"
    path.write_text(json.dumps(manifests, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(manifests, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
