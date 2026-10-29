# Data

The repository ships the deterministic splits and the Chemprop-format tables
used by the released models, not the original downloads.

- `processed/global_split.csv` and `processed/splits/*.csv`: scaffold-disjoint
  assignment of every compound (fit / early stop / calibration / test).
- `chemprop/{herg,dili,ames}/`: training tables for the benchmark models.
- `chemprop/lowdata/`: the 48 low-data training subsets.
- `chemprop/multitask/`: pooled three-endpoint tables.
- `chemprop/herg_aligned/`: threshold-aligned hERG tables and the cleaned Karim
  external set (`external_clean.csv`).

To rebuild from scratch, download the Therapeutics Data Commons hERG, DILI,
Ames, and Karim hERG collections and place the tab-separated files under
`data/external/tdc/` using the filenames referenced by `scripts/01_build_splits.py`
and `scripts/10_external_prep.py`, then run the scripts in numeric order.
TDC data and the Karim hERG labels remain subject to their original terms.
