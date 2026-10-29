"""Train/evaluate a Chemprop model (optionally CheMeleon-initialized) per endpoint."""
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
CP_DATA = ROOT / "data" / "chemprop"
RUNS = ROOT / "runs" / "chemprop"
REPORTS = ROOT / "reports"


def prepare(endpoint: str) -> dict[str, Path]:
    df = pd.read_csv(DATA, encoding="utf-8-sig")
    sub = df[df["endpoint"] == endpoint].copy()
    out = CP_DATA / endpoint
    out.mkdir(parents=True, exist_ok=True)
    paths = {}
    for split in ["train", "valid", "test"]:
        part = sub[sub["split"] == split][["smiles_std", "y", "inchikey"]].copy()
        part = part.rename(columns={"smiles_std": "smiles"})
        path = out / f"{split}.csv"
        part.to_csv(path, index=False)
        paths[split] = path
    return paths


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", required=True, choices=["herg", "dili", "ames"])
    ap.add_argument("--foundation", default="CHEMELEON", choices=["CHEMELEON", "none"])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--patience", type=int, default=15)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--max-lr", type=float, default=1e-4)
    ap.add_argument("--ensemble-size", type=int, default=1)
    ap.add_argument("--matched", action="store_true", help="random-init 2048x6 control")
    ap.add_argument("--dropout", type=float, default=None)
    ap.add_argument("--tag", default=None)
    args = ap.parse_args()

    paths = prepare(args.endpoint)
    tag = args.tag or f"{args.endpoint}_{args.foundation.lower()}_s{args.seed}"
    if args.matched:
        model_label = "chemprop_matched" + ("_dropout" if args.dropout else "")
    else:
        model_label = f"chemprop_{args.foundation.lower()}"
    save_dir = RUNS / tag
    save_dir.mkdir(parents=True, exist_ok=True)
    log = save_dir / "train.log"

    train_cmd = [
        CHEMPROP, "train",
        "-i", paths["train"], paths["valid"], paths["test"],
        "-o", save_dir,
        "--task-type", "classification",
        "--target-columns", "y",
        "--metrics", "roc", "prc", "accuracy", "binary-mcc",
        "--tracking-metric", "roc",
        "--epochs", str(args.epochs),
        "--patience", str(args.patience),
        "--batch-size", str(args.batch_size),
        "--max-lr", str(args.max_lr),
        "--ensemble-size", str(args.ensemble_size),
        "--accelerator", "gpu",
        "--devices", "1",
        "--num-workers", "0",
        "--data-seed", str(args.seed),
        "--pytorch-seed", str(args.seed),
        "--remove-checkpoints",
    ]
    if args.foundation != "none":
        train_cmd += ["--from-foundation", args.foundation]
    if args.matched:
        train_cmd += ["--message-hidden-dim", "2048", "--depth", "6"]
    if args.dropout is not None:
        train_cmd += ["--dropout", str(args.dropout)]
    run(train_cmd, log)

    rows = []
    preds = {}
    for split in ["valid", "test"]:
        pred_path = save_dir / f"pred_{split}.csv"
        run(
            [
                CHEMPROP, "predict",
                "-i", paths[split],
                "--model-paths", save_dir / "model_0" / "best.pt",
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
        preds[split] = {"y": y, "p": p}
        m = metrics(y, p)
        m.update({"endpoint": args.endpoint, "model": model_label,
                  "seed": args.seed, "split": split})
        rows.append(m)

    out_csv = REPORTS / "chemprop_runs.csv"
    df = pd.DataFrame(rows)
    if out_csv.exists():
        old = pd.read_csv(out_csv)
        key = ["endpoint", "model", "seed", "split"]
        old = old[~old.set_index(key).index.isin(df.set_index(key).index)]
        df = pd.concat([old, df], ignore_index=True)
    df.to_csv(out_csv, index=False)

    detail = {
        "endpoint": args.endpoint,
        "model": model_label,
        "seed": args.seed,
        "args": vars(args),
        "splits": {k: {kk: vv.tolist() for kk, vv in v.items()} for k, v in preds.items()},
    }
    with (save_dir / "preds.json").open("w", encoding="utf-8") as fh:
        json.dump(detail, fh)
    print(df.to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
