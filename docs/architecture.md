# Architecture

`aom_nirs` is the companion code for the Talanta paper
*Operator-adaptive PLS and Ridge calibration for NIR spectroscopy*. It ships
three sibling subpackages, all sklearn-compatible, all sharing the strict
linear-operator scope defined in the paper. Production pipelines that need
the higher-level dataset / runner machinery live in the companion library
[`nirs4all`](https://github.com/GBeurier/nirs4all); a separate C++ engine
([`pls4all`](https://github.com/GBeurier/pls4all)) provides the parity
oracle for the AOM-PLS / POP-PLS core.

## Package layout

```
aom_nirs/
├── aom_nirs/
│   ├── pls/        # AOM-PLS family
│   ├── ridge/      # AOM-Ridge family
│   ├── fast/       # FastAOM chain screening
│   └── experimental/
├── benchmarks/     # Paper runners (pls/, ridge/, fast/, runs/, scenarios/)
├── paper/          # Talanta manuscript, figures, review/
├── examples/       # 01_aom_pls_quickstart.py, 02_aom_ridge_blender.py
├── tests/          # pls/, ridge/, fast/
└── docs/           # this directory
```

### `aom_nirs.pls`

Operator-adaptive PLS implementations: AOM-PLS, POP-PLS, and their
discriminant-analysis counterparts.

| File | Role |
| --- | --- |
| `operators.py` | `LinearSpectralOperator` protocol + 7 concrete operators (`IdentityOperator`, `SavitzkyGolayOperator`, `FiniteDifferenceOperator`, `DetrendProjectionOperator`, `NorrisWilliamsOperator`, `WhittakerOperator`, `ComposedOperator`, `ExplicitMatrixOperator`). Implements `transform`, `apply_cov`, `adjoint_vec`, `matrix` such that `X_b = X A^T` and `X_b^T y = A X^T y`. |
| `banks.py` | Bank presets: `compact_bank` (9 ops), `default_bank` (~100 ops matching nirs4all), `extended_bank`, `deep_bank`. Resolved by `bank_by_name` from a string. |
| `nipals.py` | Standard NIPALS, materialized fixed-operator NIPALS, materialized per-component NIPALS, and `nipals_adjoint` (the fast variant using `A^T v`). All return a `NIPALSResult` with original-space `Z, P, Q, T`. |
| `simpls.py` | Standard SIMPLS reference, `simpls_materialized_fixed`, `simpls_materialized_per_component`, `simpls_covariance` (the fast variant using `S = X^T Y`), and `superblock_simpls`. |
| `scorers.py` | `CriterionConfig` + scoring helpers (`covariance_score`, `cv_score_regression`, `cv_score_classification`, `approx_press_regression`, `holdout_score_regression`). |
| `selection.py` | The 5 selection policies: `select_global` (AOM), `select_per_component` (POP), `select_soft`, `select_superblock`, `select_active_superblock`, plus the top-level `select` dispatcher. |
| `estimators.py` | `AOMPLSRegressor` and `POPPLSRegressor`. Share the `_AOMPLSBase` backbone; only the default `selection` and default bank differ. |
| `classification.py` | `AOMPLSDAClassifier`, `POPPLSDAClassifier`. Wrap the regression backbone with class-balanced one-hot coding and a logistic calibrator on the latent scores. |
| `preprocessing.py` | Non-strict-linear branches (e.g. `ASLSBaseline`) that the benchmark runners apply as fold-local pre-AOM steps. |
| `operator_explorer.py`, `operator_generation.py`, `operator_similarity.py` | Diagnostics helpers (family tagging, frequency / similarity tables). |
| `torch_backend.py` | Optional GPU NIPALS / SIMPLS / superblock paths. |

Class hierarchy:

```
LinearSpectralOperator (protocol)
├── IdentityOperator
├── SavitzkyGolayOperator
├── FiniteDifferenceOperator
├── DetrendProjectionOperator
├── NorrisWilliamsOperator
├── WhittakerOperator
├── ComposedOperator
└── ExplicitMatrixOperator

bank_by_name("compact" | "default" | "extended" | "deep") -> list[LinearSpectralOperator]
                                            |
                                            v
sklearn BaseEstimator + RegressorMixin
└── _AOMPLSBase
    ├── AOMPLSRegressor  (selection="global",        bank="default")
    └── POPPLSRegressor  (selection="per_component", bank="compact")

sklearn BaseEstimator + ClassifierMixin
└── _AOMPLSDABase
    ├── AOMPLSDAClassifier
    └── POPPLSDAClassifier
```

### `aom_nirs.ridge`

Dual / kernel Ridge with operator-mixture preprocessing. All routines work
in row-spectra convention and import operators / banks from `aom_nirs.pls`.

| File | Role |
| --- | --- |
| `kernels.py` | Bank resolution, fold-local fitting, block-scaling (`rms` / `none` / `scale_power`), and the core identities `K = X_c U`, `U = sum_b s_b^2 A_b^T A_b X_c^T`. |
| `solvers.py` | Dual Ridge solvers via Cholesky / `eigh` with jitter; `make_alpha_grid` for trace-relative log grids. |
| `selection.py` | Alpha and operator selection over folds (`select_alpha_superblock`, `select_alpha_active`, `select_alpha_mkl`, `select_global`, `screen_active_operators`). |
| `mkl.py` | Kernel-target alignment (KTA), simplex-projected supervised block weights for the MKL selection path. |
| `estimators.py` | `AOMRidgeRegressor`, the single-policy estimator (selections: `superblock`, `global`, `active_superblock`, `branch_global`, `mkl`). |
| `classification.py` | `AOMRidgeClassifier` (class-balanced encoding + dual Ridge + logistic calibrator). |
| `auto_selector.py` | `AOMRidgeAutoSelector`: outer-CV over a list of candidate `VariantSpec` dicts, refit best. |
| `blender.py` | `AOMRidgeBlender`: convex non-negative blend of OOF predictions from candidate variants via SLSQP simplex QP. The paper's headline AOM-Ridge result. |
| `branches.py` | Non-strict-linear branches (SNV, MSC, OSC, EMSC, ASLS) fitted fold-locally, applied before the AOM step. |
| `aom_ridge_pls.py` | Hybrid `AOMRidgePLS` / `AOMRidgePLSCV` estimators (Ridge over PLS latent scores). |
| `mkr_estimator.py`, `kernelizer.py` | `AOMMultiKernelRidge` and the kernel-construction helper. |
| `multi_branch_mkl.py` | `AOMMultiBranchMKL`: MKL across both branches and operators. |
| `local_ridge.py` | `AOMLocalRidge`: kNN-local Ridge using operator kernels. |
| `cv.py`, `split_aware_cv.py`, `_spxy.py` | CV utilities: `RepeatedSPXYFold`, SPXY-aware splitters. |
| `weights.py`, `guards.py`, `preprocessing.py` | Block weights, leakage guards, helpers. |
| `residual_tabpfn.py`, `tabpfn_candidate.py` | Experimental TabPFN-residual stacker (gated by the `tabpfn` extra). |

Class hierarchy:

```
AOMRidgeRegressor  (single fixed (selection, bank, alphas) policy)
        |
        v
AOMRidgeAutoSelector  (outer-CV over candidate VariantSpecs; refit best)
        |
        v
AOMRidgeBlender       (outer-CV OOF + convex SLSQP simplex blend; paper headline)

Sibling estimators sharing the same kernel identities:
  - AOMRidgeClassifier   (classification head)
  - AOMRidgePLS / AOMRidgePLSCV (Ridge-on-PLS-scores)
  - AOMMultiKernelRidge  (MKR with kernelizer)
  - AOMMultiBranchMKL    (MKL across branches and operators)
  - AOMLocalRidge        (kNN-local Ridge with operator kernels)
```

### `aom_nirs.fast`

FastAOM: explore very large pipelines of preprocessing chains via
adjoint-only screening + low-rank kernel evaluation, then fit one of
four sklearn-style AOM models on the surviving chains.

| File | Role |
| --- | --- |
| `bases.py` | Nonlinear base transforms (`RawBase`, `AbsorbanceBase`, `SNVBase`, `MSCBase`, `EMSCBase`, `ASLSBase`, `OSCBase`, `SNVOSCBase`, `WhittakerBaseLine`) + `build_base_bank`. |
| `operator_chain.py` | `OperatorChain` / `ChainStage`: composes strict-linear operators into one effective matrix `A_s`, with `transform`, `apply_cov`, `adjoint_vec`, `families`. |
| `grammar.py` | `ChainGrammar` (typed grammar over operator roles), `default_grammar(max_depth=4)`. |
| `chain_generator.py` | `ChainGenerationConfig` + `generate_chains`: depth-bounded chain enumeration consistent with the grammar. |
| `screening.py` | `fast_covariance_screen` (adjoint-only score), `diversity_topk` (per-base / per-family caps), `ScreeningCandidate`. |
| `lowrank.py` | `LowRankBase`: per-base truncated SVD `B(X) ≈ U diag(S) V^T` + `F_s = A_s V diag(S)` and kernel-vector helpers. |
| `xcorr_fast.py` | Vectorised cross-correlation primitives shared by chain operators. |
| `models/single_chain_pls_ridge.py` | `SingleChainPLSRidge`: best chain only, PLS-then-Ridge. |
| `models/hard_aom_chain_pls_ridge.py` | `HardAOMChainPLSRidge`: one chain per PLS component. |
| `models/soft_aom_chain_pls_ridge.py` | `SoftAOMChainPLSRidge`: sparse non-negative chain mixture per component. |
| `models/sparse_multi_kernel_ridge.py` | `SparseMultiKernelRidge`: greedy NNLS over chain kernels `K_theta = sum_s theta_s K_s`. |
| `models/fast_aom_pls_ridge.py` | `FastAOMPLSRidge` orchestrator + `FastAOMConfig` (driver that wires grammar / generation / screening / low-rank / final fit). |

Class hierarchy:

```
BaseTransform (Raw/SNV/MSC/EMSC/ASLS/OSC/SNVOSC/Absorbance/WhittakerBaseLine)
              + LinearSpectralOperator chains via ChainGrammar
                              |
                              v
                generate_chains(config)  -> list[OperatorChain]
                              |
                              v
                fast_covariance_screen + diversity_topk
                              |
                              v
                fit_lowrank_bases   -> list[LowRankBase]
                              |
                              v
sklearn BaseEstimator + RegressorMixin
├── SingleChainPLSRidge
├── HardAOMChainPLSRidge
├── SoftAOMChainPLSRidge
└── SparseMultiKernelRidge       <- all four are orchestrated by FastAOMPLSRidge
```

## Training dataflow

End-to-end for a single fit:

```
(X, y)
  │
  ▼ optional fold-local branch (SNV, MSC, EMSC, ASLS, OSC ...) for the
  │ Ridge "branch_global" path or for FastAOM nonlinear bases. PLS path
  │ usually skips this and relies on the strict-linear bank.
  ▼ centering: X_c = X - mean(X), y_c = y - mean(y)
  │
  ▼ bank resolution: list[LinearSpectralOperator] (identity prepended if missing)
  │
  ▼ engine:
  │   AOM-PLS  -> simpls_covariance | simpls_materialized | nipals_adjoint | nipals_materialized
  │   AOM-Ridge -> K = X_c U with U = sum_b s_b^2 A_b^T A_b X_c^T (dual)
  │   FastAOM  -> per-base truncated SVD + low-rank K_s and chain mixture
  │
  ▼ selection policy:
  │   PLS: "global" (AOM), "per_component" (POP), "soft", "superblock", "none"
  │   Ridge: "superblock", "global", "active_superblock", "branch_global", "mkl"
  │   FastAOM: greedy NNLS over chain kernels, or hard / soft per-component
  │
  ▼ scoring criterion (lower is better):
  │   "cv" (KFold or SPXYFold), "approx_press", "holdout" (debug),
  │   "hybrid" (covariance prescreen + CV refine), "covariance" (fast proxy)
  │
  ▼ refit on the full training set with the selected operator(s) / weights
  │
  ▼ fitted estimator
        coef_, intercept_  -> Y_hat = X coef_ + intercept_
        selected_operators_ , operator_scores_  -> diagnostics
```

`AOMRidgeAutoSelector` and `AOMRidgeBlender` wrap this loop in an outer
CV that builds fresh estimators per fold (no leakage from branch fitting
or alpha selection); the final `predict` delegates to a single
full-training refit.

## Engine choices

| Engine | When to use |
| --- | --- |
| `simpls_covariance` (PLS default) | Largest `p`, smallest `n`, many operators. Operates entirely on `S = X^T y`; cheap per-operator candidate evaluation. |
| `simpls_materialized` | Reference for testing; materialises `X_b = X A^T` then runs standard SIMPLS. |
| `nipals_adjoint` | NIPALS path using `A^T v` for iterative score extraction; saves a `p x p` materialisation. |
| `nipals_materialized` | Reference NIPALS. Slowest, used for parity tests. |
| `superblock_simpls` | Concatenate all transformed views into one wide matrix; baseline for the "no smart selection" comparison. |
| Ridge dual (Cholesky / `eigh`) | All Ridge selection modes solve the dual; switches based on conditioning. |

The `simpls_covariance` and `nipals_adjoint` paths are the speed gains
the paper relies on. Their correctness is checked against the materialised
references and against the C++ `pls4all` oracle
(`pls4all/parity/fixtures/synthetic_aom_*_v1.json`); see
`paper/review/pls4all_integration_eval.md`.
