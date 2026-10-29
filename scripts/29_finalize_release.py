"""Regenerate shipped example predictions and the bundle checksum file."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release"
PACKAGE = RELEASE / "admet_predictor"
sys.path.insert(0, str(RELEASE))

from admet_predictor import ADMETPredictor  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    inputs = pd.read_csv(PACKAGE / "examples" / "input.csv")
    predictor = ADMETPredictor()
    predictions, invalid = predictor.predict(inputs["smiles"].tolist(), return_invalid=True)
    if len(invalid):
        raise SystemExit(f"invalid example SMILES: {invalid}")
    predictions.to_csv(PACKAGE / "examples" / "expected_outputs.csv", index=False)
    print(f"refreshed {len(predictions)} example predictions")

    calibration = pd.read_csv(ROOT / "reports" / "deploy_calibration.csv").set_index("endpoint")
    ames = calibration.loc["ames"]
    card = PACKAGE / "model_card.md"
    text = card.read_text(encoding="utf-8")
    replacements = {
        "AMES_AUC": f"{ames['test_auc']:.4f}",
        "AMES_ECE_RAW": f"{ames['test_ece_raw']:.4f}",
        "AMES_ECE_CAL": f"{ames['test_ece_cal']:.4f}",
        "AMES_BRIER_CAL": f"{ames['test_brier_cal']:.4f}",
        "AMES_CAL_ECE_RAW": f"{ames['calib_ece_raw']:.4f}",
        "AMES_CAL_ECE_CAL": f"{ames['calib_ece_cal']:.4f}",
        "AMES_CAL_BRIER_RAW": f"{ames['calib_brier_raw']:.4f}",
        "AMES_CAL_BRIER_CAL": f"{ames['calib_brier_cal']:.4f}",
        "AMES_T": f"{ames['T']:.6f}",
    }
    for key, value in replacements.items():
        text = text.replace(key, value)

    sums = (PACKAGE.parent / "SHA256SUMS_models.txt").read_text(encoding="utf-8").splitlines()
    rows = []
    for line in sums:
        digest, path = line.split("  ", 1)
        rows.append(f"| {Path(path).name} | {digest} |")
    table = "| File | SHA-256 |\n|---|---|\n" + "\n".join(rows)
    text = text.replace("DEPLOY_SHA_TABLE", table)
    card.write_text(text, encoding="utf-8")
    print("updated model card placeholders")

    files = [
        "LICENSE",
        "NOTICE",
        "README.md",
        "RELEASE_NOTES_v1.1.0.md",
        "MANIFEST_weights.csv",
        "SHA256SUMS_models.txt",
        "package_weights.py",
        "admet_predictor/__init__.py",
        "admet_predictor/engine.py",
        "admet_predictor/cli.py",
        "admet_predictor/app_fastapi.py",
        "admet_predictor/app_gradio.py",
        "admet_predictor/fit_calibrators.py",
        "admet_predictor/verify.py",
        "admet_predictor/requirements.txt",
        "admet_predictor/README.md",
        "admet_predictor/model_card.md",
        "admet_predictor/examples/input.csv",
        "admet_predictor/examples/expected_outputs.csv",
    ]
    files += [
        str(path.relative_to(RELEASE)).replace("\\", "/")
        for path in sorted((PACKAGE / "calibrators").glob("*.json"))
    ]
    files += [
        str(path.relative_to(RELEASE)).replace("\\", "/")
        for path in sorted((PACKAGE / "sensitivity").glob("*.json"))
    ]
    lines = []
    for relative in files:
        path = RELEASE / relative
        if not path.exists():
            raise FileNotFoundError(path)
        lines.append(f"{sha256(path)}  {relative}")
    (RELEASE / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {RELEASE / 'SHA256SUMS'} ({len(lines)} files)")


if __name__ == "__main__":
    main()
