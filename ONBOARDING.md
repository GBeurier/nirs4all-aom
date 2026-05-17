# Onboarding — aom-nirs

**You are picking up an in-flight research codebase.** This document is the
single place where the project's history, science, code architecture,
empirical results, and open work are written down. Read it cold and you
should be able to take over.

Companion docs (deeper dives):

- `docs/architecture.md` — package layout and dataflow.
- `docs/math.md` — math derivations (covariance identity, NIPALS-adjoint,
  SIMPLS-covariance, AOM-Ridge dual, FastAOM screening).
- `docs/benchmark_protocol.md` — cohorts, splits, seeds, statistics.
- `docs/reproducibility.md` — six-section command runbook.
- `paper/main.tex` and `paper/supplement.tex` — the manuscript.
- `paper/review/aom_code_inventory.md` — per-file inventory with verdicts.
- `paper/review/aom_lib_migration_plan.md` — repo strategy and the
  three options that led to this layout.
- `paper/review/pls4all_integration_eval.md` — convergence path with the
  C++ engine.
- `paper/review/talanta_review.md` — internal Talanta review with
  weakness ranking.
- `paper/review/final_stats.md` — current paired-stats numbers.

Read this onboarding first, then jump to whichever companion doc you
need. The numbers and architecture decisions in this document are
authoritative as of the migration commit (2026-05-17); when in doubt,
the manuscript and `final_stats.md` are the sources of truth.

---

## 1. The 30-second pitch

`aom-nirs` is the citation repository for the Talanta paper
*"Operator-adaptive PLS and Ridge calibration for NIR spectroscopy"*. It
ships three Python packages plus the manuscript:

- `aom_nirs.pls` — **AOM-PLS**, **POP-PLS**, **AOM-PLS-DA**, **POP-PLS-DA**.
  Partial least squares with a built-in linear-operator bank that
  selects (or mixes) preprocessing directly inside the PLS calibration
  via a cross-covariance identity.
- `aom_nirs.ridge` — the **AOM-Ridge family** (`AOMRidgeRegressor`,
  `AOMRidgeClassifier`, `AOMRidgeBlender`, `AOMRidgeAutoSelector`,
  `AOMRidgePLS`, `AOMMultiKernelRidge`, `AOMMultiBranchMKL`,
  `AOMLocalRidge`). Dual / kernel Ridge with the same operator-mixture
  trick; **`AOMRidgeBlender` is the paper's strongest empirical result.**
- `aom_nirs.fast` — **FastAOM**: screens millions of preprocessing
  chains via adjoint-only covariance scoring + diversity-aware top-k +
  truncated-SVD low-rank kernels, then fits one of four AOM-style
  models on the survivors (single chain, hard per-component,
  soft mixture, sparse multi-kernel Ridge).

Everything else in the repo — `paper/`, `tests/`, `benchmarks/`, `docs/`,
`_archive/` — exists to support the paper and the three packages above.

## 2. The paper in two minutes

**Problem.** NIR spectroscopy calibration is dominated by a
preprocessing-search ritual: practitioners try SNV, MSC, EMSC, multiple
Savitzky-Golay configurations, derivatives, baselines, OSC, etc., and
pick the best by validation RMSE. The grid is large, the choices are
not independent, and the search is rerun for each new dataset. The paper
asks whether we can absorb the *linear* part of that search into the
calibration itself, so the analyst never has to enumerate it.

**Idea (AOM = Adaptive Operator Mixture).** A strict-linear preprocessing
operator `A ∈ R^{p×p}` acts on row spectra as `X_b = X A^T`. The
cross-covariance entering NIPALS / SIMPLS becomes `X_b^T y = A X^T y`,
which means **the operator transforms the cross-covariance, not the
data matrix**. Evaluating thousands of operator candidates costs
matrix-vector products on `X^T y` (a `p`-vector), not on `X` (a
`n × p` matrix). The PLS engine becomes the search.

**Three contributions.**

1. **AOM-PLS / POP-PLS** (`aom_nirs.pls`). One PLS estimator that
   selects an operator (global, AOM) or one per component (POP) from
   a strict-linear bank. Compact 9-operator bank, default 100-operator
   bank, extended 200+ bank. NIPALS-adjoint and SIMPLS-covariance
   engines that exploit the identity. Five selection policies (global,
   per-component, soft, superblock, none). CV / PRESS / covariance /
   holdout / hybrid scorers.

2. **AOM-Ridge family** (`aom_nirs.ridge`). Dual / kernel Ridge with
   per-operator kernels. `AOMRidgeRegressor` does single-policy
   selection; `AOMRidgeAutoSelector` runs outer-CV over a panel of
   candidate Ridge specs; `AOMRidgeBlender` learns convex non-negative
   weights over their out-of-fold predictions via SLSQP. The Blender
   produces the paper's headline: median RMSEP ratio **0.918** vs
   Ridge-default on the strict 32-dataset intersection (Wilcoxon
   Holm-corrected `p = 2.6×10⁻⁴`, 27/32 wins).

3. **FastAOM** (`aom_nirs.fast`). Operator-chain framework. A typed
   grammar over nonlinear bases (raw / absorbance / SNV / MSC / EMSC /
   ASLS / OSC / Whittaker) and chain depths 1-4 generates millions
   of candidate preprocessing pipelines. Adjoint-only covariance
   screening prunes them; truncated SVD turns the survivors into
   low-rank kernels. Four sklearn-style models consume the kernels:
   `SingleChainPLSRidge`, `HardAOMChainPLSRidge`,
   `SoftAOMChainPLSRidge`, `SparseMultiKernelRidge`. The paper's
   FastAOM headline is `SparseMultiKernelRidge` with the compact
   primitive bank (`FastAOM-sparse-mkr-compact`): median rel-RMSEP
   **1.022**, median fit **2.48 s**, Friedman rank 3.18 on the
   common 50-dataset subset.

**Cohort.** 61 regression NIR datasets + 17 classification datasets
spanning plant traits, soil, food, petroleum, pharmacology. Strict
paired intersection `N_∩ = 32` for the main paired tests; AOM-Ridge
headline uses 53 datasets; classification uses 13 paired datasets.

**Baselines compared against.** PLS-default-CV5, Ridge-default-CV5,
PLS-TabPFN-HPO (25 trials × 3 seeds), Ridge-TabPFN-HPO (60 trials × 3
seeds). PLS-default with no tuning is the "what most practitioners
deploy" baseline; the TabPFN-HPO baselines are the "what a careful
analyst with a budget" baseline.

**Talanta-review blockers (open).**

- AOM-Ridge Blender headline is **single-seed** (seed 0 only) while
  the paper's other variants run 3 seeds. Re-run with seeds 1, 2.
- HPO baselines have ~25 "not attempted" datasets each. Either fill
  them or document the missingness in the manuscript.

Both are tracked in `paper/review/talanta_review.md` weaknesses #1-#2
and `paper/review/missing_datasets_per_variant.md`.

## 3. Repo at a glance

```
aom_nirs/
├── README.md, LICENSE, CHANGELOG.md, CITATION.cff, MANIFEST.in
├── pyproject.toml                           # name=aom-nirs, version=0.1.0
├── ONBOARDING.md                            # this file
│
├── aom_nirs/                                # the Python package
│   ├── __init__.py                          # version marker
│   ├── pls/    (16 .py)                     # AOM-PLS family
│   ├── ridge/  (23 .py + _spxy.py)          # AOM-Ridge family
│   ├── fast/   (10 .py + models/ 6 .py)     # FastAOM family
│   └── experimental/                        # reserved for new ideas
│
├── tests/      (51 .py)                     # pls/ ridge/ fast/ subdirs
│   ├── conftest.py                          # shared rng + synthetic fixtures
│   ├── pls/                                 # 16 tests (incl. 3 wrapper)
│   ├── ridge/  (conftest.py)                # 24 tests
│   └── fast/   (conftest.py)                # 8 tests
│
├── benchmarks/
│   ├── pls/, ridge/, fast/                  # runners + cohort CSVs + scenario configs
│   └── runs/                                # paper-tied results
│       ├── pls/paper_aom_aompls_da_seeds012/
│       ├── ridge/paper_aom_aomridge_seeds012/
│       ├── ridge/paper_aom_aomridge_cls_seeds012/
│       ├── ridge/all54_headline/            # single-seed, blocker
│       └── scenarios/                       # 13 dirs, ~16 MB
│
├── examples/
│   ├── 01_aom_pls_quickstart.py
│   ├── 02_aom_ridge_blender.py
│   ├── 03_fastaom_quickstart.py
│   ├── paper_smoke.py                       # 5-min synthetic reproduction
│   └── README.md
│
├── docs/
│   ├── architecture.md, math.md
│   ├── benchmark_protocol.md, reproducibility.md
│   └── _audit_2026-05-17.md                 # repo readiness audit
│
├── paper/
│   ├── main.tex, supplement.tex, references.bib
│   ├── main.pdf, supplement.pdf, build.sh
│   ├── figures/ (22), tables/ (21)
│   ├── scripts/make_figures.py
│   └── review/                              # 14 files, the review dossier
│
└── _archive/                                # 1.4 GB, NOT in public API
    ├── deprecated_nirs4all/                 # 5 pre-migration nirs4all snapshots
    ├── pre_paper_drafts/                    # bench/AOM/ drafts + 1.3 GB workspace (ignored)
    ├── multi_lang/AOM_lib/                  # the old C++/R/Julia/MATLAB/JS port
    ├── trashed_runs/AOM_v0_legacy/          # legacy benchmark iterations
    └── future_work/                         # Multi-kernel + multiview side-projects
```

## 4. Why AOM exists — the science problem

Standard NIR calibration looks like this:

```
raw_spectra -> [preprocessing recipe] -> [feature/component selection] -> PLS / Ridge
```

The preprocessing recipe is the part with the most degrees of freedom.
Common recipes for a single dataset: SNV, MSC, EMSC(d=1), EMSC(d=2),
ASLS baseline, then Savitzky-Golay smoothing at multiple
`(window, polyorder, derivative)` settings, then optionally OSC, then
optionally derivative again. A modest grid covers tens of recipes; a
serious grid covers hundreds.

This costs three things:

1. **Search compute**. Each candidate recipe runs a full PLS fit (and
   cross-validation). Multiplied by datasets and seeds, the search
   dominates calibration time.
2. **Model-selection variance**. The winner of a small grid changes
   when you change the random seed of the CV split. Reviewers (and
   `paper/review/talanta_review.md`) flag this as a recurring
   weakness in the literature.
3. **Cognitive load**. The analyst memorises which recipe works on
   which dataset family. The science is "I tried 50 recipes, this one
   won."

The AOM thesis: **for linear preprocessing operators, the search
factors out of the calibration**. You do not need to fit one PLS per
candidate; the PLS engine already computes everything you need to score
all candidates simultaneously. The trick is the cross-covariance
identity.

## 5. The math — the bits you need

This is the short version. Full derivations are in `docs/math.md` and
`paper/main.tex` §3.

### 5.1 Strict linear scope

A strict-linear operator is a matrix `A ∈ R^{p×p}` that acts on row
spectra as `X_b = X A^T`. Restrictions:

- `A` does **not** depend on data — operators are pre-defined (Identity,
  finite-difference matrix, Savitzky-Golay convolution matrix,
  detrending projector, Norris-Williams kernel, Whittaker smoother).
- `A` is **fold-local** if its parameters are derived from training
  data, but here we only consider truly data-independent `A`. SNV,
  MSC, EMSC are *per-sample* operations (non-linear in this sense) and
  live upstream as `aom_nirs.pls.preprocessing` rather than inside the
  bank.

### 5.2 The covariance identity

PLS regression depends on `X` only through `X^T y`. Plug in `X_b`:

```
X_b^T y = (X A^T)^T y = A X^T y
```

So a candidate operator `A` transforms a `p`-vector, not an `n × p`
matrix. Score all `K` candidates: `K` matrix-vector products, total
`O(K p²)` instead of the naive `O(K n p)` for non-trivial dimensions.

For SIMPLS, which works directly on `X^T y`, this is a free pass — no
algorithm change, just replace the input vector. We call this the
**SIMPLS-covariance** engine.

For NIPALS, the standard formulation needs `A` explicitly. We rewrite
it as **NIPALS-adjoint**: every step that would compute `A x` is
replaced by `A^T r` where `r` is a residual vector. `A^T` is just `A`
for symmetric operators (SG smoothers) and known analytically for the
rest. No `A` is ever materialised.

### 5.3 Selection policies

Given a bank `B = {A_1, ..., A_K}` and `K` corresponding cross-covariance
vectors `{A_k X^T y}`, we pick one `A_k` per PLS component (or one
globally) by:

- **global (AOM)** — pick the `A_k` that maximises the chosen
  criterion across all components. One operator, one fit.
- **per-component (POP)** — pick `A_k` independently for each
  component. K operators per component, max-`H` operators across all
  components.
- **soft** — convex non-negative weight `θ_k` over operators per
  component; learned by gradient projection.
- **superblock** — concatenate `[X A_1^T | X A_2^T | ... | X A_K^T]`
  and run plain PLS. Expensive but transparent.
- **none** — bypass; run PLS on `X` raw.

POP-PLS turns out to **underperform** AOM-PLS on the paper cohort
(median ratio 1.37 vs PLS-default). It's kept as an honest ablation,
not a contribution.

### 5.4 AOM-Ridge dual

Kernel Ridge: `α = (K + λI)^{-1} y`, with `K = X_c X_c^T`.

For an operator-mixture: `K_θ = Σ_k θ_k K_k` where `K_k = X A_k^T A_k X^T`.
Three knobs:

- **per-block kernels** (`AOMMultiKernelRidge`) with one λ per block.
- **MKL weights via kernel-target alignment** (`AOMMultiBranchMKL`)
  with simplex projection on `θ` and a shrinkage parameter.
- **convex blender** (`AOMRidgeBlender`) over outer-CV OOF predictions
  of a candidate panel, solved by SLSQP. This is the paper headline.

Solvers in `aom_nirs/ridge/solvers.py` use Cholesky with jitter
fallback to eigh; α-grids are log-spaced and per-fold.

### 5.5 FastAOM screening

Chains are `A = A_d ∘ ... ∘ A_1` from a typed grammar (baseline →
scatter → smoothing → derivative → projection). Score for chain `s`:

```
score(s) = ||A_s^T B(X)^T y||² / (||B(X) A_s^T||_F² · ||y||²)
```

where `B(X)` is a nonlinear base (raw / SNV / MSC / EMSC / ASLS /
Whittaker). The denominator is approximated from a truncated SVD of
`B(X)`. Top-`k` survivors get full low-rank kernels
`K_s ≈ U C_s U^T`. Four AOM-style models consume the kernels.

Diversity-aware top-k: caps per-family / per-base so the survivors
span different operator types.

## 6. The three model families in detail

### 6.1 `aom_nirs.pls` — AOM-PLS and POP-PLS

**Public API (from `aom_nirs/pls/__init__.py`):**

```python
from aom_nirs.pls import (
    AOMPLSRegressor, POPPLSRegressor,
    AOMPLSDAClassifier, POPPLSDAClassifier,
    IdentityOperator, SavitzkyGolayOperator, FiniteDifferenceOperator,
    DetrendProjectionOperator, NorrisWilliamsOperator, WhittakerOperator,
    ComposedOperator, ExplicitMatrixOperator, LinearSpectralOperator,
    compact_bank, default_bank, extended_bank, bank_by_name,
)
```

**Key classes (`aom_nirs/pls/estimators.py:27`):**

```python
AOMPLSRegressor(
    n_components="auto",          # int or "auto"
    max_components=25,
    engine="simpls_covariance",   # nipals / simpls / their fast variants
    selection="global",           # global / per_component / soft / superblock / none
    criterion="cv",               # cv / press / covariance / holdout / hybrid
    operator_bank="compact",      # compact (9) / default (100) / extended / list
    orthogonalization="auto",
    center=True, scale=False, cv=5,
    random_state=0, backend="numpy",
    repeats=1, one_se_rule=False, cv_splitter=None,
)
```

**Banks** (`aom_nirs/pls/banks.py`):

- `compact_bank(p)` → 9 operators: identity, SG-smooth (w=11, p=2),
  SG-d1 (w=11, p=2), SG-d1 (w=21, p=3), SG-d2 (w=11, p=2),
  SG-d2 (w=21, p=3), detrend-d1, detrend-d2, finite-difference.
  **This is the paper's main bank.**
- `default_bank(p)` → 100 operators mirroring the production
  `nirs4all` AOM-PLS bank.
- `extended_bank(p)` → 200+ operators including Whittaker variants.

**Engines** (`aom_nirs/pls/{nipals.py,simpls.py}`):

- `nipals_standard` — reference NIPALS.
- `nipals_adjoint` — fast NIPALS using `A^T r` instead of `A`.
- `nipals_materialized_{fixed,per_component}` — variants for testing.
- `simpls_standard` — reference SIMPLS.
- `simpls_covariance` — fast SIMPLS on `A X^T y`.
- `simpls_materialized_*` — variants.
- `superblock_simpls` — SIMPLS on concatenated operator outputs.

A `backend="torch"` mode is wired (lazy import) for GPU kernels; see
`aom_nirs/pls/torch_backend.py`.

**Selection** (`aom_nirs/pls/selection.py`):

`select(criterion, engine, bank, ...)` returns a `SelectionResult`
carrying the chosen operator index, the per-component operator
sequence (POP only), the criterion scores, and the fit diagnostics
needed to compute coefficients with `B = Z (P^T Z)^+ Q^T` (see
`docs/math.md`).

**Diagnostics** (`aom_nirs/pls/diagnostics.py`):

`AOMPLSRegressor.get_diagnostics()` returns a `RunDiagnostics`
dataclass with `selected_operators`, `selected_operator_indices`,
`selected_operator_names`, `criterion_scores`, `n_components_selected`,
`fit_time`, etc. **Use this attribute, not legacy `gamma_` / `block_names_`
fields** that existed in the pre-migration `nirs4all` AOM-PLS.

### 6.2 `aom_nirs.ridge` — the AOM-Ridge family

**Public API (from `aom_nirs/ridge/__init__.py`):**

```python
from aom_nirs.ridge import (
    AOMRidgeRegressor, AOMRidgeClassifier,
    AOMRidgeBlender, AOMRidgeAutoSelector,
    AOMRidgePLS, AOMRidgePLSCV,
    AOMMultiKernelRidge, AOMKernelizer,
    AOMMultiBranchMKL, AOMLocalRidge,
)
```

Lazy-imported via `__getattr__`. The TabPFN candidates
(`residual_tabpfn.py`, `tabpfn_candidate.py`) live in the package but
are NOT in `__all__`; they activate via the optional `[tabpfn]` extra
and are reachable from `AOMRidgeAutoSelector` when explicitly
requested.

**Single-policy regressor** (`AOMRidgeRegressor`,
`aom_nirs/ridge/estimators.py`):

- `selection` ∈ {`superblock`, `global`, `active_superblock`,
  `branch_global`, `mkl`}.
- `branch` ∈ {`none`, `snv`, `msc`, `asls`, `emsc2`} — upstream
  preprocessing applied fold-locally.
- `alpha_grid` — log-spaced α candidates; per-fold CV.

**Ensemble wrappers:**

- `AOMRidgeAutoSelector` — outer-CV over a default panel of ~15
  candidates (global, superblock, active_superblock, branch_global,
  multi-branch-MKL, ridgepls, local-knn50, plus optional TabPFN
  variants). Picks the single best candidate by outer RMSE.
- `AOMRidgeBlender` — same panel as AutoSelector but learns convex
  non-negative weights over their out-of-fold predictions via SLSQP
  (`aom_nirs/ridge/blender.py`). **Paper headline: median RMSEP
  ratio 0.918 vs Ridge-default.**

**Structural / experimental variants:**

- `AOMRidgePLS` / `AOMRidgePLSCV` — PLS scores + Ridge on top.
  `colscale-cv-relative` is paper-tied; `Hmax-relative-emsc2`
  produced median RMSEP 1.981 and is removed from defaults.
- `AOMMultiKernelRidge` — per-block alpha.
- `AOMMultiBranchMKL` — soft branch weights via KTA. `shrink03`
  variant produced median RMSEP 3.599 on `seeds012` and is removed
  from defaults (failure-mode example).
- `AOMLocalRidge` — KNN local weighting in branch score space.
  `knn50` produced ratio 1.212 (4/23 wins, p=1.0) and is kept as
  the paper's "doesn't always win" example.

**Vendored** in this package: `aom_nirs/ridge/_spxy.py` carries an SPXY
K-fold splitter copied from `nirs4all.operators.splitters.SPXYFold`
to break the circular dependency. Identical algorithm; minimal API.

### 6.3 `aom_nirs.fast` — FastAOM

**Public API (from `aom_nirs/fast/__init__.py`):**

```python
from aom_nirs.fast import (
    # models
    FastAOMPLSRidge, FastAOMConfig,
    SingleChainPLSRidge, HardAOMChainPLSRidge,
    SoftAOMChainPLSRidge, SparseMultiKernelRidge,
    # bases
    RawBase, AbsorbanceBase, SNVBase, MSCBase, EMSCBase, ASLSBase,
    OSCBase, SNVOSCBase, WhittakerBaseLine, BaseTransform, build_base_bank,
    # grammar / generation
    ChainGrammar, default_grammar, ChainGenerationConfig, generate_chains,
    OperatorChain, chain_from_operators,
    # screening
    ScreeningCandidate, fast_covariance_screen, diversity_topk,
    # low-rank
    LowRankBase, fit_lowrank_bases,
)
```

**Pipeline:**

1. Pick a primitive bank (compact 9 / default 100).
2. Pick nonlinear bases (`build_base_bank()`).
3. `generate_chains(ChainGenerationConfig(grammar, primitives, depth=3))`
   enumerates chains up to depth 3 (or 4 — `d4` variants in the
   paper).
4. `fast_covariance_screen` scores all chains; `diversity_topk` keeps
   the top survivors with per-family / per-base caps.
5. `fit_lowrank_bases` computes truncated-SVD `B(X) = U Σ V^T` once
   per base; survivor kernels become `K_s ≈ U C_s U^T`.
6. Pick a model (`single_chain`, `hard_aom_chain`, `soft_aom_chain`,
   `sparse_mkr`) → fit Ridge.

The `FastAOMPLSRidge` orchestrator wraps everything behind one
sklearn-style `fit/predict`.

**Key constraint** (documented in `aom_nirs/fast/IMPLEMENTATION_NOTES.md`):
the `_xcorr_zero_pad` Python loop in `aom_nirs/pls/operators.py:153` is
the dominant cost for the 100-op default bank. Compact-bank variants
are 10-40× faster. The supplement reports this as a known limitation.

## 7. Variants explored — what stayed, what didn't

Source of truth: `paper/review/aom_code_inventory.md` §8 +
`paper/review/final_stats.md` + `paper/tables/*.tex`.

### 7.1 KEEP — paper headline / production tier

| Variant | Implementation | Score evidence |
|---------|---------------|----------------|
| AOM-PLS simple (`AOM-compact-cv5`) | `AOMPLSRegressor(bank='compact', criterion='cv', cv=5)` | ratio 0.991 vs PLS-default, 22/32 wins |
| AOM-PLS best (`ASLS-AOM-compact-cv5`) | + `ASLSBaseline()` upstream | ratio 0.985 vs PLS-default |
| AOM-PLS-DA-global | `AOMPLSDAClassifier` | seeds 0/1/2, N=13 datasets |
| AOM-Ridge simple (`global-compact-none`) | `AOMRidgeRegressor(selection='global')` | ratio 0.974 vs Ridge-default, p_Holm=0.007 |
| **AOM-Ridge best (`Blender-headline-spxy3`)** | `AOMRidgeBlender(...)` | **ratio 0.918, p_Holm=2.6e-4, 27/32 wins (single seed)** |
| AOM-Ridge AutoSelector | `AOMRidgeAutoSelector(...)` | ratio 0.963 vs Ridge-HPO, 22/32 wins (current p_Holm=0.741) |
| FastAOM-sparse-mkr-supervised | `FastAOMPLSRidge(model='sparse_mkr', supervised=True)` | ratio 1.009, Friedman rank 3.08 (N=50) |
| FastAOM-sparse-mkr-compact | `FastAOMPLSRidge(model='sparse_mkr', primitive_bank='compact')` | ratio 1.022, fit 2.48 s, rank 3.18 |

### 7.2 ABLATION — kept in code, reported in supplement only

- AOM-PLS engine ablations: `AOM-compact-cv3`, `AOM-compact-simpls-covariance`,
  `AOM-default-nipals-adjoint`, `AOM-default-simpls-covariance`.
- AOM-Ridge preprocessing variants: `*-asls`, `*-snv`, `*-msc` (median
  RMSEP 0.382-0.483).
- `AOMRidgePLS-compact-colscale-cv-relative` (0.414, 33 s).
- `AOMLocalRidge(knn=50)` — the failure-mode example
  (ratio 1.212, 4/23 wins).
- FastAOM chain-policy ablations: `single-chain`, `soft-chain`,
  `hard-chain-{osc,supervised,asls,multibase,compact}` (ratios
  1.05-1.13).
- POP-PLS / POP-PLS-DA — **negative ablation** (ratios 1.37-1.39 vs
  PLS-default). Per-component selection underperforms global.

### 7.3 DISCARDED — removed from defaults

- `AOMRidgePLS-compact-Hmax-relative-emsc2` (median RMSEP 1.981).
  Class still importable, config removed from defaults.
- `AOMRidge-MultiBranchMKL-compact-shrink03` (median RMSEP 3.599,
  ~6× Ridge-raw). Config removed.
- `FastAOM-hard-chain-compact-d4` (single dataset, ratio 1.256).
- `FastAOM-single-chain-supervised-cv5-numpy` (ratio 1.208).
- Pre-paper drafts archived at `_archive/pre_paper_drafts/`:
  - `darts_pls.py` — Darts-flavoured PLS experiment, never on cohort.
  - `moe_pls.py` — mixture-of-experts PLS, abandoned.
  - `zero_shot_router*.py` — variant routing without training.
  - `pseudo_linear*.py` — linearisation attempts.
  - `enhanced_aom.py` — early enhancements supersded by the current
    `AOMPLSRegressor`.
- TabPFN-residual stacker (`residual_tabpfn.py`,
  `tabpfn_candidate.py`) — never reached headline; gated behind the
  optional `[tabpfn]` extra.

### 7.4 FUTURE — out of paper scope

In `_archive/future_work/`:

- **Multi-kernel** (MKR / Blup / MkM, 33 MB) — multi-kernel Ridge
  with REML mixed-model variants. MKR is methodologically related
  to AOM-Ridge but reported in a separate paper draft (also under
  `_archive/`).
- **multiview** (1.3 MB) — block-sparse, lazy-POP,
  mixture-of-experts on preprocessing operators. Promising on a few
  datasets (Beer, Chla+b) but not generalised.

## 8. Code architecture walk

### 8.1 `aom_nirs/pls/`

```
operators.py         LinearSpectralOperator protocol + concrete operators
                     (Identity, SG, FD, Detrend, NW, Whittaker, Composed, ExplicitMatrix)
banks.py             compact_bank / default_bank / extended_bank / bank_by_name
nipals.py            NIPALS engines (standard, materialized, adjoint, per-component)
simpls.py            SIMPLS engines (standard, materialized, covariance, superblock)
selection.py         The `select()` dispatcher across five policies
scorers.py           CriterionConfig + cv_score_regression / covariance_score /
                     approx_press / holdout_score / cv_score_classification
estimators.py        _AOMPLSBase, AOMPLSRegressor, POPPLSRegressor
classification.py    AOMPLSDAClassifier, POPPLSDAClassifier
                     (class-balanced encoding + logistic / softmax calibration)
preprocessing.py     Upstream preprocessors: SNV, MSC, OSC, ExtendedMSC,
                     ASLSBaseline (vendored from nirs4all + pybaselines).
centering.py         StandardScaler + center_xy helpers
diagnostics.py       RunDiagnostics dataclass
metrics.py           r2, rmse, mae, balanced_accuracy, macro_f1, log_loss
operator_explorer.py Beam-search composition (for the extended bank)
operator_generation.py Primitive operator grids + chain canonicalisation
operator_similarity.py Probe-based + response-based cosine diversity
synthetic.py         Test fixtures (synthetic spectra)
torch_backend.py     GPU NIPALS / SIMPLS / superblock (lazy torch import)
```

### 8.2 `aom_nirs/ridge/`

```
estimators.py        AOMRidgeRegressor (5 selection policies)
classification.py    AOMRidgeClassifier (logistic calibration)
aom_ridge_pls.py     AOMRidgePLS, AOMRidgePLSCV
auto_selector.py     AOMRidgeAutoSelector (outer-CV over candidates)
blender.py           AOMRidgeBlender (SLSQP convex blend) — paper headline
mkr_estimator.py     AOMMultiKernelRidge
multi_branch_mkl.py  AOMMultiBranchMKL
local_ridge.py       AOMLocalRidge (KNN local weighting)
kernels.py           Fold-local linear-operator kernels
kernelizer.py        AOMKernelizer (kernel diagnostics)
solvers.py           Cholesky / eigh + jitter fallback
selection.py         CV selection policies (1042 lines of leakage prevention)
mkl.py               Block weights via KTA + simplex projection
weights.py           WeightLearningResult dataclass
branches.py          SNV / MSC / ASLS branch preprocessing (fold-local)
preprocessing.py     Centering / RMS block scaling
split_aware_cv.py    YBlockedKFold, RepeatedSPXYFold
cv.py                Wrapper around the vendored SPXYFold
_spxy.py             Vendored SPXYFold (breaks circular dep on nirs4all)
guards.py            Input validation
residual_tabpfn.py   TabPFN-residual stacker (optional [tabpfn] extra)
tabpfn_candidate.py  AutoSelector spec for the TabPFN candidate
```

### 8.3 `aom_nirs/fast/`

```
bases.py             Nonlinear bases (raw, SNV, MSC, EMSC, ASLS, OSC, Whittaker)
operator_chain.py    OperatorChain (wraps aom_nirs.pls.ComposedOperator)
grammar.py           Typed ChainGrammar
chain_generator.py   Deterministic DFS chain enumeration
lowrank.py           Truncated-SVD low-rank kernels
screening.py         Fast covariance score + diversity-aware top-k
xcorr_fast.py        FFT-accelerated cross-correlation kernel
models/_common.py    Shared utilities for the four models
models/single_chain_pls_ridge.py
models/hard_aom_chain_pls_ridge.py
models/soft_aom_chain_pls_ridge.py
models/sparse_multi_kernel_ridge.py
models/fast_aom_pls_ridge.py    Orchestrator
IMPLEMENTATION_NOTES.md         Round-by-round fix log
PACKAGE_README.md               Original FastAOM README
```

## 9. Benchmark protocol — short version

Full version: `docs/benchmark_protocol.md`. Key points:

- **Cohort.** 61 regression NIR datasets + 17 classification datasets.
  Strict paired intersection N=32 used for the main paired tests.
  AOM-Ridge headline runs over 53 datasets (the regression cohort
  minus a few that error or weren't attempted).
- **Split.** SPXY (regression) or stratified-SPXY (classification),
  single train/test split per dataset.
- **CV (model selection).** 5-fold with optional one-SE rule. Repeats
  supported for sensitive datasets.
- **Seeds.** 0/1/2 for everything *except* the AOM-Ridge headline
  (Blender + AutoSelector) which is single-seed (blocker).
- **Statistics.** Paired Wilcoxon with Holm correction; Friedman +
  Nemenyi (CD@0.05); Cliff's delta; 95% CI by paired bootstrap.
- **Variant labels.** `<family>-<bank>-<criterion>-<engine>` e.g.
  `ASLS-AOM-compact-cv5-numpy`.

## 10. Reproducing the paper

Full version: `docs/reproducibility.md`. Critical-path commands:

```bash
# 0. clone
git clone https://github.com/GBeurier/aom.git aom-nirs
cd aom-nirs

# 1. install
pip install -e .[bench]

# 2. validate
pytest tests/pls/test_estimators.py -q
pytest tests/ridge/test_blender.py -q
pytest tests/fast/test_grammar.py -q

# 3. smoke
python examples/paper_smoke.py

# 4. rebuild paper PDFs
bash paper/build.sh    # needs pdflatex + bibtex

# 5. re-aggregate stats from shipped result CSVs
python paper/review/aggregate_stats.py
# writes paper/tables/*.tex + paper/figures/*.pdf

# 6. run a fresh benchmark (multi-hour; needs NIR datasets from nirs4all)
python benchmarks/pls/run_aompls_benchmark.py --cohort benchmarks/pls/cohort_regression.csv
```

## 11. Companion repos

- **`GBeurier/nirs4all`** — the production NIRS pipeline library.
  Vendors a copy of `aom_nirs` at
  `nirs4all/operators/models/_aom_nirs/`. Thin re-export wrappers at
  `nirs4all/operators/models/sklearn/{aom_pls,aom_pls_classifier,
  pop_pls,pop_pls_classifier,aom_ridge,aom_fast}.py` give
  `nirs4all` users the same API. Mid-term plan: replace the vendored
  copy with a runtime `pip install aom-nirs` dependency.

- **`GBeurier/pls4all`** — C++17 PLS engine with stable C ABI.
  Phase 6 (shipped through 6f) implements AOM-PLS core in C++:
  operator bank, global AOM-SIMPLS CV selection
  (`p4a_aom_global_select`), POP per-component SIMPLS covariance
  selection (`p4a_aom_per_component_select`), validation-plan ABI,
  Python ctypes smoke against the AOM_v0 parity oracle (now `aom_nirs`).
  pls4all is the C++ parity reference; `aom_nirs` is the Python
  reference. See `paper/review/pls4all_integration_eval.md` for the
  convergence path.

- **`GBeurier/aompls`** — the older multi-language port
  (C++/R/Julia/MATLAB/JS) of the original AOM-PLS C++ kernel.
  Superseded by `aom_nirs` (Python) + `pls4all` (C++); kept at
  `_archive/multi_lang/AOM_lib/` as a historical reference.

## 12. Current blockers — Talanta submission

From `paper/review/talanta_review.md`, ordered by severity:

1. **AOM-Ridge Blender / AutoSelector seeds 1 and 2 not run** (weakness #2).
   The headline ratio 0.918 and the AutoSelect ratio 0.963 are
   single-seed. Effort: 50-120 core-hours per variant. Runner:
   `python benchmarks/ridge/run_aomridge_benchmark.py
   --cohort benchmarks/runs/ridge/all54_sorted_cohort.csv
   --seeds 1,2 --variants blender,auto_selector`.
2. **HPO denominator gap** (weakness #1). PLS-TabPFN-HPO and
   Ridge-TabPFN-HPO cover ~36 datasets each; strict paired
   intersection is N=32. Either fill the ~25 "not attempted" rows
   in `paper/review/missing_datasets_per_variant.md` or document
   the missingness in the manuscript. The missingness table is
   already a candidate appendix.
3. **Strong conventional baseline missing** (weakness #3).
   Reviewers may expect a `PLS+SNV+SG+derivative` recipe with tuned
   components. Pre-register the recipe before running.
4. **Single train/test split per dataset** (weakness #4). Limits
   statistical power. Either add repeated split sensitivity on a
   subset or add a clearer "inference is across datasets, not
   across partitions" caveat.
5. **Code availability** (weakness #5). **This repo is the answer.**
   Once `aom_nirs` is public + has a release tag matching the paper
   commit hash, this blocker is closed.

After acceptance, the post-paper roadmap (`CHANGELOG.md`, Unreleased
section) tracks the pls4all convergence and the second-paper
candidates from `_archive/future_work/`.

## 13. Working on the code

### 13.1 Add a new strict-linear operator

1. Subclass `LinearSpectralOperator` in `aom_nirs/pls/operators.py`.
2. Implement `_matrix_impl(p)` at minimum; override `_transform_impl`,
   `_apply_cov_impl`, `_adjoint_vec_impl` for cheap convolution paths.
3. Add an entry in `aom_nirs/pls/banks.py:compact_bank()` or
   `default_bank()` if it belongs to a paper-tied bank.
4. Add an adjoint-identity test in `tests/pls/test_operators.py`.
5. Document the operator in `docs/architecture.md`.

### 13.2 Add a new AOM-Ridge variant

1. Subclass `AOMRidgeRegressor` (or write a new estimator) in
   `aom_nirs/ridge/`. Reuse `solvers.py`, `kernels.py`, `selection.py`.
2. Register in `aom_nirs/ridge/__init__.py:__getattr__`.
3. Add a spec in `aom_nirs/ridge/auto_selector.py` if you want
   `AOMRidgeAutoSelector` to consider it.
4. Add a no-leakage test in `tests/ridge/`.
5. Run a smoke benchmark via
   `benchmarks/ridge/run_aomridge_benchmark.py --variants <yourname>`.

### 13.3 Add a new FastAOM model

1. Drop the model file under `aom_nirs/fast/models/`.
2. Register in `aom_nirs/fast/models/__init__.py` and re-export
   from `aom_nirs/fast/__init__.py`.
3. Update the `FastAOMConfig.model` choice set (see
   `aom_nirs/fast/models/fast_aom_pls_ridge.py`).
4. Add a test in `tests/fast/test_models.py`.

### 13.4 Add a new dataset to a cohort

1. Place the dataset in `nirs4all/sample_data/` (or wherever the
   runner is configured to look).
2. Add a row to the appropriate cohort CSV at
   `benchmarks/{pls/cohort_regression.csv, ridge/runs/<cohort>.csv,
   paper/review/cohort_manifest.csv}`.
3. Re-run the relevant `benchmarks/<family>/run_*.py`.
4. Re-aggregate with `python paper/review/aggregate_stats.py`.

## 14. Glossary

- **AOM** — Adaptive Operator Mixture. The umbrella name for the
  paper's approach.
- **Bank** — a list of `LinearSpectralOperator` instances. Three
  named banks: `compact` (9), `default` (100), `extended` (200+).
- **Branch** — an upstream preprocessing route (SNV, MSC, ASLS,
  EMSC2) used by AOM-Ridge before the kernel is built.
- **Cohort** — a named list of NIR datasets used as a benchmark
  scope (e.g. `all54`, `curated`, `diverse11`, `paper`).
- **Compact bank** — the 9-operator bank used by the paper headline.
- **Cross-covariance identity** — `X_b^T y = A X^T y`. The central
  trick.
- **Engine** — a NIPALS or SIMPLS variant (standard / materialized
  / adjoint / covariance / superblock).
- **NIPALS-adjoint** — NIPALS rewritten to use `A^T r` (no `A`).
- **POP** — Per-Operator-Per-component. Selects a different operator
  per PLS component. Underperforms global in the paper.
- **SIMPLS-covariance** — SIMPLS run directly on the cross-covariance.
- **Selection policy** — global / per-component / soft / superblock
  / none.
- **SPXY** — Sample-set Partitioning based on X-Y joint distance.
  The CV / split protocol used in NIRS literature (Galvao 2005).
- **Vendored** — copied into this package to avoid a runtime
  dependency on `nirs4all` (the `_spxy.py` splitter and the
  `ExtendedMSC` + `ASLSBaseline` preprocessors).

## 15. Cheat sheet

```python
# Fit the paper's main AOM-PLS preset
from aom_nirs.pls import AOMPLSRegressor
m = AOMPLSRegressor(operator_bank="compact", criterion="cv", cv=5)
m.fit(X_train, y_train); m.predict(X_test)
print(m.get_diagnostics().selected_operator_names)

# Fit the paper's best AOM-Ridge variant
from aom_nirs.ridge import AOMRidgeBlender
m = AOMRidgeBlender(outer_cv=3, random_state=0)
m.fit(X_train, y_train); m.predict(X_test)
print(m.weights_)

# Fit the paper's headline FastAOM
from aom_nirs.fast import FastAOMPLSRidge, FastAOMConfig
m = FastAOMPLSRidge(config=FastAOMConfig(model="sparse_mkr", primitive_bank="compact"))
m.fit(X_train, y_train); m.predict(X_test)

# Re-aggregate paper stats from shipped CSVs
# (writes paper/tables/*.tex and paper/figures/*.pdf)
$ python paper/review/aggregate_stats.py

# Re-build the paper PDFs
$ bash paper/build.sh
```

## 16. History notes

- **Before 2026-05-17.** The AOM code lived inside
  `nirs4all/bench/AOM_v0/` and the paper at `nirs4all/paper_aom/`.
  Three competing AOM-PLS Python implementations coexisted: a
  pure-Python NIPALS (`nirs4all/operators/models/sklearn/aom_pls.py`),
  a C++ wrapper (`aom_pls_aomlib.py`), and the bench paper-grade
  version (`bench/AOM_v0/aompls/estimators.py`). The bench version
  was the cleanest (dual NIPALS+SIMPLS engines, five selection
  policies, the full paper bank).
- **2026-05-17.** Migration to `aom_nirs/` as a separate repo.
  Three commits in `aom_nirs`:
  - `4d6887c` — Initial commit (1603 files).
  - `26dfdca` — Wrapper-API tests + workspace gitignore.
  - `aafe6a8` — Paper-readiness pass (examples + docs + scenarios).
  Three commits in `nirs4all`:
  - `404cd67e` — Migration commit (deletions of bench/AOM_v0/,
    paper_aom/, bench/AOM/, bench/AOM_lib/; addition of
    `_aom_nirs/` vendored copy + new `aom_ridge.py` /
    `aom_fast.py` wrappers; deletion of `pytorch/aom_pls.py`).
  - `cc30f13d` — Updated AOM test files (56→38, 19→14, 33→27
    tests retained; dropped tests for sparsemax / FFT / Wavelet /
    OPLS prefilter / torch in-fit / prefix / n_orth / operator_index).
- **The migration plan and three repo options** (everything in
  `nirs4all`, dedicated `aom-nirs` Python repo, `pls4all`
  bindings/python subdir) are documented in
  `paper/review/aom_lib_migration_plan.md`. Option B (dedicated
  Python repo) was chosen. Option C (`pls4all` hosting) remains the
  long-term endgame for the AOM-PLS / POP-PLS core; AOM-Ridge and
  FastAOM stay in this repo permanently because `pls4all` is
  PLS-only by design.

— *End of onboarding. If something in this document is wrong,
the manuscript and `paper/review/final_stats.md` win.*
