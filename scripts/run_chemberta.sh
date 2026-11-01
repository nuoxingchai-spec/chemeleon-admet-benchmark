#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
mkdir -p reports
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_HUB_DISABLE_TELEMETRY=1
export TOKENIZERS_PARALLELISM=false
for ep in herg dili ames; do
  for arm in pretrained matched scratch; do
    for seed in 42 1 2; do
      out="runs/chemberta/${ep}_${arm}_s${seed}"
      if [ -f "$out/metrics.json" ]; then
        echo "[$(date '+%F %T')] SKIP ${ep} ${arm} ${seed}" >> reports/chemberta_runner.log
        continue
      fi
      echo "[$(date '+%F %T')] START ${ep} ${arm} ${seed}" >> reports/chemberta_runner.log
      .venv312/Scripts/python.exe scripts/39_second_fm.py \
        --endpoint "$ep" --arm "$arm" --seed "$seed" \
        --max-epochs 40 --patience 8 --lr 1e-4 --batch-size 32 \
        --out "$out" >> reports/chemberta_runner.log 2>&1
      echo "[$(date '+%F %T')] DONE ${ep} ${arm} ${seed}" >> reports/chemberta_runner.log
    done
  done
done
echo "[$(date '+%F %T')] ALL DONE" >> reports/chemberta_runner.log
