"""Post-hoc calibration and selective prediction on saved valid/test predictions."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from metrics import ece  # noqa: E402


def logit(p: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    p = np.clip(p, eps, 1 - eps)
    return np.log(p / (1 - p))


def temperature_fit(p: np.ndarray, y: np.ndarray) -> float:
    z = logit(p)
    best_t, best_nll = 1.0, np.inf
    for t in np.geomspace(0.05, 20.0, 400):
        q = 1.0 / (1.0 + np.exp(-z / t))
        nll = log_loss(y, np.clip(q, 1e-6, 1 - 1e-6), labels=[0, 1])
        if nll < best_nll:
            best_t, best_nll = float(t), nll
    return best_t


def apply_temperature(p: np.ndarray, t: float) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-logit(p) / t))


def fit_calibrators(p_val: np.ndarray, y_val: np.ndarray) -> dict:
    return {
        "temperature": temperature_fit(p_val, y_val),
        "platt": LogisticRegression(C=1e6, solver="lbfgs").fit(
            logit(p_val).reshape(-1, 1), y_val
        ),
        "isotonic": IsotonicRegression(out_of_bounds="clip").fit(p_val, y_val),
    }


def apply_calibrators(p: np.ndarray, cal: dict) -> dict[str, np.ndarray]:
    return {
        "raw": p,
        "temperature": apply_temperature(p, cal["temperature"]),
        "platt": cal["platt"].predict_proba(logit(p).reshape(-1, 1))[:, 1],
        "isotonic": cal["isotonic"].predict(p),
    }


def conformal_q(p_cal: np.ndarray, y_cal: np.ndarray, alpha: float = 0.1) -> float:
    scores = 1.0 - np.where(y_cal == 1, p_cal, 1.0 - p_cal)
    n = len(scores)
    return float(np.quantile(scores, min(np.ceil((n + 1) * (1 - alpha)) / n, 1.0), method="higher"))


def conformal_eval(p_test: np.ndarray, y_test: np.ndarray, q: float) -> tuple[float, float]:
    p_grid = np.stack([1 - p_test, p_test], axis=1)
    in_set = (1.0 - p_grid) <= q + 1e-12
    coverage = float(in_set[np.arange(len(y_test)), y_test].mean())
    return coverage, float(in_set.sum(axis=1).mean())


def selective_risk(y: np.ndarray, p: np.ndarray) -> dict:
    conf = np.maximum(p, 1 - p)
    order = np.argsort(-conf, kind="stable")
    err = ((p >= 0.5).astype(int) != y)[order]
    n = len(y)
    ks = np.arange(20, n + 1)
    risks = np.array([err[:k].mean() for k in ks])
    cov = ks / n
    ok = np.where(risks <= 0.05)[0]
    return {
        "aurc": float(risks.mean()),
        "risk_at_80": float(risks[np.argmin(np.abs(cov - 0.8))]),
        "risk_at_90": float(risks[np.argmin(np.abs(cov - 0.9))]),
        "coverage_at_risk5": float(cov[ok.max()]) if len(ok) else 0.0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("preds", nargs="+")
    ap.add_argument("--out", default="reports/calibration.csv")
    args = ap.parse_args()

    rows = []
    for path in args.preds:
        d = json.loads(Path(path).read_text())
        p_val = np.array(d["splits"]["valid"]["p"])
        y_val = np.array(d["splits"]["valid"]["y"])
        p_te = np.array(d["splits"]["test"]["p"])
        y_te = np.array(d["splits"]["test"]["y"])
        cal = fit_calibrators(p_val, y_val)
        variants = apply_calibrators(p_te, cal)

        q = conformal_q(apply_temperature(p_val, cal["temperature"]), y_val)
        coverage, set_size = conformal_eval(
            apply_temperature(p_te, cal["temperature"]), y_te, q
        )

        for name, p in variants.items():
            rows.append({
                "run": f"{d['endpoint']}:{d['model']}:s{d['seed']}",
                "endpoint": d["endpoint"],
                "model": d["model"],
                "seed": d["seed"],
                "calibration": name,
                "n_test": len(y_te),
                "auc": float(roc_auc_score(y_te, p)),
                "brier": float(brier_score_loss(y_te, p)),
                "nll": float(log_loss(y_te, np.clip(p, 1e-6, 1 - 1e-6), labels=[0, 1])),
                "ece": ece(y_te, p),
                **selective_risk(y_te, p),
                "conformal_coverage": coverage,
                "conformal_set_size": set_size,
                "temperature": cal["temperature"] if name == "temperature" else np.nan,
            })

    out = pd.DataFrame(rows)
    out_path = ROOT / args.out
    if out_path.exists():
        old = pd.read_csv(out_path)
        keys = ["run", "calibration"]
        old = old[~old.set_index(keys).index.isin(out.set_index(keys).index)]
        out = pd.concat([old, out], ignore_index=True)
    out.to_csv(out_path, index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
