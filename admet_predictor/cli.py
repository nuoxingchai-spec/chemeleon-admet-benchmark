"""Batch prediction from a CSV file with a `smiles` column."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .engine import ADMETPredictor


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="CSV with a 'smiles' column")
    parser.add_argument("--output", required=True, help="destination CSV")
    parser.add_argument("--model-dir", default=None)
    parser.add_argument("--calibrator-dir", default=None)
    parser.add_argument("--device", default="cpu", help="cpu or cuda:0")
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()

    frame = pd.read_csv(args.input)
    if "smiles" not in frame.columns:
        raise SystemExit("input CSV must contain a 'smiles' column")

    predictor = ADMETPredictor(
        model_dir=args.model_dir,
        calibrator_dir=args.calibrator_dir,
        device=args.device,
        batch_size=args.batch_size,
    )
    predictions, invalid = predictor.predict(
        frame["smiles"].tolist(), return_invalid=True
    )
    predictions.to_csv(args.output, index=False)
    print(f"wrote {len(predictions)} predictions to {args.output}")

    if len(invalid):
        invalid_path = Path(args.output).with_suffix(".invalid.csv")
        invalid.to_csv(invalid_path, index=False)
        print(f"skipped {len(invalid)} invalid SMILES, see {invalid_path}")


if __name__ == "__main__":
    main()
