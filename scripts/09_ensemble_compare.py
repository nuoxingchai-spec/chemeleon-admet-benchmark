"""Seed-ensemble comparison: average predictions over seeds, then paired bootstrap."""
import argparse
import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from metrics import ece  # noqa: E402
from compare_helpers import load_run, paired_bootstrap  # noqa: E402


def ensemble(pattern: str, endpoint: str) -> pd.DataFrame:
    tags = [Path(p).parent.name for p in glob.glob(str(ROOT / "runs" / "chemprop" / pattern / "preds.json"))]
    if not tags:
        raise FileNotFoundError(f"no runs match {pattern}")
    frames = [load_run(t, endpoint) for t in tags]
    base = frames[0][["inchikey", "y"]]
    ps = pd.concat([f.set_index("inchikey")["p"] for f in frames], axis=1).mean(axis=1)
    out = base.merge(ps.rename("p"), on="inchikey")
    return out.sort_values("inchikey").reset_index(drop=True), tags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--pattern-a", required=True)
    ap.add_argument("--pattern-b", required=True)
    args = ap.parse_args()

    a, ta = ensemble(args.pattern_a, args.endpoint)
    b, tb = ensemble(args.pattern_b, args.endpoint)
    m = a.merge(b[["inchikey", "p"]], on="inchikey", suffixes=("_a", "_b"))
    y = m["y"].to_numpy(int)
    pa = m["p_a"].to_numpy(float)
    pb = m["p_b"].to_numpy(float)
    row = {
        "endpoint": args.endpoint,
        "model_a": f"{args.pattern_a}({len(ta)})",
        "model_b": f"{args.pattern_b}({len(tb)})",
        "n": len(y),
        "auc_a": float(roc_auc_score(y, pa)), "auc_b": float(roc_auc_score(y, pb)),
        "ece_a": ece(y, pa), "ece_b": ece(y, pb),
        "brier_a": float(brier_score_loss(y, pa)), "brier_b": float(brier_score_loss(y, pb)),
        **paired_bootstrap(y, pa, pb),
    }
    df = pd.DataFrame([row])
    print(df.to_string(index=False))
    out_path = ROOT / "reports" / "ensemble_comparisons.csv"
    if out_path.exists():
        old = pd.read_csv(out_path)
        keys = ["endpoint", "model_a", "model_b"]
        old = old[~old.set_index(keys).index.isin(df.set_index(keys).index)]
        df = pd.concat([old, df], ignore_index=True)
    df.to_csv(out_path, index=False)


if __name__ == "__main__":
    main()
