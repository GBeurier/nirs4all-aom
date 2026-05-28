# Contributing

Thanks for considering a contribution to `aompls`. The library is small
(~2,000 LOC of C++ + ~500 LOC per binding) and parity-driven: every change
must preserve numerical equivalence with the upstream Python reference.

## Development setup

```bash
git clone https://github.com/GBeurier/aompls.git
cd aompls

# C++ build (Linux/macOS):
cd cpp && mkdir -p build
c++ -std=c++17 -O2 -DEIGEN_NO_DEBUG -DEIGEN_DONT_PARALLELIZE \
    -I include tests/test_operators.cpp -o build/test_operators
c++ -std=c++17 -O2 -DEIGEN_NO_DEBUG -DEIGEN_DONT_PARALLELIZE \
    -I include tests/test_parity_kfold.cpp -o build/test_parity_kfold
./build/test_operators && ./build/test_parity_kfold tests/reference

# Python:
cd .. && pip install -e python/
pytest python/tests/

# R:
./scripts/sync_headers.sh
R CMD INSTALL r/aompls
AOMPLS_REF_DIR=$(pwd)/cpp/tests/reference \
  Rscript -e 'library(aompls); library(testthat); test_dir("r/aompls/tests/testthat")'
```

## The parity gate is non-negotiable

Every PR that touches the C++ core, scoring, or selection logic MUST keep
all three of these passing:

- `cpp/build/test_parity_kfold tests/reference` — coef Δ < 1e-8, predictions
  Δ < 1e-8, RMSE curves Δ < 1e-9.
- `pytest python/tests/` — 9/9 cases.
- R `testthat::test_dir(...)` — 54/54 assertions.

When in doubt, regenerate the JSON fixtures from the upstream reference:

```bash
NIRS4ALL_BENCH=/path/to/nirs4all/bench/AOM_v0 \
    python scripts/export_reference.py
```

## Style

- C++: header-only, no exceptions in hot paths, prefer `Eigen::Ref<>` for
  read-only matrix parameters, document operator order changes as breaking
  changes (the bank ordering is serialised model state).
- Python: pure-Python wrappers stay sklearn-compatible. New options must
  appear in `AOMPLSCompact.__init__` AND in the pybind11 binding signature.
- R: keep `aom_pls()` argument names matching the Python signature where
  feasible; document divergences inline.

## Adding a new language binding

1. Decide on the FFI strategy (direct C++ via the package's native build,
   or C ABI via `libaompls.so`). Document this choice in the binding's
   directory README.
2. Implement at minimum `fit(X, y, opts) → model` and `predict(model, X) → ŷ`.
3. Add a parity test that loads the JSON fixtures and asserts the same
   tolerances as the existing bindings.
4. Wire the new binding into `.github/workflows/ci.yml`.

## Releases

See [`PUBLISHING.md`](PUBLISHING.md). Tagging `vX.Y.Z` on `main` triggers
the release workflow which builds wheels, an R source tarball, and a
GitHub Release. PyPI uploads require the `pypi` environment secret to be
configured in the repo settings.
