# AOM code inventory — paper-tied scope

**Generated:** 2026-05-17.
**Scope:** AOM-PLS (`bench/AOM_v0/aompls/`), AOM-Ridge (`bench/AOM_v0/Ridge/aomridge/`), FastAOM (`bench/AOM_v0/FastAOM/`), and the current AOM surface inside the `nirs4all` library. Multi-kernel siblings (MKR/Blup/MkM) and `multiview/` are not paper-tied and are listed only in the triage section as ARCHIVE / FUTURE; they are out of scope for the Talanta migration.
**Companion docs:** `aom_lib_migration_plan.md` (what moves where, three repo options, reproducibility checklist), `pls4all_integration_eval.md` (cost of hosting AOM methods in pls4all directly).
**Authoritative score source:** `paper_aom/review/final_stats.md` + `v3_stats.md`. All numbers below come from those files unless noted.

---

## 1. Executive summary

The AOM codebase contains four production-grade Python packages plus a number of exploratory side-projects. The paper-tied core is small and clean:

- `bench/AOM_v0/aompls/` — 18 .py files, AOM-PLS + POP-PLS + operator bank, ~5.6 kLOC, well tested.
- `bench/AOM_v0/Ridge/aomridge/` — 23 .py files, AOM-Ridge family (Global / Blender / AutoSelect / LocalRidge / MultiBranchMKL / RidgePLS), ~8.8 kLOC, 23 dedicated test files (~6.4 kLOC).
- `bench/AOM_v0/FastAOM/` — 11 .py files, fast operator-chain screening with low-rank kernels, ~5.2 kLOC, 7 test modules.
- `nirs4all/operators/models/sklearn/{aom_pls,aom_pls_classifier,aom_pls_aomlib,pop_pls,pop_pls_classifier}.py` + `pytorch/aom_pls.py` — already in the library, but partially independent of the bench packages and missing AOM-Ridge entirely.

The Talanta paper rests on **eight headline variants** all derivable from these packages. AOM-Ridge Blender is the single best empirical result (median RMSEP ratio 0.918 vs Ridge-default, $p_{\mathrm{Holm}} = 2.6\times 10^{-4}$, 27/32 wins) and AOM-PLS simple variants are the strongest legibility/speed story (1.18-1.63 s/dataset vs 710-1584 s for HPO baselines). Several Ridge family members (LocalRidge KNN50, MultiBranchMKL shrink03, RidgePLS Hmax variants) score worse than baseline and should be downgraded from the migration.

The single largest hygiene issue is **benchmark-run sprawl**: `bench/AOM_v0/Ridge/benchmark_runs/` alone contains 30+ subdirectories of which only 2 are paper-headline. The rest are exploration iterations that should be archived/deleted before any code-release. There is no functional-code blocker — every paper-tied module is testable and self-contained — but the headline AOM-Ridge run is currently single-seed, which the Talanta review flagged as a release blocker.

---

## 2. Code territories overview

| Territory | Path | Role | Touched by paper |
| --- | --- | --- | --- |
| AOM-PLS package | `bench/AOM_v0/aompls/` | Operators, banks, NIPALS/SIMPLS engines, AOM/POP selection, classification | Yes (core) |
| AOM-Ridge package | `bench/AOM_v0/Ridge/aomridge/` | Dual/kernel Ridge with operator-mixture; selectors and ensembles | Yes (best empirical result) |
| FastAOM | `bench/AOM_v0/FastAOM/` | Fast chain screening + low-rank kernels + Ridge | Yes (supplement, v3 stats) |
| Benchmark runners | `bench/AOM_v0/{aompls,Ridge,FastAOM}/benchmarks/` | Cohort runners, paired-stats scripts | Yes (reproducibility) |
| Benchmark outputs | `bench/AOM_v0/*/benchmark_runs/` | CSVs and logs per cohort/iteration | Partial (only `paper_aom_*_seeds012` cited) |
| Library surface | `nirs4all/operators/models/sklearn/aom_*` and `pop_*` | Public sklearn-style classes | Yes (production users) |
| pls4all (C++) | `/home/delete/nirs4all/pls4all/` | C++ engine with bindings; Phase-6 AOM/POP shipped, Python wheel not yet on PyPI | Indirect (parity reference) |
| Side projects (out of scope) | `bench/AOM_v0/Multi-kernel/{MKR,Blup,MkM}`, `bench/AOM_v0/multiview/`, `bench/AOM_v0/AOM/`, `bench/AOM_lib/` | Multi-kernel / probabilistic / multiview / multi-language explorations | No (or only ablation) |

---

## 3. AOM-PLS package (`bench/AOM_v0/aompls/`)

Public version 0.1.0. The `__init__.py` exports operators, banks, and lazily imports `AOMPLSRegressor`, `POPPLSRegressor`, `AOMPLSDAClassifier`, `POPPLSDAClassifier`. The package is self-contained and clearly labeled as independent from production `nirs4all`.

### 3.1 Per-file roles and migration verdict

| File | Lines (~) | Role | Migration verdict |
| --- | ---: | --- | --- |
| `__init__.py` | 43 | Public API, lazy imports | KEEP |
| `operators.py` | * | Linear operator protocol; Identity, SG, FD, Detrend, Norris-Williams, Whittaker, Composed, ExplicitMatrix; covariance / adjoint plumbing | KEEP (core math) |
| `banks.py` | * | `compact_bank` (9-op paper bank), `default_bank` (100-op), `extended_bank`, `bank_by_name` | KEEP (paper §3.4 compact-bank) |
| `nipals.py` | * | NIPALS engines (standard, materialized, adjoint, per-component) | KEEP (engine) |
| `simpls.py` | * | SIMPLS engines (standard, materialized, covariance, superblock) | KEEP (engine) |
| `selection.py` | * | Five policies: global AOM, per-component POP, soft mixture, superblock, none | KEEP (selection core) |
| `scorers.py` | * | Criterion configs: covariance, CV, holdout, approx-PRESS, one-SE rule, repeated CV | KEEP |
| `estimators.py` | * | `AOMPLSRegressor`, `POPPLSRegressor`, `_AOMPLSBase` sklearn estimators | KEEP — but POP downgraded to ablation (see §8) |
| `classification.py` | * | `AOMPLSDAClassifier`, `POPPLSDAClassifier` with class-balanced encoding + logistic / softmax calibration | KEEP (paper classification result) |
| `preprocessing.py` | * | SNV, MSC, OSC, ExtendedMSC, ASLSBaseline (non-linear pre-fits, fold-local) | KEEP (paper §3.4 ASLS-AOM uses this) |
| `centering.py` | * | `StandardScaler`, `center_xy` | KEEP |
| `diagnostics.py` | * | `RunDiagnostics` dataclass + helpers | KEEP |
| `metrics.py` | * | r2, rmse, mae, balanced_accuracy, macro_f1, log_loss, brier_score_binary | KEEP — DEDUPE against `aompls.metrics` and `nirs4all.utils` before merge |
| `operator_explorer.py` | * | Beam search composition + similarity pruning | KEEP (exploration feature, mentioned in supplement) |
| `operator_generation.py` | * | Primitive operator grids + canonicalisation + grammar | KEEP (used by explorer and FastAOM) |
| `operator_similarity.py` | * | Probe-based & response-based cosine diversity | KEEP |
| `synthetic.py` | * | Synthetic spectra for tests/microbenchmarks | KEEP (tests) |
| `torch_backend.py` | * | Optional GPU NIPALS/SIMPLS/superblock via torch | KEEP (optional, gated by `torch_available()`) |

`*` line counts are agent estimates and need verification at merge time; the per-file recommendations do not depend on the precise line count.

### 3.2 Variants exposed by aompls/ (paper-tied)

- **AOM-PLS simple** — `AOMPLSRegressor(bank='compact', selection='global', criterion='cv', cv=5)`. Reported in `table_main_results.tex` as `AOM-PLS (simple)` → ratio 0.991 vs PLS-default (22/32 wins; $p_{\mathrm{Holm}}=0.896$).
- **AOM-PLS best (= ASLS-AOM compact CV5)** — same estimator preceded by `ASLSBaseline()`. Reported as `AOM-PLS (best)` → ratio 0.985 vs PLS-default. Reference variant in `final_stats.md`.
- **AOM-PLS-DA** — `AOMPLSDAClassifier` global, NIPALS-adjoint and SIMPLS-covariance engines, used in `paper_aom_aompls_da_seeds012`.
- **POP-PLS / POP-PLS-DA** — per-component variants. `table_aompls_family.tex` reports median ratio 1.373 (POP-nipals, 34/165 wins) and 1.385 (POP-simpls, 33/165 wins) vs PLS-default; this is a **negative ablation**, not a contribution. Keep code, downgrade narrative.

### 3.3 Test coverage (`bench/AOM_v0/tests/`)

- `test_estimators.py`, `test_classification.py`, `test_nipals.py`, `test_simpls.py`, `test_selection.py`, `test_operators.py`, `test_active_superblock.py`, `test_explorer.py`, `test_fck_operator.py`, `test_parity_with_production.py`, `test_torch_parity.py`, `test_benchmark_schema.py`.
- Synthetic fixtures only — no hard-coded dataset paths.
- `test_parity_with_production.py` cross-checks bench → `nirs4all` equivalents.

### 3.4 Internal and external dependencies

- Internal: tightly coupled (`operators.py` → `banks.py` → `selection.py` → `estimators.py`); no leaks outside the package.
- External: `numpy`, `scipy.linalg`, `scikit-learn` (BaseEstimator, clone, KFold, LogisticRegression). `torch` is optional. `preprocessing.py` references `nirs4all.operators.transforms.nirs` for `ExtendedMSC`/`ASLSBaseline`; this is a circular dep risk when merging back into `nirs4all` and must be resolved at migration time (move those two transforms to `aompls.preprocessing` or vice-versa).

---

## 4. AOM-Ridge package (`bench/AOM_v0/Ridge/aomridge/`)

Public version exposes ten classes via lazy `__getattr__`: `AOMRidgeRegressor`, `AOMRidgeClassifier`, `AOMMultiKernelRidge`, `AOMKernelizer`, `AOMRidgePLS`, `AOMRidgePLSCV`, `AOMRidgeAutoSelector`, `AOMRidgeBlender`, `AOMMultiBranchMKL`, `AOMLocalRidge`. Approx. 8.8 kLOC across 23 .py files; the dedicated test suite is ~6.4 kLOC across 23 test files.

### 4.1 Per-file roles and migration verdict

| File | LOC (agent) | Role | Migration verdict |
| --- | ---: | --- | --- |
| `estimators.py` | 926 | Primary AOM-Ridge regressor; selection ∈ {superblock, global, active_superblock, branch_global, mkl} | KEEP |
| `classification.py` | 436 | `AOMRidgeClassifier` with logistic calibration | KEEP (paper §6) |
| `aom_ridge_pls.py` | 885 | `AOMRidgePLS`, `AOMRidgePLSCV` — Ridge on PLS scores | KEEP — partial: only `colscale-cv-relative` variant is paper-tied; `Hmax-relative-emsc2` scored 1.981 (TRASH) |
| `auto_selector.py` | 634 | Outer-CV variant selector over ~15 candidates | KEEP (paper Blender's selector input) |
| `blender.py` | 440 | Convex non-negative blender (SLSQP) of variant OOFs | KEEP — **best paper result** (ratio 0.918 vs Ridge-default, $p_{\mathrm{Holm}}=2.6\mathrm{e}{-04}$) |
| `mkr_estimator.py` | 453 | Multi-kernel Ridge — per-block kernels | KEEP-AS-ABLATION |
| `multi_branch_mkl.py` | 714 | MKL across branches (SNV/MSC/ASLS/EMSC2); soft branch weights by KTA | KEEP-AS-ABLATION — `shrink03` headline variant scored 3.599 in `seeds012`, ARCHIVE that specific config |
| `local_ridge.py` | 702 | KNN-weighted local Ridge in branch score space | KEEP-AS-ABLATION — KNN50 scored ratio 1.212, $p_{\mathrm{Holm}}=1.0$, 4/23 wins (paper's "doesn't always win" example) |
| `kernels.py` | 251 | Fold-local kernel matrices, operator-bank kernels | KEEP |
| `kernelizer.py` | 335 | Kernel diagnostics (alignment, block stats) | KEEP |
| `solvers.py` | 189 | Cholesky/eigh dual-Ridge solver with jitter fallback | KEEP |
| `selection.py` | 1042 | CV selection policies (fold-local α, operator screening, branch selection) | KEEP — 1k lines of leakage prevention; review carefully before merge |
| `mkl.py` | 184 | MKL weights via kernel-target alignment + simplex projection | KEEP |
| `weights.py` | 372 | `WeightLearningResult` dataclass and helpers | KEEP |
| `branches.py` | 189 | SNV/MSC/ASLS branch preprocessing (fold-local) | KEEP |
| `preprocessing.py` | 70 | Centering / RMS block scaling | KEEP |
| `split_aware_cv.py` | 273 | YBlockedKFold, RepeatedSPXYFold | KEEP |
| `cv.py` | 107 | Wrapper around `nirs4all.operators.splitters.SPXYFold` | KEEP — review the import direction at merge time |
| `residual_tabpfn.py` | 317 | TabPFN residual stacker | ARCHIVE — never reached headline but `bench/AOM_v0/Ridge/benchmarks/run_aomridge_benchmark.py:848` imports it, so it cannot be deleted without refactoring the runner. Either gate behind optional `tabpfn` extra or strip from runner before release. |
| `tabpfn_candidate.py` | 167 | TabPFN candidate spec for AutoSelector | ARCHIVE — reachable indirectly from `run_aomridge_benchmark.py:783-786` via `auto_selector._default_headline_with_tabpfn_candidates` (factory imports at `auto_selector.py:327`). Same gating decision as `residual_tabpfn.py`. |
| `guards.py` | 75 | Input validation | KEEP |
| `__init__.py` | 46 | Lazy public API | KEEP — TabPFN entries are not in `__all__`, fine as-is |

### 4.2 Variants exposed (paper-tied) and their scores

Source: `table_aomridge_family.tex`, `final_stats.md`.

| Variant key | Family | $N$ | Median RMSEP | Median fit (s) | Verdict |
| --- | --- | ---: | ---: | ---: | --- |
| `AOMRidge-global-compact-none` | Global | 53 | 0.359 | 21.60 | KEEP (paper "simple") |
| `AOMRidge-global-compact-none-asls` | Global + ASLS | 53 | 0.382 | 24.35 | KEEP-AS-ABLATION |
| `AOMRidge-global-compact-none-snv` | Global + SNV | 53 | 0.389 | 18.23 | KEEP-AS-ABLATION |
| `AOM-PLS-compact-CV` | Ridge-PLS hybrid | 53 | 0.414 | 1.94 | KEEP (paper-PLS path) |
| `AOMRidgePLS-compact-colscale-cv-relative` | RidgePLS | 53 | 0.414 | 33.41 | KEEP-AS-ABLATION |
| `AOMRidge-Blender-headline-spxy3` | Blender | 53 | 0.471 | 960.1 | KEEP (paper "best") |
| `AOMRidge-global-compact-none-msc` | Global + MSC | 53 | 0.483 | 25.90 | KEEP-AS-ABLATION |
| `AOMRidge-AutoSelect-headline-spxy3` | AutoSelector | 53 | 0.520 | 646.2 | KEEP-AS-ABLATION |
| `Ridge-raw` | Baseline | 53 | 0.537 | 1.01 | KEEP (baseline) |
| `AOMRidge-global-compact-none-split_aware` (seeds012) | Global + split-aware CV | 25 | 0.371 | 24.68 | KEEP (multi-seed evidence) |
| `AOMRidge-Local-compact-cv-blended` (seeds012) | LocalRidge + blend | 25 | 0.484 | 4.19 | KEEP-AS-ABLATION |
| `AOMRidge-Local-compact-knn50` (seeds012) | LocalRidge | 25 | 0.523 | 3.19 | KEEP-AS-ABLATION (failure-mode example) |
| `AOMRidgePLS-compact-Hmax-relative-emsc2` | RidgePLS Hmax | 53 | 1.981 (median RMSEP) | 29.96 | TRASH |
| `AOMRidge-MultiBranchMKL-compact-shrink03` (seeds012) | MultiBranchMKL | 25 | 3.599 (median RMSEP, ~6× Ridge-raw 0.571) | 101.2 | TRASH (this config) |

Paired Wilcoxon Holm-corrected p-values (from `final_stats.md`):

- AOM-Ridge (best=Blender) vs Ridge-default — ratio 0.918, 27/32 wins, $p_{\mathrm{Holm}}=2.6\mathrm{e}{-04}$
- AOM-Ridge (best=Blender) vs Ridge-HPO — ratio 0.966, 25/32 wins, $p_{\mathrm{Holm}}=0.033$
- AOM-Ridge (simple=global) vs Ridge-default — ratio 0.974, 25/32 wins, $p_{\mathrm{Holm}}=0.007$
- AOMRidge-Local-knn50 vs Ridge-HPO — ratio 1.212, 4/23 wins, $p_{\mathrm{Holm}}=1.0$ (negative, on purpose)

### 4.3 External dependencies

- Imports `aompls.operators.*`, `aompls.estimators.AOMPLSRegressor`, `aompls.preprocessing`, `aompls.metrics.balanced_accuracy` — so `aomridge` cannot ship without `aompls`. Either keep the dependency at install time (`pip install aom-pls aom-ridge`) or merge both into a single package (`aom-nirs`).
- Imports `nirs4all.operators.splitters.SPXYFold` — a "production-to-bench" dependency; will reverse at merge time.
- Optional `tabpfn` import for `residual_tabpfn.py` / `tabpfn_candidate.py`; both are flagged for removal.

### 4.4 Tests

23 dedicated test files cover: solvers (Cholesky/eigh/jitter fallback), kernel-equivalence vs explicit-concat Ridge, CV no-leakage (fold-local centering), branch-global anti-leakage, one-SE rule + RepeatedSPXYFold, MKL-light (KTA), RidgePLS vs RidgePLSCV, round3 fixes, selection (active-superblock, global, operator screening), classifier with logistic calibration, AutoSelector outer-CV, Blender SLSQP / weight constraints, LocalRidge KNN, MultiBranchMKL shrinkage, anti-leakage branch+selector invariant, MKR estimator + kernelizer + weights + leakage, YBlockedKFold/RepeatedSPXYFold. Strong coverage; no hard-coded paths.

### 4.5 Internal "publication" folder

`bench/AOM_v0/Ridge/publication/manuscript/aomridge_paper.pdf` (78.5 kLOC `.tex`) is a **draft internal Ridge-only paper**. Source of truth for the Talanta submission is `paper_aom/`. The internal draft should be archived or marked deprecated to avoid confusion at code release.

---

## 5. FastAOM (`bench/AOM_v0/FastAOM/`)

Sibling of `aompls/`; reuses operator/grammar/banks infrastructure and adds (a) nonlinear bases (raw, SNV, MSC, EMSC, ASLS, OSC, Whittaker), (b) typed grammar over chains up to depth 4, (c) adjoint-only fast covariance screening with diversity, (d) low-rank kernel-vector evaluator, (e) four AOM-style sklearn models on screened banks.

### 5.1 Per-file roles

| File | Role | Verdict |
| --- | --- | --- |
| `bases.py` | Nonlinear base transforms (`B_j(X)`); fixes ASLS O(n³) bug from latest commit | KEEP |
| `operator_chain.py` | `OperatorChain` wrapper around `aompls.ComposedOperator` with simplification | KEEP |
| `grammar.py` | Typed `ChainGrammar` (baseline → scatter → smoothing → derivative → projection) | KEEP |
| `chain_generator.py` | Deterministic DFS chain enumeration | KEEP |
| `lowrank.py` | Truncated SVD per base → low-rank kernel approximation | KEEP |
| `screening.py` | Adjoint-only covariance scoring + diversity top-k (per-family / per-base caps) | KEEP |
| `xcorr_fast.py` | FFT-accelerated cross-correlation kernel | KEEP — but `aompls._xcorr_zero_pad` Python loop is still the bottleneck (~300 calls/chain on large p; vectorise before release) |
| `models/*` | `SingleChainPLSRidge`, `HardAOMChainPLSRidge`, `SoftAOMChainPLSRidge`, `SparseMultiKernelRidge`, `FastAOMConfig`, `FastAOMPLSRidge` orchestrator | KEEP |
| `tests/*` | 7 test modules, all green | KEEP |

The full `__all__` (per `bench/AOM_v0/FastAOM/__init__.py:81`) exports operator-chain helpers, all bases (Raw/Absorbance/SNV/MSC/EMSC/ASLS/OSC/SNVOSC/Whittaker + `build_base_bank`), grammar (`ChainGrammar`, `default_grammar`), generation (`generate_chains`, `ChainGenerationConfig`), screening (`ScreeningCandidate`, `fast_covariance_screen`, `diversity_topk`), low-rank helpers (`LowRankBase`, `fit_lowrank_bases`), and the five model classes plus `FastAOMConfig`. Migration must preserve this full public surface, not only the headline model classes.

### 5.2 Variants and scores

From `v3_stats.md`/`table_fastaom_variants.tex` (N≥50 filter):

| Variant | $N$ | Median rel. RMSEP | Median fit (s) | Wins | Verdict |
| --- | ---: | ---: | ---: | ---: | --- |
| `FastAOM-sparse-mkr-supervised` | 50 | 1.009 | 87.77 | 10 | KEEP (headline FastAOM) |
| `FastAOM-sparse-mkr-compact` | 50 | 1.022 | 2.48 | 3 | KEEP (speed champion) |
| `FastAOM-single-chain-compact` | 52 | 1.052 | 1.86 | 2 | KEEP-AS-ABLATION |
| `FastAOM-single-chain-compact-cv5-numpy` | 52 | 1.052 | 2.02 | 0 | KEEP-AS-ABLATION |
| `FastAOM-soft-chain-compact` | 52 | 1.062 | 3.05 | 1 | KEEP-AS-ABLATION |
| `FastAOM-hard-chain-osc` | 52 | 1.078 | 2.68 | 0 | KEEP-AS-ABLATION |
| `FastAOM-hard-chain-supervised` | 52 | 1.084 | 121.87 | 4 | KEEP-AS-ABLATION |
| `FastAOM-hard-chain-asls` | 52 | 1.105 | 174.46 | 3 | KEEP-AS-ABLATION |
| `FastAOM-hard-chain-multibase` | 52 | 1.109 | 5.62 | 0 | KEEP-AS-ABLATION |
| `FastAOM-hard-chain-compact` | 52 | 1.128 | 2.88 | 3 | KEEP-AS-ABLATION |
| `FastAOM-single-chain-supervised-cv5-numpy` | 52 | 1.208 | 119.19 | 2 | TRASH (worse than PLS-default) |
| `FastAOM-hard-chain-compact-d4` | 1 | 1.256 | 38.08 | 0 | TRASH (single-dataset) |

Friedman common-subset (N=50, 6 methods): ASLS-AOM (2.74) < FastAOM-sparse-mkr-supervised (3.08) < FastAOM-sparse-mkr-compact (3.18) < AOM-compact (3.44) < FastAOM-single-chain (4.20) < PLS-standard (4.36). FastAOM sparse-MKR variants are statistically competitive with the AOM-PLS headline and faster.

### 5.3 Known limitations (from `IMPLEMENTATION_NOTES.md`)

- Fixed `n_components` (no CV like aompls).
- Python `_xcorr_zero_pad` is the dominant cost on the 100-op bank.
- Dense detrend O(p²) RAM at large p.
- `SparseMultiKernelRidge` NNLS path needs the blacklist mechanism (already shipped) to avoid infinite loops on degenerate banks.

These do not block migration but should appear as known limitations in the library README.

---

## 6. Current AOM surface in the `nirs4all` library

### 6.1 `nirs4all/operators/models/sklearn/aom_pls.py` (~1.6 kLOC)

Pure-Python NIPALS implementation. Exports `AOMPLSRegressor` and eight `LinearOperator` subclasses (Identity, SavitzkyGolay, DetrendProjection, ComposedOperator, NorrisWilliams, FiniteDifference, WaveletProjection, FFTBandpass). Independent of `bench/AOM_v0/aompls`. Default bank ~38 operators; gating modes `hard` (argmax per fit) and `sparsemax` (soft mixture). Holdout-based prefix selection — **no built-in CV** beyond what the caller passes in. Optional torch backend for SG conv1d.

Tests: `tests/unit/operators/models/test_aom_pls.py` (30+ tests).

### 6.2 `aom_pls_classifier.py` (~200 LOC)

`AOMPLSClassifier` wraps `AOMPLSRegressor` for PLS-DA. One-hot for multiclass, label-encode for binary; argmax + softmax calibration.

### 6.3 `aom_pls_aomlib.py` (~315 LOC)

Thin sklearn wrapper around the C++/Eigen `aompls.AOMPLSCompact` backend from `bench/AOM_lib/python/src`. Lazy-imports `aompls`; raises a clean `ImportError` otherwise. Parameters map to `cv_mode ∈ {cv, kfold, spxy, holdout, external}` and `preprocessing ∈ {none, asls, snv, osc, snv+osc, asls+osc}`. Supports the one-SE rule. PLS1 only. Exports diagnostics (`n_components_selected_`, `selected_operator_sequence_`, `selected_operator_scores_`).

### 6.4 `pytorch/aom_pls.py` (~370 LOC)

GPU backend for the pure-Python `AOMPLSRegressor`. Mirrors the NumPy path; batched conv1d for SG adjoints; CUDA auto-detect with CPU fallback.

### 6.5 `pop_pls.py` (~1.1 kLOC) and `pop_pls_classifier.py`

`POPPLSRegressor` selects a different operator per component. Built-in PRESS-based selection (no external validation needed). Auto-tunes n_orth ∈ [0..5]. Imports operator classes from `aom_pls.py`. Score evidence from `table_aompls_family.tex`: median ratio 1.373-1.385 vs PLS-default — **negative ablation**.

### 6.6 Gap analysis

| Paper variant | Current lib coverage | Gap |
| --- | --- | --- |
| AOM-PLS simple | `AOMPLSRegressor` (lib) + `AOMPLSAomlibRegressor` (C++ wrapper) | Lib uses 38-op default vs paper's 9-op compact; lib has no built-in CV folds (holdout only). C++ wrapper is paper-faithful. |
| ASLS-AOM compact CV5 | `AOMPLSAomlibRegressor(preprocessing='asls', cv_mode='kfold', folds=5, one_se=True)` | Functional via C++ wrapper. Pure-Python lib path needs `ASLSBaseline` upstream + fold-CV plumbing. |
| AOM-PLS-DA | not in lib | Need to port `bench/AOM_v0/aompls/classification.py`. |
| POP-PLS | `POPPLSRegressor` | Present but downgrade narrative (negative ablation). |
| AOM-Ridge family | **not in lib** | Entire `aomridge/` package needs migration. |
| FastAOM | not in lib | Add as opt-in `FastAOM*` classes. |

### 6.7 Co-existence problems to fix at migration

- Three distinct AOM-PLS implementations co-exist: `nirs4all/.../aom_pls.py` (pure-Python NIPALS, 38-op bank, sparsemax), `nirs4all/.../aom_pls_aomlib.py` (C++ wrapper, paper-faithful), `bench/AOM_v0/aompls/estimators.py` (newest, paper-grade NumPy with both NIPALS and SIMPLS engines). The paper's `nirs4all-AOM-PLS-default` row uses the second wrapper. Long-term, the bench `aompls/estimators.py` is the cleanest and should become the in-lib default; the others must be reconciled (rename, deprecate, or remove). See migration plan for the decision matrix.
- `aompls.preprocessing.{ExtendedMSC,ASLSBaseline}` import `nirs4all.operators.transforms.nirs`. After migration the dependency reverses; trivial change of import path but it must happen in one commit.

---

## 7. Benchmark-runs triage

Source: agent walk of `bench/AOM_v0/{aompls,Ridge,FastAOM}/benchmark_runs/` plus `paper_aom/review/missing_datasets_per_variant.md` workspace paths.

### 7.1 Paper-tied (KEEP — needed for reproducibility)

| Path | Used for | Notes |
| --- | --- | --- |
| `bench/AOM_v0/benchmark_runs/paper_aom_aompls_da_seeds012/` | AOM-PLS-DA seeds 0/1/2, N=13 datasets | Cited in `final_stats.md` (`aom_pls_da_seeds012`, 240 rows) |
| `bench/scenarios/runs/paper_aom_aompls_seeds012/` | AOM-PLS seeds 0/1/2 | Cited as `aom_pls_seeds012` (1485 rows) in `final_stats.md` |
| `bench/AOM_v0/Ridge/benchmark_runs/paper_aom_aomridge_seeds012/` | AOM-Ridge top-5 seeds 0/1/2 | `aom_ridge_top5_seeds012` (376 rows) |
| `bench/AOM_v0/Ridge/benchmark_runs/paper_aom_aomridge_cls_seeds012/` | AOM-Ridge classification seeds | `aom_ridge_cls_seeds012` (210 rows) |
| `bench/AOM_v0/Ridge/benchmark_runs/all54_headline/` | AOM-Ridge regression headline (single-seed) | `aom_ridge_headline` (534 rows) — **needs seeds 1/2** before release |
| `bench/scenarios/runs/paper_aom_linear_hpo_full_cartesian_default_cv5_all/` | PLS-/Ridge-default-CV5 | `linear_default_cv5` (360 rows) |
| `bench/scenarios/runs/paper_aom_linear_hpo_full_cartesian_pls-tabpfn-hpo-25trials_seed*/` | PLS-TabPFN-HPO seeds 0/1/2 | 38+38+38 rows |
| `bench/scenarios/runs/paper_aom_linear_hpo_full_cartesian_ridge-tabpfn-hpo-60trials_seed*/` | Ridge-TabPFN-HPO seeds 0/1/2 | 37+37+37 rows |

### 7.2 ARCHIVE (move to `bench/AOM_v0/_archive/` with a one-line manifest)

- `bench/AOM_v0/Ridge/benchmark_runs/{all53_top5_fast_parallel, all54, all54_combined, all54_top5_fast}` — superseded by `all54_headline/`. Keep one for reference.
- `bench/AOM_v0/Ridge/benchmark_runs/{curated, curated_v2, final_curated}` — curated cohorts; useful only if a follow-up paper uses curated subsets.
- `bench/AOM_v0/Multi-kernel/benchmark_runs/{all54_stageA, all54_stageB, extended, extended12, full, full_pre_parity, full_v1_11variants}` — large Multi-kernel runs; not paper-tied.
- `bench/AOM_v0/multiview/results/` — multiview smoke runs (smoke-4, smoke-10 partial); future paper.

### 7.3 TRASH (delete before release)

- `bench/AOM_v0/Ridge/benchmark_runs/{smoke, smoke6, smoke_cv5, v5a_smoke_alpine, v5b_smoke_alpine, v5b_diverse}` — temporary validation runs.
- `bench/AOM_v0/Ridge/benchmark_runs/{diverse11_iter2, diverse_iter2, diverse_iter3_*, diverse11_ridgepls}` — exploratory iterations; superseded.
- `bench/AOM_v0/Ridge/benchmark_runs/{da001_*, da002_*, da003_*, da009_*}` — design-audit ablation runs; archive what is referenced from `final_stats.md`, delete the rest.
- `bench/AOM_v0/Multi-kernel/benchmark_runs/{iter1_active15, iter2_tuned_active, iter3_branches, iter4_score_methods, iter5_sparse, iter6_*, iter7_noretune, iter8_full54_champions, iter9_multibranch, iter11_sparse_tuned, iter12_sparse2_default, smoke, smoke3, smoke3_branches, small10, diverse8_stack5, diverse10, deep}` — exploratory.
- `bench/AOM_v0/benchmark_runs/{smoke, smoke_old_11ds, full}` — temporary; only `paper_aom_aompls_da_seeds012` is paper-tied.

### 7.4 Cohort manifests (KEEP)

Lightweight CSVs that define dataset groupings — keep them all and document each at the top: `all53_no_lucas_cohort.csv`, `all54_sorted_cohort.csv`, `all57_cohort.csv`, `curated_cohort.csv`, `diverse11_cohort.csv`, `diverse_cohort.csv`, `diverse_giants_only_cohort.csv`, `diverse_no_giants_cohort.csv`, `diverse_no_species_cohort.csv`, `N_woOutlier_only_cohort.csv`, `paper_aom/review/cohort_manifest.csv`.

---

## 8. Score-grounded variant triage

This is the consolidated triage that drives the migration plan. Every row maps to a specific implementation under `bench/AOM_v0/` and a score signal in `final_stats.md`/`table_*.tex`.

### 8.1 KEEP — paper headline / production API (11 variants)

| Variant | Implementation | Evidence | Notes |
| --- | --- | --- | --- |
| AOM-PLS simple (= `AOM-compact-cv5`) | `aompls.AOMPLSRegressor(bank='compact', criterion='cv', cv=5)` | ratio 0.991 vs PLS-default, 22/32 wins, $p=0.896$ | Headline simple |
| AOM-PLS best (= `ASLS-AOM-compact-cv5`) | + `ASLSBaseline` upstream | ratio 0.985 vs PLS-default, 20/32 wins | Headline best |
| AOM-PLS-DA-global (NIPALS-adjoint / SIMPLS-covariance) | `aompls.AOMPLSDAClassifier` | seeds 0/1/2, N=13 (AOM-PLS-DA), N=14 in `table_classification_full.tex` when AOM-Ridge classifiers are included | Classification headline |
| AOM-Ridge simple (= `AOMRidge-global-compact-none`) | `aomridge.AOMRidgeRegressor(selection='global', bank='compact')` | ratio 0.974 vs Ridge-default, 25/32 wins, $p_{\mathrm{Holm}}=0.007$; rank 3.48 | Paper "simple Ridge" |
| AOM-Ridge best (= `AOMRidge-Blender-headline-spxy3`) | `aomridge.AOMRidgeBlender(...)` over `AOMRidgeAutoSelector` candidates | ratio 0.918 vs Ridge-default, 27/32 wins, $p_{\mathrm{Holm}}=2.6\mathrm{e}{-04}$; rank 2.65 | **Best empirical result** — single-seed |
| AOM-Ridge AutoSelector (= `AOMRidge-AutoSelect-headline-spxy3`) | `aomridge.AOMRidgeAutoSelector` | ratio 0.963 vs Ridge-HPO, 22/32 wins, current $p_{\mathrm{Holm}}=0.741$ (`final_stats.md:93`); pre-registered $p_{\mathrm{Holm}}=0.044$ from `final_stats.md:27` is stale; Friedman rank 2.87 | Required to build Blender |
| AOMRidge-global-compact-none-split_aware (seeds012) | same as simple Ridge with split-aware CV | ratio 0.371 RMSEP, 25 datasets × 3 seeds | Multi-seed Ridge evidence |
| AOM-PLS-compact-CV (Ridge family) | `aomridge.AOMRidgePLS` (PLS+Ridge hybrid) | 0.414 RMSEP, 1.94 s | Ridge-PLS bridge |
| FastAOM-sparse-mkr-supervised | `fastaom.SparseMultiKernelRidge(...)` supervised | ratio 1.009, rank 3.08 (N=50) | FastAOM headline |
| FastAOM-sparse-mkr-compact | `fastaom.SparseMultiKernelRidge(...)` compact | ratio 1.022, fit 2.48 s, rank 3.18 (N=50) | Speed champion |
| `nirs4all-AOM-PLS-default` | current `nirs4all.operators.models.sklearn.aom_pls.AOMPLSRegressor` | ratio 0.999 / 1.034 (per family) | Production reference, paper compares against |

### 8.2 KEEP-AS-ABLATION (supplementary; downgrade narrative)

- `AOM-default-nipals-adjoint-numpy` (default 100-op bank) — ratio 1.005-1.034.
- `AOM-default-simpls-covariance-numpy` — alternative engine.
- `AOM-compact-cv3-numpy`, `AOM-compact-simpls-covariance-numpy` — CV/engine ablations.
- `AOMRidge-global-compact-none-{asls,snv,msc}` — preprocessing ablations (0.382-0.483).
- `AOMRidgePLS-compact-colscale-cv-relative` (0.414, 33.4 s) — alt RidgePLS path.
- `AOMRidge-Local-compact-{knn50,cv-blended}` — paper failure-mode example (knn50: ratio 1.212, 4/23 wins).
- FastAOM `single-chain`, `soft-chain`, `hard-chain-{osc,supervised,asls,multibase,compact}` — chain-policy ablations (ratios 1.05-1.13).
- POP-PLS / POP-PLS-DA — per-component ablation (ratio 1.373-1.385 vs PLS-default).

### 8.3 ARCHIVE (keep code, do not advertise)

- `aompls.operator_explorer`, `operator_generation`, `operator_similarity` — used only by the supplement's explorer figures; mark "experimental" in the library README.
- `bench/AOM_v0/Multi-kernel/{MKR,Blup,MkM}` — future papers (MKR has results, but they live in a separate side-paper; Blup/MkM benchmarks are not yet complete).
- `bench/AOM_v0/multiview/` — future paper on adaptive operator selection (smoke-4 only).
- `bench/AOM_v0/Ridge/publication/manuscript/aomridge_paper.{tex,pdf}` — internal draft; use Talanta paper as source of truth.

### 8.4 TRASH (drop before release)

- `AOMRidgePLS-compact-Hmax-relative-emsc2` (median RMSEP 1.981) — variant-config to delete, not the file.
- `AOMRidge-MultiBranchMKL-compact-shrink03` (median RMSEP 3.599 on `seeds012`, ~6× Ridge-raw) — config-to-delete.
- FastAOM `hard-chain-compact-d4` (N=1) and `single-chain-supervised-cv5-numpy` (ratio 1.208) — drop from headline tables; archive logs.
- `bench/AOM/{darts_pls.py, moe_pls.py, zero_shot_router*.py, pseudo_linear*.py, enhanced_aom.py}` — pre-paper exploration, never on the paper's cohort.

---

## 9. Tests at a glance

| Package | Test directory | Files | Coverage focus |
| --- | --- | --- | --- |
| `aompls` | `bench/AOM_v0/tests/` | 12 modules (~40 tests) | NIPALS/SIMPLS engine parity, selection policies, fold-safety, operator math, torch parity, parity with `nirs4all` production |
| `aomridge` | `bench/AOM_v0/Ridge/tests/` | 23 modules (~6.4 kLOC) | Solvers, kernel-equivalence, CV no-leakage, branch+selector invariants, MKL, RidgePLS, classifier, AutoSelector, Blender, LocalRidge, MultiBranchMKL, MKR, SPXY-aware splits |
| `FastAOM` | `bench/AOM_v0/FastAOM/tests/` | 7 modules (54 tests) | Bases, grammar, chain ops, low-rank screening, models, FFT xcorr, infinite-loop regression |
| `nirs4all` library | `nirs4all/tests/unit/operators/models/` | `test_aom_pls.py`, `test_aom_pls_classifier.py`, `test_aom_pls_aomlib.py` (skipped if `aompls` C++ missing) | Hard/sparsemax gating, classifier calibration, CV modes via C++ wrapper |

No hard-coded dataset paths in any tested module; all fixtures are synthetic.

---

## 10. Known issues that block "release-ready"

1. **Single-seed AOM-Ridge headline.** `all54_headline/` is seed=0; the paper claims multi-seed validation. Re-run Blender and AutoSelector with seeds 1, 2 on the 53-dataset cohort. Effort: 50-120 core-hours. See `paper_aom/review/talanta_review.md` weakness #2.
2. **HPO denominator gap.** `pls-tabpfn-hpo-25trials` and `ridge-tabpfn-hpo-60trials` cover ~36 datasets each; the strict intersection used in `table_main_results.tex` is N=32. Fill the gaps or document the missingness table at submission. See `missing_datasets_per_variant.md`.
3. **Three coexisting AOM-PLS Python implementations.** Decide which becomes canonical in the library (current `nirs4all` lib's pure-Python, `aom_pls_aomlib` C++ wrapper, or bench `aompls/estimators.py`) before any migration commit. Migration plan recommends `aompls/estimators.py` as canonical.
4. **Reversed dep: bench → nirs4all.** `aompls.preprocessing` imports `nirs4all.operators.transforms.nirs`; `aomridge.cv` imports `nirs4all.operators.splitters`. Flip at migration time.
5. **`xcorr_fast` Python bottleneck.** Limits FastAOM throughput on 100-op default bank. Not a release blocker but worth a vectorisation pass before publishing the library.
6. **Benchmark-run sprawl.** ~80 subdirectories in `bench/AOM_v0/*/benchmark_runs/`; release tarball must whitelist only the paper-tied runs.

---

## 11. Appendix — files definitively to TRASH

- `bench/AOM/darts_pls.py`, `bench/AOM/moe_pls.py`, `bench/AOM/zero_shot_router.py`, `bench/AOM/zero_shot_router_v1.py`, `bench/AOM/pseudo_linear_aom.py`, `bench/AOM/pseudo_linear_snv_v1.py`, `bench/AOM/enhanced_aom.py`, `bench/AOM/quick_test.py`, `bench/AOM/test_snv_jacobian.py`, `bench/AOM/run_comparison.py`, `bench/AOM/update_models.py` — all pre-paper drafts, none on the paper's cohort.
- `bench/AOM_v0/Ridge/publication/manuscript/aomridge_paper.{tex,pdf}` — internal Ridge draft superseded by Talanta paper.

(Note: `bench/AOM_v0/Ridge/aomridge/residual_tabpfn.py` and `tabpfn_candidate.py` are NOT in this TRASH list — see §4.1: they are imported by `run_aomridge_benchmark.py:783-786,848`. Treat as ARCHIVE behind an optional `tabpfn` extra.)

End of inventory. Companion plan: `aom_lib_migration_plan.md`.
