"""Fit release calibrators and inventory every checkpoint for the public release."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from metrics import ece  # noqa: E402

RUNS = ROOT / "runs" / "chemprop"
RELEASE = ROOT / "release"
MODELS = RELEASE / "admet_predictor" / "models"
CALIBRATORS = RELEASE / "admet_predictor" / "calibrators"
ENDPOINTS = ("herg", "dili", "ames")
N_VALID = {"herg": 62, "dili": 44, "ames": 712}
N_TEST = {"herg": 59, "dili": 51, "ames": 732}


def logit(p: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    p = np.clip(p, eps, 1 - eps)
    return np.log(p / (1 - p))


def fit_temperature(p: np.ndarray, y: np.ndarray) -> float:
    z = logit(p)
    best_t, best_nll = 1.0, np.inf
    for t in np.geomspace(0.05, 20.0, 400):
        q = 1.0 / (1.0 + np.exp(-z / t))
        nll = log_loss(y, np.clip(q, 1e-6, 1 - 1e-6), labels=[0, 1])
        if nll < best_nll:
            best_t, best_nll = float(t), nll
    return best_t


def ensemble(endpoint: str) -> tuple[dict, list[int]]:
    dirs = sorted(RUNS.glob(f"{endpoint}_chemeleon_s*"))
    splits, seeds, lengths = {}, [], {}
    for directory in dirs:
        payload = json.loads((directory / "preds.json").read_text())
        seeds.append(int(payload["seed"]))
        for split in ("valid", "test"):
            values = np.asarray(payload["splits"][split]["p"], dtype=float)
            assert split not in lengths or lengths[split] == len(values)
            lengths[split] = len(values)
            splits.setdefault(split, []).append(values)
            if split == "valid":
                labels_valid = np.asarray(payload["splits"][split]["y"], dtype=int)
            else:
                labels_test = np.asarray(payload["splits"][split]["y"], dtype=int)
    return {
        "valid": (np.mean(splits["valid"], axis=0), labels_valid),
        "test": (np.mean(splits["test"], axis=0), labels_test),
    }, sorted(seeds)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def categorize(path: Path) -> dict:
    rel = path.relative_to(RUNS)
    parts = rel.parts
    if parts[0] == "lowdata":
        match = re.match(
            r"^(?P<endpoint>[a-z]+)_(?P<model>.+)_n(?P<n>\d+)_s(?P<seed>\d+)$", parts[1]
        )
        if match is None:
            raise ValueError(f"unexpected lowdata directory: {parts[1]}")
        return {
            "category": "lowdata",
            "endpoint": match["endpoint"],
            "model": match["model"],
            "n_train": int(match["n"]),
            "seed": int(match["seed"]),
        }
    if parts[0] == "_archive_short_budget":
        return {"category": "archive_short_budget", "endpoint": "",
                "model": "", "n_train": None, "seed": None}
    name = parts[0]
    if name.startswith("multi_"):
        model, seed = name.split("_")[1], name.split("_")[2]
        return {"category": "multitask", "endpoint": "pooled", "model": model,
                "n_train": None, "seed": int(seed.lstrip("s"))}
    if "_aligned_" in name:
        endpoint, rest = name.split("_aligned_")
        model, seed = rest.rsplit("_s", 1)
        return {"category": "external_aligned", "endpoint": endpoint, "model": model,
                "n_train": None, "seed": int(seed)}
    endpoint, model, seed = name.rsplit("_", 2)
    return {"category": "full_data", "endpoint": endpoint, "model": model,
            "n_train": None, "seed": int(seed.lstrip("s"))}


def main() -> None:
    CALIBRATORS.mkdir(parents=True, exist_ok=True)
    rows = []
    for endpoint in ENDPOINTS:
        splits, seeds = ensemble(endpoint)
        p_valid, y_valid = splits["valid"]
        p_test, y_test = splits["test"]
        temperature = fit_temperature(p_valid, y_valid)
        calibrated = 1.0 / (1.0 + np.exp(-logit(p_test) / temperature))
        record = {
            "endpoint": endpoint,
            "method": "temperature",
            "T": round(temperature, 6),
            "logit_eps": 1e-6,
            "seed_ensemble": seeds,
            "fit": {
                "split": "valid",
                "n": int(len(y_valid)),
                "source": "global scaffold-disjoint split",
                "used_for_early_stopping": True,
            },
            "reference_test": {
                "n": int(len(y_test)),
                "auc": round(float(roc_auc_score(y_test, p_test)), 6),
                "ece_raw": round(float(ece(y_test, p_test)), 6),
                "ece_calibrated": round(float(ece(y_test, calibrated)), 6),
                "brier_calibrated": round(float(brier_score_loss(y_test, calibrated)), 6),
            },
            "created": date.today().isoformat(),
            "note": (
                "The valid split also selected the early-stopping epoch; reference_test "
                "metrics are the honest estimate. Refit on a clean calibration set with "
                "fit_calibrators.py for coverage-critical use."
            ),
        }
        (CALIBRATORS / f"{endpoint}.json").write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8"
        )
        rows.append({
            "endpoint": endpoint,
            "T": record["T"],
            "n_valid": len(y_valid),
            "n_test": len(y_test),
            "auc_test": record["reference_test"]["auc"],
            "ece_raw": record["reference_test"]["ece_raw"],
            "ece_calibrated": record["reference_test"]["ece_calibrated"],
            "brier_calibrated": record["reference_test"]["brier_calibrated"],
        })
        print(endpoint, record["reference_test"], "T=", record["T"])

    pd.DataFrame(rows).to_csv(ROOT / "reports" / "release_calibration.csv", index=False)

    manifest = []
    for path in sorted(RUNS.rglob("best.pt")):
        if "_archive_short_budget" in path.parts:
            continue
        meta = categorize(path)
        manifest.append({
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            **meta,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    manifest_df = pd.DataFrame(manifest)
    manifest_df.to_csv(RELEASE / "MANIFEST_weights.csv", index=False)
    print(f"manifest rows: {len(manifest_df)}")
    print(manifest_df.groupby("category").size().to_string())

    shipped = sorted(MODELS.glob("*.pt"))
    with (RELEASE / "SHA256SUMS_models.txt").open("w", encoding="utf-8", newline="\n") as fh:
        for path in shipped:
            fh.write(f"{sha256(path)}  admet_predictor/models/{path.name}\n")
    print(f"shipped checkpoints: {len(shipped)}")


if __name__ == "__main__":
    main()
