"""Compute InChIKeys for the CheMeleon pretraining corpus (1M PubChem SMILES)."""
from __future__ import annotations

import argparse
from multiprocessing import Pool
from pathlib import Path

import pandas as pd
from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SMILES = ROOT / "data" / "external" / "chemeleon_pretrain" / "cleaned_pubchem_1MM.smiles"
DEFAULT_OUT = ROOT / "data" / "external" / "chemeleon_pretrain" / "pretrain_inchikeys.csv"


def key_batch(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        smi = line.strip()
        if not smi:
            continue
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            continue
        try:
            out.append(Chem.MolToInchiKey(mol))
        except Exception:
            continue
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smiles", default=str(DEFAULT_SMILES))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--chunk", type=int, default=2000)
    args = ap.parse_args()

    with open(args.smiles, encoding="utf-8") as fh:
        lines = [ln for ln in fh if ln.strip()]
    chunks = [lines[i : i + args.chunk] for i in range(0, len(lines), args.chunk)]
    keys: list[str] = []
    with Pool(args.workers) as pool:
        for i, part in enumerate(pool.imap_unordered(key_batch, chunks, chunksize=1), 1):
            keys.extend(part)
            if i % 50 == 0:
                print(f"{i}/{len(chunks)} chunks, {len(keys)} keys", flush=True)
    ser = pd.Series(keys, dtype="string").drop_duplicates().sort_values().reset_index(drop=True)
    ser.to_frame("inchikey").to_csv(args.out, index=False)
    print(f"wrote {len(ser)} unique InChIKeys -> {args.out}")


if __name__ == "__main__":
    main()
