# nirs4all-aom

**Adaptive Operator-Mixture PLS and Ridge for near-infrared spectroscopy.**

Companion code for the paper *"Operator-adaptive PLS and Ridge calibration for NIR spectroscopy"* (manuscript in `paper/`).

This repository ships three sklearn-compatible model families plus benchmark runners:

- **`aom_nirs.pls`** — AOM-PLS, POP-PLS, AOM-PLS-DA, POP-PLS-DA. Operator-adaptive PLS that integrates strict-linear preprocessing operators (identity, Savitzky-Golay, finite difference, detrend, Norris-Williams, Whittaker, FCK) into the calibration via covariance / NIPALS / SIMPLS identities. Replaces external preprocessing grid-search.
- **`aom_nirs.ridge`** — AOM-Ridge family (`AOMRidgeRegressor`, `AOMRidgeBlender`, `AOMRidgeAutoSelector`, `AOMRidgeClassifier`, plus `AOMRidgePLS`, `AOMMultiKernelRidge`, `AOMMultiBranchMKL`, `AOMLocalRidge`). Dual / kernel Ridge with operator-mixture preprocessing. The paper's best empirical result (median RMSEP ratio 0.918 vs Ridge-default on 32 NIRS datasets, Wilcoxon Holm-corrected $p = 2.6\times 10^{-4}$).
- **`aom_nirs.fast`** — FastAOM chain-screening framework. Adjoint-only covariance screening with diversity-aware top-k, low-rank kernel evaluator, and four sklearn-style models (`SingleChainPLSRidge`, `HardAOMChainPLSRidge`, `SoftAOMChainPLSRidge`, `SparseChainPLSRidge`).

## Installation

```bash
pip install nirs4all-aom                # core
pip install "nirs4all-aom[torch]"        # GPU NIPALS / SIMPLS / superblock
pip install "nirs4all-aom[tabpfn]"       # TabPFN-residual experimental stacker
pip install "nirs4all-aom[bench]"        # benchmark runners and reporting tools
```

`nirs4all-aom` is pure Python; no compilation is required. The optional `pybaselines` dependency drives `aom_nirs.pls.preprocessing.ASLSBaseline`.

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

- **`nirs4all`** ([GitHub](https://github.com/GBeurier/nirs4all)) — NIRS instrumentation, acquisition, and provenance context for local benchmark inputs. The AOM methods, benchmark runners, result tables, and manuscript artifacts are distributed from this `nirs4all-aom` repository.
- **`aompls`** ([GitHub](https://github.com/GBeurier/aompls)) — older multi-language prototype. Superseded by `nirs4all-aom` for the Python reference implementation used in the paper.

## Paper

The manuscript and supplement live under `paper/`. The review dossier (`paper/review/`) contains the inventory, migration plan, cohort coverage audit, and per-variant score evidence used for the arXiv draft.

## License

Dual-license: **AGPL-3.0-or-later** (default open-source) or commercial. See `LICENSE`.

## Citation

```bibtex
@software{beurier_aom_nirs_2026,
  author = {Beurier, Gregory},
  title  = {nirs4all-aom: Adaptive Operator-Mixture PLS and Ridge for NIR spectroscopy},
  year   = {2026},
  url    = {https://github.com/GBeurier/nirs4all-aom},
  version = {0.1.0}
}
```
