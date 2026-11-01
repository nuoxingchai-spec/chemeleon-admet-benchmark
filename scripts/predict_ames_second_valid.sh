#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1
for arm in chemeleon matched scratch; do
  for seed in 42 1 2; do
    d="runs/chemprop_second/ames_${arm}_s${seed}"
    [ -f "$d/model_0/best.pt" ] || continue
    [ -f "$d/pred_valid.csv" ] && continue
    .venv312/Scripts/chemprop.exe predict -i data/chemprop_second/ames/valid.csv \
      --model-paths "$d/model_0/best.pt" -o "$d/pred_valid.csv" \
      --accelerator cpu --devices 1 --num-workers 0 >> reports/predict_ames_second_valid.log 2>&1
    echo "[$(date '+%F %T')] DONE $d" >> reports/predict_ames_second_valid.log
  done
done
echo "[$(date '+%F %T')] ALL DONE" >> reports/predict_ames_second_valid.log
