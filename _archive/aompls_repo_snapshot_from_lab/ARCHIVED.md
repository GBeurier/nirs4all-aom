# aompls — Archived

This is a snapshot of the standalone `aompls` repository (formerly at
`github.com/GBeurier/aompls`), preserved here for historical reference.

## Status

**Archived — no longer maintained.**

The AOM-PLS algorithm (and the broader PLS family it explored: POP-PLS,
multi-language bindings, etc.) has been reimplemented natively inside
`pls4all` and is exposed through `nirs4all` (see
`nirs4all.operators.models.AOMPLSRegressor`, `AOMPLSClassifier`,
`POPPLSRegressor`, `POPPLSClassifier`). All future development happens
there; this snapshot is kept only for traceability.

## Snapshot details

- Source: `github.com/GBeurier/aompls`
- Last commit: `5908b80` — *r: prepare DESCRIPTION and add man/*.Rd for CRAN* (2026-05-13)
- Tag at archive time: v0.1.0

## Contents

Multi-language reference implementations of AOM-PLS:

- `cpp/` — C++ implementation with Eigen, reference test vectors
- `python/` — Python package (pybind11 bindings)
- `r/` — R package (Rcpp bindings)
- `julia/` — Julia package
- `js/` — JavaScript / WASM
- `matlab/` — MATLAB / mex
- `packaging/`, `scripts/` — CI, release, header-sync tooling

Build artefacts (`.o`, `.so`, `.wasm`, `__pycache__`, etc.) and the
regenerated vendored Eigen headers (`r/aompls/inst/include/`) were
excluded — only files tracked by git are kept.

## If you need to revive it

The snapshot is self-contained: `cd python && pip install -e .` (or the
equivalent in each language directory) should still work. But you almost
certainly want to use `pls4all` / `nirs4all` instead.
