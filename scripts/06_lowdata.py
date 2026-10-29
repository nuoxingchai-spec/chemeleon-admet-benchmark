"""Low-data scaling curves: scratch vs CheMeleon at fixed hERG/DILI train sizes."""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PY = Path(sys.executable)
CHEMPROP = PY.parent / "chemprop.exe"
sys.path.insert(0, str(ROOT / "scripts"))
from metrics import metrics  # noqa: E402

CP_DATA = ROOT / "data" / "chemprop" / "lowdata"
RUNS = ROOT / "runs" / "chemprop" / "lowdata"
REPORTS = ROOT / "reports"


def subsample(train: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    if n >= len(train):
        return train.copy()
    frac = n / len(train)
    parts = [
        g.sample(n=max(1, int(round(len(g) * frac))), random_state=seed)
        for _, g in train.groupby("y")
    ]
    out = pd.concat(parts)
    if len(out) > n:
        out = out.sample(n=n, random_state=seed)
    elif len(out) < n:
        pool = train.drop(out.index)
        out = pd.concat([out, pool.sample(n=n - len(out), random_state=seed)])
    return out.sort_index()


def run(cmd: list[str], log: Path) -> None:
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    with log.open("a", encoding="utf-8") as fh:
        fh.write("+ " + " ".join(str(c) for c in cmd) + "\n")
        fh.flush()
        proc = subprocess.run([str(c) for c in cmd], stdout=fh, stderr=subprocess.STDOUT, cwd=ROOT, env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}), see {log}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="herg", choices=["herg", "dili"])
    ap.add_argument("--n-values", nargs="+", type=int, default=[50, 100, 200, 400])
    ap.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    ap.add_argument("--models", nargs="+", default=["none", "CHEMELEON"])
    ap.add_argument("--epochs", type=int, default=80)
    ap.add_argument("--patience", type=int, default=20)
    args = ap.parse_args()

    df = pd.read_csv(ROOT / "data" / "processed" / "global_split.csv", encoding="utf-8-sig")
    sub = df[df["endpoint"] == args.endpoint]
    train = sub[sub["split"] == "train"][["smiles_std", "y", "inchikey"]].rename(columns={"smiles_std": "smiles"})
    valid_path = ROOT / "data" / "chemprop" / args.endpoint / "valid.csv"
    test_path = ROOT / "data" / "chemprop" / args.endpoint / "test.csv"
    labels_te = pd.read_csv(test_path)

    CP_DATA.mkdir(parents=True, exist_ok=True)
    RUNS.mkdir(parents=True, exist_ok=True)
    rows = []
    for n in args.n_values:
        if n >= len(train):
            continue
        for seed in args.seeds:
            part = subsample(train, n, seed)
            train_path = CP_DATA / f"{args.endpoint}_n{n}_s{seed}.csv"
            part.to_csv(train_path, index=False)
            for model in args.models:
                name = {"CHEMELEON": "chemeleon", "none": "scratch", "matched": "matched",
                        "matched_dropout": "matched_dropout"}[model]
                tag = f"{args.endpoint}_{name}_n{n}_s{seed}"
                save_dir = RUNS / tag
                if (save_dir / "preds.json").exists():
                    rows.append(json.loads((save_dir / "preds.json").read_text())["row"])
                    continue
                save_dir.mkdir(parents=True, exist_ok=True)
                log = save_dir / "train.log"
                cmd = [
                    CHEMPROP, "train",
                    "-i", train_path, valid_path, test_path,
                    "-o", save_dir,
                    "--task-type", "classification",
                    "--target-columns", "y",
                    "--metrics", "roc", "prc", "accuracy", "binary-mcc",
                    "--tracking-metric", "roc",
                    "--epochs", str(args.epochs),
                    "--patience", str(args.patience),
                    "--batch-size", "64",
                    "--max-lr", "1e-4",
                    "--accelerator", "gpu",
                    "--devices", "1",
                    "--num-workers", "0",
                    "--data-seed", str(seed),
                    "--pytorch-seed", str(seed),
                    "--remove-checkpoints",
                ]
                if model == "CHEMELEON":
                    cmd += ["--from-foundation", model]
                elif model == "matched":
                    cmd += ["--message-hidden-dim", "2048", "--depth", "6"]
                elif model == "matched_dropout":
                    cmd += ["--message-hidden-dim", "2048", "--depth", "6", "--dropout", "0.1"]
                t0 = time.time()
                run(cmd, log)
                train_seconds = time.time() - t0

                pred_path = save_dir / "pred_test.csv"
                run(
                    [
                        CHEMPROP, "predict", "-i", test_path,
                        "--model-paths", save_dir / "model_0" / "best.pt",
                        "-o", pred_path,
                        "--accelerator", "gpu", "--devices", "1", "--num-workers", "0",
                    ],
                    log,
                )
                pred = pd.read_csv(pred_path).rename(columns={"y": "p"})
                pred = pred[["inchikey", "p"]].merge(labels_te[["inchikey", "y"]], on="inchikey")
                m = metrics(pred["y"].to_numpy(int), pred["p"].to_numpy(float))
                row = {
                    "endpoint": args.endpoint, "model": name, "train_n": n,
                    "seed": seed, "train_seconds": round(train_seconds, 1), **m,
                }
                rows.append(row)
                (save_dir / "preds.json").write_text(json.dumps({"row": row}), encoding="utf-8")
                print(json.dumps(row), flush=True)

    out_path = REPORTS / "lowdata.csv"
    out = pd.DataFrame(rows)
    if out_path.exists():
        old = pd.read_csv(out_path)
        keys = ["endpoint", "model", "train_n", "seed"]
        old = old[~old.set_index(keys).index.isin(out.set_index(keys).index)]
        out = pd.concat([old, out], ignore_index=True)
    out.to_csv(out_path, index=False)


if __name__ == "__main__":
    main()
