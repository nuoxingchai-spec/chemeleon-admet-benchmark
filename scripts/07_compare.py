"""Paired bootstrap comparison of two runs on the same test compounds."""
import argparse
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from compare_helpers import load_run, paired_bootstrap  # noqa: E402
from metrics import ece  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--tag-a", required=True, help="new model")
    ap.add_argument("--tag-b", required=True, help="reference model")
    args = ap.parse_args()

    a = load_run(args.tag_a, args.endpoint).rename(columns={"y": "y_a", "p": "p_a"})
    b = load_run(args.tag_b, args.endpoint).rename(columns={"y": "y_b", "p": "p_b"})
    m = a.merge(b[["inchikey", "p_b", "y_b"]], on="inchikey")
    assert (m["y_a"] == m["y_b"]).all(), "label mismatch"
    y = m["y_a"].to_numpy(int)
    pa = m["p_a"].to_numpy(float)
    pb = m["p_b"].to_numpy(float)

    row = {
        "endpoint": args.endpoint, "model_a": args.tag_a, "model_b": args.tag_b,
        "n": len(y),
        "auc_a": float(roc_auc_score(y, pa)), "auc_b": float(roc_auc_score(y, pb)),
        "ece_a": ece(y, pa), "ece_b": ece(y, pb),
        "brier_a": float(brier_score_loss(y, pa)), "brier_b": float(brier_score_loss(y, pb)),
        **paired_bootstrap(y, pa, pb),
    }
    print(pd.DataFrame([row]).to_string(index=False))
    out_path = ROOT / "reports" / "paired_comparisons.csv"
    df = pd.DataFrame([row])
    if out_path.exists():
        old = pd.read_csv(out_path)
        keys = ["endpoint", "model_a", "model_b"]
        old = old[~old.set_index(keys).index.isin(df.set_index(keys).index)]
        df = pd.concat([old, df], ignore_index=True)
    df.to_csv(out_path, index=False)


if __name__ == "__main__":
    main()
