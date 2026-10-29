# Model Card: CheMeleon ADMET Predictor

Version 1.1.0, 2026-10-29.

## Model details

- Three single-task directed message-passing neural networks (D-MPNN,
  Chemprop 2.3.1), initialized from the CheMeleon foundation model and
  fine-tuned separately on hERG, DILI, and Ames.
- Encoder 2048x6; 9,329,247 parameters per model. Three training seeds
  (42, 1, 2) per endpoint; the prediction is the mean of the three seed
  probabilities, followed by temperature scaling.
- The deployment checkpoints were retrained with an internal
  scaffold-disjoint early-stopping split carved out of the training data
  (12% of compounds). The global validation split therefore never
  participated in model selection and is used only for calibration. The
  paper's benchmark checkpoints retain their original protocol and are
  reported separately.
- Input: one SMILES string per compound. Output: raw probability, calibrated
  probability, and a label at threshold 0.5 for each endpoint.
- The fine-tuned checkpoints are self-contained; the CheMeleon foundation
  checkpoint is not needed at inference.

## Training data

The deployment split is scaffold-disjoint at every boundary:

| Endpoint | Fit | Early stop | Calibration | Test | Positives (fit/es/calib/test) | Scaffolds (fit/es/calib/test) |
|---|---|---|---|---|---|---|
| hERG | 427 | 58 | 62 | 59 | 295 / 40 / 36 / 42 | 291 / 22 / 36 / 33 |
| DILI | 334 | 45 | 44 | 51 | 168 / 23 / 23 / 22 | 248 / 20 / 38 / 39 |
| Ames | 5,106 | 696 | 712 | 732 | 2,750 / 392 / 426 / 377 | 2,218 / 48 / 283 / 289 |

Zero scaffold overlap between fit, early-stop, calibration, and test for every
endpoint. Labels come from the Therapeutics Data Commons hERG, DILI, and Ames
collections after label cleaning and conflict-group removal. The original hERG
SI "external" set overlaps the Karim external set (458 of 606 compounds,
75.6%) and is not used for evaluation.

The benchmark models reported in the paper use the global 485/62/59 (hERG),
379/44/51 (DILI), and 5,802/712/732 (Ames) split; their metrics are not
interchangeable with the deployment numbers below.

## Training

100 epochs, early-stopping patience 20 on validation ROC-AUC, batch size 64,
learning rate 1e-4, seeds 42/1/2, one model per endpoint and seed. Deployment
models stop on the internal early-stopping split; the calibration and test
splits are not used for model selection. Training and inference were run on a
single 6 GB GPU (RTX A2000) and CPU, respectively.

## Metrics

Deployment seed-ensemble probabilities on the untouched test split:

| Endpoint | n test | AUC | ECE raw | ECE calibrated | Brier calibrated |
|---|---|---|---|---|---|
| hERG | 59 | 0.8768 | 0.1858 | 0.1215 | 0.1413 |
| DILI | 51 | 0.9013 | 0.1608 | 0.1214 | 0.1318 |
| Ames | 732 | 0.8209 | 0.1409 | 0.0814 | 0.1800 |

Calibration-split diagnostics:

| Endpoint | n calib | ECE raw | ECE calibrated | Brier raw | Brier calibrated |
|---|---|---|---|---|---|
| hERG | 62 | 0.1706 | 0.1073 | 0.1644 | 0.1381 |
| DILI | 44 | 0.1716 | 0.1182 | 0.1275 | 0.1268 |
| Ames | 712 | 0.0692 | 0.0350 | 0.1335 | 0.1288 |

For reference, the paper's benchmark models (validation split reused for early
stopping and calibration) report test AUC / ECE raw / ECE calibrated / Brier:
0.8908 / 0.0996 / 0.0974 / 0.1377 (hERG), 0.8777 / 0.1345 / 0.1364 / 0.1421
(DILI), 0.8269 / 0.1018 / 0.0756 / 0.1738 (Ames). Those numbers are not a
clean-calibration estimate; the deployment rows above are.

The hERG and DILI test sets are small (59 and 51 compounds), so their intervals
are wide. Ames (732) carries the most weight for calibration conclusions.

## Calibration

- Method: temperature scaling per endpoint in logit space (eps = 1e-6),
  fitted by minimizing negative log-likelihood on the calibration split.
- Parameters: hERG T = 4.248222 (n = 62), DILI T = 0.855638 (n = 44),
  Ames T = 1.612246 (n = 712).
- The calibration split is the global validation split. Because deployment
  early stopping uses a separate internal split, no calibration point
  influenced model selection. No test labels were used to fit the shipped
  parameters.
- Conformal prediction is not shipped. Under the leaky benchmark protocol,
  Ames coverage was 0.848 against a nominal 0.90; a calibration split that
  never participates in model selection is required for distribution-free
  guarantees. The deployment split removes the model-selection leakage, but
  scaffold shift still violates exchangeability, so coverage is not claimed.
- `fit_calibrators.py` refits the temperature on a user-supplied labeled set
  (columns `smiles,y`) that was not used for model selection.

### External-refit sensitivity (hERG)

The Karim hERG set is the only independent labeled external set. After
compound- and Murcko-scaffold overlap removal it has 11,899 compounds (5,844
positives) and labels blockade at 10 uM, whereas the local labels use a ~40 uM
boundary. Fitting a temperature on it is therefore a stress test, not the
shipped calibration:

| Evaluation | T | ECE | Brier |
|---|---|---|---|
| External, raw | 1.0 | 0.4011 | 0.4099 |
| External, external-fitted T | 20.0 (search bound) | 0.0760 | 0.2455 |
| External, internal T | 4.2482 | 0.2526 | 0.3039 |
| Local test, internal T | 4.2482 | 0.1215 | 0.1413 |
| Local test, external T | 20.0 | 0.2079 | 0.1977 |

The external fit hits the upper search bound, so even a temperature fitted on
the external set cannot fully recalibrate it; and that temperature degrades the
local test split. The shipped calibrator stays on the internal clean split.
The artifact is in `sensitivity/herg_external_refit.json`.

## Intended use

Early ADMET risk triage and compound prioritization in research settings.
Suitable for drug-like small molecules resembling the TDC collections. Not for
clinical decision-making, regulatory submission, or safety-critical use, and
not a substitute for experimental assays.

## Limitations

- 2D graph input only: no 3D conformers, protein structure, metabolism, or
  formulation effects.
- Calibration under distribution shift is not guaranteed; coverage is not
  claimed.
- External transfer is bounded: on the scaffold-clean Karim hERG set, AUC is
  0.632 (0.60-0.65 across analyses; 0.80 on shared scaffolds, 0.65 on novel
  scaffolds).
- The hERG and DILI test sets (59 and 51 compounds) give wide confidence
  intervals; endpoint conclusions are correspondingly uncertain.
- The deployment retraining changes the point estimates relative to the
  benchmark models; both are reported so that the effect of the clean protocol
  is visible.
- Labels are TDC-derived and may contain residual noise; three seeds only.
- No prospective experimental validation was performed.

## License and attribution

- Code, fine-tuned weights, and calibration parameters: MIT (see `LICENSE`).
- Base model CheMeleon: MIT. Burns, Zalte, Abreu, Sieg, Feldmann, Mathea, Green,
  "Deep Learning Foundation Models from Classical Molecular Descriptors",
  arXiv:2506.15792, https://github.com/JacksonBurns/CheMeleon.
- Chemprop: Yang et al. (2019), J. Chem. Inf. Model. 59, 3370-3388; Heid et al.
  (2024), J. Chem. Inf. Model. 64, 8178-8192.
- Training labels remain subject to the terms of their original TDC sources.

## Released weights

The product bundle ships 9 deployment checkpoints (3 endpoints x 3 seeds). The
full public release contains 93 checkpoints under the same MIT license: the 27
full-data benchmark models (CheMeleon, matched, scratch), 6 threshold-aligned
models, 3 multi-task models, 48 low-data models, and the 9 deployment models.
Every file and its SHA-256 is listed in `../MANIFEST_weights.csv`; the archives
are assembled by `../package_weights.py`. Superseded short-budget runs are not
part of the release.

## Reproducibility

Environment: Python 3.12.16, chemprop 2.3.1, torch 2.6.0+cu124,
lightning 2.6.6, rdkit 2026.03.6, numpy 2.5.4, pandas 3.1.0,
scikit-learn 1.9.1.

Shipped deployment checkpoint SHA-256 (`sha256sum -c SHA256SUMS_models.txt`):

| File | SHA-256 |
|---|---|
| ames_seed1.pt | 39e24e7ef23d7fc9c3531b5332a3b3bbdf06ada76afd661563d0a6fd9b3974b2 |
| ames_seed2.pt | 13c940f432396885093a76697a5671ec5402e8c27cf477d3648b264d5ef87c07 |
| ames_seed42.pt | 6cd72478ba41bbcc45aacde5a460adf857bd632c1a556a180baf57c90ccb65bd |
| dili_seed1.pt | 8374a64d69549e3c26e900490d4b702f39e5e2579beaaf1c0becbbdf197673f5 |
| dili_seed2.pt | 45da2c3a9f5ebe545e5edc1482b04ba4894f7537f101ce7768a7295ac5c3c49b |
| dili_seed42.pt | 615dab5980d93e65720ccea350bc6c40c98ac5d6885622e14dbf0898431d01ec |
| herg_seed1.pt | 414754e97a7eea009f0bc11d57b8474c9bb89325363a32150623fdb654ddfc91 |
| herg_seed2.pt | 9bed6bb98d584b65df8b7a7ff8a5038cf1c4abe52610e921fbc3789ee4216338 |
| herg_seed42.pt | d7314c4a4bb94c4189c41dbd6f1351a264c2bc623e05a60714c10a3eae08ac85 |

Verify the installation end to end with `python -m admet_predictor.verify`.
