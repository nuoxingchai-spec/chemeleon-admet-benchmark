#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
# usage: bash scripts/run_chemberta_lr.sh <lr-tag> <lr> <endpoints...>
tag="$1"; lr="$2"; shift 2
eps="$*"
mkdir -p reports
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_HUB_DISABLE_TELEMETRY=1
export TOKENIZERS_PARALLELISM=false
for ep in $eps; do
  for arm in pretrained matched scratch; do
    for seed in 42 1 2; do
      out="runs/chemberta_${tag}/${ep}_${arm}_s${seed}"
      if [ -f "$out/metrics.json" ]; then
        echo "[$(date '+%F %T')] SKIP ${ep} ${arm} ${seed}" >> "reports/chemberta_${tag}_runner.log"
        continue
      fi
      echo "[$(date '+%F %T')] START ${ep} ${arm} ${seed}" >> "reports/chemberta_${tag}_runner.log"
      .venv312/Scripts/python.exe scripts/39_second_fm.py \
        --endpoint "$ep" --arm "$arm" --seed "$seed" \
        --max-epochs 40 --patience 8 --lr "$lr" --batch-size 32 \
        --out "$out" >> "reports/chemberta_${tag}_runner.log" 2>&1
      echo "[$(date '+%F %T')] DONE ${ep} ${arm} ${seed}" >> "reports/chemberta_${tag}_runner.log"
    done
  done
done
echo "[$(date '+%F %T')] ALL DONE" >> "reports/chemberta_${tag}_runner.log"
