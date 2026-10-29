# CheMeleon ADMET benchmark

Code, deterministic splits, predictions, and fine-tuned checkpoints for a
controlled evaluation of a molecular foundation model on three ADMET endpoints:
hERG blockade, DILI, and Ames mutagenicity. Prepared for anonymous review.

The study separates three factors that are often conflated in molecular
foundation-model evaluations: capacity, scaffold leakage, and the calibration
protocol. It reports a global scaffold-disjoint benchmark, capacity-matched
controls (CheMeleon, matched, scratch), low-data scaling, selective and
conformal diagnostics, and an external hERG stress test.

## Contents

```
admet_predictor/     # seed-ensemble package (CLI, API, Gradio, browser studio)
data/                # deterministic global and deployment splits
reports/             # predictions, metrics, figures, and analysis tables
scripts/             # split construction, training, calibration, table builders
MANIFEST_weights.csv # 93 checkpoints with sizes and SHA-256
```

## Predictor quick start

The nine deployment checkpoints are distributed as the
`admet_predictor_weights.zip` release asset. Download and unpack it, then copy
`admet_predictor_weights/models/*.pt` into `admet_predictor/models/`:

```
pip install -r admet_predictor/requirements.txt
python -m admet_predictor.verify
python -m admet_predictor.cli --input admet_predictor/examples/input.csv --output preds.csv
python -m admet_predictor.studio
```

The studio opens at `http://127.0.0.1:8000/` and provides a structure preview,
per-endpoint calibration meters, and batch scoring for up to 50 SMILES.

See `admet_predictor/README.md` and `admet_predictor/model_card.md`.

## Calibration protocol

The deployment checkpoints use an internal scaffold-disjoint early-stopping
split carved out of the training data. The global validation split is therefore
clean and is used only to fit the temperature (n = 62 hERG, 44 DILI, 712 Ames).
The paper's benchmark models use the original protocol and are reported
separately. On the untouched deployment test splits:

| Endpoint | n | AUC | ECE raw | ECE calibrated |
|---|---|---|---|---|
| hERG | 59 | 0.8768 | 0.1858 | 0.1215 |
| DILI | 51 | 0.9013 | 0.1608 | 0.1214 |
| Ames | 732 | 0.8209 | 0.1409 | 0.0814 |

The external Karim refit is a sensitivity artifact, not the shipped calibrator;
see the model card.

## Checkpoints

`MANIFEST_weights.csv` lists all 93 checkpoints: 84 benchmark models (27
full-data, 6 threshold-aligned, 3 multi-task, 48 low-data) and 9 deployment
models. Every file is a Chemprop 2.3.1 `best.pt` loadable with
`chemprop.models.MPNN.load_from_file`. The checkpoints are distributed as
three release assets, each below GitHub's 2 GiB per-file limit:

| Asset | Contents | Size | SHA-256 |
|---|---|---|---|
| `admet_predictor_weights.zip` | 9 deployment models + calibrators + model card | 0.31 GB | `884a7ce20b62c491c353b69ee22faaef06510858bcfe9c195d73f596f816f7ec` |
| `admet_benchmark_weights_full.zip` | 36 benchmark models | 0.85 GB | `d500c95d3b06de61e38339d52840162e038e1510a4f45ae2133776fc44d3a3c7` |
| `admet_benchmark_weights_lowdata.zip` | 48 low-data models | 1.26 GB | `c5d1659c6f37603e38c60c344def2f34d9ae839f41182710113df44b60bfceb6` |

The archives contain a copy of the manifest and MIT license; verify them
against the published `.sha256` sidecars.

## Reproducing the study

`scripts/` is numbered in execution order: split construction (`01`), classical
and Chemprop baselines (`02`-`03`), calibration and conformal diagnostics
(`04`, `11`-`19`), table/figure builders (`20`-`22`), and the release pipeline
(`24`-`29`). `data/README.md` lists the raw downloads that are not
redistributed. The released prediction tables under `reports/` and
`data/chemprop/` allow most analyses to be rerun without retraining.

## Data

The splits are derived from the Therapeutics Data Commons hERG, DILI, and Ames
collections after label cleaning and conflict-group removal. Raw TDC files are
not redistributed; `data/README.md` lists the required downloads and the
scripts document the cleaning rules. The external hERG components come from the
Karim set, with compounds and Murcko scaffolds overlapping local data removed.
The cleaned external table is included for reproducibility and remains subject
to the terms of the original Karim release.

## License

MIT for code, fine-tuned weights, and calibration parameters. CheMeleon is MIT.
Training labels remain subject to the terms of their original TDC sources. See
`LICENSE` and `NOTICE`. Research use only; not for clinical or regulatory
decisions.
