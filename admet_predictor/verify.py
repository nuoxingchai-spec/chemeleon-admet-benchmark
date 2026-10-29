"""Smoke test: reproduce the shipped example predictions and check metadata."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .engine import ADMETPredictor

TOLERANCE = 1e-4


def main() -> None:
    root = Path(__file__).resolve().parent
    inputs = pd.read_csv(root / "examples" / "input.csv")
    expected = pd.read_csv(root / "examples" / "expected_outputs.csv")

    predictor = ADMETPredictor()
    predictions, invalid = predictor.predict(
        inputs["smiles"].tolist(), return_invalid=True
    )
    if len(invalid):
        raise AssertionError(f"unexpected invalid SMILES: {len(invalid)}")

    columns = [column for column in expected.columns if column != "smiles"]
    difference = np.abs(
        predictions[columns].to_numpy() - expected[columns].to_numpy()
    ).max()
    print(f"max |engine - expected| = {difference:.2e}")
    if difference > TOLERANCE:
        raise AssertionError(f"prediction mismatch above {TOLERANCE}")

    try:
        predictor.predict(["this-is-not-a-smiles"])
    except ValueError:
        print("invalid SMILES rejected")
    else:
        raise AssertionError("invalid SMILES was not rejected")

    for endpoint, calibrator in predictor.calibrators.items():
        reference = calibrator["reference_test"]
        print(
            f"{endpoint}: T={calibrator['T']:.3f} "
            f"n_fit={calibrator['fit']['n']} "
            f"test ECE raw={reference['ece_raw']:.3f} "
            f"calibrated={reference['ece_calibrated']:.3f}"
        )
    print("release verification passed")


if __name__ == "__main__":
    main()
