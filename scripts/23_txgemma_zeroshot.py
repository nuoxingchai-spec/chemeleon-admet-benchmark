"""Zero-shot TxGemma-2B on the local hERG/DILI/Ames test splits (TDC prompt templates)."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from metrics import ece  # noqa: E402
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss  # noqa: E402

MODEL = ROOT / "models" / "txgemma-2b-predict"
PROMPTS = json.loads((MODEL / "tdc_prompts.json").read_text(encoding="utf-8"))
TASKS = {"herg": "hERG", "dili": "DILI", "ames": "AMES"}


def prompt_for(task, smiles):
    return PROMPTS[task].replace("{Drug SMILES}", smiles)


def seq_logprob(model, tok, prompt, answer):
    p_ids = tok(prompt, return_tensors="pt", add_special_tokens=True)["input_ids"]
    p_ids = p_ids.to(model.device)
    a_ids = tok(answer, return_tensors="pt", add_special_tokens=False)["input_ids"]
    a_ids = a_ids.to(model.device)
    ids = torch.cat([p_ids, a_ids], dim=1)
    with torch.no_grad():
        out = model(input_ids=ids)
    logits = out.logits[0, p_ids.shape[1] - 1: p_ids.shape[1] - 1 + a_ids.shape[1]].float()
    logp = torch.log_softmax(logits, dim=-1)
    return float(logp.gather(1, a_ids[0].unsqueeze(1)).sum())


def score(model, tok, prompt):
    la = seq_logprob(model, tok, prompt, "(A)")
    lb = seq_logprob(model, tok, prompt, "(B)")
    return 1.0 / (1.0 + np.exp(la - lb))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoints", nargs="+", default=["herg", "dili", "ames"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="reports/txgemma_zeroshot.csv")
    args = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(MODEL)
    quant = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL, quantization_config=quant, device_map={"": 0}, torch_dtype=torch.float16,
        attn_implementation="eager",
    )
    model.eval()

    rows = []
    for ep in args.endpoints:
        df = pd.read_csv(ROOT / f"data/chemprop/{ep}/test.csv")
        if args.limit:
            df = df.head(args.limit)
        for i, r in df.iterrows():
            p = score(model, tok, prompt_for(TASKS[ep], r["smiles"]))
            rows.append({"endpoint": ep, "inchikey": r["inchikey"], "smiles": r["smiles"],
                         "y": int(r["y"]), "p": p})
            if (i + 1) % 25 == 0:
                print(f"{ep} {i + 1}/{len(df)}", flush=True)
        d = pd.DataFrame([x for x in rows if x["endpoint"] == ep])
        print(ep, "n", len(d), "AUC", roc_auc_score(d.y, d.p),
              "AP", average_precision_score(d.y, d.p), flush=True)

    out = pd.DataFrame(rows)
    out.to_csv(ROOT / args.out, index=False)
    summary = []
    for ep, d in out.groupby("endpoint"):
        summary.append({
            "endpoint": ep, "n": len(d), "pos": int(d.y.sum()),
            "auc": roc_auc_score(d.y, d.p),
            "pr_auc": average_precision_score(d.y, d.p),
            "brier": brier_score_loss(d.y, d.p),
            "ece": ece(d.y.to_numpy(), d.p.to_numpy()),
            "mean_p": float(d.p.mean()),
        })
    s = pd.DataFrame(summary)
    s.to_csv(ROOT / "reports/txgemma_zeroshot_summary.csv", index=False)
    print(s.to_string(index=False))


if __name__ == "__main__":
    main()