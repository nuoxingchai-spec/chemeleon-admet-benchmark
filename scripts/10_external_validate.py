"""External hERG validation on the Karim set.

Two local training-label regimes:
  aligned   local positives pIC50>=5, negatives pIC50<=4.4 (matches Karim's 10 uM cutoff)
  original  local 40 uM labels (sensitivity analysis; threshold mismatch expected)
Two external sets:
  external_all    Karim minus exact local compounds
  external_clean  also minus compounds sharing a Murcko scaffold with local data
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem import rdFingerprintGenerator
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[1]
PY = Path(sys.executable)
CHEMPROP = PY.parent / "chemprop.exe"
sys.path.insert(0, str(ROOT / "scripts"))
from metrics import metrics  # noqa: E402

RDLogger.DisableLog("rdApp.*")
CP = ROOT / "data" / "chemprop" / "herg_aligned"
RUNS = ROOT / "runs" / "chemprop"
REPORTS = ROOT / "reports"
GEN = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
EXTERNAL = {"external_all": CP / "external_all.csv", "external_clean": CP / "external_clean.csv"}


def run(cmd, log):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    with log.open("a", encoding="utf-8") as fh:
        fh.write("+ " + " ".join(str(c) for c in cmd) + "\n")
        fh.flush()
        proc = subprocess.run([str(c) for c in cmd], stdout=fh, stderr=subprocess.STDOUT,
                              cwd=ROOT, env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}), see {log}")


def predict_external(model_path: Path, tag: str, log: Path) -> dict:
    out = {}
    for name, path in EXTERNAL.items():
        pred_path = RUNS / tag / f"pred_{name}.csv"
        run([CHEMPROP, "predict", "-i", path, "--model-paths", model_path, "-o", pred_path,
             "--accelerator", "gpu", "--devices", "1", "--num-workers", "0"], log)
        pred = pd.read_csv(pred_path).rename(columns={"y": "p"})
        labels = pd.read_csv(path)[["inchikey", "y"]]
        pred = pred.merge(labels, on="inchikey", how="left")
        out[name] = (pred["y"].to_numpy(dtype=int), pred["p"].to_numpy(dtype=float))
    return out


def record(results: dict, model: str, source: str, seed, extra: dict, out_csv: Path):
    rows = []
    for name, (y, p) in results.items():
        m = metrics(y, p)
        m.update({"endpoint": "herg", "eval_set": name, "model": model, "source": source,
                  "seed": seed, **extra})
        rows.append(m)
    df = pd.DataFrame(rows)
    if out_csv.exists():
        old = pd.read_csv(out_csv)
        key = ["model", "source", "seed", "eval_set"]
        for k in key:
            old[k] = old[k].astype(str)
            df[k] = df[k].astype(str)
        old = old[~old.set_index(key).index.isin(df.set_index(key).index)]
        df = pd.concat([old, df], ignore_index=True)
    df.to_csv(out_csv, index=False)
    return rows


def fp(smiles):
    mol = Chem.MolFromSmiles(smiles)
    arr = np.zeros((2048,), dtype=np.float32)
    if mol is not None:
        arr[:] = np.asarray(GEN.GetFingerprint(mol), dtype=np.float32)
    return arr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["train", "predict", "classical"])
    ap.add_argument("--model", default="chemeleon", choices=["chemeleon", "scratch"])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--run-dir", default=None)
    ap.add_argument("--source", default=None, choices=["aligned", "original"])
    ap.add_argument("--epochs", type=int, default=80)
    ap.add_argument("--patience", type=int, default=20)
    ap.add_argument("--out", default="reports/external_runs.csv")
    args = ap.parse_args()
    out_csv = ROOT / args.out

    if args.mode == "train":
        tag = f"herg_aligned_{args.model}_s{args.seed}"
        save_dir = RUNS / tag
        save_dir.mkdir(parents=True, exist_ok=True)
        log = save_dir / "train.log"
        cmd = [
            CHEMPROP, "train", "-i", CP / "train.csv", CP / "valid.csv", CP / "test.csv",
            "-o", save_dir, "--task-type", "classification", "--target-columns", "y",
            "--metrics", "roc", "prc", "accuracy", "binary-mcc", "--tracking-metric", "roc",
            "--epochs", str(args.epochs), "--patience", str(args.patience),
            "--batch-size", "32", "--max-lr", "1e-4", "--ensemble-size", "1",
            "--accelerator", "gpu", "--devices", "1", "--num-workers", "0",
            "--data-seed", str(args.seed), "--pytorch-seed", str(args.seed), "--remove-checkpoints",
        ]
        if args.model == "chemeleon":
            cmd += ["--from-foundation", "CHEMELEON"]
        run(cmd, log)
        results = predict_external(save_dir / "model_0" / "best.pt", tag, log)
        rows = record(results, args.model, "aligned", args.seed, {"run": tag}, out_csv)
        print(pd.DataFrame(rows).to_string(index=False))

    elif args.mode == "predict":
        tag = args.run_dir
        save_dir = RUNS / tag
        log = save_dir / "train.log"
        model_name = "chemeleon" if "chemeleon" in tag else ("matched" if "matched" in tag else "scratch")
        results = predict_external(save_dir / "model_0" / "best.pt", tag, log)
        rows = record(results, model_name, args.source or "original", args.seed,
                      {"run": tag}, out_csv)
        print(pd.DataFrame(rows).to_string(index=False))

    else:
        src = args.source or "aligned"
        train_dir = CP if src == "aligned" else ROOT / "data" / "chemprop" / "herg"
        tr = pd.read_csv(train_dir / "train.csv")
        x_tr = np.vstack([fp(s) for s in tr["smiles"]])
        y_tr = tr["y"].to_numpy()
        models = {
            "rf": RandomForestClassifier(n_estimators=500, n_jobs=-1, random_state=42,
                                         class_weight="balanced"),
            "histgb": HistGradientBoostingClassifier(max_iter=400, learning_rate=0.06,
                                                     max_leaf_nodes=31, l2_regularization=1.0,
                                                     random_state=42, class_weight="balanced"),
            "logreg": LogisticRegression(max_iter=3000, C=1.0, class_weight="balanced"),
        }
        for name, model in models.items():
            model.fit(x_tr, y_tr)
            results = {}
            for ename, path in EXTERNAL.items():
                ext = pd.read_csv(path)
                p = model.predict_proba(np.vstack([fp(s) for s in ext["smiles"]]))[:, 1]
                results[ename] = (ext["y"].to_numpy(dtype=int), p)
            rows = record(results, name, src, "na", {"run": ""}, out_csv)
            print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
