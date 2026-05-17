# `_archive/` — material removed from the active code release

This directory holds historical artifacts that are not part of `aom-nirs`'s
public API or the paper's reproducibility bundle. They live in the repo for
audit and future reference. Nothing here is imported by `aom_nirs/`.

| Subfolder | Origin | Why archived | Verdict from inventory |
| --- | --- | --- | --- |
| `deprecated_nirs4all/` | `nirs4all/operators/models/sklearn/{aom_pls,aom_pls_classifier,pop_pls,pop_pls_classifier}.py` + `pytorch/aom_pls.py`, snapshot taken before vendoring | Snapshot of the previous library implementations; the production paths now re-export the vendored `aom_nirs` canonical classes from `nirs4all/operators/models/_aom_nirs/`. Kept here for diff comparison. | KEEP-AS-SNAPSHOT |
| `pre_paper_drafts/` | `bench/AOM/*.py`, `bench/AOM/*.md`, `bench/AOM/run.log` | Pre-paper draft scripts (`darts_pls.py`, `moe_pls.py`, `zero_shot_router*.py`, `pseudo_linear*.py`, `enhanced_aom.py`, `quick_test.py`, `test_snv_jacobian.py`, `run_comparison.py`, `update_models.py`). Never used in the Talanta benchmark cohort. | TRASH (kept for traceability) |
| `multi_lang/AOM_lib/` | `bench/AOM_lib/` (40 MB) | Earlier multi-language port (cpp/r/julia/matlab/js/python/scripts) of the AOM library. Superseded by (a) `aom-nirs` for Python and (b) the standalone `GBeurier/aompls` GitHub repo for the multi-language stack. Kept here so the Python reference can be cross-checked against the multi-lang artifact if questions arise. | ARCHIVE |
| `trashed_runs/AOM_v0_legacy/` | Everything under the old `bench/AOM_v0/` that was not paper-tied: legacy benchmark_runs (smoke, smoke6, smoke_cv5, v5a_smoke_alpine, v5b_*, iter1..iter12, diverse_iter2/3_*, da001/002/003/009_*, classification_all17, cls_smoke, curated, curated_v2, final_curated, all53_top5_fast_parallel, all54, all54_combined, all54_top5_fast), the bench Ridge `publication/` draft (internal AOM-Ridge paper superseded by the Talanta submission), the bench `docs/`, `source_materials/`, `rf_model_leaves/`, and the bench-level `Prompt.md` / `README.md` / `Summary.md`. | TRASH / ARCHIVE |
| `future_work/Multi-kernel/` | `bench/AOM_v0/Multi-kernel/` (33 MB) — MKR (Multi-Kernel Ridge), Blup (per-block BLUP), MkM (probabilistic REML mixed model). | Out of scope for the Talanta paper. MKR is methodologically related and has 56-dataset Blender results (median rel-RMSEP 0.918), but reporting it as a separate paper is cleaner than bundling. Blup/MkM benchmarks are incomplete. | FUTURE |
| `future_work/multiview/` | `bench/AOM_v0/multiview/` (1.3 MB) — block-sparse, lazy-POP, MoE on preprocessing operators. | Promising on specific datasets (Beer, Chla+b) but not generalizable yet; smoke-4 only. Separate paper on adaptive operator selection. | FUTURE |

## Paper-tied benchmark outputs

Not in `_archive/`. The paper-tied runs live under
`aom_nirs/benchmarks/runs/{pls,ridge}/`:

- `pls/paper_aom_aompls_da_seeds012/` (AOM-PLS-DA seeds 0/1/2, N=13)
- `ridge/paper_aom_aomridge_seeds012/` (AOM-Ridge top-5 seeds 0/1/2)
- `ridge/paper_aom_aomridge_cls_seeds012/` (AOM-Ridge classification seeds)
- `ridge/all54_headline/` (AOM-Ridge regression headline, single-seed; **seeds 1/2 to be added per `paper/review/talanta_review.md` weakness #2**)
- `ridge/<cohort>.csv` (paper cohort manifests: all53/all54/all57/curated/diverse/N_woOutlier)

The PLS multi-seed runs and HPO baselines referenced by
`paper/review/final_stats.md` (paper_aom_aompls_seed[0-2],
paper_aom_aompls_seeds012, paper_aom_linear_hpo_full_cartesian_*) are still
in the original `nirs4all/bench/scenarios/runs/` location because they are
too heavy to bundle with the source repo. The paper's reproducibility
section documents the paths.

## Workspace cache (not migrated)

The 1.3 GB DuckDB workspace under `nirs4all/bench/AOM/workspace/` (cache of
the pre-paper draft runs in `pre_paper_drafts/`) was deliberately left in
place. It is not part of the paper and is too large to commit; delete it
when no longer needed for inspection.
