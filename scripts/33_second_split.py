"""Build a second hERG-only scaffold-disjoint split for split-sensitivity analysis."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SPLIT = ROOT / "data" / "processed" / "global_split.csv"
OUT = ROOT / "data" / "processed" / "second_split"
REPORTS = ROOT / "reports"
FRACS = {"train": 0.8, "valid": 0.1, "test": 0.1}


def main() -> None:
    df = pd.read_csv(SPLIT, encoding="utf-8-sig")
    h = df[df["endpoint"] == "herg"].copy()
    scaffolds = (
        h.groupby("scaffold_key")
        .agg(n=("y", "size"), pos=("y", "sum"))
        .reset_index()
    )
    rng = np.random.default_rng(2027)
    scaffolds = scaffolds.iloc[rng.permutation(len(scaffolds))].reset_index(drop=True)

    targets = {s: FRACS[s] * len(h) for s in FRACS}
    pos_targets = {s: FRACS[s] * int(h["y"].sum()) for s in FRACS}
    cur = {s: 0 for s in FRACS}
    cur_pos = {s: 0 for s in FRACS}
    assignment: dict[str, str] = {}

    for row in scaffolds.itertuples(index=False):
        best_score, best_split = None, None
        for s in FRACS:
            score = (cur[s] + row.n) / targets[s] + 0.3 * (
                (cur_pos[s] + row.pos) / max(pos_targets[s], 1.0)
            )
            if best_score is None or score < best_score:
                best_score, best_split = score, s
        assignment[row.scaffold_key] = best_split
        cur[best_split] += row.n
        cur_pos[best_split] += row.pos

    h["split"] = h["scaffold_key"].map(assignment)
    checks = {
        "scaffold_disjoint": bool(h.groupby("scaffold_key")["split"].nunique().max() == 1),
        "compound_disjoint": bool(h.groupby("inchikey")["split"].nunique().max() == 1),
        "split_counts": {s: int((h["split"] == s).sum()) for s in FRACS},
        "split_positives": {s: int(h.loc[h["split"] == s, "y"].sum()) for s in FRACS},
        "n_compounds": int(len(h)),
        "n_scaffolds": int(h["scaffold_key"].nunique()),
    }
    if not checks["scaffold_disjoint"] or not checks["compound_disjoint"]:
        raise RuntimeError(f"split is not disjoint: {checks}")
    for s in FRACS:
        sub = h[h["split"] == s]
        if sub["y"].nunique() < 2:
            raise RuntimeError(f"{s} split has one class: {checks}")

    OUT.mkdir(parents=True, exist_ok=True)
    for s in FRACS:
        part = h[h["split"] == s][["smiles_std", "y", "inchikey"]].rename(
            columns={"smiles_std": "smiles"}
        )
        part.to_csv(OUT / f"herg_{s}.csv", index=False)
    h.to_csv(OUT / "herg_all.csv", index=False, encoding="utf-8-sig")
    manifest = {
        "endpoint": "herg",
        "seed": 2027,
        "algorithm": "random scaffold order + greedy deficit assignment",
        "fractions": FRACS,
        "checks": checks,
    }
    (REPORTS / "p0_split_manifest_second.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
