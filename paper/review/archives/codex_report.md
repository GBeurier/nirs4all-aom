# Codex finalization report

Date: 2026-05-13.

## Step 1 validation

| Item | Status | Finding |
| --- | --- | --- |
| Cohort manifest CSV | ⚠️ | Exists with 78 rows and required columns. It has 61 regression + 17 classification rows, but `status_in_primary_analysis=include` is 61 regression + 16 classification because `Quartz_spxy70` remains `include` with `exclusion_reason=denominator_near_zero_pairwise`; requested primary count was 60 + 16. |
| Cohort manifest MD | ⚠️ | Exists with denominator rules, but documents 61 included regression rows / paired AOM-PLS vs PLS denominator 61, not the requested 60 primary-regression denominator. |
| Claim ledger | ✅ | Claims A-E and evidence paths are present; statuses remain blocked/provisional. |
| Aggregator | ✅ | `python paper_aom/review/aggregate_stats.py --partial` completed; Step 2 refresh loaded 10,749 rows from 8 workspaces. |
| Selector diagnostics | ✅ | Regenerated CSV/Markdown/TeX outputs. AOM-Ridge diagnostics parsed 0 rows from the current partial top5_fast file. |
| AOM-lib wrapper | ✅ | `ruff`, `mypy`, 7 unit tests, and the nirs4all example all passed. |
| Software table | ✅ | 10 data rows plus status legend. |
| AOM_lib C/Python parity | ✅ | `c_smoke`, `test_operators`, `test_parity_kfold`, and Python parity tests passed; `c_smoke.c` includes `<math.h>`. |
| Linear HPO runner | ✅ | `bench/tabpfn_paper/run_linear_hpo_paper_aom.py` exists. |
| Result workspaces | ✅ | All six listed workspaces/files exist. Final row counts had grown while background jobs continued: AOM-PLS 1485 data rows, AOM-Ridge top5_fast 76, partial headline 11, AOM-PLS-DA 232, AOM-Ridge classification 39, linear-HPO 94. |

## Headline numbers

- AOM-PLS paper provisional: median RMSEP/PLS `0.960`, `42/57` wins.
- Refreshed AOM-PLS multi-seed robustness: median RMSEP/PLS `0.9623`, `37/53` wins after averaging RMSEP across seeds.
- `final_stats.md` partial paired overlap for ASLS-AOM vs PLS-default: ratio `0.964`, `6/7` wins.
- AOM-Ridge paper provisional: `2.22%` median improvement, `35/52` wins vs tuned Ridge.
- Refreshed `final_stats.md` AOM-Ridge overlap: Blender vs Ridge-HPO ratio `0.905`, `4/4` wins; denominator is still partial and not a full-cohort promotion.

## Files edited

- `paper_aom/main.tex`
- `paper_aom/supplement.tex`
- `paper_aom/tables/table_main_results.tex` (escaped `paper_aom` in generated table source so LaTeX builds)
- `paper_aom/review/aggregate_stats.py` (escapes plain-text LaTeX table cells so the same issue does not recur on refresh)

Aggregation and diagnostic commands also refreshed generated review/table artifacts under `paper_aom/review/` and `paper_aom/tables/`.

## PDF build

- `paper_aom/main.pdf`: built without fatal errors after two clean final runs.
- `paper_aom/supplement.pdf`: built without fatal errors; one extra run was used to settle references.
- Remaining warnings: overfull boxes from long code paths in `table_software.tex` and one long result path in the main text; several supplement `[h]` floats changed to `ht`. No unresolved references remained in the final logs.

## Open items

- Linear-HPO timing run is still incomplete; refresh aggregation/table once finished.
- Full AOM-Ridge Blender/AutoSelect headline rerun remains pending; current full-cohort run is top5_fast only.
- Add Talanta Novelty Statement and AI-assisted-technology declaration before submission.
- Resolve the manifest/documentation mismatch for QUARTZ if primary analyses must report 60 regression includes rather than 61 absolute-error rows.

## v3 update (2026-05-17)

### Files touched

- Manuscript sources and rebuilt PDFs: `paper_aom/main.tex`, `paper_aom/supplement.tex`, `paper_aom/main.pdf`, `paper_aom/supplement.pdf`, plus refreshed LaTeX build artifacts (`main.aux`, `main.bbl`, `main.blg`, `main.out`, `supplement.aux`, `supplement.out`, `supplement.toc`).
- Generated tables: `paper_aom/tables/table_main_results.tex`, `table_paired_stats.tex`, `table_time_budget.tex`, `table_classification_main.tex`, `table_classification_full.tex`, `table_selector_diagnostics.tex`, `table_operator_bank.tex`, `table_benchmark_diversity.tex`, `table_software.tex`, `table_fastaom_variants.tex`, `table_supplement_long_results.tex`, `table_seed_stability.tex`, `table_failure_modes.tex`.
- Generated figures: `paper_aom/figures/fig_accuracy_time_pareto.{pdf,png}`, `fig_runtime_distribution.{pdf,png}`, `fig_results.pdf`, `fig_budget.pdf`, `fig_operator_heatmap.{pdf,png}`, `fig_dataset_variant_heatmap.{pdf,png}`, `fig_fastaom_variants.{pdf,png}`.
- Review artifacts and scripts: `paper_aom/review/final_stats.md`, `paper_aom/review/v3_stats.md`, `paper_aom/review/build_paper_figures.py`, refreshed `selector_diagnostics.csv`, `operator_frequency.csv`, `failure_mode_table.csv`, `compact_bank_justification.md`.

### Headline numbers used in the abstract

- ASLS-AOM-compact-cv5 vs PLS-standard: median RMSEP ratio `0.962` on `53` paired datasets, `37/53` wins, Holm-adjusted Wilcoxon `p=0.043`.
- AOMRidge-Blender vs Ridge-default: median RMSEP ratio `0.913` on `52` paired datasets, `44/52` wins, `p=2.8e-06`.
- AOMRidge-Blender vs Ridge-TabPFN-HPO: median RMSEP ratio `0.956` on `34` paired datasets, `27/34` wins, `p=0.011`.
- FastAOM-sparse-mkr-supervised vs PLS-standard: median RMSEP ratio `0.953` on `50` paired datasets, `35/50` wins.
- FastAOM summary after the `N>=50` filter: sparse-MKR supervised `N=50`, median relative RMSEP `1.009`, median fit `87.77 s`; sparse-MKR compact `N=50`, median relative RMSEP `1.022`, median fit `2.48 s`; single-chain compact `N=52`, median relative RMSEP `1.052`, median fit `1.86 s`.
- Cartesian linear-HPO coverage: `36` complete PLS-HPO datasets and `35` complete Ridge-HPO datasets with three successful seeds.

### FastAOM integration summary

FastAOM is now integrated in the main methods, results, discussion and reproducibility sections.  The main text presents only the performant FastAOM variants after the `N>=50` filter plus the `FastAOMPLSRidge` orchestrator concept.  The supplement reports the full FastAOM family table, the hard/soft chain exploration, runtime distribution, chain-depth/rank/top-k notes, and the full per-dataset FastAOM/reference long table.

### Data limitations and handling

- The legacy `aggregate_stats.py` still points at a stale single linear-HPO workspace, so it refreshes AOM and selector diagnostics but does not ingest the actual cartesian-HPO seed workspaces.  I handled this with `paper_aom/review/build_paper_figures.py`, which reads the real PLS/Ridge HPO seed directories and writes `v3_stats.md`, tables and figures.
- The cartesian-HPO runs are intentionally reported only on successful complete subsets.  LUCAS_SOC exceeded the compute budget, and two FUSARIUM rows failed estimator checks because of NaN response values.
- FastAOM seed0 is deterministic for fixed train/test splits and configurations, so it is used as chain-space evidence rather than split-resampling evidence.

### Wording and build checks

Commands run:

```bash
grep -n "Talanta\|talanta\|tbd\|TBD\|draft to be completed" paper_aom/main.tex paper_aom/supplement.tex
grep -niE "tbd|to be completed|placeholder|in progress|remaining experiments|pending" paper_aom/main.tex paper_aom/supplement.tex
```

Both commands returned empty output.

PDF rebuild completed with:

```bash
bibtex main
bibtex supplement
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode supplement.tex
pdflatex -interaction=nonstopmode supplement.tex
```

`paper_aom/main.pdf` and `paper_aom/supplement.pdf` were produced without fatal LaTeX errors.  Remaining warnings are overfull/underfull boxes from long dataset names and code paths in tables, which are expected for the supplement's long-form evidence tables.

## v4 update (2026-05-17)

### Files touched

- Manuscript sources: `paper_aom/main.tex`, `paper_aom/supplement.tex`.
- Bibliography and figure/table generators: `paper_aom/references.bib`, `paper_aom/review/build_paper_figures.py`, `paper_aom/scripts/make_figures.py`.
- Generated review artifacts: `paper_aom/review/final_stats.md`, `paper_aom/review/selector_diagnostics.csv`, `paper_aom/review/operator_frequency.csv`, `paper_aom/review/failure_mode_table.csv`, `paper_aom/review/selector_seed_stability.csv`, `paper_aom/review/compact_bank_justification.md`.
- Main generated tables: `paper_aom/tables/table_main_results.tex`, `table_time_budget.tex`, `table_classification_main.tex`, `table_benchmark_diversity.tex`, `table_software.tex`, `table_budget.tex`.
- Supplement generated tables: `paper_aom/tables/table_paired_stats.tex`, `table_fastaom_variants.tex`, `table_supplement_long_results.tex`, `table_classification_full.tex`, `table_seed_stability.tex`, `table_failure_modes.tex`, `table_selector_diagnostics.tex`, plus new `table_cohort_manifest.tex`, `table_aompls_family.tex`, `table_aomridge_family.tex`, `table_pop_summary.tex`.
- Regenerated figures: `fig_accuracy_time_pareto.{pdf,png}`, `fig_runtime_distribution.{pdf,png}`, `fig_results.pdf`, `fig_budget.pdf`, `fig_operator_heatmap.{pdf,png}`, `fig_dataset_variant_heatmap.{pdf,png}`, `fig_fastaom_variants.{pdf,png}`.  `fig_concept.pdf` and `fig_math.pdf` were not regenerated.
- Build artifacts and PDFs: `paper_aom/main.pdf`, `paper_aom/supplement.pdf`, `main.aux`, `main.bbl`, `main.blg`, `main.out`, `supplement.aux`, `supplement.bbl`, `supplement.blg`, `supplement.out`, `supplement.toc`.

### Chosen best-AOM variants

- PLS regression: `ASLS-AOM-compact-cv5`, chosen from the largest AOM-PLS paired screening denominator and retained as the only PLS-regression AOM variant in the main manuscript.
- Ridge regression: `AOMRidge-Blender-headline-spxy3`, chosen by the refreshed paired Ridge results against both Ridge-default and Ridge-HPO.
- Classification: `AOM-PLS-DA-global-simpls-covariance`, retained as the only main-text classification AOM result; POP and AOM-Ridge classification variants are supplementary.

### Refreshed headline numbers

- Regression vs PLS-HPO: `ASLS-AOM-compact-cv5` median RMSEP ratio `1.002` on `N=32`, `15/32` wins, Holm-adjusted `p=1.000`.
- Regression vs PLS-default: `ASLS-AOM-compact-cv5` median RMSEP ratio `0.985` on `N=52`, `33/52` wins, `p=0.410`.
- Ridge vs Ridge-HPO: `AOMRidge-Blender-headline-spxy3` median RMSEP ratio `0.956` on `N=34`, `27/34` wins, `p=0.011`.
- Ridge vs Ridge-default: `AOMRidge-Blender-headline-spxy3` median RMSEP ratio `0.913` on `N=52`, `44/52` wins, `p=2.8e-06`.
- Classification: `AOM-PLS-DA-global-simpls-covariance` median balanced-accuracy gain `0.159` on `N=13`, `12/13` wins, `p=0.007`.
- Time-budget headline: PLS-HPO median total time `984.90 s` versus selected AOM-PLS median total time `1.94 s`, about `508x` faster on the reported medians.

### Cleanup confirmation

- Removed CatBoost/CNN/deep-learning wording from the live manuscript, generated tables, active figure-generation script, legacy figure helper, and bibliography.
- Removed the two disallowed rows from `table_budget.tex`.
- Rewrote `fig_budget` to show only `PLS-default`, `PLS-HPO`, `Ridge-default`, `Ridge-HPO`, and `AOM (best)`.
- Removed the `nirs4all-webapp` URL from the paper path and removed its bibliography entry.
- Main manuscript now contains only the selected AOM variant per task; FastAOM, POP and non-selected AOM variants are in the supplement.

### Partial-data decisions

- `aggregate_stats.py --partial` still reports the stale `linear_hpo_seed0` workspace as missing.  The v4 tables and figures therefore continue to use `build_paper_figures.py` for the actual cartesian-HPO seed workspaces, matching the v3 data flow.
- The ASLS AOM-PLS vs PLS-HPO number moved materially from the prompt's v3 note, so the refreshed value `1.002` on `32` paired datasets is used in the abstract and main results.
- HPO claims are stated only on completed denominators: `36` PLS-HPO datasets and `35` Ridge-HPO datasets.

### Final checks

- `grep -iE "catboost|cnn-?1?d|talanta|tbd|to be completed|placeholder|pending|in progress" paper_aom/main.tex paper_aom/supplement.tex` returned empty output.
- Citation resolution check found `18` used BibTeX keys and `0` missing keys.
- Final PDFs: `paper_aom/main.pdf` is `12` pages / `434212` bytes; `paper_aom/supplement.pdf` is `32` pages / `498571` bytes.
- Final LaTeX logs have no fatal errors, emergency stops, undefined citations or unresolved references; remaining warnings are overfull/underfull boxes and float placement changes in long supplement tables.

## v5 update (2026-05-17)

### Dataset presentation

- Added `\subsection{Datasets}` under `\section{Datasets and protocol}` in the main manuscript, with the cohort diversity text, split protocol, outlier-handling sentence and a supplement forward reference.
- New compact dataset summary table:
  - Classification: `N=17`, median/min/max `n=511/56/7323`, median/min/max `p=1951/235/2177`, median `p/n=2.055`, median classes `C=2`, median largest-class share `I=0.513`.
  - Regression: `N=61`, median/min/max `n=402/40/45417`, median/min/max `p=1023/125/4200`, median `p/n=2.382`.
- Added `paper_aom/tables/table_dataset_statistics.tex`.
- Replaced the old cohort listing in the supplement with `paper_aom/tables/table_dataset_overview_supp.tex`: a `longtable` in `landscape`, one row per cohort dataset, with dataset, task, `n`, `p`, `p/n`, response/range, split type and domain.

### Simple AOM baselines

- `AOM-compact-cv5` vs PLS-default: `N=52`, median RMSEP ratio `0.996`, `32/52` wins, Holm `p=0.735`.
- `AOM-compact-cv5` vs PLS-HPO: `N=32`, median RMSEP ratio `0.990`, `19/32` wins, Holm `p=1.000`.
- `AOMRidge-global-compact-none` vs Ridge-default: `N=52`, median RMSEP ratio `0.974`, `41/52` wins, Holm `p=0.002`.
- `AOMRidge-global-compact-none` vs Ridge-HPO: `N=34`, median RMSEP ratio `0.978`, `21/34` wins, Holm `p=0.735`.
- Refreshed `table_main_results.tex`, `table_paired_stats.tex`, and `table_time_budget.tex` with the plain AOM rows alongside the selected v4 rows.

### Figures regenerated

- Regenerated `fig_results.pdf` with plain and selected AOM-PLS/AOM-Ridge bars.
- Regenerated `fig_dataset_variant_heatmap.{pdf,png}` with compact AOM-PLS and global compact AOM-Ridge columns.
- Regenerated `fig_accuracy_time_pareto.{pdf,png}` with separate simple-vs-selected AOM markers.
- Regenerated `fig_budget.pdf` with both `AOM (simple)` and `AOM (best)` bars.
- Regenerated `fig_runtime_distribution.{pdf,png}`, `fig_operator_heatmap.{pdf,png}`, and `fig_fastaom_variants.{pdf,png}` from the refreshed generator.
- Added `fig_dataset_diversity.{pdf,png}`: log-log `n_samples` vs `n_features`, colored by regression/classification with the Okabe-Ito theme and a domain-count inset.
- `fig_concept.pdf` and `fig_math.pdf` were not modified.

### Supplement layout fixes

- Added only `pdflscape` to `supplement.tex`; no extra layout packages were needed.
- Converted the cohort overview to a landscape `longtable` with repeated headers and continuation footer.
- Rotated the per-dataset regression longtable (`table_supplement_long_results.tex`) to landscape and added break points inside long dataset/variant names.
- Shortened the seed-stability table display labels to remove the previous wide-table overflow.
- Rendered the final supplement pages to PNGs with `pdftoppm -r 100`; the landscape longtables and figure/table boundaries were visually checked from the generated contact sheet.

### Acceptance gate

- Cleanliness grep on `main.tex` and `supplement.tex`: `0`, `0`.
- v5 presence checks: `AOM-compact-cv5=7`, `AOMRidge-global-compact-none=6`, `table_dataset_statistics=1`, `fig_dataset_diversity=1`, supplement `longtable=1`.
- Repository link checks: `gbeurier/aom=1`, `gbeurier/pls4all=1`, `GBeurier/nirs4all=1`.
- Undefined-reference grep: `main.log=0`, `supplement.log=0`.
- Supplement overfull `\hbox >20pt`: `1` line, below the `<=3` gate.
- Rebuilt PDFs exist: `paper_aom/main.pdf` (`14` pages, `453K`) and `paper_aom/supplement.pdf` (`44` pages, `502K`).
- Refresh commands run: `aggregate_stats.py --partial`, `selector_diagnostics.py`, `build_paper_figures.py`, then final `pdflatex`/`bibtex` rebuilds.  The legacy `aggregate_stats.py --partial` still reports the stale `linear_hpo_seed0` path as missing; the v5 tables and figures are produced by `build_paper_figures.py`, which reads the actual cartesian-HPO seed workspaces.

## v6 update (2026-05-17)

### Per-figure variant audit

- `fig_budget`: caption now claims the eight paper variants. Before v6 the body had six bars (`PLS-default`, `PLS-HPO`, `Ridge-default`, `Ridge-HPO`, `AOM (simple)`, `AOM (best)`) and collapsed AOM-PLS with AOM-Ridge, so the body did not match the claim. After v6 the body has exactly `PLS-default`, `PLS-HPO`, `AOM-PLS (simple)`, `AOM-PLS (best)`, `Ridge-default`, `Ridge-HPO`, `AOM-Ridge (simple)`, `AOM-Ridge (best)`.
- `fig_runtime_distribution`: caption now claims all eight paper variants. Before v6 the body had six boxes (`PLS-HPO total`, `Ridge-HPO total`, `AOM-compact fit`, `ASLS-AOM fit`, `AOMRidge-global fit`, `AOMRidge-Blender fit`) and omitted `PLS-default` and `Ridge-default`. After v6 the body has all eight boxes listed below.
- `fig_accuracy_time_pareto`: caption claims all eight paper variants. Before v6 the body already had eight points, but the AOM labels were runner-style and the time-axis wording did not make the total fit/search convention explicit. After v6 the body has the exact eight paper labels, family colours, and role markers (`^` for default/HPO, `s` for simple, `o` for best), with median total fit/search time on the x-axis.
- `fig_results`: caption claims eight paired regression comparisons. Before v6 the keep list already covered all eight paired rows, but the displayed labels were not normalized to the paper-label vocabulary. After v6 the body rows are `AOM-PLS (simple) vs PLS-default`, `AOM-PLS (best) vs PLS-default`, `AOM-PLS (simple) vs PLS-HPO`, `AOM-PLS (best) vs PLS-HPO`, `AOM-Ridge (simple) vs Ridge-default`, `AOM-Ridge (best) vs Ridge-default`, `AOM-Ridge (simple) vs Ridge-HPO`, and `AOM-Ridge (best) vs Ridge-HPO`.
- `fig_dataset_variant_heatmap` (supplement): supplement-only comparison heatmap. Before v6 the column order was not the requested PLS, AOM-PLS, Ridge, AOM-Ridge, exploration sequence. After v6 the body columns are ordered as `PLS-default`, `PLS-HPO`, `AOM-PLS (simple)`, `AOM-PLS (best)`, `Ridge-default`, `Ridge-HPO`, `AOM-Ridge (simple)`, `AOM-Ridge (best)`, then the FastAOM/POP exploration columns; the simple AOM columns are present.
- `fig_dataset_diversity`: single-purpose cohort-shape figure, not a variant comparison; no eight-variant claim.
- `fig_operator_heatmap` and `fig_fastaom_variants`: supplement-only scoped figures; no all-eight claim. Both regenerate cleanly.

### Search-budget figure

- `PLS-default`: `25`
- `PLS-HPO`: `3000`
- `AOM-PLS (simple)`: `45` fits, median observed time `1.76 s`
- `AOM-PLS (best)`: `45` fits, median observed time `1.94 s`
- `Ridge-default`: `15`
- `Ridge-HPO`: `6000`
- `AOM-Ridge (simple)`: `450` fits, median observed time `21.60 s`
- `AOM-Ridge (best)`: `32` fits, median observed time `960.71 s`

### Runtime-distribution figure

- `PLS-default total`
- `PLS-HPO total`
- `AOM-PLS (simple) fit`
- `AOM-PLS (best) fit`
- `Ridge-default total`
- `Ridge-HPO total`
- `AOM-Ridge (simple) fit`
- `AOM-Ridge (best) fit`

### Reproducibility rewrite

Chose Option B. The standalone `Reproducibility` section was removed and the software table now follows the Data and code availability section. The rewritten reproducibility paragraph is:

> The reproducibility protocol is defined by the cohort denominators in
> Section~\ref{sec:datasets}, the fold-local model-selection rules in the
> Methods, and paired dataset-level tests with Holm correction for the reported
> families of comparisons.  The supplementary material gives the full cohort
> manifest, per-dataset regression table, seed-stability diagnostics, failure
> ledger and software-validation matrix.  Table~\ref{tab:software} summarizes
> the software artifacts and validation status for the public release.

The supplement section is now `Reproducibility and Software Artifacts`; it refers to benchmark result tables produced by the public repositories announced in the main manuscript, reports the cohort denominators, seed protocol, paired tests and Holm correction, and references only `Table~\ref{tab:sup_software}` for the software matrix.

### Acceptance gate

- Cleanliness grep on `main.tex` and `supplement.tex`: `0`, `0`.
- Local-path/script grep for `paper_aom/review`, `paper_aom/scripts`, `aggregate_stats`, `selector_diagnostics`, and `build_paper_figures`: empty.
- Main-manuscript runner-key counts: `pls-default-cv5=1`, `pls-tabpfn-hpo=1`, `AOM-compact-cv5=9`, `ASLS-AOM-compact-cv5=3`, `ridge-default-cv5=1`, `ridge-tabpfn-hpo=1`, `AOMRidge-global-compact-none=7`, `AOMRidge-Blender=4`.
- Repository link checks in `main.tex`: `gbeurier/aom=1`, `gbeurier/pls4all=1`, `GBeurier/nirs4all=1`.
- Undefined-reference grep: `main.log=0`, `supplement.log=0`.
- PDFs rebuilt and present: `paper_aom/main.pdf` and `paper_aom/supplement.pdf`.
- Refresh/rebuild commands run: `python paper_aom/review/aggregate_stats.py --partial`, `python paper_aom/review/selector_diagnostics.py ...`, `python paper_aom/review/build_paper_figures.py`, then the requested `pdflatex`/`bibtex` passes for `main.tex` and `supplement.tex`. The legacy partial aggregation warning about the stale `linear_hpo_seed0` workspace still appears; the rebuilt figures/tables use the actual cartesian-HPO seed workspaces.

### Self-review

Rendered `main.pdf` was reviewed page-by-page with `pdftotext -f N -l N -layout`, and the supplement was reviewed the same way. I also extracted the generated figure PDFs directly with `pdftotext` to verify body labels. No caption now claims all variants while omitting a plotted variant, and no rendered local path/script references remain. The main residual weakness is interpretive rather than a broken build: `AOM-Ridge (best)` uses a top-level selector count (`8 candidates x 3 outer folds + 8 refits`) because its candidate internals are heterogeneous; the observed median time annotation is therefore the clearest cost signal. LaTeX still reports overfull/underfull boxes and float-placement warnings in long tables/figures, but there are no undefined references or citations.

## v7 update (2026-05-17)

### Strict intersection

- `N_cap=32` regression datasets are used for all main paired regression comparisons.
- Computation: `paper_aom/review/paper_data.py` reads the current CSVs for the eight paper variants, normalizes dataset IDs by the final path component, filters `status=="ok"`, requires all three seed CSVs for `pls-tabpfn-hpo-25trials` and `ridge-tabpfn-hpo-60trials`, requires three ok seeds in the AOM-PLS seeds012 table for `AOM-compact-cv5-numpy` and `ASLS-AOM-compact-cv5-numpy`, and requires ok rows in the AOM-Ridge headline table for `AOMRidge-global-compact-none` and `AOMRidge-Blender-headline-spxy3`.
- `aggregate_stats.py --partial` and `build_paper_figures.py` now filter regression rows to this CSV join before computing paired medians, wins, p-values, tables and figures.

### Refreshed headline numbers on `N_cap=32`

- `AOM-PLS (simple)` vs PLS-default: median RMSEP ratio `0.991`, `22/32` wins, Holm `p=0.896`.
- `AOM-PLS (best)` vs PLS-default: `0.985`, `20/32`, `p=1.000`.
- `AOM-PLS (simple)` vs PLS-HPO: `0.990`, `19/32`, `p=1.000`.
- `AOM-PLS (best)` vs PLS-HPO: `1.002`, `15/32`, `p=1.000`.
- `AOM-Ridge (simple)` vs Ridge-default: `0.974`, `25/32`, `p=0.007`.
- `AOM-Ridge (best)` vs Ridge-default: `0.918`, `27/32`, `p=2.6e-04`.
- `AOM-Ridge (simple)` vs Ridge-HPO: `0.984`, `19/32`, `p=1.000`.
- `AOM-Ridge (best)` vs Ridge-HPO: `0.966`, `25/32`, `p=0.033`.

### Prediction-quality figures

- Main: `paper_aom/figures/fig_paired_rmsep_scatter.{pdf,png}`. Four log-log paired RMSEP panels for selected AOM-PLS/AOM-Ridge vs default and HPO references, with domain colors and per-panel `N`, wins, ratio and Holm p-value.
- Main: `paper_aom/figures/fig_r2_cdf.{pdf,png}`. One coverage curve panel showing the fraction of `N=32` datasets at or above each test-`R^2` threshold for all eight paper variants.
- Supplement: `paper_aom/figures/fig_gain_per_dataset.{pdf,png}` under `\section{Per-dataset prediction quality}`. Two horizontal gain panels: selected AOM-PLS vs PLS-default/PLS-HPO and selected AOM-Ridge vs Ridge-default/Ridge-HPO.

### Incident-language sweep

The final requested paper grep returns zero hits:

```text
paper_aom/main.tex:0
paper_aom/supplement.tex:0
```

Command pattern:

```bash
grep -ciE "lucas|compute.budget|completed.subset|did not complete|partial cohort|stall|crash|oom|fusarium.*fail|workspace.*completed|workspaces that completed|attempted but unsuccessful" paper_aom/main.tex paper_aom/supplement.tex
```

### Working artifact

- `paper_aom/review/missing_datasets_per_variant.md`
- Size: `8707 bytes`
- Contains the reference regression cohort, the full `N_∩=32` list, per-variant status counts and missing rows per variant. It is not referenced from `main.tex` or `supplement.tex`.

### Acceptance gate

- Cleanliness grep on `main.tex` and `supplement.tex`: `0`, `0`.
- Local-path/script grep for `paper_aom/review`, `paper_aom/scripts`, `aggregate_stats`, `selector_diagnostics` and `build_paper_figures`: empty.
- Dev-incident grep on `main.tex` and `supplement.tex`: `0`, `0`.
- New figure files exist: `fig_paired_rmsep_scatter.pdf`, `fig_r2_cdf.pdf`, `fig_gain_per_dataset.pdf`.
- Figure placements: `fig_paired_rmsep_scatter=1` in `main.tex`, `fig_r2_cdf=1` in `main.tex`, `fig_gain_per_dataset=1` in `supplement.tex`.
- Intersection language: `grep -c "intersection" paper_aom/main.tex` returns `1`.
- Runner-key counts in `main.tex`: `pls-default-cv5=1`, `pls-tabpfn-hpo=1`, `AOM-compact-cv5=9`, `ASLS-AOM-compact-cv5=3`, `ridge-default-cv5=1`, `ridge-tabpfn-hpo=1`, `AOMRidge-global-compact-none=7`, `AOMRidge-Blender=4`.
- Repository link checks in `main.tex`: `gbeurier/aom=1`, `gbeurier/pls4all=1`, `GBeurier/nirs4all=1`.
- Undefined-reference grep: `paper_aom/main.log:0`, `paper_aom/supplement.log:0`.
- Missing-dataset artifact exists and variant-key grep returns `16`.
- Refresh/rebuild commands run: `aggregate_stats.py --partial`, `selector_diagnostics.py`, `build_paper_figures.py`, then `pdflatex`/`bibtex` passes for `main.tex` and `supplement.tex`.

### Self-review

- I did not retune the older supplementary FastAOM narrative to the strict `N_cap=32` denominator; the main regression tables, main figures, supplement per-dataset heatmap and long table now use the strict intersection, while the FastAOM family table remains a scoped exploratory summary. The remaining LaTeX warnings are overfull/underfull boxes and float-placement changes in wide tables, with no undefined references.
