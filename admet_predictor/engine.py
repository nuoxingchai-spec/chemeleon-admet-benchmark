"""Unified inference engine for the CheMeleon ADMET model family."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
import torch
from chemprop import data, featurizers, models
from lightning import pytorch as pl
from rdkit import Chem, rdBase

ENDPOINTS = ("herg", "dili", "ames")
PACKAGE_DIR = Path(__file__).resolve().parent
LOGIT_EPS = 1e-6


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=float), LOGIT_EPS, 1.0 - LOGIT_EPS)
    return np.log(p / (1.0 - p))


def apply_temperature(p: np.ndarray, t: float) -> np.ndarray:
    if not t > 0:
        raise ValueError(f"temperature must be positive, got {t}")
    return 1.0 / (1.0 + np.exp(-_logit(p) / t))


class ADMETPredictor:
    """Seed-ensemble predictor with per-endpoint temperature calibration.

    The shipped checkpoints output probabilities directly (Chemprop
    classification head), so no sigmoid is applied to model outputs.
    """

    def __init__(
        self,
        model_dir: str | Path | None = None,
        calibrator_dir: str | Path | None = None,
        device: str = "cpu",
        batch_size: int = 64,
    ) -> None:
        self.model_dir = Path(model_dir) if model_dir else PACKAGE_DIR / "models"
        self.calibrator_dir = (
            Path(calibrator_dir) if calibrator_dir else PACKAGE_DIR / "calibrators"
        )
        self.device = device
        self.batch_size = int(batch_size)
        if device.startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError("CUDA requested but not available")
        self._torch_device = torch.device(device)
        self._featurizer = featurizers.SimpleMoleculeMolGraphFeaturizer(
            atom_featurizer=featurizers.MultiHotAtomFeaturizer.v2()
        )
        self._trainer = pl.Trainer(
            logger=False,
            enable_progress_bar=False,
            enable_model_summary=False,
            accelerator="gpu" if device.startswith("cuda") else "cpu",
            devices=1,
        )
        self.models = {ep: self._load_endpoint(ep) for ep in ENDPOINTS}
        self.calibrators = {ep: self._load_calibrator(ep) for ep in ENDPOINTS}
        self.last_invalid: list[tuple[int, str]] = []

    def _load_endpoint(self, endpoint: str) -> list:
        paths = sorted(self.model_dir.glob(f"{endpoint}_seed*.pt"))
        if not paths:
            raise FileNotFoundError(
                f"no checkpoints matching {endpoint}_seed*.pt in {self.model_dir}"
            )
        return [
            models.MPNN.load_from_file(
                str(path), map_location=self._torch_device
            ).eval()
            for path in paths
        ]

    def _load_calibrator(self, endpoint: str) -> dict:
        path = self.calibrator_dir / f"{endpoint}.json"
        if not path.exists():
            raise FileNotFoundError(f"missing calibrator: {path}")
        cal = json.loads(path.read_text(encoding="utf-8"))
        if cal.get("method") != "temperature":
            raise ValueError(f"unsupported calibration method in {path}")
        if not float(cal.get("T", 0)) > 0:
            raise ValueError(f"invalid temperature in {path}")
        return cal

    @staticmethod
    def _validate(smiles: Sequence[str]) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
        valid, invalid = [], []
        for index, value in enumerate(smiles):
            smi = "" if value is None else str(value)
            with rdBase.BlockLogs():
                valid_mol = Chem.MolFromSmiles(smi) if smi else None
            if valid_mol is None:
                invalid.append((index, smi))
            else:
                valid.append((index, smi))
        return valid, invalid

    def _raw_prob(self, endpoint: str, smiles: Sequence[str]) -> np.ndarray:
        datapoints = [data.MoleculeDatapoint.from_smi(smi) for smi in smiles]
        dataset = data.MoleculeDataset(datapoints, featurizer=self._featurizer)
        loader = data.build_dataloader(
            dataset, batch_size=self.batch_size, shuffle=False, num_workers=0
        )
        seed_probs = []
        for model in self.models[endpoint]:
            with torch.inference_mode():
                batches = self._trainer.predict(model, loader)
            seed_probs.append(
                np.concatenate(
                    [batch.detach().cpu().numpy().reshape(-1) for batch in batches]
                )
            )
        return np.mean(seed_probs, axis=0)

    def predict(
        self, smiles: Sequence[str] | str, return_invalid: bool = False
    ) -> pd.DataFrame | tuple[pd.DataFrame, pd.DataFrame]:
        if isinstance(smiles, str):
            smiles = [smiles]
        valid, invalid = self._validate(smiles)
        self.last_invalid = invalid
        if not valid:
            raise ValueError("no valid SMILES after RDKit parsing")

        valid_smiles = [smi for _, smi in valid]
        result: dict[str, object] = {"smiles": valid_smiles}
        for endpoint in ENDPOINTS:
            raw = self._raw_prob(endpoint, valid_smiles)
            calibrated = apply_temperature(raw, self.calibrators[endpoint]["T"])
            result[f"{endpoint}_raw_prob"] = raw
            result[f"{endpoint}_prob"] = calibrated
            result[f"{endpoint}_pred_label"] = (calibrated >= 0.5).astype(int)

        predictions = pd.DataFrame(result)
        if return_invalid:
            invalid_df = pd.DataFrame(invalid, columns=["row_index", "smiles"])
            return predictions, invalid_df
        return predictions
