# pls4all integration evaluation — can it host the AOM paper?

**Generated:** 2026-05-17.
**Question this doc answers:** is it worth shipping the AOM paper's code through `pls4all` (Option C from `aom_lib_migration_plan.md`), or should we ship an independent `aom-nirs` Python repo (Option B) and let pls4all be the long-term C++ home?

**TL;DR.** pls4all already implements the AOM-PLS *core* in C++ behind a public C ABI (Phase 6a-6f shipped: operator bank, global AOM-SIMPLS CV selection, POP per-component SIMPLS covariance selection, validation-plan ABI, Python ctypes smoke against the bench oracle). But the paper's *full* surface — AOM-Ridge family (best empirical result), FastAOM chain-based pipelines, AOM-PLS-DA, soft/sparse/superblock policies, AOM-NIPALS, holdout/approx-PRESS/one-SE variants, benchmark cohort runners, Python wheel on PyPI — is **6-8 months of additional work** to replicate behind a C ABI. That timeline does not fit the Talanta submission window. Recommend: ship `aom-nirs` for Talanta; let pls4all be parity oracle now and the long-term v1.x home (post-paper); add a one-line cross-citation between the two.

---

## 1. What pls4all has today

Sources: `pls4all/README.md` ("Phase 6e AOM/POP strict-operator/selection core live"), `pls4all/ROADMAP.md` §"Phase 6 - AOM-PLS and POP-PLS - shipped through 6f", `pls4all/cpp/src/core/aom_*.{hpp,cpp}`, `pls4all/cpp/src/c_api/c_api_aom_selection.cpp`, `pls4all/bindings/python/smoke_aom_pop.py`.

### 1.1 Shipped in C++ core + C ABI (Phase 6a-6f)

| Phase | What | C++ location | C ABI entry | Notes |
| --- | --- | --- | --- | --- |
| 6a | Internal soft/hard AOM preprocessing-bank transform primitive | `cpp/src/core/aom_preprocessing.{hpp,cpp}` | — | Bank application primitive only |
| 6b | Internal global AOM-SIMPLS CV selection (identity/detrend) | `cpp/src/core/aom_selection.{hpp,cpp}` | `p4a_aom_global_select` | Validated against `nirs4all/bench/AOM_v0/aompls` |
| 6c | Strict-linear AOM kernels: zero-padded SG, FD, Norris-Williams | `cpp/src/core/aom_operators.{hpp,cpp}` | (via bank) | Direct-transform parity verified |
| 6d | Whittaker smoothing + FCK operators | `cpp/src/core/aom_operators.{hpp,cpp}` | (via bank) | Same parity oracle |
| 6e | POP-PLS per-component SIMPLS covariance selector | `cpp/src/core/aom_selection.{hpp,cpp}` | `p4a_aom_per_component_select` | Per-component covariance only |
| 6f | Public C ABI for validation plans, AOM global, POP per-component | `cpp/src/c_api/c_api_aom_selection.cpp`, `cpp/include/pls4all/p4a.h` | `p4a_validation_plan_*`, `p4a_aom_global_select`, `p4a_aom_per_component_select` | Python ctypes smoke green |

### 1.2 Shipped on the Python side

- `pls4all/bindings/python/smoke_aom_pop.py` (223 lines): ctypes binding drives `p4a_aom_global_select` and `p4a_aom_per_component_select` through pls4all.Context / OperatorBank / ValidationPlan / Config. Compares against JSON fixtures under `parity/fixtures/`. Drives the public C ABI end-to-end.
- `pls4all/bindings/python/src/pls4all/` (20 .py files): ctypes wrapper layer with `Context`, `Config`, `OperatorBank`, `ValidationPlan`. Tier-1 raw FFI; sklearn tier-2 wrappers exist for 42 of 68 reachable methods (62 %).

### 1.3 What is **not** in pls4all today (per CHANGELOG + ROADMAP)

| Gap | Roadmap status | Effort estimate (C++) |
| --- | --- | --- |
| AOM-NIPALS materialized engine (the paper uses both NIPALS and SIMPLS) | Phase 6g planned | 2-4 weeks |
| Soft / sparse / superblock AOM selection policies | Phase 6g planned | 2-3 weeks |
| POP holdout / approximate-PRESS / one-SE variants | Phase 6g planned | 2 weeks |
| Per-block / per-target AOM plans | Phase 6g planned | 1-2 weeks |
| AOM-PLS-DA classifier (paper §6) | Phase 6h-ish; no explicit ticket | 1-2 weeks |
| AOM-Ridge family (entire) | **Out of pls4all scope** (PLS-only engine) | 2-3 months if added as new module |
| FastAOM chain enumeration + low-rank screening + sparse-MKR | **Out of pls4all scope** | 1.5-2 months |
| Cohort runners + benchmark scripts (paper-headline reproducibility) | Not on roadmap | 2-3 weeks |
| Python wheel on PyPI ("not yet on PyPI" per README) | Phase 7+ | 1-2 weeks |
| Tier-2 sklearn AOM-PLS / POP wrappers | "3 AOM entries" missing per CHANGELOG phase-54 | 1-2 weeks |
| Paper-grade docs site for AOM (math + API + examples) | Not on roadmap | 1-2 weeks |
| `gbeurier/aom` citation surface (GitHub repo, DOI, release tag matching paper) | Not on roadmap | 0.5 day if `pls4all` co-tags |

### 1.4 Architectural fit (revisited)

`pls4all/ARCHITECTURE.md:29,38` defines bindings as objects that "translate native objects, call `p4a_*`, translate results back, and **never own numerical logic**." `pls4all/Overview.md:672,1012` frames the v0.6 AOM milestone as "AOM in C++ core, bindings only translate". This means:

- **Native pls4all path:** add C++ implementations of AOM-Ridge, FastAOM, AOM-NIPALS, soft/sparse selection, classifiers, etc.; the Python binding stays thin.
- **Awkward pls4all path:** put 25 kLOC of Python AOM scientific code under `bindings/python/aom/`. This contradicts the documented binding model — bindings would suddenly own numerical logic — and would also force `pls4all`'s Python wheel size to grow ~6×.

The architecture does not **forbid** the awkward path, but the project's own documentation states the opposite intent. Going against it would create a permanent code-organization debt.

---

## 2. Cost model — porting the paper to pls4all C++

This counts only the *core developer time* assuming one full-time C++ developer with prior pls4all experience. CI, review, benchmark, and stabilisation are separate buckets.

| Block | Description | Effort | Calendar (1 FTE) |
| --- | --- | --- | --- |
| **A. Phase 6g** completion | AOM-NIPALS materialized + soft/sparse/superblock selection + POP holdout/approx-PRESS/one-SE + per-block/per-target plans | 7-11 dev-weeks | 2-3 months |
| **B. AOM-PLS-DA** | Classifier API in C++ core + C ABI + Python wrapper | 2-3 dev-weeks | 0.5-1 month |
| **C. AOM-Ridge family** | Dual / kernel Ridge in C++ (Cholesky / eigh with jitter fallback); global / blender / auto-selector / multi-branch-MKL / local-Ridge policies; OOF / SLSQP plumbing for Blender; classifier wrapper | 10-14 dev-weeks | 2.5-3.5 months |
| **D. FastAOM** | Chain grammar + DFS generator + adjoint-only covariance screening + low-rank kernels + sparse-MKR (NNLS) + four AOM models | 7-9 dev-weeks | 1.5-2 months |
| **E. Cohort runners** | Reproduce `paper_aom_*_seeds012` flows from C++/Python; cohort manifests; result CSV schema | 2-3 dev-weeks | 0.5-1 month |
| **F. Python wheel + tier-2 wrappers** | Publish `pls4all` wheel on PyPI; close the 26 missing tier-2 sklearn entries (3 of which are AOM); update CHANGELOG and CITATION | 3-4 dev-weeks | 1 month |
| **G. Paper-grade docs** | API reference, math derivations, AOM bench parity tables, smoke examples | 2-3 dev-weeks | 0.5-1 month |
| **Total** | | **33-47 dev-weeks** | **8-12 months** (1 FTE) |

Two paths exist:

- **Full port (A-G)**: 8-12 months. Talanta has already submitted (or been rejected) by then. Only useful as the post-paper roadmap.
- **Minimal "PLS-only paper" port (A + B + E partial + F)**: 4-5 months. Replicates the AOM-PLS / AOM-PLS-DA / POP-PLS halves of the paper through `pls4all`, but **does not** cover the strongest empirical result (AOM-Ridge Blender at 0.918 vs Ridge-default, $p_{\mathrm{Holm}}=2.6\mathrm{e}{-04}$) or FastAOM. The paper's headline would then have to either drop the Ridge claim or cite `aom-nirs` for that half anyway — defeating the purpose of going through pls4all.

Neither path is realistic before Talanta. The full path is realistic as a v1.x effort *after* the paper.

---

## 3. What the paper actually needs from the host repo

From `talanta_review.md` weakness #5 (code availability — blocker): the reviewers want a single repository they can clone in one minute and run a smoke example that reproduces a small subset of the benchmark. Concrete requirements:

1. Public GitHub repo with stable URL and DOI.
2. `pip install <package>` works without compiling C++.
3. A smoke example that reproduces AOM-PLS simple, AOM-Ridge Blender (or a smaller Ridge variant if Blender is too slow), and one FastAOM variant.
4. A release tag matching the paper's commit hash.
5. Tests run from a clean clone.

pls4all today fails 1 (the repo exists but does not have an AOM-specific identity), 2 (no PyPI wheel, requires cmake build), 3 (no AOM-Ridge, no FastAOM through the C ABI), 5 (smoke targets only AOM/POP selection, not full reproducibility runs).

`aom-nirs` from `aom_lib_migration_plan.md` Option B can satisfy all five within ~5-8 dev-days because the code already exists in `bench/AOM_v0/`; the work is packaging + dependency reversal + CI, not new implementation.

---

## 4. Recommendation: dual track

### 4.1 Track A — Talanta submission (next ~2-3 weeks)

- Ship `aom-nirs` per `aom_lib_migration_plan.md` Option B. PyPI package, GitHub repo at `/home/delete/nirs4all/aom/`, v0.1.0 tag matching the paper.
- Add this paragraph to `paper_aom/main.tex` `\software{}` section (or wherever code is cited):
  > *AOM-PLS, AOM-Ridge and FastAOM are released as the Python package `aom-nirs` v0.1.0 (DOI: <to be assigned>; <github.com/gbeurier/aom>). A complementary C++ implementation of the strict-linear AOM operator family and the global / per-component selectors is under development as part of the `pls4all` engine (<github.com/gbeurier/pls4all>); current parity status is reported in `aom-nirs/docs/pls4all_parity.md`.*
- Update `pls4all/README.md` Phase-6 row to add a one-line cross-link: "Python reference and benchmarks: `gbeurier/aom`."
- Re-use `pls4all`'s `parity/fixtures/` JSON oracles as a smoke-test dataset for `aom-nirs` — bit-exact match validates that the two implementations stay in sync.

### 4.2 Track B — post-paper (next 6-12 months)

Use `aom-nirs` as the moving Python reference; let `pls4all` v1.x catch up:

1. **Phase 6g** (planned in pls4all ROADMAP): AOM-NIPALS, soft/sparse selection, POP holdout/approx-PRESS, one-SE. ~2-3 months. Validates against `aom-nirs`.
2. **AOM-PLS-DA** in pls4all C ABI. ~1 month.
3. **`pls4all` v1.0 wheel on PyPI** with tier-2 sklearn coverage at 100 % (closes the 26 missing entries, including 3 AOM). ~1-2 months.
4. **AOM-Ridge** added as a new module (`pls4all/cpp/src/core/aom_ridge_*`) — **scope expansion required.** pls4all today frames itself as a "Partial Least Squares family" engine (`pls4all/README.md:7`); the existing ROADMAP mention of "Ridge/regularized/penalized PLS" at `pls4all/ROADMAP.md:491` is *ridge-regularized PLS* (RPLSR), not standalone Ridge regression. Hosting AOM-Ridge in pls4all therefore requires an explicit pls4all-scope-expansion decision, not a tick on the existing roadmap. Only worth doing if there is independent demand for a C++ Ridge engine. Otherwise AOM-Ridge stays in `aom-nirs` permanently. ~2.5-3.5 months **conditional on scope expansion**.
5. **FastAOM** added analogously — also a scope question, since FastAOM is Ridge-flavoured (sparse-MKR + PLS-Ridge). ~1.5-2 months conditional on the same scope decision.
6. At each pls4all minor release, ship a bit-exact parity check between `aom-nirs` and the new C++ entry point. For the AOM-PLS / POP-PLS / AOM-PLS-DA half (which is on the existing pls4all roadmap), `aom-nirs` can eventually re-export from `pls4all.sklearn` once those tier-2 wrappers ship. For AOM-Ridge and FastAOM, the dual-track is the long-term arrangement unless and until pls4all chooses to host them — **the convergence is partial, not total**.

### 4.3 Why dual-track is better than waiting for pls4all

- **Timing.** Talanta submission cannot wait 6-12 months.
- **Risk.** AOM-Ridge in C++ is non-trivial (multi-branch kernels, SLSQP-style blender, KNN local). Estimating without prototyping is dangerous. A working Python reference de-risks the C++ port later.
- **Citation hygiene.** Releasing `aom-nirs` now gives the paper a stable DOI and a one-clone reproduction story today. `pls4all` keeps its identity as the C++ engine.
- **Eventual convergence is preserved.** Track B explicitly plans the `aom-nirs` → `pls4all.sklearn` thin-wrapper migration. Users never need to relearn the API.

### 4.4 Why **not** dual-track

The only realistic argument against this plan is "two repos to maintain". The mitigation is in §4.2: `aom-nirs` is the moving Python reference; `pls4all` is the long-term C++ host; their public Python API converges. We pay for two pyproject.tomls + two CI configs for ~1 year, then we shift weight.

---

## 5. Concrete action items if you adopt the dual track

| # | Action | Effort | Repo |
| --- | --- | --- | --- |
| 1 | Create `aom-nirs` repo per Option B (see `aom_lib_migration_plan.md` §6) | 5-8 dev-days | new `aom/` |
| 2 | Re-use `pls4all/parity/fixtures/synthetic_aom_*_v1.json` as `aom_nirs`'s parity oracles; ship `aom_nirs/tests/test_pls4all_parity.py` that runs the same fixtures and compares against `pls4all`'s expected outputs | 0.5 day | new `aom/` |
| 3 | Document parity status in `aom_nirs/docs/pls4all_parity.md` (current 6a-6f matrix, with TODO entries for 6g/6h items) | 0.5 day | new `aom/` |
| 4 | Add `Python reference: gbeurier/aom` to `pls4all/README.md` (§31 Phase-6 row) and `pls4all/CITATION.cff` (related-software list) | 0.5 day | `pls4all` |
| 5 | Open `pls4all` issues for the 3 missing AOM tier-2 sklearn entries that CHANGELOG phase-54 references (lines 32-34 mention "3 AOM entries" without naming them; from the tier-1 surface they are presumably the sklearn wrappers around `p4a_aom_global_select`, `p4a_aom_per_component_select`, and a soft-gate variant — confirm with the pls4all author before filing). Link each issue to the corresponding `aom-nirs` class as parity target. | 0.5 day | `pls4all` |
| 6 | After Talanta acceptance, write a v1.x convergence ticket in `pls4all/ROADMAP.md` Phase 6h, 6i pointing at the `aom-nirs` Python reference and the per-class effort estimates from §2 above | 0.5 day | `pls4all` |

Total integration overhead beyond Track A's `aom-nirs` release: ~2 dev-days. That is the price of keeping the long-term path open without slowing Talanta.

---

## 6. Risk register

- **Risk:** Track B Phase 6g slips past Talanta acceptance, journal asks for "the canonical C++ implementation". **Mitigation:** Track A's `aom-nirs` is *itself* canonical; pls4all is the *complementary C++ engine*. The wording in §4.1 avoids any implication that pls4all is canonical for AOM-Ridge / FastAOM.
- **Risk:** API drift between `aom-nirs` (Python) and `pls4all.sklearn` (C++) makes the eventual convergence painful. **Mitigation:** in `aom_nirs/tests/test_pls4all_parity.py` we run the same fixtures through both; any deviation flags CI. The `pls4all/parity/fixtures/synthetic_aom_*_v1.json` fixtures are portable (see §5 / Codex review note: they include both numeric enum codes and human-readable `operator_names`, so `aom-nirs` only needs a small enum-to-name table to consume them). For AOM-PLS / POP only — AOM-Ridge / FastAOM stay in `aom-nirs`.
- **Risk:** `pls4all` Python wheel never lands on PyPI (current status: "not yet"). **Mitigation:** `aom-nirs` does not depend on `pls4all` at runtime; only the parity test does, and CI can build `pls4all` from source for it.
- **Risk:** Reviewers conflate the two repos and ask "why are there two?". **Mitigation:** the README of `aom-nirs` explicitly says "Python reference for the Talanta paper" and "the C++ engine that hosts AOM-PLS core under development is `pls4all`; see `docs/pls4all_parity.md`". The README of `pls4all` says "Python reference: `gbeurier/aom`". Both READMEs link to each other.

---

## 7. What this evaluation does *not* claim

- pls4all is not "wrong" to be C++-first. The architecture is sound for a long-term engine that powers multiple language bindings.
- The dual-track plan is not "two products forever". Track B explicitly plans convergence.
- `aom-nirs` is not "throw-away". Even after Track B's convergence, the Python repo remains the user-facing entry for AOM-Ridge / FastAOM if those don't get C++ ports.

---

End of evaluation. The Talanta migration follow-through is fully specified across the three docs:

- `aom_code_inventory.md` — what code exists and where.
- `aom_lib_migration_plan.md` — what moves where, with three repo options and a recommendation (Option B).
- `pls4all_integration_eval.md` — why Option B beats Option C for now, and how the two converge later.
