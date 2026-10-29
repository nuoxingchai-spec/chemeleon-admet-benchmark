"""Rebuild reports/chemprop_runs.csv from run artifacts so model labels are unambiguous."""
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from metrics import metrics  # noqa: E402

RUNS = ROOT / "runs" / "chemprop"
OUT = ROOT / "reports" / "chemprop_runs.csv"
PATTERN = re.compile(r"^(herg|dili|ames)_(chemeleon|scratch|matched_dropout|matched)_s(\d+)$")
LABEL = {
    "chemeleon": "chemprop_chemeleon",
    "scratch": "chemprop_none",
    "matched": "chemprop_matched",
    "matched_dropout": "chemprop_matched_dropout",
}


def main():
    rows = []
    for d in sorted(RUNS.iterdir()):
        pj = d / "preds.json"
        if not pj.exists():
            continue
        data = json.loads(pj.read_text())
        m = PATTERN.match(d.name)
        if m:
            endpoint, model, seed = m.group(1), LABEL[m.group(2)], int(m.group(3))
            for split in ["valid", "test"]:
                s = data["splits"][split]
                met = metrics(pd.Series(s["y"]).to_numpy(), pd.Series(s["p"]).to_numpy(dtype=float))
                met.update({"endpoint": endpoint, "model": model, "seed": seed, "split": split})
                rows.append(met)
        elif d.name.startswith("multi_chemeleon_s"):
            seed = int(d.name.rsplit("_s", 1)[1])
            for split in ["valid", "test"]:
                for endpoint, s in data["splits"][split].items():
                    met = metrics(pd.Series(s["y"]).to_numpy(), pd.Series(s["p"]).to_numpy(dtype=float))
                    met.update({"endpoint": endpoint, "model": "multitask_chemeleon",
                                "seed": seed, "split": split})
                    rows.append(met)
    df = pd.DataFrame(rows)
    cols = ["endpoint", "model", "seed", "split", "n", "pos", "auc", "auc_ci_low", "auc_ci_high",
            "pr_auc", "acc", "mcc", "brier", "ece"]
    df = df[cols].sort_values(["endpoint", "model", "seed", "split"]).reset_index(drop=True)
    df.to_csv(OUT, index=False)
    print(df.to_string(index=False))
    print(f"\nwrote {OUT} ({len(df)} rows)")


if __name__ == "__main__":
    main()
