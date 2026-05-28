# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-05-13

Initial release. Extracted from the `nirs4all` benchmark tree
(`bench/AOM_v0`) as a standalone, dependency-free library.

### Added

- **C++17 header-only core** with vendored Eigen 3.4.0 (MPL 2.0).
- **Compact operator bank** (9 strict-linear operators): identity, Savitzky-Golay
  smoothing (w=11,21), 1st and 2nd derivatives, polynomial detrend (degrees 1, 2),
  finite difference.
- **Materialised SIMPLS** engine with auto-prefix CV scoring, optional one-SE
  parsimony rule, K-fold / SPXY / holdout / EXTERNAL split modes.
- **One-shot preprocessing**: SNV, MSC, OSC (Wold 1998), ASLS (Eilers-Boelens 2005),
  plus `snv+osc` and `asls+osc` combinations.
- **C ABI** (`cpp/include/aompls/c_api.h`, `cpp/src/c_api.cpp`) producing
  `libaompls.so` for FFI consumers.
- **Python** package `aompls` via pybind11 — sklearn-compatible `AOMPLSCompact`
  estimator, `tune()` outer-K-fold HPO wrapper.
- **R** package `aompls` via Rcpp — `aom_pls()`, `predict.aom_pls()`,
  `aom_pls_tune()`.
- **MATLAB** MEX wrapper (`matlab/aompls_mex.cpp`) with `.m` helpers.
- **Julia** package `AompLS.jl` calling `libaompls.so` through `ccall`.
- **JavaScript / WASM** bundle via Emscripten + Embind (Node.js + browser).
- **Parity gate** (BEER, CORN, ALPINE × KFold5 / KFold5+oneSE / SPXY5):
  - C++ unit tests pass (coef Δ ≤ 2.9e-12, predictions Δ ≤ 1.3e-13,
    RMSE curves Δ ≤ 9e-15).
  - Python: 9/9 pytest cases pass.
  - R: 54/54 testthat assertions pass.

### Known limitations

- PLS1 only (`q == 1`). PLS2 (multi-target) is not supported in v1.
- C++ KFold uses its own LCG-based shuffler — **not bit-compatible** with
  `sklearn.KFold(shuffle=True, random_state=...)`. Use `cv_mode = "external"`
  with externally supplied fold indices for bit-exact parity.
- ASLS hyperparameters are exposed via `AOMConfig::asls` but are not part of
  the inner CV search; tune via the outer HPO wrapper.
- MATLAB / Julia / JS bindings ship verified source code but require their
  respective toolchains (`mex`, `julia`, `emsdk`) to compile locally.
