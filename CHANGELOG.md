# Changelog

All notable changes to `nirs4all-aom` are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/) and Semantic Versioning.

## [Unreleased]

### Planned (post-submission)

- Fill the HPO denominator gap for PLS-TabPFN-HPO and Ridge-TabPFN-HPO
  (see `paper/review/missing_datasets_per_variant.md`).
- External-split / instrument-transfer demonstration.
- Conventional PLS+SNV+SG+derivative baseline.
- `pls4all` parity matrix as data tests in CI (once `pls4all` v1.0
  ships on PyPI).
- Replace the in-tree vendored copy inside `nirs4all/operators/models/
  _aom_nirs/` with a runtime `pip install nirs4all-aom` dependency.

## [0.1.1] — 2026-05-28

### Fixed

- sklearn ≥ 1.6 / 1.8 compatibility: swapped inheritance order to
  `RegressorMixin/ClassifierMixin/TransformerMixin, BaseEstimator` on
  20 production estimator and transformer classes in `aom_nirs/pls/`,
  `aom_nirs/ridge/` and `aom_nirs/fast/`. Under the previous order
  `BaseEstimator.__sklearn_tags__` returned `estimator_type=None` and
  `sklearn.base.is_regressor` / `is_classifier` returned `False` for
  every AOM model.
- Test suite: corrected `benchmarks.pls.*` import paths in
  `tests/pls/test_benchmark_schema.py`, the `parents[2]` runner-path
  lookup in `tests/ridge/test_no_selector_branch_leak.py`, and added
  `pytest.importorskip` guards for optional `nirs4all` imports in
  `tests/pls/test_aom_pls_wrapper.py` and
  `tests/ridge/test_ridge_branch_global.py`. Sklearn-1.8 `_estimator_type`
  attribute assertions replaced with `is_regressor` / `is_classifier`.
- Clean-clone smoke test now reports 571 passed, 26 skipped, 0 failed
  (was 1 collection error + 7 failures before the sweep).

### Changed

- Bumped `matplotlib` floor in the `[bench]` extra from `>=3.7` to
  `>=3.9` (required by `loc="outside ..."` legend positioning used by
  the regenerated paired-RMSEP scatter figure).
- Re-laid out `paper/figures/fig_paired_rmsep_scatter.pdf` with
  `constrained_layout=True` and `figsize=(7.2, 7.4)` so subplot titles
  and x-axis labels no longer collide. New helper
  `paper/review/regen_paired_rmsep_scatter.py` regenerates this figure
  without running the rest of the figure pipeline.

### Packaging

- Synced `aom_nirs.__version__` to `0.1.1` (was lagging at `0.1.0`).
- Slimmed the source distribution to the standard set — package + test
  suite + project metadata. The benchmark result CSVs (~17 MB), paper
  PDFs/sources, rendered docs and examples are no longer bundled in the
  sdist; they remain in the GitHub repository as the reproduction
  artifact (see `REPRODUCTION.md`). The wheel was already package-only.
- Added `.github/workflows/publish-pypi.yml` (PyPI Trusted Publishing via
  OIDC; build + `twine check`, then a publish job gated on the `pypi`
  environment).

### Paper (manuscript revision)

- Added SPORT/PORTO/PROSAC + preprocessing-ensemble citations
  (Engel 2013, Mishra 2020/2021/2022, Roger 2020/2022) to Related Work
  and model-selection-bias citations (Varma-Simon 2006,
  Cawley-Talbot 2010, Bergstra-Bengio 2012) to the Introduction.
- Clarified the cartesian-HPO search space in §3.2
  (norm × smooth × baseline × osc × n_components) and the framing as
  "strong conventional preprocessing search under HPO".
- Promoted the missingness audit and the failure-modes diagnostic to
  the supplement (`table_missingness_audit.tex`,
  `table_failure_modes.tex`). New main-text *Failure modes*
  subsection enumerates datasets where ASLS-AOM trails PLS-HPO and
  the rows that drive the POP-PLS drop.
- Added empirical-determinism note for the AOM-Ridge headline in the
  supplement, with a new `aggregate_ridge_seed_audit.py` script that
  unions the two archived seeds-0/1/2 workspaces, asserts
  cross-workspace agreement, and produces
  `table_ridge_seed_audit.tex` (18 N_cap=32 overlap datasets,
  byte-identical RMSEP across seeds 0/1/2 for both Blender and
  AutoSelect).

## [0.1.0] — 2026-05-17

### Added

- Initial public release. Companion Python implementation of the
  paper *"Operator-adaptive PLS and Ridge calibration for NIR
  spectroscopy"*.
- `aom_nirs.pls` — AOM-PLS, POP-PLS, AOM-PLS-DA, POP-PLS-DA. Strict
  linear operator bank (identity, Savitzky-Golay, finite difference,
  detrend, Norris-Williams, Whittaker), NIPALS and SIMPLS engines
  (standard / materialized / covariance / adjoint variants), five
  selection policies (global / per-component / soft / superblock /
  none), CV / PRESS / covariance / holdout / hybrid scorers, one-SE
  rule, optional GPU backend via `[torch]` extra. Vendored
  `ExtendedMSC` and `pybaselines`-based `ASLSBaseline` for upstream
  preprocessing.
- `aom_nirs.ridge` — AOM-Ridge family: `AOMRidgeRegressor` (5
  selection policies: superblock, global, active_superblock,
  branch_global, mkl), `AOMRidgeClassifier`, `AOMRidgeBlender` (convex
  non-negative blend of OOF predictions via SLSQP), `AOMRidgeAutoSelector`
  (outer-CV variant selector), `AOMRidgePLS` / `AOMRidgePLSCV` (Ridge
  on PLS scores), `AOMMultiKernelRidge` (per-block kernels),
  `AOMMultiBranchMKL` (MKL across SNV/MSC/ASLS branches),
  `AOMLocalRidge` (KNN local weighting). Vendored SPXY-based K-fold
  splitter at `ridge/_spxy.py`.
- `aom_nirs.fast` — FastAOM chain-screening framework: nonlinear bases
  (raw, absorbance, SNV, MSC, EMSC, ASLS, OSC, Whittaker), typed
  `ChainGrammar` for valid operator sequences, deterministic DFS chain
  generator, adjoint-only fast covariance screening with diversity-aware
  top-k filtering, truncated-SVD low-rank kernel evaluator, four
  sklearn-style models (`SingleChainPLSRidge`, `HardAOMChainPLSRidge`,
  `SoftAOMChainPLSRidge`, `SparseMultiKernelRidge`) plus the
  `FastAOMPLSRidge` orchestrator.
- Optional `[tabpfn]` extra exposes the experimental TabPFN-residual
  stacker (`aom_nirs/ridge/residual_tabpfn.py`) and its AutoSelector
  candidate (`aom_nirs/ridge/tabpfn_candidate.py`). These are not part
  of the paper headline.
- `paper/` directory carries the full manuscript and supplement:
  `main.tex`, `supplement.tex`, `references.bib`, `build.sh`,
  pre-built `main.pdf` + `supplement.pdf`, 22 figures, 21 tables, and
  the complete review dossier at `paper/review/` (final_stats.md,
  v3_stats.md, classification_stats.md, missing_datasets_per_variant.md,
  cohort_manifest.csv, failure_mode_table.csv, plus
  `aom_code_inventory.md`, `aom_lib_migration_plan.md`,
  `pls4all_integration_eval.md`, `paper_review.md`).
- `benchmarks/` carries cohort runners for all three families plus the
  paper-tied result outputs under `benchmarks/runs/{pls,ridge,fast,
  scenarios}/`. Total 16 MB of paper-tied result CSVs.
- `_archive/` preserves historical material: deprecated `nirs4all`
  wrappers snapshot, pre-paper draft scripts, multi-language port
  (`aompls` C++/R/Julia/MATLAB/JS), legacy AOM_v0 benchmark
  iterations, Multi-kernel / multiview side projects (future work),
  and the 1.3 GB DuckDB workspace cache (excluded from git).
- Tests: 35+ tests across `tests/pls/`, `tests/ridge/`, `tests/fast/`.
- Documentation: `docs/architecture.md`, `docs/math.md`,
  `docs/benchmark_protocol.md`, `docs/reproducibility.md`.
- Examples: `examples/01_aom_pls_quickstart.py`,
  `02_aom_ridge_blender.py`, `03_fastaom_quickstart.py`,
  `paper_smoke.py`.

### Migration notes

- Code formerly at `nirs4all/bench/AOM_v0/{aompls,Ridge/aomridge,
  FastAOM}/`. The original locations are now empty in `nirs4all`.
- The paper formerly at `nirs4all/paper_aom/` now lives at
  `aom_nirs/paper/`. A `paper_aom/README.md` breadcrumb at the old
  location points here.
- `nirs4all` retains thin wrapper modules at
  `nirs4all/operators/models/sklearn/{aom_pls, aom_pls_classifier,
  pop_pls, pop_pls_classifier, aom_ridge, aom_fast}.py` that
  re-export from a vendored copy of `aom_nirs` at
  `nirs4all/operators/models/_aom_nirs/`. Mid-term plan: replace the
  vendored copy with a runtime `nirs4all-aom` dependency once this
  package is on PyPI.
- API changes vs the previous `nirs4all` pure-Python `AOMPLSRegressor`:
  `gate='sparsemax'`, `FFTBandpassOperator`, `WaveletProjectionOperator`,
  the `tau` / `n_orth` / `operator_index` / `prefix` arguments, and
  the in-fit torch dispatch are dropped. None of those features are
  part of the paper. The torch backend now lives at
  `aom_nirs/pls/torch_backend.py` and is selected via the `backend`
  argument.
