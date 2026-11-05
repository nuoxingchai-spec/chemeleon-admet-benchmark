# Auditing ADMET foundation-model claims: research manuscript

This directory contains the 12-page English LNCS research manuscript, editable
LaTeX, aggregate evidence, and audit/revision plans dated 2026-11-05.

**Status: exploratory research under inherited source labels.** Source/label
gaps remain UNVERIFIED/BLOCKED where documented. Waiving the wait for an
independent reviewer did not confer independent approval.

## Read the current work

- [Research manuscript (PDF)](Auditing_ADMET_Final_Research_Manuscript.pdf)
- [Editable LaTeX](paper/main.tex)
- [PAKDD assessment and submission-policy limitations](PAKDD_ASSESSMENT.md)
- [Claim-to-artifact mapping](reports/CLAIM_ARTIFACT_MAP.json)
- [Source-file identities](reports/SOURCE_FILE_IDENTITIES.json)
- [Public-source validation](reports/PUBLIC_UPDATE_VALIDATION.json)
- [Paper claim/evidence matrix](audit/PAPER_CLAIM_EVIDENCE_MATRIX.md)
- [Data provenance audit](audit/DATA_PROVENANCE_AUDIT.md)
- [Statistical audit](audit/STATISTICAL_AUDIT.md)
- [Experiment upgrade plan](audit/EXPERIMENT_UPGRADE_PLAN.md)
- [Paper revision plan](audit/PAPER_REVISION_PLAN.md)

The experiment matrix comprises 790 model/trajectory configurations plus nine
historical classical reconstructions. Canonical fixed-weight FP32 inference was
replayed for 682 neural models and 60 candidate states (1,841 prediction roles).
These are local reproducibility checks, not independent external replication.
Raw BF16 deterministic replay remains blocked and its historical outputs were
preserved. New neural statistics use the separately versioned FP32 evaluation.

## Rebuild the paper

Install Python with numpy/pandas and Tectonic, then run:

    .\rebuild_from_bundle.ps1 -Python python -Tectonic tectonic

Or set ADMET_EXPERIMENT_ROOT to this directory's evidence folder,
ADMET_BIB_SOURCE to its paper folder, and TECTONIC_EXE to the compiler path,
then run scripts/build_paper.py. This rebuilds paper tables and the PDF from
aggregate reports; it does not train models or reconstruct member-level data.
The public-source rebuild produced identical page text and generated table
values to the visually inspected local manuscript.

The [source ZIP](ADMET_Manuscript_Public_Source.zip) is a convenience archive
of these files, excluding compiled intermediates and itself.

## Evidence and publication boundaries

Only aggregate per-fit/per-comparison results are distributed here. No new raw
endpoint data, structure/member lists, individual prediction probabilities,
fine-tuned weights, restricted lineage maps, or external candidate datasets are
included. Links to non-distributed local evidence in audit documents are labeled
as such. File identity and data-processing replay do not approve upstream assay
semantics or prove checkpoint training membership. No new external formal
evaluation was performed.

Generative AI assisted restructuring and drafting, beyond grammatical correction.
This is disclosed in the manuscript. The current PAKDD2027 Author's Kit permits
only grammatical correction, so this artifact is not represented as a compliant,
ready-to-submit PAKDD submission. The assessment's 30%/20% figures are subjective,
conditional academic judgments, not calibrated forecasts or admission promises.

This GitHub update is source/aggregate-artifact sharing authorized by the author;
it is not a venue submission, journal publication, or independent scientific
approval. Existing data/model licenses and restrictions remain applicable.
