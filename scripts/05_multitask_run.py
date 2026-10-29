"""Multi-endpoint partial-label Chemprop training on the global scaffold split."""
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

CP_DATA = ROOT / "data" / "chemprop" / "multitask"
RUNS = ROOT / "runs" / "chemprop"
REPORTS = ROOT / "reports"
ENDPOINTS = ["herg", "dili", "ames"]


def prepare(include_potency: bool) -> dict[str, Path]:
    df = pd.read_csv(ROOT / "data" / "processed" / "global_split.csv", encoding="utf-8-sig")
    base = (
        df.sort_values(["inchikey", "endpoint"])
        .groupby("inchikey")
        .agg(smiles=("smiles_std", "first"), split=("split", "first"))
        .reset_index()
    )
    for ep in ENDPOINTS:
        sub = df[df["endpoint"] == ep].set_index("inchikey")["y"]
        base[ep] = base["inchikey"].map(sub)
    herg = df[df["endpoint"] == "herg"].set_index("inchikey")
    base["herg_potent"] = base["inchikey"].map((herg["pIC50"] >= 7).astype(float).where(herg["pIC50"].notna()))

    targets = ENDPOINTS + (["herg_potent"] if include_potency else [])
    out = {}
    CP_DATA.mkdir(parents=True, exist_ok=True)
    for split in ["train", "valid", "test"]:
        part = base[base["split"] == split][["smiles", "inchikey"] + targets].copy()
        path = CP_DATA / f"{split}.csv"
        part.to_csv(path, index=False)
        out[split] = path
    return out


def run(cmd: list[str], log: Path) -> None:
    print("+", " ".join(str(c) for c in cmd), flush=True)
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    with log.open("a", encoding="utf-8") as fh:
        fh.write("+ " + " ".join(str(c) for c in cmd) + "\n")
        fh.flush()
        proc = subprocess.run([str(c) for c in cmd], stdout=fh, stderr=subprocess.STDOUT, cwd=ROOT, env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}), see {log}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--foundation", default="CHEMELEON", choices=["CHEMELEON", "none"])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--epochs", type=int, default=80)
    ap.add_argument("--patience", type=int, default=20)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--max-lr", type=float, default=1e-4)
    ap.add_argument("--include-potency", action="store_true")
    ap.add_argument("--task-weights", nargs="+", type=float, default=None)
    ap.add_argument("--tag", default=None)
    args = ap.parse_args()

    paths = prepare(args.include_potency)
    targets = ENDPOINTS + (["herg_potent"] if args.include_potency else [])
    tag = args.tag or f"multi_{args.foundation.lower()}_s{args.seed}"
    save_dir = RUNS / tag
    save_dir.mkdir(parents=True, exist_ok=True)
    log = save_dir / "train.log"

    cmd = [
        CHEMPROP, "train",
        "-i", paths["train"], paths["valid"], paths["test"],
        "-o", save_dir,
        "--task-type", "classification",
        "--target-columns", *targets,
        "--metrics", "roc", "prc", "accuracy", "binary-mcc",
        "--tracking-metric", "roc",
        "--epochs", str(args.epochs),
        "--patience", str(args.patience),
        "--batch-size", str(args.batch_size),
        "--max-lr", str(args.max_lr),
        "--accelerator", "gpu",
        "--devices", "1",
        "--num-workers", "0",
        "--data-seed", str(args.seed),
        "--pytorch-seed", str(args.seed),
        "--remove-checkpoints",
    ]
    if args.task_weights:
        cmd += ["--task-weights", *[str(w) for w in args.task_weights]]
    if args.foundation != "none":
        cmd += ["--from-foundation", args.foundation]
    run(cmd, log)

    rows = []
    preds = {}
    labels_all = pd.read_csv(paths["test"])
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
        labels = pd.read_csv(paths[split])[["inchikey"] + ENDPOINTS]
        pred = pred[["inchikey"] + ENDPOINTS].merge(labels, on="inchikey", suffixes=("_p", ""))
        for ep in ENDPOINTS:
            mask = pred[ep].notna().to_numpy()
            y = pred.loc[mask, ep].to_numpy(dtype=int)
            p = pred.loc[mask, f"{ep}_p"].to_numpy(dtype=float)
            preds.setdefault(split, {})[ep] = {"y": y.tolist(), "p": p.tolist()}
            m = metrics(y, p)
            m.update({"endpoint": ep, "model": f"multitask_{args.foundation.lower()}",
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
        "endpoint": "multitask",
        "model": f"multitask_{args.foundation.lower()}",
        "seed": args.seed,
        "args": vars(args),
        "splits": preds,
    }
    with (save_dir / "preds.json").open("w", encoding="utf-8") as fh:
        json.dump(detail, fh)
    print(df.to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
