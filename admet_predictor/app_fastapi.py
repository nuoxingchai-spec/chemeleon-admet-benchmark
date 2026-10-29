"""HTTP API for the CheMeleon ADMET predictor.

Run with a single worker: the Chemprop/Lightning predictor is serialized
behind a lock and each worker would load its own copy of the weights.
`uvicorn admet_predictor.app_fastapi:app --host 127.0.0.1 --port 8000 --workers 1`
"""

from __future__ import annotations

import os
import threading

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .engine import ADMETPredictor


class PredictRequest(BaseModel):
    smiles: list[str] = Field(..., min_length=1, max_length=1000)


def create_app(
    model_dir: str | None = None,
    calibrator_dir: str | None = None,
    device: str | None = None,
) -> FastAPI:
    predictor = ADMETPredictor(
        model_dir=model_dir,
        calibrator_dir=calibrator_dir,
        device=device or os.environ.get("ADMET_DEVICE", "cpu"),
    )
    lock = threading.Lock()
    app = FastAPI(title="CheMeleon ADMET Predictor", version="1.1.0")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "endpoints": ["herg", "dili", "ames"]}

    @app.post("/predict")
    def predict(request: PredictRequest) -> dict:
        try:
            with lock:
                frame, invalid = predictor.predict(
                    request.smiles, return_invalid=True
                )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "predictions": frame.to_dict(orient="records"),
            "invalid": invalid.to_dict(orient="records"),
        }

    return app


app = create_app()
