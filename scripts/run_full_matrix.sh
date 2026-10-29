#!/usr/bin/env bash
# Standardized full-data matrix: all models 100 epochs / patience 20, identical budget.
# Older runs with shorter caps are archived under runs/chemprop/_archive_short_budget/.
set -u
cd "$(dirname "$0")/.."
PY=.venv312/Scripts/python.exe
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1
ARCH=runs/chemprop/_archive_short_budget
mkdir -p "$ARCH"

train () {
  local ep=$1 mode=$2 seed=$3
  local tag="${ep}_${mode}_s${seed}"
  local extra=()
  case "$mode" in
    chemeleon) extra=(--foundation CHEMELEON) ;;
    scratch)   extra=(--foundation none) ;;
    matched)   extra=(--foundation none --matched) ;;
    *) echo "bad mode $mode"; exit 1 ;;
  esac
  if [ -d "runs/chemprop/$tag" ]; then
    local dest="$ARCH/$tag"
    [ -e "$dest" ] && dest="$ARCH/${tag}.$(date +%s)"
    mv "runs/chemprop/$tag" "$dest"
  fi
  "$PY" scripts/03_chemprop_run.py --endpoint "$ep" --seed "$seed" --tag "$tag" \
    --epochs 100 --patience 20 --batch-size 64 --max-lr 1e-4 "${extra[@]}" || exit 1
}

for ep in herg dili; do
  for mode in chemeleon scratch matched; do
    for s in 42 1 2; do train "$ep" "$mode" "$s"; done
  done
done

for mode in chemeleon scratch matched; do
  for s in 42 1 2; do train ames "$mode" "$s"; done
done

echo "MATRIX DONE"
