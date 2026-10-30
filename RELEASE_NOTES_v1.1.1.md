# v1.1.1: browser studio and blue interface

This release adds a local browser studio to the released predictor. Models,
calibrators, splits, and checkpoints are unchanged from v1.1.0; the three
weight archives and their SHA-256 sidecars remain valid.

## Added

- `python -m admet_predictor.studio` launches a single-page studio at
  `http://127.0.0.1:8000/` and opens it in the default browser.
- 2D structure preview rendered with RDKit, per-endpoint calibrated
  probabilities with HIGH/LOW flags, test AUC and temperature context, and
  batch scoring for up to 50 SMILES.
- JSON endpoints `/metadata` and `/molecule.png`; `/health` now reports the
  package version and endpoint list.

## Changed

- The interface uses a light-blue theme with a strict blue/white palette.
- Molecule line art is rendered in matching blue tones.
- Package version is 1.1.1.

## Downloads

The model weights are unchanged. Use the three archives from the v1.1.0
release (Assets section):

| Asset | Size | SHA-256 |
|---|---|---|
| `admet_predictor_weights.zip` | 0.31 GB | `884a7ce20b62c491c353b69ee22faaef06510858bcfe9c195d73f596f816f7ec` |
| `admet_benchmark_weights_full.zip` | 0.85 GB | `d500c95d3b06de61e38339d52840162e038e1510a4f45ae2133776fc44d3a3c7` |
| `admet_benchmark_weights_lowdata.zip` | 1.26 GB | `c5d1659c6f37603e38c60c344def2f34d9ae839f41182710113df44b60bfceb6` |

After unpacking the deployment weights, install `admet_predictor/requirements.txt`
and run `python -m admet_predictor.verify`.
