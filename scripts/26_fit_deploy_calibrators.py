"""Fit deployment calibrators on the clean calibration split.

Deployment models are trained with an internal early-stopping split carved out
of train.  The global validation split is therefore never used for model
selection and can serve as an uncontaminated calibration set.
"""
import argparse
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs" / "deploy"
REPORTS = ROOT / "reports"
PACKAGE = ROOT / "admet_predictor" if (ROOT / "admet_predictor").exists() else ROOT / "release" / "admet_predictor"
CAL_DIR = PACKAGE / "calibrators"
EPS = 1e-6
SEEDS = (1, 2, 42)


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=float), EPS, 1.0 - EPS)
    return np.log(p / (1.0 - p))


def sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-z))


def apply_temperature(p: np.ndarray, t: float) -> np.ndarray:
    return sigmoid(logit(p) / t)


def ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (p >= lo) & (p < hi if hi < 1 else p <= hi)
        if mask.sum() == 0:
            continue
        total += mask.mean() * abs(y[mask].mean() - p[mask].mean())
    return float(total)


def brier(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def fit_temperature(p: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    z = logit(p)

    def nll(t: float) -> float:
        q = sigmoid(z / t)
        return float(-np.mean(y * np.log(np.clip(q, EPS, 1)) + (1 - y) * np.log(np.clip(1 - q, EPS, 1))))

    result = minimize_scalar(nll, bounds=(0.05, 20.0), method="bounded", options={"xatol": 1e-10})
    return float(result.x), float(result.fun)


def load_split(endpoint: str, split: str) -> tuple[np.ndarray, np.ndarray, list[str]]:
    frames = []
    for seed in SEEDS:
        path = RUNS / f"{endpoint}_s{seed}" / f"pred_{split}.csv"
        if not path.exists():
            raise FileNotFoundError(path)
        frame = pd.read_csv(path).rename(columns={"y": f"p{seed}"})
        frames.append(frame[["inchikey", f"p{seed}"]])
    merged = frames[0]
    for frame in frames[1:]:
        merged = merged.merge(frame, on="inchikey", how="inner", validate="one_to_one")
    labels = pd.read_csv(ROOT / "data" / "chemprop_deploy" / endpoint / f"{split}.csv")
    labels = labels[["inchikey", "y"]]
    merged = merged.merge(labels, on="inchikey", how="left", validate="one_to_one")
    if merged["y"].isna().any():
        raise ValueError(f"{endpoint}/{split}: missing labels after merge")
    probs = merged[[f"p{seed}" for seed in SEEDS]].to_numpy(dtype=float)
    return merged["y"].to_numpy(dtype=int), probs.mean(axis=1), merged["inchikey"].tolist()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", required=True, choices=["herg", "dili", "ames"])
    args = ap.parse_args()
    endpoint = args.endpoint

    y_cal, p_cal, _ = load_split(endpoint, "calib")
    y_test, p_test, keys = load_split(endpoint, "test")
    t, nll = fit_temperature(p_cal, y_cal)
    p_cal_t = apply_temperature(p_cal, t)
    p_test_t = apply_temperature(p_test, t)

    old_path = CAL_DIR / f"{endpoint}.json"

    row = {
        "endpoint": endpoint,
        "T": round(t, 6),
        "calib_n": int(len(y_cal)),
        "calib_pos": int(y_cal.sum()),
        "calib_ece_raw": ece(y_cal, p_cal),
        "calib_ece_cal": ece(y_cal, p_cal_t),
        "calib_brier_raw": brier(y_cal, p_cal),
        "calib_brier_cal": brier(y_cal, p_cal_t),
        "test_n": int(len(y_test)),
        "test_pos": int(y_test.sum()),
        "test_auc": float(roc_auc_score(y_test, p_test)),
        "test_ece_raw": ece(y_test, p_test),
        "test_ece_cal": ece(y_test, p_test_t),
        "test_brier_raw": brier(y_test, p_test),
        "test_brier_cal": brier(y_test, p_test_t),
        "test_nll_cal": float(-np.mean(y_test * np.log(np.clip(p_test_t, EPS, 1)) + (1 - y_test) * np.log(np.clip(1 - p_test_t, EPS, 1)))),
    }
    out = REPORTS / "deploy_calibration.csv"
    df = pd.DataFrame([row])
    if out.exists():
        old_df = pd.read_csv(out)
        old_df = old_df[old_df["endpoint"] != endpoint]
        df = pd.concat([old_df, df], ignore_index=True)
    df.to_csv(out, index=False)

    pd.DataFrame({"inchikey": keys, "y": y_test, "p_raw": p_test, "p_cal": p_test_t}).to_csv(
        REPORTS / f"deploy_ensemble_{endpoint}_test.csv", index=False
    )

    payload = {
        "endpoint": endpoint,
        "method": "temperature",
        "T": round(t, 6),
        "logit_eps": EPS,
        "seed_ensemble": list(SEEDS),
        "fit": {
            "split": "global valid (calibration only)",
            "n": int(len(y_cal)),
            "positives": int(y_cal.sum()),
            "source": "global scaffold-disjoint split",
            "used_for_early_stopping": False,
            "early_stopping": "internal scaffold-disjoint split carved from train (12% of compounds)",
        },
        "reference_test": {
            "n": int(len(y_test)),
            "positives": int(y_test.sum()),
            "auc": round(row["test_auc"], 6),
            "ece_raw": round(row["test_ece_raw"], 6),
            "ece_calibrated": round(row["test_ece_cal"], 6),
            "brier_raw": round(row["test_brier_raw"], 6),
            "brier_calibrated": round(row["test_brier_cal"], 6),
        },
        "deployment_models": {
            "description": "CheMeleon fine-tuned with internal early stopping; calibration split never used for model selection",
            "seeds": list(SEEDS),
            "train_fraction": 0.88,
        },
        "created": str(date.today()),
    }
    old_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"endpoint": endpoint, **row}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
