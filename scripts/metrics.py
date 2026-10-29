"""Shared classification metrics for baseline and Chemprop evaluations."""
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    matthews_corrcoef,
    roc_auc_score,
)


def ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (p >= lo) & (p < hi if hi < 1 else p <= hi)
        if mask.sum() == 0:
            continue
        total += mask.mean() * abs(y[mask].mean() - p[mask].mean())
    return float(total)


def bootstrap_auc(y: np.ndarray, p: np.ndarray, n: int = 1000, seed: int = 42):
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n):
        idx = rng.integers(0, len(y), len(y))
        if len(np.unique(y[idx])) < 2:
            continue
        vals.append(roc_auc_score(y[idx], p[idx]))
    if not vals:
        return (float("nan"), float("nan"))
    return tuple(float(v) for v in np.percentile(vals, [2.5, 97.5]))


def metrics(y, p, threshold=0.5):
    pred = (p >= threshold).astype(int)
    lo, hi = bootstrap_auc(y, p)
    return {
        "n": int(len(y)),
        "pos": int(y.sum()),
        "auc": float(roc_auc_score(y, p)),
        "auc_ci_low": lo,
        "auc_ci_high": hi,
        "pr_auc": float(average_precision_score(y, p)),
        "acc": float(accuracy_score(y, pred)),
        "mcc": float(matthews_corrcoef(y, pred)),
        "brier": float(brier_score_loss(y, p)),
        "ece": ece(y, p),
    }
