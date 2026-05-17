# Mathematical reference

Companion notes to the Talanta paper *Operator-adaptive PLS and Ridge
calibration for NIR spectroscopy*. The paper (`paper/main.tex`) contains
the full derivations and the formal statements; this document gives just
enough to map each formula to the corresponding code in `aom_nirs`.
The companion library [`nirs4all`](https://github.com/GBeurier/nirs4all)
hosts production pipelines; the math itself is exactly the math implemented
here.

Notation (matches the paper):

- `X ∈ R^{n × p}` is the centered spectral matrix (rows = samples,
  columns = wavelengths).
- `y ∈ R^{n}` or `Y ∈ R^{n × q}` is the centered response.
- An operator is a fixed matrix `A ∈ R^{p × p}`.
- Row-spectra convention: applying `A` to a row spectrum gives
  `X_A = X A^T`.
- For brevity we write `S = X^T y` (or `S = X^T Y` for multi-output).
- `K ∈ R^{n × n}` denotes a Gram-style kernel.

## 1. Strict-linear operator scope

A strict linear operator is a fixed matrix `A` (paper §3.1, `main.tex`
lines 177-211). Its action on a row spectrum is `X_A = X A^T`. The
matrix is determined once the wavelength grid and the operator
parameters are fixed; in particular it does **not** depend on:

- the response `y`,
- the validation fold,
- the current sample,
- a reference spectrum estimated from the calibration set.

The bank used in the main experiments contains identity, Savitzky-Golay
smoothers, Savitzky-Golay first and second derivatives, finite
differences, polynomial detrending projections, Norris-Williams gap
derivatives and Whittaker smoothers. SNV, MSC, EMSC, ASLS, and OSC
are **not** strict-linear: SNV uses sample-specific centering /
scaling, MSC and EMSC estimate parameters against a reference, ASLS is
iterative, OSC is supervised. These transformations remain in the
benchmark but as fold-local *branches* fitted before the strict-linear
operator bank — implemented in `aom_nirs/ridge/branches.py` and in
`aom_nirs/fast/bases.py` as `BaseTransform` subclasses.

The fold-locality requirement is enforced by every selector that fits
a branch: branch parameters are estimated on the outer-train rows only,
then applied to outer-validation rows (`branches.fit_transform_branch`).

In code, the operator protocol is `aom_nirs.pls.operators.LinearSpectralOperator`:

```python
class LinearSpectralOperator:
    is_strict_linear: bool = True
    def transform(self, X) -> np.ndarray:   # row spectra: X_A = X A.T
    def apply_cov(self, S) -> np.ndarray:   # left action: A S
    def adjoint_vec(self, v) -> np.ndarray: # adjoint: A.T v
    def matrix(self, p) -> np.ndarray:      # explicit p x p materialisation
```

Concrete operators override `_transform_impl`, `_apply_cov_impl`,
`_adjoint_vec_impl` to avoid materialising `A` when a cheap convolution
form exists (Savitzky-Golay, finite difference, Norris-Williams,
Whittaker, identity).

## 2. The cross-covariance identity

For centered `X` and `Y` and a strict linear operator `A`,

```
(X A^T)^T Y = A X^T Y               # paper Eq. (2)
```

This is the central trick of AOM. A bank `{A_b}` can be screened on the
single matrix `X^T Y` by left-multiplication, without materialising
`X_b = X A_b^T` for any `b`. Numerically:

```
S_b = A_b S                         # via op.apply_cov(S)
```

is `O(p × q)` per operator instead of `O(n × p)` for materialising
`X_b`. The check `(X A^T)^T y - A X^T y` is used as a unit-test
invariant in `tests/pls/test_operators.py` and `tests/pls/test_selection.py`.

## 3. NIPALS-adjoint

Standard NIPALS extracts each component by alternating

```
w = X^T u / ||X^T u||,   t = X w,   c = Y^T t / ||t||^2,   u = Y c / ||c||^2
```

then deflates `X -> X - t p^T` with `p = X^T t / ||t||^2`. For a strict
linear operator `A`, the transformed-space NIPALS direction `r_a` maps
back to the original space as

```
z_a = A^T r_a                       # paper §3.2
```

i.e. the *adjoint* of `A` applied to the transformed-space direction.
With `Z = [z_1, ..., z_k]` and `T = X Z`, the recovered coefficient
matrix is

```
B = Z (P^T Z)^+ Q^T                 # paper Eq. (4)
```

where `+` is the Moore-Penrose pseudoinverse. The NIPALS-adjoint
engine never materialises `X_b`; per iteration it uses
`op.adjoint_vec(w)` and the original `X`. Implementation:
`aom_nirs/pls/nipals.py::nipals_adjoint`. The reference
`nipals_materialized_fixed` builds `X_b` explicitly and runs standard
NIPALS — used to test the adjoint variant.

## 4. SIMPLS-covariance

de Jong's SIMPLS extracts components from `S = X^T Y` directly:

```
for a = 1..K:
    r = u_1(S)              # leading left singular vector
    t = X r;  normalise
    p = X^T t
    q = Y^T t
    S <- (I - V V^T) S      # deflate S via Gram-Schmidt of loadings
```

Combined with the covariance identity, SIMPLS becomes the natural fast
engine for AOM-PLS: every operator candidate `A_b` is scored on
`S_b = A_b S` and the dominant direction `r_b = u_1(S_b)` is mapped back
to original space by `z = A_b^T r_b`. Implementation:
`aom_nirs/pls/simpls.py::simpls_covariance`. The reference
`simpls_materialized_fixed` is the same algorithm running on the
explicitly-built `X_b`.

The covariance identity makes the per-component candidate evaluation
nearly free once `S` is precomputed. This is the algorithmic gain that
makes AOM-PLS comparable in cost to a single PLS fit while internally
exploring the whole bank.

## 5. AOM selection policies

Five selection policies are implemented in
`aom_nirs/pls/selection.py`. All operate on already-centered `Xc, yc`
and a resolved operator bank `[A_1, ..., A_B]`. Each returns a
`SelectionResult` with `operator_indices` (one entry per chosen
component) and the final `NIPALSResult`.

| Policy | Definition | Code |
| --- | --- | --- |
| `none` | Bank must be a singleton; runs the engine with the only operator. | `select` with `selection="none"` |
| `global` (AOM) | Pick one `A_b` for *all* components by minimising the selection criterion over `b`. | `select_global` |
| `per_component` (POP) | At each component pick the best `A_b` independently; deflate in original space. | `select_per_component` |
| `soft` | Convex non-negative mixture of operators per component on the covariance objective. | `select_soft` |
| `superblock` | Concatenate transformed views `[X A_1^T | ... | X A_B^T]` and run standard PLS. | `select_superblock` |
| `active_superblock` | Superblock restricted to the active set selected by `screen_active_operators`. | `select_active_superblock` |

The criterion is `CriterionConfig(kind, cv, prescreen_top_m, ...)` from
`aom_nirs/pls/scorers.py`:

- `covariance`: fast proxy `score(b) = -||A_b S||` (smoke-mode).
- `cv`: K-fold CV RMSE (or balanced log-loss for classification).
- `approx_press`: leverage-corrected training residuals
  `(y - Xc B_k) / (1 - h_i)` with `h = diag(X (X^T X)^+ X^T)` (one full
  fit, all prefixes evaluated).
- `hybrid`: covariance prescreen of the top-`m` operators followed by
  CV refinement.
- `holdout`: legacy single train/val split (default seed 42, debug only).

Both `cv` and `approx_press` support `auto_prefix=True`: the prefix
length `k ≤ n_components_max` minimising the criterion is selected.

## 6. AOM-PLS coefficient recovery

For any operator sequence `(A_{b_1}, ..., A_{b_K})` selected by the
policy, the per-component transformed-space direction `r_a` is mapped
to original space:

```
z_a = A_{b_a}^T r_a
Z   = [z_1, ..., z_K]
T   = X Z
P   = X^T T diag(1 / ||t_a||^2)         # original-space loadings
Q   = Y^T T diag(1 / ||t_a||^2)
B   = Z (P^T Z)^+ Q^T
```

The model is a single linear calibration on the original wavelength
grid — there is no preprocessing stage to replay at predict time. This
is the property emphasised in paper §3.2.

## 7. AOM-Ridge dual / kernel formulation

Ridge regression for centered `Xc, Yc` and regulariser `α > 0` is
solved in the dual via the kernel `K = Xc Xc^T`. The operator-induced
kernel for `A_b` is (paper Eq. (5)-(7)):

```
K_b = Xc A_b^T A_b Xc^T
C   = (K_b + α I_n)^{-1} Yc
β_b = A_b^T A_b Xc^T C
```

The block-mixture (superblock) kernel collapses several operators into
one:

```
K   = sum_b s_b^2 Xc A_b^T A_b Xc^T
U   = sum_b s_b^2 A_b^T A_b Xc^T          # shape (p, n)
β   = U C,    with C = (K + α I)^{-1} Yc
```

so `K = Xc U` and the coefficient `β` lives in the original feature
space. The implementation never materialises the wide block matrix
`Phi = [s_1 Xc A_1^T | ... | s_B Xc A_B^T]`; `explicit_superblock`
exists only for the equivalence tests in
`tests/ridge/test_ridge_kernel_equivalence.py`.

Block scales `s_b` follow `aom_nirs/ridge/kernels.py::compute_block_scales_from_xt`:

- `"none"`: `s_b = 1` (raw blocks).
- `"rms"` (default): `s_b = 1 / (RMS(X_b) + ε)` so all blocks share
  approximately the same Frobenius norm.
- `"scale_power"`: soft interpolation between `none` and `rms`.

Solver: Cholesky for well-conditioned kernels, eigen decomposition with
jitter for ill-conditioned cases
(`aom_nirs/ridge/solvers.py::solve_dual_ridge`). The α grid is a
trace-relative log grid (`make_alpha_grid`).

## 8. MKL kernel-target alignment

`aom_nirs/ridge/mkl.py` learns supervised block weights `w_b` on the
simplex via kernel-target alignment (KTA, Cristianini et al.):

```
align_b = <K_b, Y Y^T>_F / (||K_b||_F ||Y Y^T||_F)
w_b     = max(align_b, 0) / sum_b max(align_b, 0)   (top-k mask)
```

Only the top-`k` operators get positive weight; the combined kernel is
*linear* in the weights:

```
K_mkl = sum_b w_b K_b
U_mkl = sum_b w_b A_b^T A_b Xc^T
```

so the standard dual identities still hold and the predict-time
coefficient `β = U_mkl C` is recovered in the original feature space.
KTA is computed fold-locally (the `Y` matrix is the outer-train slice
only) so the weights are leakage-safe.

## 9. The Blender: convex non-negative OOF blend

`aom_nirs/ridge/blender.py` is the paper's headline AOM-Ridge
selector. For each candidate variant `c ∈ {1, ..., K}`:

1. Run an outer K-fold CV. Per fold: fit a fresh estimator from the
   candidate spec on outer-train rows only, predict on outer-val rows,
   write into the candidate's OOF column.
2. Stack OOF columns into `Z ∈ R^{n × K}`.
3. Solve the regularised convex QP

```
min_w   0.5 || y - Z w ||^2 + 0.5 λ || w - (1/K) 1 ||^2
s.t.    w >= 0,  sum_k w_k = 1
```

via `scipy.optimize.minimize(method="SLSQP")` with the simplex
constraint. The regulariser biases the solution toward the uniform
mixture `w = 1/K`, which is the small-`n` fallback to plain averaging.

4. Refit every candidate on the full training set; at predict time
   build `Z_test` and return `Z_test @ w`.

Anti-leakage invariant: the outer-train slice is the only data that
ever flows into the candidate estimators and into the branch
preprocessor for that fold. Verified by
`tests/ridge/test_blender.py` and `tests/ridge/test_no_selector_branch_leak.py`.

## 10. FastAOM screening + low-rank evaluation

FastAOM (`aom_nirs/fast/`) extends AOM to a much larger search space —
*chains* of strict-linear operators applied on top of a small set of
nonlinear bases (Raw, SNV, MSC, EMSC, ASLS, OSC, ...). A chain
`s = (op_1, op_2, ..., op_d)` composes into a single effective matrix
`A_s` (`OperatorChain.matrix`), so the cross-covariance identity still
applies: `(B_j(X) A_s^T)^T y = A_s B_j(X)^T y`.

The adjoint-only covariance score (paper §3.5 / `screening.py`) is

```
score(j, s) = || A_s^T B_j(X)^T y ||^2 / ( || B_j(X) A_s^T ||_F^2 || y ||^2 )
            ∈ [0, 1] by Cauchy-Schwarz
```

with numerator computed as `chain.apply_cov(g_0)` where
`g_0 = B_j(X)^T y` (centered), and denominator approximated from a
truncated SVD of `B_j(X)` as `||F_s||_F^2` with
`F_s = chain.apply_cov(V diag(S))`. The score never materialises
`B_j(X) A_s^T` and avoids one full PLS / Ridge fit per chain.

`diversity_topk` then enforces per-base and per-family caps so the
finalist pool is not swamped by near-duplicate chains from one
operator family (e.g. dozens of slightly different SG-d1 windows).

For the finalists, kernels are computed via a low-rank decomposition.
For each base `B_j(X) ≈ U diag(S) V^T` (rank `r ≈ 50-300`):

```
F_s = A_s V diag(S)                  # shape (p, r)
C_s = F_s^T F_s                      # shape (r, r)
K_s = U C_s U^T                      # implicit n x n kernel
K_s v = U (C_s (U^T v))              # O(n r + r^2) per chain
```

The decomposition is computed once per fold from centered `B_j(X)`,
since PLS and Ridge are translation-invariant when both `X` and `y`
are centered. Implementation: `aom_nirs/fast/lowrank.py::LowRankBase`.

The four FastAOM final models all consume the screened chains plus
the low-rank bases:

| Model | Selection |
| --- | --- |
| `SingleChainPLSRidge` | Best chain only, PLS-then-Ridge. |
| `HardAOMChainPLSRidge` | One chain per PLS component. |
| `SoftAOMChainPLSRidge` | Sparse non-negative chain mixture per component. |
| `SparseMultiKernelRidge` | Greedy NNLS over chain kernels `K_θ = Σ_s θ_s K_s` with `θ_s ≥ 0`. |

The `SparseMultiKernelRidge` greedy step picks the chain whose kernel
best aligns with the current residual:
`score(s) = (y_res^T K_s y_res) / sqrt(trace(K_s K_s) + ε)`, then
refits `θ` via projected-gradient NNLS and `α` by GCV.

## Pointers

For the formal derivations and the discussion that motivates each
choice (e.g. why strict-linear, why dual Ridge, why KTA over learned
weights, why convex blend over a global meta-learner) see:

- `paper/main.tex` §3.1-3.4 — Linear-operator scope, covariance
  identity, AOM-PLS solvers, AOM-Ridge kernels.
- `paper/supplement.tex` — Extended bank, soft / superblock /
  active-superblock derivations, GCV α grid, MKL weights, multi-branch
  MKL, local Ridge.
- `paper/review/aom_code_inventory.md` — per-variant inventory mapping
  each paper claim to the implementing module.
- `paper/review/pls4all_integration_eval.md` — parity oracle for the
  AOM-PLS / POP-PLS core (`pls4all` C++ engine).
