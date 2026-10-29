"""HTTP API and browser studio for the CheMeleon ADMET predictor.

Run with a single worker: the Chemprop/Lightning predictor is serialized
behind a lock and each worker would load its own copy of the weights.

`python -m admet_predictor.studio` opens the studio in a browser.
`uvicorn admet_predictor.app_fastapi:app --host 127.0.0.1 --port 8000 --workers 1`
serves it headless.
"""

from __future__ import annotations

import io
import os
import threading
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel, Field
from rdkit import Chem, rdBase
from rdkit.Chem import Draw

from . import __version__
from .engine import ENDPOINTS, ADMETPredictor

PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_DIR / "static"


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
    app = FastAPI(title="CheMeleon ADMET Predictor", version=__version__)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html", media_type="text/html")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "endpoints": list(ENDPOINTS), "version": __version__}

    @app.get("/metadata")
    def metadata() -> dict:
        endpoints = {}
        for endpoint in ENDPOINTS:
            calibrator = predictor.calibrators[endpoint]
            reference = calibrator.get("reference_test", {})
            endpoints[endpoint] = {
                "temperature": calibrator["T"],
                "calibration_n": calibrator["fit"]["n"],
                "test_auc": reference.get("auc"),
                "test_ece_raw": reference.get("ece_raw"),
                "test_ece_calibrated": reference.get("ece_calibrated"),
            }
        return {"version": __version__, "endpoints": endpoints}

    @app.get("/molecule.png", include_in_schema=False)
    def molecule_png(
        smiles: str = Query(..., min_length=1, max_length=2000),
        size: int = Query(420, ge=160, le=720),
    ) -> Response:
        with rdBase.BlockLogs():
            mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise HTTPException(status_code=400, detail="invalid SMILES")
        try:
            image = Draw.MolToImage(mol, size=(size, size)).convert("RGBA")
        except Exception as exc:
            raise HTTPException(status_code=422, detail="could not render molecule") from exc

        # RDKit draws black bonds and coloured atom labels on white; chroma
        # separates the two, since black is dark but not saturated.
        rgba = np.asarray(image, dtype=np.float32)
        rgb = rgba[..., :3]
        chroma = rgb.max(axis=-1) - rgb.min(axis=-1)
        luminance = rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722
        alpha = np.where(
            chroma > 24.0,
            np.clip((255.0 - luminance) * 1.8, 0.0, 255.0),
            np.clip((255.0 - luminance) * 1.08, 0.0, 255.0),
        )
        bond = np.array([30.0, 79.0, 184.0], dtype=np.float32)
        atom = np.array([18.0, 63.0, 142.0], dtype=np.float32)
        rgba[..., :3] = np.where((chroma <= 24.0)[..., None], bond, atom)
        rgba[..., 3] = alpha
        image = Image.fromarray(rgba.astype(np.uint8), mode="RGBA")

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return Response(
            content=buffer.getvalue(),
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=86400"},
        )

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
