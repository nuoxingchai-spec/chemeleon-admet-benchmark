"""Gradio UI for single-molecule ADMET predictions.

`python -m admet_predictor.app_gradio`
"""

from __future__ import annotations

import gradio as gr
import pandas as pd
from rdkit import Chem, rdBase
from rdkit.Chem import Draw

from .engine import ADMETPredictor


def build_demo(predictor: ADMETPredictor | None = None) -> gr.Blocks:
    predictor = predictor or ADMETPredictor()

    def predict_single(smiles: str):
        with rdBase.BlockLogs():
            mol = Chem.MolFromSmiles(smiles) if smiles else None
        if mol is None:
            return None, pd.DataFrame({"error": ["Invalid SMILES"]})
        frame = predictor.predict([smiles])
        image = Draw.MolToImage(mol, size=(320, 320))
        table = frame.drop(columns=["smiles"]).T.reset_index()
        table.columns = ["output", "value"]
        return image, table

    with gr.Blocks(title="CheMeleon ADMET Predictor") as demo:
        gr.Markdown(
            "## CheMeleon ADMET Predictor\n"
            "Calibrated probabilities for hERG blockade, DILI, and Ames mutagenicity. "
            "Research use only."
        )
        with gr.Row():
            smiles = gr.Textbox(
                label="SMILES",
                placeholder="CC(=O)Nc1ccc(O)cc1",
                autofocus=True,
            )
            image = gr.Image(label="Structure", type="pil")
        table = gr.Dataframe(label="Predictions")
        button = gr.Button("Predict", variant="primary")
        button.click(predict_single, inputs=smiles, outputs=[image, table])
        smiles.submit(predict_single, inputs=smiles, outputs=[image, table])
    return demo


if __name__ == "__main__":
    build_demo().launch(server_name="127.0.0.1", server_port=7860)
