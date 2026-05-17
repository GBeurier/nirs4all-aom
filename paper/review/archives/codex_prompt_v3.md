# Codex v3 — Finish the AOM paper (no Talanta framing, full draft)

Working directory: `/home/delete/nirs4all/nirs4all`.

You have full write authority on `paper_aom/` and its subfolders. Read
the existing artifacts, integrate the new FastAOM evidence, strip every
journal-specific reference, and produce a complete standalone draft of
the main manuscript + supplementary material with no remaining
"placeholder", "tbd", "pending" or "in progress" wording.

The user's instructions, verbatim:

> intègre fastAOM puis met le papier à jour [...] Je ne veux pas qu'il
> parle de talanta mais qu'il soit un draft complet qui parle d'AOM,
> qui intègre les nouveaux résultats. Qui parle math, performance, et
> qui compare à pls/ridge avec un hpo "complet" des prétraitements. Un
> mélange de changement de paradigme, d'optimisation et d'exploration.
> Je veux que dans le manuscript on ne présente que les variants
> performants avec explications, qu'on montre bien les comparaisons,
> et dans les supplémentary je veux une synthèse de l'exploration,
> des heatmaps complètes analysées, etc. En gros [...] qu'il soit à un
> niveau sans plus aucune partie manquante ni dans le main, ni dans
> supplementary. Un papier complet !

The deliverable is the complete paper (main.tex / supplement.tex /
PDFs), not a journal submission package.

---

## 1. Hard constraints

1. **Strip every mention of "Talanta"** from `paper_aom/main.tex` and
   `paper_aom/supplement.tex`. There are five mentions today:
   - `main.tex:752` ("For a Talanta submission, the priority experiments are...")
   - `main.tex:797` ("Before Talanta submission, add the Novelty Statement...")
   - `supplement.tex:57` ("For a Talanta submission, the supplement should...")
   - `supplement.tex:611` ("...the final Talanta cohort manifest is frozen.")
   - and any other you find. The bib entry for the 2005 Talanta paper
     in `references.bib` is a real citation and **must stay**.
   Replace every "for [journal] submission" framing with neutral
   "for the final manuscript" / "in this work" wording or remove the
   sentence entirely if it only flags an open submission task.
2. **No more "draft to be completed"** sections. Every section in main
   and supplement must read as finished prose with real numbers and
   real cross-references. If a section is currently a stub or a TODO
   list, either fill it from the available evidence or delete it.
3. **No new LaTeX packages.** Reuse those already loaded.
4. **Do not change the author block, affiliations or `\title{}`** —
   keep the existing manuscript title and authors.
5. **Do not commit or push.** The user commits manually.
6. **Do not delete benchmark CSVs or workspaces.** You may add new
   files under `paper_aom/`, `bench/AOM_v0/FastAOM/`, etc.
7. **Don't skip the LaTeX rebuild.** End the task by rebuilding both
   PDFs and checking they were produced.

---

## 2. Data you must integrate

### 2.1 FastAOM evidence (new, never integrated yet)

Source workspaces:
- `bench/scenarios/runs/paper_aom_fastaom_full60_seed0/` — full cohort,
  16 model variants + 4 reference variants, seed 0.
- `bench/scenarios/runs/paper_aom_fastaom_seed0/` — 11-dataset smoke
  cohort + per-variant `comparison.csv`, dashboard data, headline
  winners.
- `bench/AOM_v0/FastAOM/README.md` and `IMPLEMENTATION_NOTES.md` —
  authoritative description of the four FastAOM model families and
  the screening / low-rank math.

Headline files to lean on:
- `paper_aom_fastaom_full60_seed0/headline_with_lucas.csv` (wide table,
  one row per dataset, columns = models, values = median RMSEP).
- `paper_aom_fastaom_full60_seed0/headline_with_lucas_summary.csv`
  (per-model `n_datasets`, `median_rel_rmse`, `mean_rel_rmse`,
  `median_fit_time`).
- `paper_aom_fastaom_full60_seed0/headline_with_lucas_winners.csv`
  (per-model headline-wins count).
- `paper_aom_fastaom_seed0/comparison.csv` (per-dataset paired with
  PLS reference: `ref_pls_rmse`, `rel_rmse_vs_pls`, `delta_rmse_vs_pls`).
- `paper_aom_fastaom_full60_seed0/merged_results_with_lucas.csv` (long
  format, raw fit times per seed and per dataset).

### 2.2 Linear PLS / Ridge HPO baselines (partial but usable)

These runs implement the TabPFN-paper cartesian preprocessing protocol
(5 norm × 10 smooth × 3 baseline × 4 OSC = 600 combos, per-combo Optuna).
They stalled at ~40 / 60 datasets per cell (LUCAS_SOC_all_26650 blocker),
so they are **the explicit "complete preprocessing HPO" baseline** the
user asked us to compare against, on the subset where they finished.

Workspaces:
- `bench/scenarios/runs/paper_aom_linear_hpo_full_cartesian_pls-tabpfn-hpo-25trials_seed{0,1,2}/results.csv`
  (40 datasets × 3 seeds, PLS, 600 combos × 5 trials each).
- `bench/scenarios/runs/paper_aom_linear_hpo_full_cartesian_ridge-tabpfn-hpo-60trials_seed{0,1,2}/results.csv`
  (39 datasets × 3 seeds, Ridge, 600 combos × 10 trials each).
- `bench/scenarios/runs/paper_aom_linear_hpo_full_cartesian_default_cv5_all/results.csv`
  (default-CV reference, 60 datasets, no HPO — used as the "untuned
  PLS/Ridge" baseline for the time-budget comparison).

When you describe these in the paper, be explicit:
"Linear HPO baselines were obtained on the subset of $N$ datasets where
the per-combo Optuna search converged (the LUCAS_SOC subset exceeded
our compute budget)."

### 2.3 Existing AOM evidence (already in v2 numbers)

- `bench/scenarios/runs/paper_aom_aompls_seeds012/results.csv` —
  multi-seed AOM-PLS / POP-PLS regression, 56-60 datasets × 3 seeds.
- `bench/AOM_v0/Ridge/benchmark_runs/paper_aom_aomridge_seeds012/`
  (top5_fast variant set) — partial 25/60 datasets, OOM-blocked.
- `bench/AOM_v0/Ridge/benchmark_runs/all54_headline/results.csv` —
  full-cohort single-seed Ridge headline (Blender / AutoSelect /
  Local-knn50 / global-compact-none).
- `bench/scenarios/runs/paper_aom_aompls_da_seeds012/results.csv`
  + `bench/AOM_v0/Ridge/benchmark_runs/paper_aom_aomridge_cls_seeds012/results.csv`
  — classification.
- `paper_aom/review/final_stats.md` — current aggregated numbers
  (regenerated by `aggregate_stats.py --partial`).
- `paper_aom/review/classification_stats.md` and
  `classification_stats_ext.md` — classification paired tests.
- `paper_aom/review/selector_diagnostics.csv`,
  `operator_frequency.csv`, `compact_bank_justification.md`,
  `failure_mode_table.csv` — selector/operator diagnostics.

### 2.4 Refresh the aggregator before writing

Run:
```bash
python paper_aom/review/aggregate_stats.py --partial
python paper_aom/review/selector_diagnostics.py \
    --aompls bench/scenarios/runs/paper_aom_aompls_seeds012/results.csv \
    --aomridge bench/AOM_v0/Ridge/benchmark_runs/paper_aom_aomridge_seeds012/results.csv \
    --out paper_aom/review/ --tables paper_aom/tables/
```
Then read `paper_aom/review/final_stats.md` again. Lift every concrete
median / win-rate / Wilcoxon $p$ / Friedman rank used in the abstract
and Results from that file or from the FastAOM summary CSVs above.
Never invent numbers.

You may extend `aggregate_stats.py` (or add a small companion script
under `paper_aom/review/`) to (a) ingest the FastAOM long-format CSVs,
(b) emit a paired comparison table FastAOM vs PLS-TabPFN-HPO and
FastAOM vs Ridge-TabPFN-HPO on the overlapping datasets,
(c) emit a runtime table for FastAOM. Save outputs under
`paper_aom/review/` and reference them from the new tables.

---

## 3. "Performant variants" rule for the main manuscript

The user's hard rule: **main text presents only the performant variants
with explanations and comparisons; non-performant variants live in the
supplement.**

Apply this filter:

| Family | Performant (main text) | Exploration only (supplement) |
| --- | --- | --- |
| AOM-PLS | `AOM-compact-cv5`, `ASLS-AOM-compact-cv5`, `AOM-default-nipals-adjoint` (the three currently-cited variants) | the other AOM-PLS variants and seed-stability tables |
| FastAOM | the **top three by median rel RMSEP** in `headline_with_lucas_summary.csv` after filtering to variants run on $\ge$ 50 datasets, **plus the orchestrator entry point** (`FastAOMPLSRidge`). On the current data those are: `FastAOM-sparse-mkr-supervised` (median rel 1.009, N=50), `FastAOM-sparse-mkr-compact` (1.022, N=50), `FastAOM-single-chain-compact` (1.052, N=52). Verify with the refreshed CSV before writing. | all `FastAOM-hard-chain-*` (compact, asls, multibase, osc, supervised, compact-d4), `FastAOM-soft-chain-compact`, `FastAOM-single-chain-supervised-cv5-numpy` |
| POP-PLS | keep only the one variant that is competitive against PLS (`POP-PLS-DA-simpls-covariance` in classification). Both regression POP variants underperformed massively (`POP-nipals-adjoint-numpy` median rel 1.475 and `nirs4all-POP-PLS-default` 4.752) — those go to supplement only, with a clear "POP-PLS is not competitive on regression at default settings" note. | both POP regression variants, with diagnostics |
| AOM-Ridge | `Blender`, `AutoSelect`, `global-compact-none`, `Local-knn50` (already in main text via Option A headline) | seed-stability checks, top5_fast partial results |
| Classification | the two variants that win Wilcoxon-Holm (AOM-PLS-DA-global-simpls-covariance, POP-PLS-DA-simpls-covariance) + AOM-Ridge-Cls if competitive | the n.s. variants |
| Linear HPO baselines | the partial 40-dataset HPO results are the headline baseline for the comparison; cite N explicitly | the per-trial diagnostics, per-combo Optuna logs (only mention path) |

---

## 4. Main manuscript structure (target outline)

Rebuild / harmonize `paper_aom/main.tex` around the following sections.
Reuse existing prose wherever it is still accurate; rewrite the rest.

1. **Abstract** (existing, update with FastAOM headline number and
   drop any Talanta-specific framing).
2. **Introduction** — paradigm shift: preprocessing-as-model-internal
   calibration. Keep the existing rationale; add one sentence about
   the practical cost of "complete preprocessing HPO" and forward-
   reference Section 5 (comparison with cartesian-HPO PLS/Ridge).
3. **Related work** — short paragraph each on: (a) external preprocessing
   search (TabPFN-paper style), (b) AOM-PLS and POP-PLS precedents,
   (c) low-rank kernel methods and operator dictionaries (motivating
   FastAOM).
4. **Methods**
   - 4.1 Operator-adaptive calibration (math from current §3-4).
   - 4.2 AOM-PLS (math + compact bank justification, cite
     `compact_bank_justification.md`).
   - 4.3 AOM-Ridge (math + selectors: AutoSelect, Blender, Local-knn50,
     global-compact-none).
   - 4.4 **FastAOM** (new) — present the four FastAOM model families
     from `IMPLEMENTATION_NOTES.md` but in the main text **show only
     the screening / low-rank math + the two performant model classes**
     (`SparseMultiKernelRidge` and `SingleChainPLSRidge`/orchestrator).
     The hard/soft variants are mentioned as "additional chain-routing
     strategies explored in the supplement". Include one mathematical
     display for the kernel-vector product
     $K_s \approx U C_s U^\top$ and one for the screening score.
5. **Datasets and protocol** — point to cohort manifest with current
   counts. Refresh from `paper_aom/review/cohort_manifest.csv`.
6. **Results**
   - 6.1 Headline regression: AOM-PLS vs PLS-default and vs PLS-TabPFN-HPO
     (paired stats, multi-seed median, win counts).
   - 6.2 AOM-Ridge: Blender vs Ridge-default and vs Ridge-TabPFN-HPO.
   - 6.3 **FastAOM**: SparseMultiKernel-supervised vs PLS-TabPFN-HPO
     and vs AOM-PLS (paired ratio, win counts, fit-time comparison).
   - 6.4 Time-budget Pareto (regenerate or re-cite
     `figures/fig_accuracy_time_pareto.{pdf,png}` +
     `tables/table_time_budget.tex`).
   - 6.5 Classification as secondary validation (existing prose, refresh
     numbers from `classification_stats.md`).
7. **Discussion** — paradigm change, where AOM wins, where it loses;
   what FastAOM adds (cheaper exploration of chain space); explicit
   honesty about the LUCAS subset gap.
8. **Reproducibility** — refresh against `table_software.tex` and
   `paper_aom/review/codex_report.md`.
9. **Conclusion** — concise.

If the existing main.tex has a `\section{Open items}` or "remaining
experiments" section, **delete it** — the user wants a complete paper,
not a roadmap.

---

## 5. Supplement structure (target outline)

The supplement is where the full exploration lives.

1. Notation + linear-operator scope (keep current).
2. Full math derivations (keep current AOM-PLS / AOM-Ridge sections,
   add §FastAOM derivations: chain grammar, simplification,
   low-rank SVD identities, screening, four model variants
   side-by-side).
3. **Operator bank exploration** — operator-frequency table
   (`operator_frequency.csv`), compact-vs-default analysis, full
   selector heatmap (build it: per-dataset × per-operator selection
   counts, as a heatmap PNG saved under
   `paper_aom/figures/fig_operator_heatmap.{pdf,png}`). Analyze it
   in prose: which operators dominate which dataset families, which
   datasets refuse the compact bank, what this implies for bank
   curation.
4. **FastAOM exploration** — full 16-variant table
   (`headline_with_lucas_summary.csv`), all four chain-routing
   strategies' winner counts, runtime distribution, dependency on
   chain depth / rank / top_k caps (use diagnostics from
   `bench/AOM_v0/FastAOM/IMPLEMENTATION_NOTES.md`).
5. **Linear HPO baseline details** — cartesian protocol, per-combo
   Optuna budget (5 trials PLS / 10 trials Ridge), known partial-cohort
   caveat (40/60 datasets), per-dataset comparison heatmap PLS-HPO vs
   PLS-default vs AOM-PLS (build a small heatmap: rows = datasets,
   columns = variants, cell = rel RMSEP).
6. **Per-dataset full results table** — long-form table for the
   regression cohort (median RMSEP per variant per dataset).
7. **Classification full results** — all four AOM-PLS-DA variants +
   AOM-Ridge-Cls variants, paired stats including the n.s. ones.
8. **Failure modes** — `failure_mode_table.csv` analysis.
9. **Seed-stability** — per-variant winner-change counts, rank
   correlations across seeds.
10. **Reproducibility** — cohort manifest, software versions
    (`table_software.tex`), exact commands for each runner, AI-assistance
    statement (the existing one; just drop the "Talanta" wording).

Every supplement section must have prose, not just a table.

---

## 6. Figures to produce or refresh

| Figure | Path | Status | Action |
| --- | --- | --- | --- |
| Concept | `figures/fig_concept.pdf` | exists | keep, no change |
| Math | `figures/fig_math.pdf` | exists | keep |
| Accuracy/time Pareto | `figures/fig_accuracy_time_pareto.{pdf,png}` | exists, partial | regenerate via `aggregate_stats.py` so it includes FastAOM points |
| Runtime distribution | `figures/fig_runtime_distribution.{pdf,png}` | exists, partial | regenerate including FastAOM variants |
| Results overview | `figures/fig_results.pdf` | exists | regenerate or extend with FastAOM-PLS comparison |
| Budget | `figures/fig_budget.pdf` | exists | confirm numbers still match `table_time_budget.tex` |
| Operator heatmap (NEW) | `figures/fig_operator_heatmap.{pdf,png}` | does not exist | build from `selector_diagnostics.csv` and `operator_frequency.csv`; cluster rows by dataset family |
| Per-dataset comparison heatmap (NEW) | `figures/fig_dataset_variant_heatmap.{pdf,png}` | does not exist | build from `headline_with_lucas.csv` + AOM-PLS / AOM-Ridge / PLS-HPO ratios |
| FastAOM model-family comparison (NEW) | `figures/fig_fastaom_variants.{pdf,png}` | does not exist | small bar/dotplot of the 16 FastAOM variants ordered by median rel RMSEP, fit-time on second axis |

For the new figures: matplotlib only, no extra dependencies, saved as
both PDF and PNG (300dpi), generation script under
`paper_aom/review/build_paper_figures.py` (or extend an existing
script if simpler).

---

## 7. Tables to refresh or add

| Table | File | Action |
| --- | --- | --- |
| Main results | `tables/table_main_results.tex` | refresh with current numbers, add FastAOM-SparseMKR row |
| Paired stats | `tables/table_paired_stats.tex` | regenerate via `aggregate_stats.py`, include FastAOM rows |
| Time budget | `tables/table_time_budget.tex` | refresh with FastAOM and linear-HPO totals |
| Classification | `tables/table_classification_main.tex` | refresh from `classification_stats.md` |
| Selector diagnostics | `tables/table_selector_diagnostics.tex` | refresh |
| Operator bank | `tables/table_operator_bank.tex` | refresh |
| Benchmark diversity | `tables/table_benchmark_diversity.tex` | refresh |
| Software | `tables/table_software.tex` | confirm FastAOM row added with status `validated by four Codex review rounds` |
| FastAOM-variant table (NEW) | `tables/table_fastaom_variants.tex` | full 16-row variant table, columns: family, N, median rel RMSEP, median fit time, winners |
| Long-form results (supplement, NEW) | `tables/table_supplement_long_results.tex` | per-dataset × per-variant rel RMSEP, use `longtable` package which is already in supplement.tex |

---

## 8. Output sequence

1. Read the existing `main.tex`, `supplement.tex`, the v1/v2 codex
   reports, and the data sources listed above.
2. Refresh aggregator + selector diagnostics (Section 2.4 commands).
3. Write the FastAOM ingestion add-on (if needed) and emit the new
   paired-stat outputs.
4. Build the new figures and tables.
5. Strip Talanta wording.
6. Rewrite main.tex and supplement.tex sections per Sections 4-5.
7. Rebuild PDFs:
   ```bash
   cd paper_aom && \
     pdflatex -interaction=nonstopmode main.tex && \
     pdflatex -interaction=nonstopmode main.tex && \
     pdflatex -interaction=nonstopmode supplement.tex && \
     pdflatex -interaction=nonstopmode supplement.tex
   ```
   Verify both PDFs were produced (check `main.pdf`, `supplement.pdf`
   mtime). Overfull/underfull box warnings are acceptable. Fatal LaTeX
   errors are not.
8. Append a `## v3 update (2026-05-17)` section to
   `paper_aom/review/codex_report.md` with:
   - the file list you touched,
   - the headline numbers used in the abstract,
   - the FastAOM integration summary,
   - any data source you found insufficient and how you handled it,
   - confirmation that no "Talanta" or "tbd" or "draft to be completed"
     wording remains (run `grep -n "Talanta\|talanta\|tbd\|TBD\|draft to be completed" paper_aom/main.tex paper_aom/supplement.tex` and paste the empty result).

---

## 9. Final acceptance check

The task is done iff:

- `grep -i "talanta" paper_aom/main.tex paper_aom/supplement.tex` is
  empty (it is OK if `references.bib` still has the citation entry).
- `grep -iE "tbd|to be completed|placeholder|in progress|remaining experiments" paper_aom/main.tex paper_aom/supplement.tex` is empty.
- Every `\input{}` target resolves.
- `paper_aom/main.pdf` and `paper_aom/supplement.pdf` both rebuilt.
- The "v3 update" section in `paper_aom/review/codex_report.md`
  documents every change you made.

Report back when done.
