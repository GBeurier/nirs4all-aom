# aom-nirs

**Adaptive Operator-Mixture PLS and Ridge for near-infrared spectroscopy.**

Companion code for the Talanta paper *"Operator-adaptive PLS and Ridge calibration for NIR spectroscopy"* (manuscript in `paper/`).

This repository ships three sklearn-compatible model families plus benchmark runners:

- **`aom_nirs.pls`** — AOM-PLS, POP-PLS, AOM-PLS-DA, POP-PLS-DA. Operator-adaptive PLS that integrates strict-linear preprocessing operators (identity, Savitzky-Golay, finite difference, detrend, Norris-Williams, Whittaker, FCK) into the calibration via covariance / NIPALS / SIMPLS identities. Replaces external preprocessing grid-search.
- **`aom_nirs.ridge`** — AOM-Ridge family (`AOMRidgeRegressor`, `AOMRidgeBlender`, `AOMRidgeAutoSelector`, `AOMRidgeClassifier`, plus `AOMRidgePLS`, `AOMMultiKernelRidge`, `AOMMultiBranchMKL`, `AOMLocalRidge`). Dual / kernel Ridge with operator-mixture preprocessing. The paper's best empirical result (median RMSEP ratio 0.918 vs Ridge-default on 32 NIRS datasets, Wilcoxon Holm-corrected $p = 2.6\times 10^{-4}$).
- **`aom_nirs.fast`** — FastAOM chain-screening framework. Adjoint-only covariance screening with diversity-aware top-k, low-rank kernel evaluator, and four sklearn-style models (`SingleChainPLSRidge`, `HardAOMChainPLSRidge`, `SoftAOMChainPLSRidge`, `SparseMultiKernelRidge`).

## Installation

```bash
pip install aom-nirs                # core
pip install "aom-nirs[torch]"        # GPU NIPALS / SIMPLS / superblock
pip install "aom-nirs[tabpfn]"       # TabPFN-residual experimental stacker
pip install "aom-nirs[bench]"        # benchmark runners and reporting tools
```

`aom-nirs` is pure Python; no compilation is required. The optional `pybaselines` dependency drives `aom_nirs.pls.preprocessing.ASLSBaseline`.

## Quick start

```python
from sklearn.cross_decomposition import PLSRegression
from sklearn.model_selection import KFold
from aom_nirs.pls import AOMPLSRegressor
from aom_nirs.ridge import AOMRidgeRegressor, AOMRidgeBlender

# AOM-PLS, paper "simple" preset
aom_pls = AOMPLSRegressor(bank="compact", criterion="cv", cv=5)
aom_pls.fit(X_train, y_train)
y_pred = aom_pls.predict(X_test)

# AOM-Ridge, paper "best" preset
aom_ridge = AOMRidgeBlender()        # convex non-negative blend of Ridge candidates
aom_ridge.fit(X_train, y_train)
```

A full reproduction of one smoke dataset for AOM-PLS, AOM-Ridge, and FastAOM is in `examples/paper_smoke.py`.

## Relationship to other repos

- **`nirs4all`** ([GitHub](https://github.com/GBeurier/nirs4all)) — production NIRS pipeline library. `nirs4all` currently vendors a copy of `aom-nirs` under `nirs4all/operators/models/_aom_nirs/`. Once `aom-nirs` reaches PyPI, the vendored copy becomes a runtime dependency.
- **`pls4all`** ([GitHub](https://github.com/GBeurier/pls4all)) — C++ engine with a stable C ABI and Python bindings. Phase 6a-6f ships the AOM-PLS / POP-PLS *core* (global AOM-SIMPLS CV selection, POP per-component SIMPLS covariance selection) in C++. `aom-nirs` is the Python reference; `pls4all/parity/fixtures/synthetic_aom_*_v1.json` are bit-exact oracles. See `paper/review/pls4all_integration_eval.md`.
- **`aompls`** ([GitHub](https://github.com/GBeurier/aompls)) — older multi-language port (C++/R/Julia/MATLAB/JS). Superseded by `aom-nirs` (Python) plus `pls4all` (C++).

## Paper

The Talanta manuscript and supplement live under `paper/`. The review dossier (`paper/review/`) contains the inventory, migration plan, and pls4all-integration evaluation that drove this code release. See `paper/review/aom_code_inventory.md` for the per-variant score evidence.

## License

Dual-license: **AGPL-3.0-or-later** (default open-source) or commercial. See `LICENSE`.

## Citation

```bibtex
@software{beurier_aom_nirs_2026,
  author = {Beurier, Gregory},
  title  = {aom-nirs: Adaptive Operator-Mixture PLS and Ridge for NIR spectroscopy},
  year   = {2026},
  url    = {https://github.com/GBeurier/aom},
  version = {0.1.0}
}
```
