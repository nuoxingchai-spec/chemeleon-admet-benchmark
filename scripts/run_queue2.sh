#!/usr/bin/env bash
# Third GPU batch: threshold-aligned external models (appendix sensitivity analysis).
set -u
cd "$(dirname "$0")/.."
PY=.venv312/Scripts/python.exe
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1

for model in chemeleon scratch; do
  for s in 42 1 2; do
    "$PY" scripts/10_external_validate.py --mode train --model "$model" --seed "$s" \
      --epochs 100 --patience 20 || exit 1
  done
done
echo "QUEUE2 DONE"
