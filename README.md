# nirs4all-aom

**Adaptive Operator-Mixture PLS and Ridge for near-infrared spectroscopy.**

AOM research, reference implementations, experimental extensions and generic benchmarks. Production calibration facades live in `nirs4all-methods`.

This repository ships three sklearn-compatible model families plus benchmark runners:

- **`aom_nirs.pls`** — AOM-PLS, POP-PLS, AOM-PLS-DA, POP-PLS-DA. Operator-adaptive PLS that integrates strict-linear preprocessing operators (identity, Savitzky-Golay, finite difference, detrend, Norris-Williams, Whittaker, FCK) into the calibration via covariance / NIPALS / SIMPLS identities. Replaces external preprocessing grid-search.
- **`aom_nirs.ridge`** — AOM-Ridge family (`AOMRidgeRegressor`, `AOMRidgeBlender`, `AOMRidgeAutoSelector`, `AOMRidgeClassifier`, plus `AOMRidgePLS`, `AOMMultiKernelRidge`, `AOMMultiBranchMKL`, `AOMLocalRidge`). Dual / kernel Ridge with operator-mixture preprocessing.
- **`aom_nirs.fast`** — FastAOM chain-screening framework. Adjoint-only covariance screening with diversity-aware top-k, low-rank kernel evaluator, and four sklearn-style models (`SingleChainPLSRidge`, `HardAOMChainPLSRidge`, `SoftAOMChainPLSRidge`, `SparseChainPLSRidge`).

## Installation

```bash
pip install nirs4all-aom                # core
pip install "nirs4all-aom[torch]"        # GPU NIPALS / SIMPLS / superblock
pip install "nirs4all-aom[tabpfn]"       # TabPFN-residual experimental stacker
pip install "nirs4all-aom[bench]"        # benchmark runners and reporting tools
```

`nirs4all-aom` is pure Python; no compilation is required. The optional `pybaselines` dependency drives `aom_nirs.pls.preprocessing.ASLSBaseline`.

## Python reference examples

```python
from sklearn.model_selection import KFold
from aom_nirs.pls import AOMPLSRegressor
from aom_nirs.ridge import AOMRidgeRegressor, AOMRidgeBlender

inner_cv = KFold(n_splits=5, shuffle=True, random_state=0)
outer_cv = KFold(n_splits=5, shuffle=True, random_state=1)

# Historical AOM-PLS reference preset
aom_pls = AOMPLSRegressor(
    operator_bank="compact",
    criterion="cv",
    cv=inner_cv.get_n_splits(),
    cv_splitter=inner_cv,
)
aom_pls.fit(X_train, y_train)
y_pred = aom_pls.predict(X_test)

# AOM-Ridge, fast single-estimator preset
aom_ridge = AOMRidgeRegressor(
    selection="global",
    operator_bank="compact",
    cv=inner_cv,
)
aom_ridge.fit(X_train, y_train)

# Experimental convex Ridge blend
aom_blender = AOMRidgeBlender(
    outer_cv=outer_cv,
    inner_cv=inner_cv,
)  # convex non-negative blend of Ridge candidates
aom_blender.fit(X_train, y_train)
```

A generic demonstration on one smoke dataset for AOM-PLS, AOM-Ridge, and FastAOM is in `examples/paper_smoke.py`.
For a user-facing split-aware tour of the full AOM family, run `examples/04_aom_panoply.py`.
See `docs/aom_panoply.md` for the standalone AOM splitter guide.

## Live WebAssembly demo

The [AOM-PLS browser demonstration](https://gbeurier.github.io/nirs4all-aom/)
runs the portable `n4m` engine entirely in WebAssembly, screens its strict-linear
operator bank and predicts held-out raw spectra from original-grid coefficients.
Its self-contained source and staged bundle are in [`demo/wasm`](demo/wasm/).

## Relationship to other repos

- **`nirs4all`** ([GitHub](https://github.com/GBeurier/nirs4all)) — NIRS instrumentation, acquisition, and provenance context for local benchmark inputs. This repository contains AOM research and generic benchmark tooling; production methods live in `nirs4all-methods`, and publication artifacts are maintained privately in `nirs4all-drafts`.
- **`aompls`** ([GitHub](https://github.com/GBeurier/aompls)) — older multi-language prototype. Superseded by `nirs4all-aom` for the Python reference implementation used in the paper.

## Paper

Manuscripts, supplements, editorial reviews and submission-specific experiments
are maintained in the private `nirs4all-drafts` repository until submission.
The public repository contains the AOM research code, generic experiments and
demonstration. Stable production implementations are consolidated in
[`nirs4all-methods`](https://github.com/GBeurier/nirs4all-methods).

## License

`nirs4all-aom` is dual-licensed open-source — **`CeCILL-2.1 OR AGPL-3.0-or-later`** (your choice) —
with an optional **commercial license** for closed-source / SaaS use. For any commercial use, contact
<nirs4all-admin@cirad.fr>. See [`LICENSING.md`](LICENSING.md), the texts under [`LICENSES/`](LICENSES/),
and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Citation

```bibtex
@software{beurier_aom_nirs_2026,
  author = {Beurier, Gregory},
  title  = {nirs4all-aom: Adaptive Operator-Mixture PLS and Ridge for NIR spectroscopy},
  year   = {2026},
  url    = {https://github.com/GBeurier/nirs4all-aom},
  version = {0.10.4}
}
```
