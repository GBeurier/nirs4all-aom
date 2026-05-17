# Codex v6 — Variant coverage audit + Reproducibility section fix

Working directory: `/home/delete/nirs4all/nirs4all`. Full write
authority on `paper_aom/`. Do not commit.

This is a tight revision pass on the v5 draft. Two specific issues
to fix, plus a self-review at the end. Preserve everything else
(v4 cleanliness: no CatBoost/CNN/Talanta; v5 additions: Datasets
subsection, simple AOM baselines, supplement longtable layout).

## User's brief — verbatim

> Les figures ne présentent pas systématiquement tous les variants
> (search budget), fais attention à ca. Le paragraph Reproducibility
> ne veut rien dire. Soit tu met les documents en supp et tu
> références les supp, soit tu met dans le main, mais tu référence
> pas un markdown local, ca veut rien dire. Corrige tout ca et fais
> review par codex.

Translated: (1) the figures do not systematically include all the
paper's variants — the search-budget figure in particular is
inconsistent; audit and fix every comparison figure. (2) The
Reproducibility paragraph in main.tex is meaningless: it references
`paper_aom/review` (a local directory). Either put the reproduction
material in the supplement and reference the supplement, or put it
in main, but do not point at a local markdown — that is nonsense
in a published paper. Then have Codex review the work.

## The eight paper variants — single source of truth

The main manuscript currently builds its claims around these eight
variants. Every comparison figure must include all eight when the
figure is a comparison; the only exception is a figure scoped to a
single family (PLS-only or Ridge-only), in which case its caption
must say so explicitly.

| # | Variant key in CSV / runner | Paper label | Family |
| --- | --- | --- | --- |
| 1 | `pls-default-cv5` | PLS-default | PLS |
| 2 | `pls-tabpfn-hpo-25trials` | PLS-HPO | PLS |
| 3 | `AOM-compact-cv5-numpy` | AOM-PLS (simple) | AOM-PLS |
| 4 | `ASLS-AOM-compact-cv5-numpy` | AOM-PLS (best) | AOM-PLS |
| 5 | `ridge-default-cv5` | Ridge-default | Ridge |
| 6 | `ridge-tabpfn-hpo-60trials` | Ridge-HPO | Ridge |
| 7 | `AOMRidge-global-compact-none` | AOM-Ridge (simple) | AOM-Ridge |
| 8 | `AOMRidge-Blender-headline-spxy3` | AOM-Ridge (best) | AOM-Ridge |

Use exactly these eight paper labels everywhere — figure tick
labels, table rows, prose. Do not invent variants. Do not collapse
two variants into a single bar.

## Block A — Audit and fix every comparison figure

For each matplotlib figure, verify that the variants shown are
exactly the set the caption claims. If a figure is supposed to
present "all variants" or "the main methods", it must show all
eight. Patch the generator in
`paper_aom/review/build_paper_figures.py` and regenerate.

Specifically:

### fig_budget (`build_budget_figure` around line 1568)

Currently shows six bars `["PLS-default", "PLS-HPO", "Ridge-default",
"Ridge-HPO", "AOM (simple)", "AOM (best)"]`. The two AOM bars
collapse the PLS-AOM and Ridge-AOM families together, which is
incoherent (an AOM-PLS fit and an AOM-Ridge fit are not the same
candidate count). Rewrite as **eight bars** matching the paper
variants list above, with their actual candidate evaluations per
dataset. The four AOM bars are short by design — that is the point
of the figure. Use the family colour scheme from `FAMILY_COLORS`
(PLS, AOM-PLS, Ridge, AOM-Ridge).

Suggested values (compute exactly from the runner code in
`bench/tabpfn_paper/run_linear_hpo_paper_aom.py`, do not guess):

- `PLS-default`: 25 candidate fits (n_components ∈ [1..25], CV-5
  multiplied internally — count the actual `n_trials` reported by
  the runner).
- `PLS-HPO`: 600 cartesian × 5 Optuna trials = 3000 candidate fits
  (× CV-5 if your convention counts the CV multiplier).
- `Ridge-default`: 15 (alpha grid points).
- `Ridge-HPO`: 600 × 10 = 6000.
- `AOM-PLS (simple)`: 9-operator compact bank with internal CV-5 →
  the actual number from the AOM runner. Confirm.
- `AOM-PLS (best)`: same compact bank + ASLS branch → likewise
  compute.
- `AOM-Ridge (simple)`: global compact bank, no selector.
- `AOM-Ridge (best)`: Blender selector with spxy3.

For the AOM rows, also report the **median observed fit time** in
seconds (compute from the workspace CSVs) — annotate each AOM bar
with `Nfits | Ts s` to make the cost gap visible.

Caption update: explicitly list the eight bars and what each count
means. Drop the current ambiguous "AOM (simple)" framing.

### fig_runtime_distribution (`build_runtime_distribution` around line 1459)

Currently shows six box plots: `PLS-HPO total`, `Ridge-HPO total`,
`AOM-compact fit`, `ASLS-AOM fit`, `AOMRidge-global fit`,
`AOMRidge-Blender fit`. Missing: `PLS-default total` and
`Ridge-default total`.

Add the two missing default-CV5 baselines so the reader sees the
full spectrum from "no search" to "full search" to "AOM single
fit". Eight box plots total. Stable colour-coding by family.

Caption: state that the box plot includes all eight variants and
that AOM rows are single-fit times while PLS/Ridge rows include
the entire HPO or default-CV search.

### fig_accuracy_time_pareto (`build_accuracy_time` around line 1404)

Currently shows eight points (the eight variants). Verify the
labels are exactly the paper labels above. The PLS-default and
Ridge-default points sit at ratio 1.0 by definition (they are the
reference for their family) — that is correct.

Action: confirm the eight points are present, the legend uses the
four family colours plus a single shape per role (`^` for default,
`s` for simple, `o` for best, plus `^` for HPO since HPO is the
baseline at-cost), and the x-axis time is **fit + search time**
consistently (do not mix `total_time_s` for HPO with `fit_time_s`
for AOM without flagging it in the caption).

### fig_results (`build_results_overview` around line 1514)

Already paired-comparison rows. Verify the keep list includes:
- `AOM-compact-cv5 vs PLS-default`,
- `ASLS-AOM-compact-cv5 vs PLS-default`,
- `AOM-compact-cv5 vs PLS-TabPFN-HPO`,
- `ASLS-AOM-compact-cv5 vs PLS-TabPFN-HPO`,
- `AOMRidge-global-compact-none vs Ridge-default`,
- `AOMRidge-Blender vs Ridge-default`,
- `AOMRidge-global-compact-none vs Ridge-TabPFN-HPO`,
- `AOMRidge-Blender vs Ridge-TabPFN-HPO`.

That is eight rows. If the v5 figure is missing the last four, add
them. Verify visually after regeneration.

### fig_dataset_diversity (v5 new)

Single-purpose figure (cohort shape), not a comparison; no variant
audit needed.

### fig_dataset_variant_heatmap (supplement)

Supplement-only. Already exists. Verify that the column ordering
puts PLS family first, AOM-PLS next, Ridge, AOM-Ridge, then the
exploration variants. Confirm the simple AOM columns are present.

### fig_operator_heatmap, fig_fastaom_variants (supplement)

Supplement-only; no audit needed beyond verifying they regenerate.

## Block B — Fix the Reproducibility section in main.tex

Current section (`main.tex` around lines 600-614):

```latex
\section{Reproducibility}

The numerical artifacts are summarized in Table~\ref{tab:software}.
The tables and matplotlib figures in this manuscript are
regenerated from the review result workspaces by the aggregation
and figure scripts in \texttt{paper\_aom/review}.  The live cohort
denominators are those described in Section~\ref{sec:datasets}.

\begin{table}[t]
  \centering
  \caption{Software artifacts and validation status.}
  \label{tab:software}
  \small
  \input{tables/table_software.tex}
\end{table}
```

This is wrong for a published paper. It references
`paper_aom/review` (a private directory).

**Rewrite this section to one of two acceptable shapes**, your
choice — pick the one that flows better with the existing
Data & Code Availability section.

**Option A** — Keep `\section{Reproducibility}` in main, but make
it self-contained: describe the protocol (cohort denominators,
multi-seed setup, paired statistical tests with Holm correction,
software versions in the table) without pointing at any local
file. Forward-reference the supplement for the full cohort table
and per-dataset results.

**Option B** — Delete the `\section{Reproducibility}` paragraph
entirely (keep only the software table, possibly inline with the
Data & Code Availability section). The Methods + Datasets sections
already describe the protocol. The supplement holds the cohort,
per-dataset results, and software validation status. Forward-
reference the supplement and the announced repos.

Option B is cleaner and recommended unless there is something the
Methods section does not already say.

Either way, the final paragraph must NOT reference
`paper_aom/review`, `paper_aom/scripts`, `aggregate_stats.py`, or
any other local file name. The paper is a self-contained document.

The corresponding supplement section (currently `\section{Reproducibility}`
in supplement.tex) must (a) stay self-contained too, (b) refer back
to the announced repos rather than to local paths, and (c) describe
the protocol with full detail (cohort denominators, run-count per
seed, statistical-test family-wise correction, software validation
matrix referencing only the published Table N in the same
supplement).

## Block C — Audit + report

After your edits and rebuild, perform an internal review pass: read
the rebuilt `main.pdf` page by page (use `pdftotext -f N -l N
-layout main.pdf -`) and the supplement page by page. Verify:

1. No matplotlib figure caption claims "all variants" or "the main
   methods" while the figure body is missing a variant — list each
   figure's caption claim vs body content in your final report.
2. The Reproducibility section reads as a self-contained scientific
   paragraph; quote it in your report.
3. The Data & Code Availability section announces only the three
   public URLs (`GBeurier/nirs4all`, `gbeurier/aom`, `gbeurier/pls4all`)
   and nothing about local paths.
4. The supplement section that used to hold local-path references
   is also clean.

If you find any other issue (an orphan citation, a stale
`\ref{}`, a table caption that contradicts the table body), patch
it in this pass.

## Refresh + rebuild

```bash
python paper_aom/review/aggregate_stats.py --partial
python paper_aom/review/selector_diagnostics.py \
    --aompls bench/scenarios/runs/paper_aom_aompls_seeds012/results.csv \
    --aomridge bench/AOM_v0/Ridge/benchmark_runs/paper_aom_aomridge_seeds012/results.csv \
    --out paper_aom/review/ --tables paper_aom/tables/
python paper_aom/review/build_paper_figures.py

cd paper_aom
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode supplement.tex
bibtex supplement
pdflatex -interaction=nonstopmode supplement.tex
pdflatex -interaction=nonstopmode supplement.tex
```

## Acceptance gate (all must pass)

```bash
cd /home/delete/nirs4all/nirs4all

# v4 cleanliness preserved
grep -ciE "catboost|cnn|deep learning|gradient boosting|talanta|tbd|placeholder|pending|in progress" paper_aom/main.tex paper_aom/supplement.tex   # → 0

# Reproducibility no longer references local paths
grep -nE "paper_aom/review|paper_aom/scripts|aggregate_stats|selector_diagnostics|build_paper_figures" paper_aom/main.tex paper_aom/supplement.tex   # → empty

# eight variants present in main results / methods prose
for v in pls-default-cv5 pls-tabpfn-hpo AOM-compact-cv5 ASLS-AOM-compact-cv5 ridge-default-cv5 ridge-tabpfn-hpo AOMRidge-global-compact-none AOMRidge-Blender; do
  n=$(grep -c "$v" paper_aom/main.tex)
  echo "$v : $n"   # each must be ≥ 1
done

# repos still announced once each
grep -c "gbeurier/aom" paper_aom/main.tex                  # ≥ 1
grep -c "gbeurier/pls4all" paper_aom/main.tex              # ≥ 1
grep -c "GBeurier/nirs4all" paper_aom/main.tex             # ≥ 1

# no broken refs
grep -c "undefined" paper_aom/main.log paper_aom/supplement.log   # 0 each

# PDFs rebuilt
test -f paper_aom/main.pdf && test -f paper_aom/supplement.pdf
```

## v6 report

Append a `## v6 update (2026-05-17)` section to
`paper_aom/review/codex_report.md` with:
- Per-figure audit: list each comparison figure, the variants in
  its caption claim, the variants in its body, and whether they
  matched before vs after your edit.
- The new fig_budget bar list (8 bars with their counts).
- The new fig_runtime_distribution box list (8 boxes).
- Which Reproducibility shape you chose (Option A or B) and the
  rewritten paragraph in full.
- Confirmation that all acceptance commands above return their
  expected values.
- One paragraph self-review: any residual weaknesses you noticed
  but did not fix (and why).

## Hard constraints

- No new LaTeX packages.
- No new Python dependencies.
- Do not commit.
- Do not reintroduce CatBoost / CNN / Talanta / "tbd" / "to be
  completed" wording.
- Preserve `fig_concept.pdf` and `fig_math.pdf` (vector schematics).
- The simple AOM baselines (Block B from v5) must remain in main.
- The Datasets subsection (Block A from v5) must remain in main.
- The supplement longtable / landscape layout (Block D from v5)
  must remain.

Report back when done.
