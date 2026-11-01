#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1
mkdir -p reports runs/chemprop_second
for ep in dili ames; do
  for arm in chemeleon matched scratch; do
    for seed in 42 1 2; do
      out="runs/chemprop_second/${ep}_${arm}_s${seed}"
      if [ -f "$out/pred_test.csv" ]; then
        echo "[$(date '+%F %T')] SKIP ${ep} ${arm} ${seed}" >> reports/second_split_chemprop.log
        continue
      fi
      echo "[$(date '+%F %T')] START ${ep} ${arm} ${seed}" >> reports/second_split_chemprop.log
      extra=()
      if [ "$arm" = "chemeleon" ]; then
        extra=(--from-foundation CHEMELEON)
      elif [ "$arm" = "matched" ]; then
        extra=(--message-hidden-dim 2048 --depth 6)
      fi
      .venv312/Scripts/chemprop.exe train \
        -i "data/chemprop_second/${ep}/train.csv" \
           "data/chemprop_second/${ep}/valid.csv" \
           "data/chemprop_second/${ep}/test.csv" \
        -o "$out" --task-type classification --target-columns y \
        --metrics roc prc accuracy binary-mcc --tracking-metric roc \
        --epochs 100 --patience 20 --batch-size 64 --max-lr 0.0001 \
        --ensemble-size 1 --accelerator gpu --devices 1 --num-workers 0 \
        --data-seed "$seed" --pytorch-seed "$seed" --remove-checkpoints \
        "${extra[@]}" >> reports/second_split_chemprop.log 2>&1
      echo "[$(date '+%F %T')] DONE ${ep} ${arm} ${seed}" >> reports/second_split_chemprop.log
    done
  done
done
echo "[$(date '+%F %T')] ALL DONE" >> reports/second_split_chemprop.log
