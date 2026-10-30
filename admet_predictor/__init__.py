"""CheMeleon-based ADMET predictor (hERG / DILI / Ames)."""

from .engine import ENDPOINTS, ADMETPredictor

__all__ = ["ADMETPredictor", "ENDPOINTS"]
__version__ = "1.1.1"
