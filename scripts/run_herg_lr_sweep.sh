#!/usr/bin/env bash
# Equal-tuning sensitivity for the hERG capacity control: pretrained and random-init
# encoders at two additional learning rates, same budget and seeds as the main matrix.
set -u
cd "$(dirname "$0")/.."
PY=.venv312/Scripts/python.exe
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1

for lr in 0.0003 0.001; do
  for arm in chemeleon matched; do
    for seed in 42 1 2; do
      tag="herg_${arm}_lr${lr/./}_s${seed}"
      extra=(--foundation CHEMELEON)
      if [ "$arm" = "matched" ]; then
        extra=(--foundation none --matched)
      fi
      echo "=== $tag ==="
      "$PY" scripts/03_chemprop_run.py --endpoint herg --seed "$seed" --tag "$tag" \
        --epochs 100 --patience 20 --batch-size 64 --max-lr "$lr" \
        --runs-dir runs/chemprop_lr --report-csv reports/chemprop_runs_lr.csv \
        "${extra[@]}" || exit 1
    done
  done
done

echo "LR SWEEP DONE"
