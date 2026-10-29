# v1.1.0: clean-calibration ADMET predictor and full benchmark release

This release accompanies the anonymous submission and contains:

- `admet_predictor_weights.zip`: 9 deployment checkpoints (3 endpoints x 3
  seeds), the shipped temperature calibrators, the external-refit sensitivity
  artifact, the model card, and the full 93-row manifest.
- `admet_benchmark_weights_full.zip`: 36 benchmark checkpoints (27 full-data,
  6 threshold-aligned, 3 multi-task).
- `admet_benchmark_weights_lowdata.zip`: 48 low-data checkpoints.
- SHA-256 sidecars for every archive.

All checkpoints are Chemprop 2.3.1 files loadable with
`chemprop.models.MPNN.load_from_file`, released under the MIT License (see
`LICENSE` and `NOTICE`). The repository contains the code, deterministic splits,
predictions, metrics, and figures.

The deployment models were retrained with an internal scaffold-disjoint
early-stopping split, so the global validation split is used only for
temperature calibration. The paper's benchmark models retain their original
protocol and are reported separately. The external Karim hERG refit is a
sensitivity artifact, not the shipped calibrator: its temperature hits the
search bound and degrades the local test split, so the shipped parameters stay
on the internal clean split.


| Asset | Size | SHA-256 |
|---|---|---|
| `admet_predictor_weights.zip` | 0.31 GB | `884a7ce20b62c491c353b69ee22faaef06510858bcfe9c195d73f596f816f7ec` |
| `admet_benchmark_weights_full.zip` | 0.85 GB | `d500c95d3b06de61e38339d52840162e038e1510a4f45ae2133776fc44d3a3c7` |
| `admet_benchmark_weights_lowdata.zip` | 1.26 GB | `c5d1659c6f37603e38c60c344def2f34d9ae839f41182710113df44b60bfceb6` |

Verify with `python -m admet_predictor.verify` after unpacking the deployment
weights and installing `admet_predictor/requirements.txt`.
