"""Refit temperature scaling on a user-supplied labeled calibration set.

The shipped calibrators were fitted on the global validation split, which the
deployment models never used for early stopping.  For coverage-critical or
shifted deployments, pass a fresh labeled CSV (`smiles,y`):

    python -m admet_predictor.fit_calibrators \
        --endpoint herg --input my_calibration.csv --out herg.json
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss

from .engine import ENDPOINTS, _logit, ADMETPredictor


def fit_temperature(probabilities: np.ndarray, labels: np.ndarray) -> float:
    logits = _logit(probabilities)
    best_t, best_nll = 1.0, np.inf
    for t in np.geomspace(0.05, 20.0, 400):
        q = 1.0 / (1.0 + np.exp(-logits / t))
        nll = log_loss(labels, np.clip(q, 1e-6, 1 - 1e-6), labels=[0, 1])
        if nll < best_nll:
            best_t, best_nll = float(t), float(nll)
    return best_t


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True, choices=ENDPOINTS)
    parser.add_argument("--input", required=True, help="CSV with smiles and y columns")
    parser.add_argument("--out", required=True, help="output calibrator JSON")
    parser.add_argument("--model-dir", default=None)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    frame = pd.read_csv(args.input)
    missing = {"smiles", "y"} - set(frame.columns)
    if missing:
        raise SystemExit(f"input CSV is missing columns: {sorted(missing)}")

    predictor = ADMETPredictor(model_dir=args.model_dir, device=args.device)
    valid, invalid = predictor._validate(frame["smiles"].tolist())
    if invalid:
        raise SystemExit(
            f"{len(invalid)} invalid SMILES; clean the calibration set first"
        )
    raw = predictor._raw_prob(args.endpoint, [smi for _, smi in valid])
    labels = frame["y"].to_numpy(dtype=int)
    temperature = fit_temperature(raw, labels)

    seeds = sorted(int(p.stem.split("seed")[1]) for p in predictor.model_dir.glob(
        f"{args.endpoint}_seed*.pt"
    ))
    calibrator = {
        "endpoint": args.endpoint,
        "method": "temperature",
        "T": round(temperature, 6),
        "logit_eps": 1e-6,
        "seed_ensemble": seeds,
        "fit": {
            "split": "user-supplied",
            "n": int(len(labels)),
            "source": Path(args.input).name,
            "used_for_early_stopping": False,
        },
        "created": date.today().isoformat(),
        "note": "Refit on a user-supplied calibration set; verify that it was not used for model selection.",
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(calibrator, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out_path} (T={temperature:.4f}, n={len(labels)})")


if __name__ == "__main__":
    main()
