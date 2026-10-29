"""Install deployment checkpoints into the bundle and extend the manifest."""
import hashlib
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs" / "deploy"
RELEASE = ROOT / "release"
MODELS = RELEASE / "admet_predictor" / "models"
MANIFEST = RELEASE / "MANIFEST_weights.csv"
SEEDS = (1, 2, 42)
ENDPOINTS = ("herg", "dili", "ames")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    MODELS.mkdir(parents=True, exist_ok=True)
    manifest = pd.read_csv(MANIFEST)
    manifest = manifest[manifest["category"] != "deployment"].copy()
    rows = []
    for endpoint in ENDPOINTS:
        for seed in SEEDS:
            source = RUNS / f"{endpoint}_s{seed}" / "model_0" / "best.pt"
            if not source.exists():
                raise FileNotFoundError(source)
            target = MODELS / f"{endpoint}_seed{seed}.pt"
            shutil.copy2(source, target)
            rows.append(
                {
                    "path": str(source.relative_to(ROOT)).replace("\\", "/"),
                    "category": "deployment",
                    "endpoint": endpoint,
                    "model": "chemeleon",
                    "n_train": None,
                    "seed": seed,
                    "bytes": target.stat().st_size,
                    "sha256": sha256(target),
                }
            )
    manifest = pd.concat([manifest, pd.DataFrame(rows)], ignore_index=True)
    order = {"full_data": 0, "deployment": 1, "external_aligned": 2, "multitask": 3, "lowdata": 4}
    manifest["_order"] = manifest["category"].map(order).fillna(9).astype(int)
    manifest = manifest.sort_values(["_order", "endpoint", "seed", "path"]).drop(columns="_order")
    manifest.to_csv(MANIFEST, index=False)

    with (RELEASE / "SHA256SUMS_models.txt").open("w", encoding="utf-8", newline="\n") as handle:
        for path in sorted(MODELS.glob("*.pt")):
            handle.write(f"{sha256(path)}  admet_predictor/models/{path.name}\n")

    print(manifest.groupby("category").size().to_string())
    print(f"shipped checkpoints: {len(list(MODELS.glob('*.pt')))}")


if __name__ == "__main__":
    main()
