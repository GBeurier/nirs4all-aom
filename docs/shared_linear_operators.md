# Shared strict-linear projector & weighting operators (EPO, GLSW) for the AOM bank

> New strict-linear operators introduced while building AOM-based calibration transfer
> (`nirs4all-lab/AOM-transfer/`). They are documented here because they are **not
> transfer-specific**: they are ordinary strict-linear preprocessing operators that satisfy
> the AOM cross-covariance identity, drop into the operator bank, and may improve ordinary
> **prediction**, not only transfer. Reference implementation:
> `nirs4all-lab/AOM-transfer/aom_transfer/transfer_operators.py`.

## 1. Why they belong in the AOM bank

AOM screens an operator `A` by the order-1 cross-covariance identity
`(X Aᵀ)ᵀ y = A (Xᵀ y)`, valid for **any fixed matrix** `A ∈ ℝ^{p×p}` independent of `y`,
fold and sample (Prop. 1, `docs/math.md`). Both operators below are fixed `p×p` matrices
once their (data-derived) parameters are set, so:

- they satisfy `S → A S` and the order-2 congruence `C → A C Aᵀ` exactly;
- they expose `apply_cov` / `adjoint_vec` in `O(p·k)` (projector) or `O(p²)` (dense
  weighting) **without materializing `X Aᵀ`**;
- they compose with SG / derivative / detrend / Whittaker into FastAOM chains
  (`A_s = A_d···A_1` is still a fixed matrix).

They generalise the detrend projector (`I − QQᵀ`) and OSC-style filtering to an arbitrary,
data-chosen nuisance subspace.

## 2. EPO projector — `EPOProjectionOperator`

```
A = I − V Vᵀ ,     V ∈ ℝ^{p×k} orthonormal
apply_cov(S) = S − V (Vᵀ S)          adjoint_vec(v) = v − V (Vᵀ v)   (symmetric idempotent)
matrix(p)    = I − V Vᵀ
```

An orthogonal projector that **removes the `k`-dimensional nuisance subspace** spanned by
`V`. It is strict-linear (a fixed projector once `V` is chosen), so AOM's identities hold
verbatim; cost is `O(p·k)` per apply.

**Choosing `V`.**
- *Calibration transfer* (its origin): `V` = top-`k` right singular vectors of the paired
  difference spectra `D = X_target_std − X_source_std` (the inter-instrument subspace) —
  this is the feature-axis EPO/TOP of Roger 2003 / Andrew–Fearn 2004, applied identically
  to both instruments.
- *Prediction*: `V` can target **any** structured nuisance — replicate/repeat-scan
  difference directions, temperature/scatter/clutter directions, or a baseline subspace.
  If `V` is derived from `y` (OSC-style, deflating directions orthogonal to the response)
  the operator becomes **supervised** — still linear at apply, but no longer `y`-agnostic;
  keep that distinct from the unsupervised projector.

**Load-bearing hyperparameter — the rank `k`.** In the transfer experiments the *available
rank range* was decisive: a bank with only `k ∈ {1,2,3}` under-removed the nuisance subspace
and lost badly (corn moisture m5→mp5 RMSEP ≈ 0.30), while `k = 8` reached **0.124** (better
than a tuned standalone EPO). **Span the rank** (e.g. `{1,2,3,5,8,12,16}`) and let the
screen/CV pick; do not assume a small `k`.

## 3. GLSW weighting — `SymmetricWeightOperator`

```
A = W = (C_clutter + α² I)^{-1/2}     (symmetric, SPD)
apply_cov(S) = W S        adjoint_vec(v) = W v        matrix(p) = W
transform(X) = X W        (W symmetric ⇒ X Aᵀ = X W)
```

A full-rank symmetric weighting that **down-weights high-clutter directions** (a soft,
plain-rank analogue of EPO). `α` is the only hyperparameter — the **ε-ridge** that sets how
aggressively clutter is suppressed (small `α` → stronger suppression but ill-conditioning;
sweep `α ∈ {1e-3 … 1}`). At `n < p`, shrink `C_clutter` (Ledoit–Wolf) before the inverse.

**Choosing `C_clutter`.** Transfer: the paired-difference covariance `DᵀD/(k−1)`.
Prediction: a replicate/within-group clutter covariance, or any nuisance covariance whose
directions should be attenuated relative to the analyte.

## 4. Asymmetric target→source maps (DS / PDS / SST) — also moment-computable, but a *different* class

A frequent question: *can PDS/DS be expressed in the AOM/moment framework?* The correction
maps are themselves **fixed linear operators** — DS is a dense `F = (X_t^{std})^+ X_s^{std}`,
PDS a **banded** `F` (a local window regression per channel) — so their effect on the moment
set is closed-form:

```
target corrected by F:   μ_t → F μ_t ,   C_t → F C_t Fᵀ ,   shift δ_F = μ_s − F μ_t
```

Hence a **family of DS/PDS/SST maps** (varying window / regularisation / rank) **can be
scored by the same moment-space alignment criterion** as the shared operators
(`‖R^T δ_F‖² + λ‖R^T(C_s − F C_t Fᵀ)R‖²_F`), i.e. they are *screenable in moment space*.

The crucial difference is **symmetry/scope**, not screenability:

| | EPO / GLSW (here) | DS / PDS / SST |
|---|---|---|
| applied to | **both** instruments (shared `A`) | **target only** (asymmetric `F`) |
| deployable object | one calibration on the original grid, **no replay** | a transported map `F` + the model |
| AOM category | **i** (shared strict-linear, in this bank) | **ii** (instrument-specific, transported) |

So EPO/GLSW are *members of the shared bank*; DS/PDS/SST are a distinct, **asymmetric**
operator family. They can be unified under one moment-space screen (select the best of
shared-vs-instrument-specific per dataset), but a shared `A` cannot in general reproduce a
PDS-induced pair (isospectrality, AOM transfer note §7). For pure **prediction** (single
instrument) the asymmetric maps are not relevant; EPO/GLSW are.

## 5. API & integration

Both subclass `aom_nirs.pls.operators.LinearSpectralOperator` and are drop-in for
`simpls_covariance`, `fast_covariance_screen`, banks and chains:

```python
from aom_transfer.transfer_operators import (
    EPOProjectionOperator, SymmetricWeightOperator, build_epo, build_glsw)

epo = build_epo(X_ref_a, X_ref_b, n_epo=8)        # V from difference SVD; or pass V directly
glsw = build_glsw(X_ref_a, X_ref_b, alpha=1e-2)   # W from clutter covariance
bank = bank_by_name("default", p=p) + [build_epo(...) for k in (1,2,3,5,8,12,16)] + [glsw]
```

**Leakage discipline.** Both are *data-derived* (V / clutter estimated from data). When used
inside cross-validation, **re-estimate them inside each fold** so they are never scored in
sample; a `y`-derived `V` (OSC-style) is supervised and must be nested as such.

## 6. Status

Implemented and validated in `nirs4all-lab/AOM-transfer/` (the closed-form screen using these
operators matches a brute-force reference to 3e-15). Candidates for graduation into the
`aom_nirs` operator set if they prove useful as general predictive preprocessing; the rank-`k`
EPO family in particular behaves like a tunable, data-chosen detrend/OSC and is cheap to screen.
