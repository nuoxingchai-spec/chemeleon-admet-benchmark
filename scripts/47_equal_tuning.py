"""Equal-tuning sensitivity for the hERG CheMeleon/matched capacity control."""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
SPLIT = ROOT / "data" / "processed" / "global_split.csv"
DATA = ROOT / "data" / "chemprop" / "herg"
PRIMARY = ROOT / "runs" / "chemprop"
SWEEP = ROOT / "runs" / "chemprop_lr"
REPORTS = ROOT / "reports"
SEEDS = (42, 1, 2)
ARMS = ("chemeleon", "matched")
N_BOOT = 5000
BOOT_SEED = 20261101


def contrast(y, p_a, p_b, groups=None, n_boot=N_BOOT, seed=BOOT_SEED):
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(n_boot):
        if groups is None:
            idx = rng.integers(0, len(y), len(y))
        else:
            uniq = np.unique(groups)
            picked = rng.choice(uniq, len(uniq), replace=True)
            idx = np.concatenate([np.where(groups == x)[0] for x in picked])
        if len(np.unique(y[idx])) < 2:
            continue
        diffs.append(roc_auc_score(y[idx], p_a[idx]) - roc_auc_score(y[idx], p_b[idx]))
    d = np.asarray(diffs)
    lo, hi = np.percentile(d, [2.5, 97.5])
    p = 2.0 * min(float((d <= 0).mean()), float((d >= 0).mean()))
    return {"delta": float(roc_auc_score(y, p_a) - roc_auc_score(y, p_b)),
            "ci_low": float(lo), "ci_high": float(hi), "p": float(min(1.0, p))}


def best_epoch(log: Path) -> int:
    matches = re.findall(r"best-epoch=(\d+)-val_roc", log.read_text(encoding="utf-8", errors="ignore"))
    return int(matches[-1]) if matches else -1


def load_run(run_dir: Path, truth: pd.DataFrame, valid_labels: pd.DataFrame):
    p_test = pd.read_csv(run_dir / "pred_test.csv").set_index("inchikey")["y"]
    p_valid = pd.read_csv(run_dir / "pred_valid.csv").set_index("inchikey")["y"]
    test = truth[["inchikey"]].merge(p_test.rename("p").reset_index(), on="inchikey", how="left")
    valid = valid_labels[["inchikey"]].merge(p_valid.rename("p").reset_index(), on="inchikey", how="left")
    if test["p"].isna().any() or valid["p"].isna().any():
        raise ValueError(f"missing predictions in {run_dir}")
    return test["p"].to_numpy(float), valid["p"].to_numpy(float)


def main() -> None:
    split = pd.read_csv(SPLIT, encoding="utf-8-sig")
    truth = split[(split["endpoint"] == "herg") & (split["split"] == "test")][
        ["inchikey", "y", "scaffold_key"]
    ].reset_index(drop=True)
    y = truth["y"].to_numpy(int)
    groups = truth["scaffold_key"].to_numpy()
    valid_labels = pd.read_csv(DATA / "valid.csv")[["inchikey", "y"]]

    runs: dict[tuple[str, float], dict] = {}
    for arm in ARMS:
        for seed in SEEDS:
            runs[(arm, 1e-4, seed)] = PRIMARY / f"herg_{arm}_s{seed}"
        for d in sorted(SWEEP.glob(f"herg_{arm}_lr*_s*")):
            meta = json.loads((d / "preds.json").read_text(encoding="utf-8"))
            lr = float(meta["args"]["max_lr"])
            seed = int(meta["args"]["seed"])
            runs[(arm, lr, seed)] = d

    lrs = sorted({lr for (_, lr, _) in runs})
    report: dict = {"learning_rates": lrs, "arms": {}, "contrasts": {}, "tuned": {}}
    seed_probs: dict[tuple[str, float], dict[int, np.ndarray]] = {}
    for arm in ARMS:
        report["arms"][arm] = {}
        for lr in lrs:
            test_aucs, valid_aucs, epochs, test_probs, valid_probs = [], [], [], [], []
            for seed in SEEDS:
                d = runs[(arm, lr, seed)]
                p_test, p_valid = load_run(d, truth, valid_labels)
                test_aucs.append(float(roc_auc_score(y, p_test)))
                valid_aucs.append(float(roc_auc_score(valid_labels["y"], p_valid)))
                epochs.append(best_epoch(d / "train.log"))
                test_probs.append(p_test)
                valid_probs.append(p_valid)
            seed_probs[(arm, lr)] = dict(zip(SEEDS, test_probs))
            report["arms"][arm][str(lr)] = {
                "test_auc_seed_mean": float(np.mean(test_aucs)),
                "test_auc_seed_sd": float(np.std(test_aucs, ddof=1)),
                "test_auc_seed_values": test_aucs,
                "valid_auc_seed_mean": float(np.mean(valid_aucs)),
                "valid_auc_seed_values": valid_aucs,
                "best_epochs": epochs,
                "test_auc_ensemble": float(roc_auc_score(y, np.mean(test_probs, axis=0))),
            }

    for lr in lrs:
        p_a = np.mean([seed_probs[("chemeleon", lr)][s] for s in SEEDS], axis=0)
        p_b = np.mean([seed_probs[("matched", lr)][s] for s in SEEDS], axis=0)
        per_seed = [
            float(roc_auc_score(y, seed_probs[("chemeleon", lr)][s])
                  - roc_auc_score(y, seed_probs[("matched", lr)][s]))
            for s in SEEDS
        ]
        report["contrasts"][str(lr)] = {
            "per_seed": per_seed,
            "compound": contrast(y, p_a, p_b, None),
            "scaffold": contrast(y, p_a, p_b, groups),
        }

    best = {
        arm: max(lrs, key=lambda lr: report["arms"][arm][str(lr)]["valid_auc_seed_mean"])
        for arm in ARMS
    }
    lr_a, lr_b = best["chemeleon"], best["matched"]
    p_a = np.mean([seed_probs[("chemeleon", lr_a)][s] for s in SEEDS], axis=0)
    p_b = np.mean([seed_probs[("matched", lr_b)][s] for s in SEEDS], axis=0)
    report["tuned"] = {
        "selected_lr": {arm: best[arm] for arm in ARMS},
        "chemeleon_auc": float(roc_auc_score(y, p_a)),
        "matched_auc": float(roc_auc_score(y, p_b)),
        "compound": contrast(y, p_a, p_b, None),
        "scaffold": contrast(y, p_a, p_b, groups),
    }

    p_a_same = np.mean([seed_probs[("chemeleon", lr_b)][s] for s in SEEDS], axis=0)
    report["matched_best_same_lr"] = {
        "selected_lr": lr_b,
        "chemeleon_auc": float(roc_auc_score(y, p_a_same)),
        "matched_auc": float(roc_auc_score(y, p_b)),
        "compound": contrast(y, p_a_same, p_b, None),
        "scaffold": contrast(y, p_a_same, p_b, groups),
    }

    rows = []
    for arm in ARMS:
        for lr in lrs:
            for seed in SEEDS:
                row = {"arm": arm, "max_lr": lr, "seed": seed}
                row.update({k: v for k, v in report["arms"][arm][str(lr)].items()
                            if k not in ("test_auc_seed_values", "valid_auc_seed_values", "best_epochs")})
                idx = SEEDS.index(seed)
                row["test_auc"] = report["arms"][arm][str(lr)]["test_auc_seed_values"][idx]
                row["valid_auc"] = report["arms"][arm][str(lr)]["valid_auc_seed_values"][idx]
                row["best_epoch"] = report["arms"][arm][str(lr)]["best_epochs"][idx]
                rows.append(row)
    pd.DataFrame(rows).to_csv(REPORTS / "chemprop_runs_lr_tidy.csv", index=False)

    (REPORTS / "equal_tuning.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
