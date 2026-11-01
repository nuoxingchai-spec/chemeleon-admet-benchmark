"""Train ChemBERTa-2 arms (pretrained / random-init matched / small scratch) on one endpoint."""
from __future__ import annotations

import argparse
import json
import math
import random
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    matthews_corrcoef,
    roc_auc_score,
)
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoConfig,
    AutoModelForSequenceClassification,
    AutoTokenizer,
    RobertaConfig,
    RobertaForSequenceClassification,
    get_linear_schedule_with_warmup,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "chemprop"
RUNS = ROOT / "runs" / "chemberta"
MODEL = "seyonec/ChemBERTa-zinc-base-v1"


class MolDataset(Dataset):
    def __init__(self, df: pd.DataFrame, tok, max_len: int):
        enc = tok(
            df["smiles"].tolist(),
            truncation=True,
            padding="max_length",
            max_length=max_len,
            return_tensors="pt",
        )
        self.input_ids = enc["input_ids"]
        self.attention_mask = enc["attention_mask"]
        self.y = torch.tensor(df["y"].to_numpy(), dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.y)

    def __getitem__(self, i: int):
        return {
            "input_ids": self.input_ids[i],
            "attention_mask": self.attention_mask[i],
            "y": self.y[i],
        }


def ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (p >= lo) & (p < hi if hi < 1 else p <= hi)
        if mask.sum() == 0:
            continue
        total += mask.mean() * abs(y[mask].mean() - p[mask].mean())
    return float(total)


def point_metrics(y: np.ndarray, p: np.ndarray) -> dict:
    pred = (p >= 0.5).astype(int)
    return {
        "n": int(len(y)),
        "pos": int(y.sum()),
        "auc": float(roc_auc_score(y, p)),
        "pr_auc": float(average_precision_score(y, p)),
        "acc": float((pred == y).mean()),
        "mcc": float(matthews_corrcoef(y, pred)),
        "brier": float(brier_score_loss(y, p)),
        "ece": ece(y, p),
    }


def load_split(endpoint: str, name: str) -> pd.DataFrame:
    path = DATA / endpoint / f"{name}.csv"
    return pd.read_csv(path, encoding="utf-8-sig")[["smiles", "y", "inchikey"]]


def build_model(arm: str, tok):
    if arm == "pretrained":
        model = AutoModelForSequenceClassification.from_pretrained(MODEL, num_labels=1)
    elif arm == "matched":
        cfg = AutoConfig.from_pretrained(MODEL)
        cfg.num_labels = 1
        cfg.pad_token_id = tok.pad_token_id
        model = AutoModelForSequenceClassification.from_config(cfg)
    elif arm == "scratch":
        cfg = RobertaConfig(
            vocab_size=len(tok),
            hidden_size=256,
            num_hidden_layers=4,
            num_attention_heads=4,
            intermediate_size=1024,
            max_position_embeddings=514,
            type_vocab_size=1,
            pad_token_id=tok.pad_token_id,
            num_labels=1,
        )
        model = RobertaForSequenceClassification(cfg)
    else:
        raise ValueError(arm)
    return model


@torch.inference_mode()
def predict(model, loader, device):
    model.eval()
    probs, ys = [], []
    for batch in loader:
        ids = batch["input_ids"].to(device, non_blocking=True)
        mask = batch["attention_mask"].to(device, non_blocking=True)
        with torch.autocast("cuda", dtype=torch.float16):
            logits = model(input_ids=ids, attention_mask=mask).logits.squeeze(-1)
        probs.append(torch.sigmoid(logits.float()).cpu().numpy())
        ys.append(batch["y"].numpy())
    return np.concatenate(ys), np.concatenate(probs)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", required=True, choices=["herg", "dili", "ames"])
    ap.add_argument("--arm", required=True, choices=["pretrained", "matched", "scratch"])
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--max-epochs", type=int, default=40)
    ap.add_argument("--patience", type=int, default=8)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--max-len", type=int, default=192)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.backends.cudnn.benchmark = False

    out = Path(args.out) if args.out else RUNS / f"{args.endpoint}_{args.arm}_s{args.seed}"
    out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    tok = AutoTokenizer.from_pretrained(MODEL)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    train = load_split(args.endpoint, "train")
    valid = load_split(args.endpoint, "valid")
    test = load_split(args.endpoint, "test")
    ds_train = MolDataset(train, tok, args.max_len)
    ds_valid = MolDataset(valid, tok, args.max_len)
    ds_test = MolDataset(test, tok, args.max_len)
    dl_train = DataLoader(ds_train, batch_size=args.batch_size, shuffle=True, num_workers=0, drop_last=False)
    dl_valid = DataLoader(ds_valid, batch_size=args.batch_size, shuffle=False, num_workers=0)
    dl_test = DataLoader(ds_test, batch_size=args.batch_size, shuffle=False, num_workers=0)

    model = build_model(args.arm, tok).to(device)
    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)

    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    total_steps = max(1, args.max_epochs * len(dl_train))
    sched = get_linear_schedule_with_warmup(opt, int(0.06 * total_steps), total_steps)
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")

    best_auc, best_epoch, best_state = -1.0, -1, None
    log_lines = [
        f"endpoint={args.endpoint} arm={args.arm} seed={args.seed} params={n_params} "
        f"train={len(train)} valid={len(valid)} test={len(test)}"
    ]
    t0 = time.time()
    for epoch in range(1, args.max_epochs + 1):
        model.train()
        losses = []
        for batch in dl_train:
            ids = batch["input_ids"].to(device, non_blocking=True)
            mask = batch["attention_mask"].to(device, non_blocking=True)
            y = batch["y"].to(device, non_blocking=True)
            opt.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.float16, enabled=device.type == "cuda"):
                logits = model(input_ids=ids, attention_mask=mask).logits.squeeze(-1)
                loss = F.binary_cross_entropy_with_logits(logits, y)
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            scaler.step(opt)
            scaler.update()
            sched.step()
            losses.append(float(loss.detach().cpu()))
        yv, pv = predict(model, dl_valid, device)
        val_auc = float(roc_auc_score(yv, pv))
        log_lines.append(f"epoch {epoch} loss {np.mean(losses):.4f} valid_auc {val_auc:.4f}")
        if val_auc > best_auc:
            best_auc, best_epoch = val_auc, epoch
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        if epoch - best_epoch >= args.patience:
            break
    if best_state is not None:
        model.load_state_dict(best_state)
    yv, pv = predict(model, dl_valid, device)
    yt, pt = predict(model, dl_test, device)
    metrics = {
        "endpoint": args.endpoint,
        "arm": args.arm,
        "seed": args.seed,
        "params": int(n_params),
        "best_epoch": int(best_epoch),
        "best_valid_auc": float(best_auc),
        "train_seconds": float(time.time() - t0),
        "valid": point_metrics(yv, pv),
        "test": point_metrics(yt, pt),
    }
    test_out = test.copy()
    test_out["y"] = pt
    test_out[["smiles", "y", "inchikey"]].to_csv(out / "pred_test.csv", index=False)
    valid_out = valid.copy()
    valid_out["y"] = pv
    valid_out[["smiles", "y", "inchikey"]].to_csv(out / "pred_valid.csv", index=False)
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (out / "train.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
