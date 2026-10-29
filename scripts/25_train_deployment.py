"""Train deployment models with a clean internal early-stopping split.

The benchmark models used the global validation split for early stopping and
then reused the same split for calibration.  Deployment models instead carve a
scaffold-disjoint early-stopping split out of the training portion, keep the
global validation split untouched for calibration, and never see test labels.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PY = Path(sys.executable)
CHEMPROP = PY.parent / "chemprop.exe"
sys.path.insert(0, str(ROOT / "scripts"))
from metrics import metrics  # noqa: E402

DATA = ROOT / "data" / "processed" / "global_split.csv"
CP_DATA = ROOT / "data" / "chemprop_deploy"
RUNS = ROOT / "runs" / "deploy"
REPORTS = ROOT / "reports"


def run(cmd: list[str], log: Path) -> None:
    print("+", " ".join(str(c) for c in cmd), flush=True)
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    with log.open("a", encoding="utf-8") as fh:
        fh.write("+ " + " ".join(str(c) for c in cmd) + "\n")
        fh.flush()
        proc = subprocess.run(
            [str(c) for c in cmd],
            stdout=fh,
            stderr=subprocess.STDOUT,
            cwd=ROOT,
            env=env,
        )
    if proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}), see {log}")


def carve_es(train: pd.DataFrame, frac: float, min_n: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Greedy scaffold-level assignment balancing size and positive count."""
    groups = [(str(k), g) for k, g in train.groupby("scaffold_key", sort=False)]
    target_n = max(min_n, int(round(frac * len(train))))
    target_pos = max(1, int(round(frac * float(train["y"].sum()))))
    remaining = groups[:]
    chosen: list[tuple[str, pd.DataFrame]] = []
    es_n = es_pos = 0
    # Keep the early-stopping set diverse: prefer many small scaffolds instead
    # of a few large clusters that would make model selection noisy.
    max_group = max(3, int(round(target_n * 0.05)))
    while remaining and es_n < target_n:
        best = None
        for limit in (max_group, target_n):
            for i, (key, g) in enumerate(remaining):
                n = len(g)
                pos = int(g["y"].sum())
                if n > limit or es_n + n > target_n * 1.30:
                    continue
                cost = abs((es_n + n) / target_n - 1.0) + abs((es_pos + pos) / target_pos - 1.0)
                if best is None or cost < best[0]:
                    best = (cost, i)
            if best is not None:
                break
        if best is None:
            break
        _, idx = best
        key, g = remaining.pop(idx)
        chosen.append((key, g))
        es_n += len(g)
        es_pos += int(g["y"].sum())

    es_idx = pd.Index([])
    for _, g in chosen:
        es_idx = es_idx.append(g.index)
    es = train.loc[es_idx].copy()
    fit = train.drop(index=es_idx).copy()
    return fit, es


def prepare(endpoint: str, frac: float, min_n: int) -> dict[str, Path]:
    df = pd.read_csv(DATA, encoding="utf-8-sig")
    sub = df[df["endpoint"] == endpoint].copy()
    train = sub[sub["split"] == "train"].copy()
    fit, es = carve_es(train, frac, min_n)
    parts = {
        "fit": fit,
        "es": es,
        "calib": sub[sub["split"] == "valid"].copy(),
        "test": sub[sub["split"] == "test"].copy(),
    }
    out = CP_DATA / endpoint
    out.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, part in parts.items():
        part = part[["smiles_std", "y", "inchikey"]].rename(columns={"smiles_std": "smiles"})
        path = out / f"{name}.csv"
        part.to_csv(path, index=False)
        paths[name] = path

    manifest_path = REPORTS / "deploy_split_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    manifest[endpoint] = {
        "n": {name: int(len(part)) for name, part in parts.items()},
        "pos": {name: int(part["y"].sum()) for name, part in parts.items()},
        "n_scaffolds": {name: int(part["scaffold_key"].nunique()) for name, part in parts.items()},
        "scaffold_overlap_fit_es": int(len(set(fit["scaffold_key"]) & set(es["scaffold_key"]))),
        "scaffold_overlap_train_calib": int(
            len((set(fit["scaffold_key"]) | set(es["scaffold_key"])) & set(parts["calib"]["scaffold_key"]))
        ),
        "scaffold_overlap_train_test": int(
            len((set(fit["scaffold_key"]) | set(es["scaffold_key"])) & set(parts["test"]["scaffold_key"]))
        ),
        "es_fraction": round(len(es) / len(train), 4),
        "rule": "scaffold-level greedy targeting 12% of compounds and positives; global valid kept for calibration",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return paths


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", required=True, choices=["herg", "dili", "ames"])
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--es-fraction", type=float, default=0.12)
    ap.add_argument("--min-es", type=int, default=40)
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--patience", type=int, default=20)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--max-lr", type=float, default=1e-4)
    args = ap.parse_args()

    paths = prepare(args.endpoint, args.es_fraction, args.min_es)
    tag = f"{args.endpoint}_s{args.seed}"
    save_dir = RUNS / tag
    save_dir.mkdir(parents=True, exist_ok=True)
    log = save_dir / "train.log"
    best = save_dir / "model_0" / "best.pt"
    done = save_dir / "preds.json"

    if not best.exists():
        run(
            [
                CHEMPROP, "train",
                "-i", paths["fit"], paths["es"], paths["test"],
                "-o", save_dir,
                "--task-type", "classification",
                "--target-columns", "y",
                "--metrics", "roc", "prc", "accuracy", "binary-mcc",
                "--tracking-metric", "roc",
                "--epochs", str(args.epochs),
                "--patience", str(args.patience),
                "--batch-size", str(args.batch_size),
                "--max-lr", str(args.max_lr),
                "--ensemble-size", "1",
                "--accelerator", "gpu",
                "--devices", "1",
                "--num-workers", "0",
                "--data-seed", str(args.seed),
                "--pytorch-seed", str(args.seed),
                "--remove-checkpoints",
                "--from-foundation", "CHEMELEON",
            ],
            log,
        )

    detail = {}
    if done.exists():
        detail = json.loads(done.read_text(encoding="utf-8"))
    rows = []
    for split in ["calib", "test"]:
        pred_path = save_dir / f"pred_{split}.csv"
        if not pred_path.exists():
            run(
                [
                    CHEMPROP, "predict",
                    "-i", paths[split],
                    "--model-paths", best,
                    "-o", pred_path,
                    "--accelerator", "gpu",
                    "--devices", "1",
                    "--num-workers", "0",
                ],
                log,
            )
        pred = pd.read_csv(pred_path)
        labels = pd.read_csv(paths[split])[["inchikey", "y"]]
        pred = pred.rename(columns={"y": "p"}).merge(labels, on="inchikey", how="left")
        p = pred["p"].to_numpy(dtype=float)
        y = pred["y"].to_numpy(dtype=int)
        detail[split] = {"y": y.tolist(), "p": p.tolist(), "inchikey": pred["inchikey"].tolist()}
        m = metrics(y, p)
        m.update({"endpoint": args.endpoint, "seed": args.seed, "split": split})
        rows.append(m)

    done.write_text(json.dumps(detail), encoding="utf-8")
    out_csv = REPORTS / "deploy_runs.csv"
    df = pd.DataFrame(rows)
    if out_csv.exists():
        old = pd.read_csv(out_csv)
        key = ["endpoint", "seed", "split"]
        old = old[~old.set_index(key).index.isin(df.set_index(key).index)]
        df = pd.concat([old, df], ignore_index=True)
    df.to_csv(out_csv, index=False)
    print(df.to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
