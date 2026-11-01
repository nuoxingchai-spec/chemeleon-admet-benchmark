"""Corpus exposure of the external hERG evaluation sets."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PRETRAIN = ROOT / "data" / "external" / "chemeleon_pretrain" / "pretrain_inchikeys.csv"
EXTERNAL = ROOT / "data" / "chemprop" / "herg_aligned"
REPORTS = ROOT / "reports"


def main() -> None:
    pre = pd.read_csv(PRETRAIN, dtype=str)["inchikey"]
    keys = set(pre)
    conn = set(pre.str[:14])
    report = {}
    for name in ("external_all", "external_clean"):
        df = pd.read_csv(EXTERNAL / f"{name}.csv", dtype={"inchikey": str})
        ik = df["inchikey"].astype(str)
        exact = ik.isin(keys)
        overlap = ik.str[:14].isin(conn)
        report[name] = {
            "n": int(len(ik)),
            "exact": int(exact.sum()),
            "exact_frac": float(exact.mean()),
            "connectivity": int(overlap.sum()),
            "connectivity_frac": float(overlap.mean()),
            "connectivity_clean": int((~overlap).sum()),
        }
    (REPORTS / "external_exposure.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
