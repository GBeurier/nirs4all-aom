# AOM library migration plan

**Generated:** 2026-05-17.
**Companion:** `aom_code_inventory.md` (the *what*) → this doc (the *where*, *how*, *in what order*).
**Goal:** ship a code release that lets a Talanta reviewer (and any future user) reproduce every paper headline, with the variant triage from `final_stats.md` baked into the public API.

This plan answers three questions:

1. **Where does the code live after migration?** — three repo strategies (§2), with one recommendation.
2. **What ships and what does not?** — per-module migration table (§4) and variant triage (§5).
3. **In what order, with what effort?** — phased rollout (§6) + reproducibility checklist for the paper itself (§7).

---

## 1. Constraints driving the plan

- **Hard deadline:** Talanta submission needs (a) code that runs `examples/U01_aompls_compact.py` from a clean clone, and (b) one command that reproduces a smoke subset of the paper. Anything not on that critical path is post-submission.
- **Headline result is single-seed.** AOM-Ridge Blender is the strongest empirical claim (median RMSEP ratio 0.918, $p_{\mathrm{Holm}}=2.6\mathrm{e}{-04}$); we cannot ship it without seeds 1, 2 results.
- **Three coexisting AOM-PLS Python implementations.** `nirs4all/.../aom_pls.py` (pure-Python NIPALS), `aom_pls_aomlib.py` (C++ wrapper), `bench/AOM_v0/aompls/estimators.py` (bench paper-grade). Migration **must** pick one canonical and deprecate the others — anything else doubles maintenance forever.
- **pls4all is C++/ABI-first, not Python-first.** It can be a parity reference but not a near-term host for Python AOM-PLS/AOM-Ridge/FastAOM (see `pls4all_integration_eval.md`).
- **No regression in library install.** `pip install nirs4all` must keep working without TabPFN, without the C++ `aompls`, without `torch`. All optional deps go behind extras.

---

## 2. Repo strategy — three options

### Option A — Everything under `nirs4all.operators.models` (no new repo)

```
nirs4all/operators/models/aom/
├── pls/                     # was bench/AOM_v0/aompls/
│   ├── operators.py, banks.py, nipals.py, simpls.py, selection.py,
│   │   scorers.py, estimators.py, classification.py, preprocessing.py,
│   │   centering.py, diagnostics.py, metrics.py, operator_explorer.py,
│   │   operator_generation.py, operator_similarity.py, synthetic.py,
│   │   torch_backend.py, __init__.py
├── ridge/                   # was bench/AOM_v0/Ridge/aomridge/
│   └── (21 .py — drop residual_tabpfn / tabpfn_candidate from default,
│        keep behind extras[tabpfn])
└── fast/                    # was bench/AOM_v0/FastAOM/
    └── (11 .py)
```

- **Pros:** single `pip install nirs4all`; users get AOM everywhere; no new packaging work; CI is already wired; everything in `nirs4all.operators.models` is already on the public release flow.
- **Cons:** the paper cannot cite "the AOM repo"; users who only want AOM pull the full `nirs4all` dependency tree (sklearn-pipeline / pyarrow / duckdb / etc.); FastAOM and AOM-Ridge are larger than what `operators/models` typically holds (~25k LOC); release cadence is tied to `nirs4all` cadence.
- **Effort:** ~3-5 dev-days (move + import-path rewrite + dedupe with existing `aom_pls.py` / `pop_pls.py`). No new infra.
- **Best for:** if Talanta is in 2 weeks and the only goal is "code reachable from the paper".

### Option B — New Python repository `aom-nirs` (recommended)

```
/home/delete/nirs4all/aom/              # new repo (gbeurier/aom GitHub)
├── pyproject.toml                       # package name: aom-nirs
├── aom_nirs/
│   ├── pls/, ridge/, fast/, banks/, operators/, ...
│   ├── examples/                        # one-script reproductions of paper headlines
│   └── benchmarks/                      # the smoke runner + cohort manifests
├── tests/                               # all bench tests, paths updated
├── docs/                                # MkDocs site with paper math + variant table
├── .github/workflows/{ci.yml,release.yml}
└── README.md                            # cites Talanta paper, links to pls4all
```

- **Pros:** the paper cites *one* DOI / GitHub URL (`gbeurier/aom`); `pip install aom-nirs` works without pulling `nirs4all`; release cadence independent of `nirs4all` so seeds 1/2 / HPO gap fill can ship as `0.1.1`, `0.1.2`; clean public API with no historical bench cruft. Talanta reviewers can run the smoke test in one minute.
- **Cons:** new CI pipeline, new PyPI namespace, ~1-2 days of packaging work; users who already have `nirs4all` need a second install; cross-reference docs (when to use `aom-nirs` vs `nirs4all.operators.models.aom_pls`) take care.
- **Bridge with `nirs4all`:** `nirs4all` keeps thin sklearn-compatible wrappers (`AOMPLSRegressor`, `AOMRidgeRegressor`, `FastAOMPLSRegressor`) that re-export from `aom_nirs` and raise a clean `ImportError` if `aom-nirs` is not installed. Pattern mirrors `aom_pls_aomlib.py`.
- **Effort:** ~5-8 dev-days (split + packaging + CI + thin lib wrappers + import-path rewrites).
- **Best for:** Talanta submission + medium-term sustainability. **This is the recommended option.**

### Option C — Subpackage `pls4all/bindings/python/aom/`

Add AOM as a Python module hosted by the existing `pls4all` repo, alongside the ctypes bindings.

- **Pros:** uses the existing repo brand (`pls4all`); citation surface already exists (`CITATION.cff`); leverages the planned PyPI wheel for `pls4all`; long-term lets AOM operators get C++ implementations under the same roof.
- **Cons:** the pls4all binding model says bindings "translate native objects, call `p4a_*`, translate results back, and **never own numerical logic**" (`pls4all/ARCHITECTURE.md:29,38`). Hosting 25 kLOC of Python AOM logic in `bindings/python/aom/` contradicts that model — bindings would suddenly *own* numerical logic. The right pls4all-native path is to add a C++ AOM implementation behind the C ABI and let bindings call it. README and Overview already frame AOM as C++-owned core (`pls4all/README.md:7`, `pls4all/Overview.md:672,1012`). Without the C++ port being ready, Option C is architecturally awkward (not forbidden, but inconsistent with the documented binding role).
- **Cons (timing):** `pls4all` Python wheel is "not yet on PyPI" (README); phase-6 ships AOM/POP as first-class C++ but the Python bindings parity is at 62% (sklearn 42/68). Locking the Talanta release to `pls4all` v1.0 means waiting.
- **Effort:** ~10-15 dev-days (packaging + ABI decisions + the same import-path / dedupe work as B, plus reconciling with the C++ AOM-PLS already in `pls4all/cpp/`).
- **Best for:** post-Talanta, once `pls4all` v1.0 ships and Python wheels are on PyPI. See `pls4all_integration_eval.md` for the longer-term roadmap.

### 2.1 Recommendation

**Option B for Talanta submission, with a documented Option C migration path for v1.0.** Concretely:

- Create `/home/delete/nirs4all/aom/` repo, PyPI package `aom-nirs`. The internal name `aom_nirs` avoids the existing C++ `aompls` PyPI claim.
- `nirs4all` ships thin re-export wrappers (one file each: `aom_pls.py`, `aom_ridge.py`, `aom_fast.py`) that depend on `aom-nirs` as an optional `[aom]` extra.
- `pls4all/CITATION.cff` and `pls4all/README.md` get a one-line "Python reference: `gbeurier/aom`" link.
- Within 1-2 minor releases of `pls4all` v1.0 reaching parity, we revisit Option C.

This recommendation matches what `pls4all`'s phase-6 plan already assumes (the README says it cross-checks against `nirs4all/bench/AOM_v0/aompls`, i.e. expects the Python reference to live elsewhere).

---

## 3. Reconciling the three coexisting AOM-PLS implementations

| Implementation | Backend | Built-in CV folds | Default bank | Best fitness |
| --- | --- | --- | --- | --- |
| `nirs4all/operators/models/sklearn/aom_pls.py` (pure-Python NIPALS) | numpy + optional torch | No (holdout only) | ~38 ops | educational, GPU experiments |
| `nirs4all/operators/models/sklearn/aom_pls_aomlib.py` (C++ wrapper) | `aompls.AOMPLSCompact` (C++ via `bench/AOM_lib`) | yes (`cv`, `kfold`, `spxy`, `holdout`, `external`) | 9-op compact | Talanta-faithful, production |
| `bench/AOM_v0/aompls/estimators.py` (bench paper-grade NumPy) | numpy + optional torch | yes (`scorers.cv_score_regression`, repeated, one-SE) | 9 / 100 / extended | paper-faithful, dual NIPALS+SIMPLS |

**Decision:** `bench/AOM_v0/aompls/estimators.py` becomes the canonical AOM-PLS implementation in `aom-nirs`. Reasons:

- It is the *newest* and *cleanest* code; it has both NIPALS and SIMPLS engines (the C++ wrapper has only one; the pure-Python has only NIPALS).
- It carries the paper's covariance identity proof in the code comments (lines around the SIMPLS covariance derivation).
- It supports the full selection-policy menu (global / per-component / soft / superblock / none) that the paper uses for ablations.
- Test parity is already validated against `nirs4all` production by `bench/AOM_v0/tests/test_parity_with_production.py`.

### 3.1 Feature audit before deletion

The current pure-Python `nirs4all/operators/models/sklearn/aom_pls.py` carries non-paper features that the bench class does **not** expose. Before any wrapper-replacement these must be either re-implemented or explicitly deprecated:

| Feature in current lib `aom_pls.py` | Status in `bench/AOM_v0/aompls/estimators.py` | Migration decision |
| --- | --- | --- |
| `gate='sparsemax'` (`nirs4all/.../aom_pls.py:742, 1084, 1371`) | Not present | **Deprecate.** Not in paper; current users (search of `nirs4all`/`examples`/`paper_aom` finds no internal caller passing this argument). Emit `DeprecationWarning` for one minor release, then drop. |
| `WaveletProjection` operator (`aom_pls.py:446`) | Not in bench bank | **Deprecate** from default banks; if external users need it, expose as `aom_nirs.pls.experimental.WaveletProjection`. |
| `FFTBandpass` operator (`aom_pls.py:520`) | Not in bench bank | Same: experimental, behind explicit import. |
| Torch dispatch in `fit()` (`aom_pls.py:1208, 1434`) | Bench has `torch_backend.py` but does not dispatch from `fit` (`bench/AOM_v0/aompls/estimators.py:155`) | **Port the dispatch** into `aom_nirs.pls.estimators` (call `torch_backend.aompls_fit_torch` when `backend='torch'`). This is a 1-day port; do it as part of Phase 1 so the wrapper does not silently regress. |

If we do not preserve these (or explicit deprecate them), `nirs4all`'s public API silently changes — that violates the "no regression" constraint in §1.

**Migration outcome for the three lib files:**

- `nirs4all/operators/models/sklearn/aom_pls.py` — **replace** with a wrapper that imports from `aom_nirs.pls`. The wrapper preserves `backend='torch'` dispatch (via the ported `torch_backend` call); raises `DeprecationWarning` for `gate='sparsemax'` and the FFT/wavelet operators with a pointer to `aom_nirs.pls.experimental`.
- `nirs4all/operators/models/sklearn/aom_pls_classifier.py` — same treatment, wraps `aom_nirs.pls.AOMPLSDAClassifier`.
- `nirs4all/operators/models/sklearn/aom_pls_aomlib.py` — **keep** as the C++-fast path. Now it lives alongside the NumPy `AOMPLSRegressor` from `aom_nirs`; users get both; we document when to pick which.
- `nirs4all/operators/models/pytorch/aom_pls.py` — **delete**. The torch backend moves to `aom_nirs.pls.torch_backend`; the lib wrapper handles dispatch.
- `nirs4all/operators/models/sklearn/pop_pls.py` and `pop_pls_classifier.py` — **delete and wrap**. POP is a paper ablation only; the canonical comes from `aom_nirs.pls.estimators.POPPLSRegressor`.

This is the only path that ends the three-way drift.

---

## 4. Per-module migration table

Notation: source path → destination (under chosen Option B). "Library wrapper" = thin re-export in `nirs4all/operators/models/sklearn/`.

### 4.1 AOM-PLS package

| Source | Destination (`aom_nirs/pls/`) | Library wrapper | Notes |
| --- | --- | --- | --- |
| `bench/AOM_v0/aompls/operators.py` | `operators.py` | — | Move as-is |
| `bench/AOM_v0/aompls/banks.py` | `banks.py` | — | Move as-is |
| `bench/AOM_v0/aompls/nipals.py` | `engines/nipals.py` | — | Group engines |
| `bench/AOM_v0/aompls/simpls.py` | `engines/simpls.py` | — | Group engines |
| `bench/AOM_v0/aompls/selection.py` | `selection.py` | — | Keep public `select()` API |
| `bench/AOM_v0/aompls/scorers.py` | `scorers.py` | — | |
| `bench/AOM_v0/aompls/estimators.py` | `estimators.py` | `AOMPLSRegressor` thin re-export | Canonical AOM-PLS |
| `bench/AOM_v0/aompls/classification.py` | `classification.py` | `AOMPLSDAClassifier` thin re-export | |
| `bench/AOM_v0/aompls/preprocessing.py` | `preprocessing.py` | — | **Flip dep:** the file actually defines local `ExtendedMSC`/`ASLSBaseline` *wrappers* that delegate to `nirs4all.operators.transforms.nirs.ExtendedMultiplicativeScatterCorrection` (self-contained, easy to vendor — `nirs4all/operators/transforms/nirs.py:378`) and `ASLSBaseline` (harder: inherits a baseline-alias stack at `:1847` / `:2193` and uses lazy `pybaselines` dispatch at `:1584`). Plan: vendor `ExtendedMultiplicativeScatterCorrection` directly into `aom_nirs`; for ASLS take a `pybaselines` hard dep and copy the alias-resolution logic (~half-day extraction). |
| `bench/AOM_v0/aompls/centering.py` | `centering.py` | — | |
| `bench/AOM_v0/aompls/diagnostics.py` | `diagnostics.py` | — | |
| `bench/AOM_v0/aompls/metrics.py` | — (delete) | — | Dedupe against `aom_nirs.metrics` or `sklearn.metrics`; do not export a third `rmse`/`r2`/etc. |
| `bench/AOM_v0/aompls/operator_explorer.py` | `experimental/operator_explorer.py` | — | Tag "experimental" in docs |
| `bench/AOM_v0/aompls/operator_generation.py` | `operators_grammar.py` | — | |
| `bench/AOM_v0/aompls/operator_similarity.py` | `experimental/operator_similarity.py` | — | |
| `bench/AOM_v0/aompls/synthetic.py` | `tests/_synthetic.py` | — | Tests-only |
| `bench/AOM_v0/aompls/torch_backend.py` | `torch_backend.py` | — | Optional, guarded by `torch_available()` |
| `bench/AOM_v0/tests/test_*.py` | `tests/pls/test_*.py` | — | All keep; paths only |

### 4.2 AOM-Ridge package

| Source | Destination (`aom_nirs/ridge/`) | Library wrapper | Notes |
| --- | --- | --- | --- |
| `aomridge/__init__.py` | `__init__.py` | — | Drop `residual_tabpfn`/`tabpfn_candidate` entries; gate behind `[tabpfn]` extra |
| `estimators.py` | `estimators.py` | `AOMRidgeRegressor` thin re-export | Primary regressor |
| `classification.py` | `classification.py` | `AOMRidgeClassifier` thin re-export | |
| `aom_ridge_pls.py` | `ridge_pls.py` | — | Drop `Hmax-relative-emsc2` variant default; keep the class |
| `auto_selector.py` | `auto_selector.py` | — | Refactor `_default_headline_with_tabpfn_candidates` so TabPFN is opt-in (do not crash on missing `tabpfn`) |
| `blender.py` | `blender.py` | — | **Best paper variant** |
| `mkr_estimator.py` | `experimental/mkr.py` | — | Ablation only |
| `multi_branch_mkl.py` | `experimental/multibranch_mkl.py` | — | Ablation only; drop `shrink03` default (poor scores) |
| `local_ridge.py` | `experimental/local_ridge.py` | — | Failure-mode example |
| `kernels.py`, `kernelizer.py`, `solvers.py`, `mkl.py`, `weights.py`, `branches.py`, `preprocessing.py`, `split_aware_cv.py`, `cv.py` | `_kernels/`, `_solvers/`, etc. | — | Internal; private under `_` |
| `cv.py` | `cv.py` | — | **Flip dep:** `nirs4all.operators.splitters.SPXYFold` becomes either an inlined SPXY implementation or an optional `nirs4all` extra |
| `selection.py` | `selection.py` | — | 1k lines — request a focused review at merge time |
| `residual_tabpfn.py` | `experimental/_tabpfn_residual.py` | — | Gate behind `[tabpfn]` extra; document benchmark runner refactor |
| `tabpfn_candidate.py` | `experimental/_tabpfn_candidate.py` | — | Same gating |
| `guards.py` | `_guards.py` | — | Internal |
| `tests/test_*.py` (23 files) | `tests/ridge/test_*.py` | — | Keep all |
| `publication/manuscript/aomridge_paper.{tex,pdf}` | — (delete) | — | Superseded by Talanta paper |

### 4.3 FastAOM package

| Source | Destination (`aom_nirs/fast/`) | Library wrapper | Notes |
| --- | --- | --- | --- |
| `bench/AOM_v0/FastAOM/bases.py` | `bases.py` | — | Post-ASLS-bugfix version |
| `operator_chain.py`, `grammar.py`, `chain_generator.py` | same names | — | |
| `lowrank.py`, `screening.py`, `xcorr_fast.py` | same names | — | Document the `xcorr_zero_pad` Python bottleneck |
| `models/*.py` | `models.py` (or split) | `FastAOMPLSRegressor` thin re-export | Match full `__all__` |
| `tests/*` (7 modules) | `tests/fast/test_*.py` | — | Keep all |
| `IMPLEMENTATION_NOTES.md` | `docs/fast_implementation_notes.md` | — | Useful for users |
| `README.md` | merge into top-level README | — | |

### 4.4 Benchmark runners and outputs

| Source | Destination | Action |
| --- | --- | --- |
| `bench/AOM_v0/{aompls,Ridge,FastAOM}/benchmarks/run_*.py` | `aom_nirs/benchmarks/` | Move; trim to paper-tied variants only |
| `bench/AOM_v0/Ridge/scenarios/configs/` | `aom_nirs/benchmarks/configs/` | Keep; document each |
| `bench/scenarios/runs/paper_aom_*` | NOT moved (stays in `bench/`) | The "paper bundle" is too heavy for the repo; ship just the smoke subset |
| `paper_aom/review/cohort_manifest.csv` and other manifests | `aom_nirs/benchmarks/cohorts/*.csv` | Cohort definitions are reproducibility-critical |
| ARCHIVE / TRASH benchmark runs from inventory §7 | delete locally before push | One-time cleanup task |

### 4.5 nirs4all library deletions / wrappers

| Library file | Action after migration |
| --- | --- |
| `nirs4all/operators/models/sklearn/aom_pls.py` | replace with 50-line wrapper (import from `aom_nirs.pls`); preserves public class name `AOMPLSRegressor` |
| `nirs4all/operators/models/sklearn/aom_pls_classifier.py` | replace with wrapper |
| `nirs4all/operators/models/sklearn/aom_pls_aomlib.py` | KEEP — this is the C++ fast path; document it as the "fast path" complement to `AOMPLSRegressor` |
| `nirs4all/operators/models/sklearn/pop_pls.py` | replace with wrapper (importing `POPPLSRegressor` from `aom_nirs.pls`) |
| `nirs4all/operators/models/sklearn/pop_pls_classifier.py` | replace with wrapper |
| `nirs4all/operators/models/pytorch/aom_pls.py` | **delete**; torch path is in `aom_nirs.pls.torch_backend` |
| new: `nirs4all/operators/models/sklearn/aom_ridge.py` | thin re-export `AOMRidgeRegressor`, `AOMRidgeClassifier`, `AOMRidgeBlender`, `AOMRidgeAutoSelector` |
| new: `nirs4all/operators/models/sklearn/aom_fast.py` | thin re-export `FastAOMPLSRegressor` + bases / config |
| `nirs4all/tests/unit/operators/models/test_aom_pls*.py`, `test_aom_pls_aomlib.py` | trim to "the wrapper imports and runs"; full coverage moves to `aom_nirs` |

---

## 5. Score-grounded variant catalog

The library exposes variants in three tiers, mapped from §8 of `aom_code_inventory.md`. The table below is what the public API should advertise.

### 5.1 Production tier (`aom_nirs.pls`, `.ridge`, `.fast` — top-level)

| Public class / preset | Paper variant | Score signal | Notes |
| --- | --- | --- | --- |
| `aom_nirs.pls.AOMPLSRegressor(bank='compact', criterion='cv', cv=5)` | AOM-PLS simple | ratio 0.991 vs PLS-default, 22/32 wins | Default preset |
| `aom_nirs.pls.AOMPLSRegressor(...)` + upstream `ASLSBaseline()` | AOM-PLS best (ASLS-AOM compact CV5) | ratio 0.985 vs PLS-default | Documented composition |
| `aom_nirs.pls.AOMPLSDAClassifier(...)` | AOM-PLS-DA-global | seeds 0/1/2, N=13 | Classification |
| `aom_nirs.ridge.AOMRidgeRegressor(selection='global', bank='compact')` | AOM-Ridge simple | ratio 0.974 vs Ridge-default, $p_{\mathrm{Holm}}=0.007$ | "Simple" Ridge |
| `aom_nirs.ridge.AOMRidgeBlender(...)` over `AOMRidgeAutoSelector` candidates | AOM-Ridge best | ratio 0.918 vs Ridge-default, $p_{\mathrm{Holm}}=2.6\mathrm{e}{-04}$, 27/32 wins | **Best paper result** — needs seeds 1/2 before release |
| `aom_nirs.ridge.AOMRidgeAutoSelector(...)` | AOM-Ridge AutoSelect | ratio 0.963 vs Ridge-HPO, 22/32 wins, current $p_{\mathrm{Holm}}=0.741$ | Required dependency of Blender |
| `aom_nirs.fast.FastAOMPLSRegressor(model='sparse_mkr_supervised')` | FastAOM-sparse-mkr-supervised | ratio 1.009, N=50, Friedman rank 3.08 | FastAOM headline |
| `aom_nirs.fast.FastAOMPLSRegressor(model='sparse_mkr_compact')` | FastAOM-sparse-mkr-compact | ratio 1.022, 2.48 s, Friedman rank 3.18 | FastAOM speed champion |

### 5.2 Ablation tier (`aom_nirs.pls.experimental`, `.ridge.experimental`, `.fast.experimental`)

- AOM-PLS engine ablations: `AOM-default-nipals-adjoint`, `AOM-default-simpls-covariance`, `AOM-compact-cv3`, `AOM-compact-simpls-covariance`.
- AOM-Ridge preprocessing ablations: `*-asls`, `*-snv`, `*-msc` global Ridge variants (0.382-0.483 RMSEP).
- AOM-Ridge structural ablations: `AOMRidgePLS-compact-colscale-cv-relative` (0.414, 33 s); `AOMRidgeAutoSelect-split_aware`.
- AOM-Ridge failure-mode example: `AOMLocalRidge(knn=50)` — ratio 1.212, 4/23 wins.
- FastAOM chain-policy ablations: `single-chain`, `soft-chain`, `hard-chain-{osc,supervised,asls,multibase,compact}` (ratios 1.05-1.13).
- POP-PLS / POP-PLS-DA — negative ablation; advertised as "per-component selection underperforms global".

### 5.3 Hidden / removed at release

- `AOMRidgePLS-compact-Hmax-relative-emsc2` (median RMSEP 1.981) — remove from defaults; constructor still accepts the config but the docstring warns it underperforms.
- `AOMRidge-MultiBranchMKL-compact-shrink03` (median RMSEP 3.599, ~6× Ridge-raw) — remove from defaults.
- `FastAOM-hard-chain-compact-d4` (single dataset) and `FastAOM-single-chain-supervised-cv5-numpy` (ratio 1.208) — drop from headline tables and presets.
- `bench/AOM/{darts_pls,moe_pls,zero_shot_router,zero_shot_router_v1,pseudo_linear_aom,pseudo_linear_snv_v1,enhanced_aom,quick_test,test_snv_jacobian,run_comparison,update_models}.py` — **do not migrate**; pre-paper drafts.
- `bench/AOM_v0/Ridge/publication/manuscript/aomridge_paper.{tex,pdf}` — do not migrate.

---

## 6. Phased rollout

### Phase 0 — pre-migration hygiene (~1 day, local only)

1. Decide repo strategy (Option B is the recommendation).
2. Delete TRASH benchmark runs from inventory §7 — local cleanup only; commit a list of deletions in `bench/AOM_v0/_archive/MANIFEST.md`.
3. Move ARCHIVE benchmark runs to `bench/AOM_v0/_archive/` with the same manifest entry per directory.
4. Run `pytest bench/AOM_v0/tests bench/AOM_v0/Ridge/tests bench/AOM_v0/FastAOM/tests` to confirm green baseline.

### Phase 1 — repo split (Option B; ~2-3 days)

1. `git init` at `/home/delete/nirs4all/aom/`; pyproject.toml with package name `aom-nirs`.
2. Move `bench/AOM_v0/aompls/` → `aom/aom_nirs/pls/`, with import-path rewrites (one search/replace, then `pytest` until green).
3. Move `bench/AOM_v0/Ridge/aomridge/` → `aom/aom_nirs/ridge/`. Same import rewrite. Gate TabPFN.
4. Move `bench/AOM_v0/FastAOM/` → `aom/aom_nirs/fast/`.
5. Move benchmark runners and cohort manifests; trim to paper-tied variants only.
6. Wire up GitHub Actions CI (single test job + lint job).

### Phase 2 — `nirs4all` integration (~1-2 days)

1. Replace `nirs4all/operators/models/sklearn/aom_pls.py` etc. with thin wrappers. Update `__init__.py` exports.
2. Add `nirs4all/operators/models/sklearn/aom_ridge.py` and `aom_fast.py` wrappers.
3. Update `nirs4all/pyproject.toml` extras: `nirs4all[aom]` pulls `aom-nirs`; `nirs4all[aom-tabpfn]` pulls `aom-nirs[tabpfn]`; `nirs4all[aom-fast]` pulls `aom-nirs` (no extra Python dep but documents intent).
4. Run `pytest nirs4all/tests` and confirm the wrappers work with `aom-nirs` installed and the import-skips are clean when it is not.

### Phase 3 — paper reproducibility (~10-15 days; dominated by compute)

1. Run AOM-Ridge Blender + AutoSelector with seeds 1, 2 on the 53-dataset cohort (`bench/AOM_v0/Ridge/benchmark_runs/all54_headline/`, with split-aware CV). Effort: 50-120 core-hours; 4-6 human-hours of monitoring.
2. Fill the HPO denominator gaps in `missing_datasets_per_variant.md` for PLS-TabPFN-HPO and Ridge-TabPFN-HPO where datasets are merely "not attempted" (i.e. exclude the ones that error on NaN). Effort: 150-300 core-hours; 6-10 human-hours.
3. Regenerate `final_stats.md`, `paired_stats.tex`, `table_main_results.tex`, `table_aomridge_family.tex` from the new CSVs.
4. Re-issue `paper_aom/main.tex` with the updated tables and a one-paragraph note that the strict denominator is now N=$x$ (likely > 32, possibly close to 53 after the gap fill).

### Phase 4 — pre-submission packaging (~1-2 days)

1. Tag `aom-nirs v0.1.0` matching the paper's commit hash; publish on PyPI (`twine upload`).
2. Write `aom_nirs/examples/paper_smoke.py` that reproduces a 3-dataset smoke (e.g. `Beer_OriginalExtract_60_KS`, `Corn_Oil_80_*`, `Rice_Amylose_313_YbasedSplit`) for AOM-PLS, AOM-Ridge, and FastAOM. One command, < 5 minutes.
3. Update `paper_aom/main.tex` `\code` and `\software` sections to cite `aom-nirs v0.1.0` and `nirs4all v0.8.11`.
4. Update `pls4all/README.md` and `CITATION.cff` to link `gbeurier/aom`.

### Phase 5 — post-submission (parallel with review cycle)

- External-split / instrument-transfer demonstration (Talanta review weakness #4).
- Strong conventional PLS+SNV+SG+derivative baseline (review weakness #3).
- `aom-nirs` documentation site (MkDocs).
- Evaluate Option C (move into `pls4all`) once `pls4all` v1.0 is out — see `pls4all_integration_eval.md`.

---

## 7. Reproducibility checklist (Talanta submission)

| # | Item | Owner | Effort | Blocking? |
| --- | --- | --- | --- | --- |
| 1 | AOM-Ridge Blender seeds 1, 2 on 53 datasets | benchmark runner | 50-120 core-h, 4-6 human-h | **Yes** |
| 2 | AOM-Ridge AutoSelect seeds 1, 2 on 53 datasets | benchmark runner | 50-120 core-h, 4-6 human-h | **Yes** |
| 3 | Fill HPO gaps for `pls-tabpfn-hpo-25trials` and `ridge-tabpfn-hpo-60trials` (the "not attempted" rows) | benchmark runner | 150-300 core-h, 6-10 human-h | **Yes** (or document |
| 4 | Regenerate `final_stats.md`, `paired_stats.tex`, `table_main_results.tex` | stats scripts | 0.5 day | **Yes** |
| 5 | `aom-nirs` repo public on GitHub with passing CI | dev | 2-3 days | **Yes** |
| 6 | `aom-nirs` v0.1.0 on PyPI tagged with paper commit hash | dev | 0.5 day | **Yes** |
| 7 | `aom_nirs/examples/paper_smoke.py` runs in < 5 min | dev | 0.5 day | **Yes** |
| 8 | `paper_aom/main.tex` `\software` updated to cite `aom-nirs` and `nirs4all` versions | dev | 0.5 day | **Yes** |
| 9 | Failure-mode paragraph in `paper_aom/main.tex` referencing `failure_mode_table.csv` and the LocalRidge KNN50 negative result | author | 0.5 day | Recommended |
| 10 | Strong conventional PLS+SNV+SG+derivative baseline | author + compute | 1 day + 10-100 core-h | Recommended |
| 11 | `nirs4all` minor release that re-exports `aom-nirs` and ships smoke-tested wrappers | dev | 1-2 days | Recommended |
| 12 | `pls4all/README.md` and `CITATION.cff` link `gbeurier/aom` | dev | 0.5 day | Recommended |

Total blocking effort: ~250-540 core-hours + ~25-35 human-hours. Conservatively two weeks of calendar time if compute can run in parallel with packaging.

---

## 8. Risks and watch-items

- **`pls4all` C++ AOM and the Python `aom-nirs` drift apart.** Mitigation: cross-check `aom_nirs.pls.AOMPLSRegressor(bank='compact', criterion='cv', cv=5)` against `pls4all/bindings/python` predictions on the smoke cohort; ship a 1-page parity table in `aom_nirs/docs/parity.md`. Already partially done by `bench/AOM_v0/tests/test_parity_with_production.py`.
- **Seeds 1, 2 weaken the Blender headline.** Mitigation: if median ratio rises from 0.918 to e.g. 0.95, update the abstract claim ("at least 5% RMSEP improvement over Ridge-HPO" instead of "8%"); rerun statistical tests.
- **HPO gap-fill takes longer than estimated on LUCAS-scale datasets.** Mitigation: prepare the missingness table as the fallback and submit with N < 53 (current 32) honestly framed.
- **`tabpfn` extra breaks installs on macOS arm64.** Mitigation: keep `tabpfn` as a `pip install aom-nirs[tabpfn]` extra; document in README.
- **Circular dep between `aom_nirs.pls.preprocessing` and `nirs4all.operators.transforms.nirs`.** Mitigation: at migration time inline `ExtendedMSC` and `ASLSBaseline` into `aom_nirs`, then re-export them from `nirs4all` if needed for transform-pipeline composition.

---

## 9. Out-of-scope (do not migrate to `aom-nirs`)

- `bench/AOM_v0/Multi-kernel/{MKR,Blup,MkM}` — separate paper, keep in `bench/`.
- `bench/AOM_v0/multiview/` — future paper.
- `bench/AOM_v0/source_materials/`, `bench/AOM_v0/tabpfn_paper/`, `bench/AOM_v0/synthesis/` — non-AOM artifacts.
- `bench/AOM_lib/{cpp,r,julia,matlab,js,scripts}/` — C++/multi-language; either lives in `pls4all` already or is its own legacy area.

End of plan. Next: `pls4all_integration_eval.md` (where Option C is examined in detail).
