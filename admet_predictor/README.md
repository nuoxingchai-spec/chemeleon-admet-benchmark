# CheMeleon ADMET Predictor

Unified inference for three fine-tuned CheMeleon models: hERG blockade, DILI,
and Ames mutagenicity. Each endpoint is a seed ensemble of three Chemprop
D-MPNN checkpoints with temperature-calibrated probabilities.

## Layout

```
admet_predictor/
├── models/               # 9 checkpoints (3 endpoints x 3 seeds)
├── calibrators/          # temperature parameters per endpoint
├── sensitivity/          # external-refit sensitivity artifact (hERG)
├── engine.py             # ADMETPredictor
├── cli.py                # batch CSV
├── app_fastapi.py        # HTTP API + studio host
├── studio.py             # one-command browser launcher
├── static/               # studio frontend (HTML/CSS/JS)
├── app_gradio.py         # minimal Gradio UI
├── fit_calibrators.py    # refit on a user-supplied clean set
├── verify.py             # smoke test
├── model_card.md
├── requirements.txt
└── examples/
```

The nine checkpoints are distributed as the `admet_predictor_weights.zip`
release asset. Unpack it and copy `admet_predictor_weights/models/*.pt` into
`admet_predictor/models/`. The repository itself stays small; the benchmark
checkpoints are in separate release assets.

## Install

Python 3.10+ (tested with 3.12.16):

```
pip install -r requirements.txt
```

The fine-tuned checkpoints are self-contained; no foundation checkpoint download
is required. CPU inference works; `--device cuda:0` uses a GPU if available.

## Quick start

From the directory that contains `admet_predictor/`:

```
python -m admet_predictor.verify
python -m admet_predictor.cli --input admet_predictor/examples/input.csv --output preds.csv
```

Browser studio (opens automatically; single molecule, 2D structure, live
calibration meters, and a batch table for up to 50 SMILES):

```
python -m admet_predictor.studio
```

Use `--no-browser --port 8000` for a headless server. The page is served at
`http://127.0.0.1:8000/`; `/health`, `/metadata`, `/molecule.png` and
`/predict` are available alongside it.

Python:

```python
from admet_predictor import ADMETPredictor

predictor = ADMETPredictor(device="cpu")
frame = predictor.predict(["CC(=O)Nc1ccc(O)cc1"])
```

Invalid SMILES are skipped and reported instead of being silently dropped:

```python
frame, invalid = predictor.predict(smiles, return_invalid=True)
```

API (single worker; the predictor is serialized behind a lock):

```
uvicorn admet_predictor.app_fastapi:app --host 127.0.0.1 --port 8000 --workers 1
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d "{\"smiles\": [\"CCO\"]}"
```

Minimal Gradio UI, kept as a dependency-light fallback:

```
python -m admet_predictor.app_gradio
```

## Calibration protocol

The deployment checkpoints were trained with an internal scaffold-disjoint
early-stopping split carved out of the training data (12% of compounds). The
global validation split therefore never participated in model selection and is
used only to fit the temperature: n = 62 hERG, 44 DILI, 712 Ames. The test
split was never used to fit any parameter.

`calibrators/<endpoint>.json` records the temperature, the calibration split
size, and raw/calibrated test metrics. hERG and DILI test sets are small (59 and
51 compounds), so their intervals are wide; Ames (732) carries the most weight.

To refit on a fresh labeled set that did not participate in model selection:

```
python -m admet_predictor.fit_calibrators \
  --endpoint herg --input my_calibration.csv --out calibrators/herg.json
```

The CSV must contain `smiles` and `y` columns. See `model_card.md` for metrics,
data provenance, limitations, weight checksums, and the external-refit
sensitivity analysis.

## License

MIT for code and fine-tuned weights. CheMeleon is MIT; see `NOTICE`.
Research use only, not for clinical or regulatory decisions.
