"""External clean-data calibration refit and stress test (hERG).

The only independent labelled external set in this project is the Karim hERG
set after compound- and scaffold-overlap removal.  It uses a 10 uM decision
boundary, whereas the local models are trained at ~40 uM, so fitting a
temperature on it is a stress test rather than the shipped calibration.
"""
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
PY = Path(sys.executable)
CHEMPROP = PY.parent / "chemprop.exe"
RUNS = ROOT / "runs" / "deploy"
EXT = ROOT / "data" / "chemprop" / "herg_aligned" / "external_clean.csv"
REPORTS = ROOT / "reports"
PACKAGE = ROOT / "admet_predictor" if (ROOT / "admet_predictor").exists() else ROOT / "release" / "admet_predictor"
CAL = PACKAGE / "calibrators" / "herg.json"
SENS = PACKAGE / "sensitivity"
EPS = 1e-6
SEEDS = (1, 2, 42)


def logit(p):
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    return np.log(p / (1 - p))


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def ece(y, p, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (p >= lo) & (p < hi if hi < 1 else p <= hi)
        if mask.any():
            total += mask.mean() * abs(y[mask].mean() - p[mask].mean())
    return float(total)


def brier(y, p):
    return float(np.mean((p - y) ** 2))


def fit_t(p, y):
    z = logit(p)

    def nll(t):
        q = sigmoid(z / t)
        return float(-np.mean(y * np.log(np.clip(q, EPS, 1)) + (1 - y) * np.log(np.clip(1 - q, EPS, 1))))

    r = minimize_scalar(nll, bounds=(0.05, 20.0), method="bounded", options={"xatol": 1e-10})
    return float(r.x)


def predict_external() -> pd.DataFrame:
    first = RUNS / "herg_s1" / "pred_external.csv"
    frames = []
    for seed in SEEDS:
        path = RUNS / f"herg_s{seed}" / "pred_external.csv"
        if not path.exists():
            cmd = [
                str(CHEMPROP), "predict",
                "-i", str(EXT),
                "--model-paths", str(RUNS / f"herg_s{seed}" / "model_0" / "best.pt"),
                "-o", str(path),
                "--accelerator", "cpu", "--devices", "1", "--num-workers", "0",
            ]
            env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
            with (RUNS / f"herg_s{seed}" / "train.log").open("a", encoding="utf-8") as fh:
                fh.write("+ " + " ".join(cmd) + "\n")
                proc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, cwd=ROOT, env=env)
            if proc.returncode != 0:
                raise RuntimeError(f"predict failed for seed {seed}")
        frame = pd.read_csv(path).rename(columns={"y": f"p{seed}"})[["inchikey", f"p{seed}"]]
        frames.append(frame)
    merged = frames[0]
    for frame in frames[1:]:
        merged = merged.merge(frame, on="inchikey", how="inner", validate="one_to_one")
    labels = pd.read_csv(EXT)[["inchikey", "y"]]
    merged = merged.merge(labels, on="inchikey", how="left", validate="one_to_one")
    merged["p"] = merged[[f"p{seed}" for seed in SEEDS]].mean(axis=1)
    return merged[["inchikey", "y", "p"]]


def main() -> None:
    ext = predict_external()
    y_ext = ext["y"].to_numpy(dtype=int)
    p_ext = ext["p"].to_numpy(dtype=float)
    t_ext = fit_t(p_ext, y_ext)

    cal = json.loads(CAL.read_text(encoding="utf-8"))
    t_int = float(cal["T"])

    test = pd.read_csv(REPORTS / "deploy_ensemble_herg_test.csv")
    y_te = test["y"].to_numpy(dtype=int)
    p_te = test["p_raw"].to_numpy(dtype=float)

    ext_fit = sigmoid(logit(p_ext) / t_ext)
    int_on_ext = sigmoid(logit(p_ext) / t_int)
    ext_on_test = sigmoid(logit(p_te) / t_ext)

    rows = [
        {"setting": "external_clean vs external_fit", "n": len(y_ext), "T": t_ext,
         "ece": ece(y_ext, ext_fit), "brier": brier(y_ext, ext_fit)},
        {"setting": "external_clean vs internal_T", "n": len(y_ext), "T": t_int,
         "ece": ece(y_ext, int_on_ext), "brier": brier(y_ext, int_on_ext)},
        {"setting": "local_test vs internal_T", "n": len(y_te), "T": t_int,
         "ece": ece(y_te, sigmoid(logit(p_te) / t_int)),
         "brier": brier(y_te, sigmoid(logit(p_te) / t_int))},
        {"setting": "local_test vs external_fit", "n": len(y_te), "T": t_ext,
         "ece": ece(y_te, ext_on_test), "brier": brier(y_te, ext_on_test)},
    ]
    df = pd.DataFrame(rows)
    df.to_csv(REPORTS / "external_refit_calibration.csv", index=False)

    payload = {
        "endpoint": "herg",
        "source": "Karim hERG, compounds and Murcko scaffolds overlapping local data removed",
        "n": int(len(y_ext)),
        "positives": int(y_ext.sum()),
        "external_T": round(t_ext, 6),
        "external_T_at_bound": bool(t_ext > 19.99),
        "internal_T": round(t_int, 6),
        "external": {
            "auc": round(float(roc_auc_score(y_ext, p_ext)), 6),
            "ece_raw": round(ece(y_ext, p_ext), 6),
            "ece_with_external_T": round(ece(y_ext, ext_fit), 6),
            "ece_with_internal_T": round(ece(y_ext, int_on_ext), 6),
            "brier_raw": round(brier(y_ext, p_ext), 6),
            "brier_external_T": round(brier(y_ext, ext_fit), 6),
        },
        "local_test": {
            "n": int(len(y_te)),
            "ece_internal_T": round(ece(y_te, sigmoid(logit(p_te) / t_int)), 6),
            "ece_external_T": round(ece(y_te, ext_on_test), 6),
            "brier_internal_T": round(brier(y_te, sigmoid(logit(p_te) / t_int)), 6),
            "brier_external_T": round(brier(y_te, ext_on_test), 6),
        },
        "decision": "external refit kept as a sensitivity artifact; shipped calibrator stays on the internal clean split",
        "caveats": [
            "Karim labels hERG blockade at 10 uM; local training labels use a ~40 uM boundary",
            "external_clean is scaffold-disjoint and therefore out-of-domain (AUC 0.60-0.65 in the paper)",
            "no independent labelled external set exists for DILI or Ames in this project",
        ],
        "created": str(date.today()),
    }
    SENS.mkdir(parents=True, exist_ok=True)
    (SENS / "herg_external_refit.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(df.to_string(index=False))
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
