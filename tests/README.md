# nirs4all-aom tests

Suite organised by package. Run from the repo root.

```bash
pytest tests/                  # all tests
pytest tests/pls/              # AOM-PLS only
pytest tests/ridge/            # AOM-Ridge only
pytest tests/fast/             # FastAOM only
pytest tests/ -k "not slow"    # skip slow tests if any are marked
pytest tests/ -x               # stop on first failure
pytest --cov=aom_nirs tests/   # with coverage
```

## Layout

- `tests/pls/` — 16 files covering the AOM-PLS package
  - `test_estimators.py`, `test_classification.py` — fit/predict semantics
  - `test_nipals.py`, `test_simpls.py` — engine parity (standard / materialized / adjoint / covariance)
  - `test_selection.py` — five selection policies + fold safety
  - `test_operators.py` — operator math (adjoint identity, transform, apply_cov)
  - `test_active_superblock.py` — beam search exploration
  - `test_explorer.py`, `test_fck_operator.py` — operator generation
  - `test_parity_with_production.py` — bench → installed `nirs4all` parity (skipped if `nirs4all` not on the path)
  - `test_torch_parity.py` — torch backend bit-exact vs numpy (skipped if `[torch]` extra not installed)
  - `test_aom_pls_wrapper.py`, `test_aom_pls_classifier_wrapper.py`, `test_pop_pls_wrapper.py` — copies of the `nirs4all` wrapper-level tests, retargeted at `aom_nirs.pls`
- `tests/ridge/` — 24 files covering AOM-Ridge
  - `test_ridge_estimators.py`, `test_ridge_solvers.py`, `test_ridge_kernel_equivalence.py` — dual / kernel Ridge math
  - `test_ridge_cv_no_leakage.py`, `test_ridge_branch_global.py`, `test_no_selector_branch_leak.py` — anti-leakage invariants
  - `test_blender.py`, `test_auto_selector.py`, `test_local_ridge.py`, `test_multi_branch_mkl.py`, `test_mkr_*` — selectors / ensemble classes
  - `test_ridge_classifier.py`, `test_ridge_pls.py`, `test_ridge_selection.py` — classifier and selection helpers
  - `test_split_aware_cv.py`, `test_ridge_one_se_and_repeated_cv.py` — SPXY-aware CV
  - `test_ridge_round3_fixes.py` — post-review correctness regression set
- `tests/fast/` — 8 files covering FastAOM
  - `test_bases.py`, `test_grammar.py` — chain prerequisites
  - `test_operator_chain.py`, `test_lowrank_screening.py`, `test_xcorr_fast.py` — chain math + screening
  - `test_models.py` — the four AOM-style models + the orchestrator

## Fixtures

`tests/{ridge,fast}/conftest.py` provide synthetic data generators sized for
unit tests. No real NIR data is used in unit tests — every fixture is a
seeded numpy RNG. The PLS suite uses inline fixtures from
`aom_nirs/pls/synthetic.py`.

## Markers

No custom pytest markers are required; tests skip themselves via
`pytest.importorskip` when optional extras are missing (`torch`, `tabpfn`,
`nirs4all`).

## Companion suite

The same wrapper-level tests are mirrored in `nirs4all/tests/unit/operators/
models/test_aom_pls*.py` and `test_pop_pls.py`. They exercise the thin
re-export at `nirs4all/operators/models/sklearn/aom_pls.py` etc., which
imports from the vendored `nirs4all/operators/models/_aom_nirs/` tree.
Keeping both in sync helps catch import-path drift early.
