# Codex v5 — Datasets presentation + simple AOM baselines + supplement layout

Working directory: `/home/delete/nirs4all/nirs4all`. Full write
authority on `paper_aom/`. Do not commit.

This is a **focused revision pass on the v4 draft**, not a full
rewrite. Keep the v4 structure, abstract focus, and the absence of
CatBoost / CNN / Talanta wording. Only fix the four issues below.

## User's brief — verbatim

> des problèmes. Les supplémentary tabs se chevauchent, c'est pas
> propre. En plus, les datasets sont présentés nulle part. On doit
> reprendre la présentation du tabpfn_paper (robin), pour les
> datasets. Et je trouve que les modèles de références sont peu être
> trop complexe. Il faudrait les baselines de modèles "simples":
> AOM-PLS-cv5 ou pareil pour Ridge, en plus du reste. JE dois
> justifier que c'est plus intéressant de faire ca que de faire de
> la grid avec pls ou ridge.

Translated: (1) supplement tables overlap and look unclean. (2) the
datasets are not presented anywhere; copy the tabpfn_paper style for
that. (3) the reference comparators are arguably too complex; add a
**simple AOM baseline** (`AOM-PLS-cv5`, and the same for Ridge) so
we can show that even the *plain* AOM is already better than running
a preprocessing grid with default PLS or Ridge. (4) strengthen the
justification: why is doing this *more interesting* than running a
preprocessing grid with PLS or Ridge?

## Inputs you must read first

1. `paper_aom/main.tex` and `paper_aom/supplement.tex` — current v4 state.
2. `paper_aom/review/codex_prompt_v4.md` — the rules that produced
   the v4 (still apply: no CatBoost/CNN/Talanta/etc.).
3. `paper_aom/review/codex_report.md` (especially the `## v4 update`
   section) — the choices Codex made.
4. **`bench/tabpfn_paper/article/main.tex`** — the reference draft
   for dataset presentation. Read in particular:
   - `\subsection{Datasets}` at line 141 (4 paragraphs + figure
     reference to `Figures/dataset_diversity.png` + reference to the
     supplementary long tables).
   - `Tables/table_dataset_statistics.tex` — compact summary table
     used in the main text (one row per task: classification /
     regression with $N$, $n_\text{median}$, $n_\min$, $n_\max$,
     $p_\text{median}$, $p_\min$, $p_\max$, $(p/n)_\text{median}$,
     $C_\text{median}$, $I_\text{median}$).
   - `Tables/table_dataset_overview_supp.tex` — the long per-dataset
     table used in the supplement (longtable form, landscape,
     handles 60+ rows without overlap).
5. `paper_aom/review/cohort_manifest.csv` — authoritative cohort
   list with the columns we need to build both tables. If a needed
   field is missing, derive it from the available CSVs in
   `bench/scenarios/runs/paper_aom_aompls_seeds012/` and
   `bench/scenarios/runs/paper_aom_aompls_da_seeds012/` (each row
   has `n_samples`, `n_features` after the data are loaded; some
   meta CSVs exist under `bench/_data/`).

## What to do — four blocks

### Block A — Datasets presentation (main + supplement)

Add a new subsection `\subsection{Datasets}` to the main manuscript
under the existing `\section{Datasets and protocol}`. Model it on
the tabpfn_paper subsection 4.1, but **adapted to our AOM cohort and
to the chemometrics framing** (no "foundation model" rhetoric).
Target ~3-4 paragraphs:

1. Why the cohort is heterogeneous (sample types, target variables,
   sample-size and dimensionality regimes). Keep it descriptive,
   not promotional.
2. Compact summary statistics, citing the new table
   `\input{tables/table_dataset_statistics.tex}` (build it from the
   cohort manifest; structure mirrors the tabpfn one — separate
   rows for regression and classification with $N$, median /
   min / max $n$, median / min / max $p$, median $p/n$, plus
   $C_\text{median}$, $I_\text{median}$ for classification).
3. Split protocol: preserved split where available, otherwise SPXY
   (or stratified SPXY for classification). Cite the same Galvão
   2005 reference our paper already has in `references.bib`.
4. One sentence on outlier handling (kept in calibration/test as
   in the source datasets).
5. Forward-reference to the supplement long table.

Add a **new diversity figure** `figures/fig_dataset_diversity.{pdf,png}`:
log-log scatter of $n_\text{samples}$ vs $n_\text{features}$ for
the 78 cohort rows, with regression and classification colour-coded
using the Okabe-Ito palette from `apply_paper_theme()`. Optional
small inset: bar chart of dataset domains (Cereal / Fruit / Leaf /
Pharma / Soil / Other, from the manifest). Generator function in
`paper_aom/review/build_paper_figures.py` reusing the v3 theme.

In the supplement, add or move the **long per-dataset table** to a
proper `longtable` (the LaTeX package is already imported in
`supplement.tex`) with `\small` text, an explicit caption mentioning
"continued on next page" handling, and `\landscape` (via `pdflscape`
— add `\usepackage{pdflscape}` if missing) if it does not fit
portrait. One row per dataset, columns: dataset name, task type,
$n$, $p$, $p/n$, response type or range, original split type,
domain. Replace the current ad-hoc table if it overlaps.

### Block B — Simple AOM baselines

The user's exact request: "Il faudrait les baselines de modèles
'simples': AOM-PLS-cv5 ou pareil pour Ridge, en plus du reste."
Translated: add the plain, no-bells-and-whistles AOM variants to
the comparison so the reader sees that even the simplest form of
the algebra wins against the grid baseline.

Variants to add:

- **PLS regression**: `AOM-compact-cv5-numpy` (the compact 9-operator
  bank with internal CV-5 selection, no ASLS branch). Already
  present in
  `bench/scenarios/runs/paper_aom_aompls_seeds012/results.csv`.
- **Ridge regression**: `AOMRidge-global-compact-none` (compact bank,
  global selector, no Blender, no Local-knn50). Already present in
  `bench/AOM_v0/Ridge/benchmark_runs/all54_headline/results.csv`
  and in `paper_aom_aomridge_seeds012/`.

Refresh the paired-stat table and the headline numbers so that each
comparison line is computed for BOTH the simple AOM baseline AND the
selected v4 "best" AOM variant. Concretely:

- `table_main_results.tex` (or its equivalent) gains two new rows:
  one for `AOM-compact-cv5` vs PLS-default and vs PLS-HPO; one for
  `AOMRidge-global-compact-none` vs Ridge-default and vs Ridge-HPO.
- `table_paired_stats.tex` likewise.
- The abstract gains one sentence: "Even the plain
  compact-bank AOM-PLS, fitted in seconds, already improves over
  default PLS on N=NN paired datasets (median RMSEP ratio X.XXX,
  WW/NN wins), and reaches parity / near-parity with the
  preprocessing-HPO baseline." (use the actual numbers — recompute
  from the refreshed CSV).
- The Results subsection 6.1 gains a paragraph or two-line table
  block on the simple baseline. Same for 6.2.

Re-run the aggregation (`paper_aom/review/aggregate_stats.py
--partial`, `selector_diagnostics.py`, `build_paper_figures.py`) so
all tables and figures embed the simple baselines.

For the **figures**:
- `fig_results.pdf` and `fig_dataset_variant_heatmap.pdf` must include
  the two new simple-baseline columns/bars.
- `fig_accuracy_time_pareto.pdf` must also plot the two simple
  baselines as separate points (use the Okabe-Ito palette family
  colours but a different marker shape so the reader sees "simple"
  vs "best").
- `fig_budget.pdf` already shows "AOM (best)"; add a second bar
  for "AOM (simple)" so the budget gap is also visible for the
  plain variant.

### Block C — Strengthen the "why" justification

The user explicitly said: "JE dois justifier que c'est plus
intéressant de faire ca que de faire de la grid avec pls ou ridge."
Translated: "I need to justify why this is more interesting than
running a preprocessing grid with PLS or Ridge."

Strengthen Section 1 (Introduction) and Section 7 (Discussion) of
the main with explicit, concrete arguments. Each argument must be
short and backed by either a number from the benchmark or a clear
algebraic / engineering reason. Suggested arguments:

1. **Compute cost** — a cartesian preprocessing grid is 600+
   combinations × candidate fits per combination × cross-validation
   folds. Cite the order-of-magnitude number from
   `table_budget.tex`.
2. **Statistical stability** — repeated re-fits on small calibration
   sets inflate variance of the selected pipeline; the AOM single
   fit selects operators by a single covariance / kernel pass
   instead of a multiplicative search loop.
3. **Auditability** — the AOM model is a single linear calibration
   object on the original wavelength axis; an external grid winner
   is a *pipeline* that can hide selection choices and is harder to
   re-deploy across instruments. (Cite the recovered-original-space
   coefficient property.)
4. **Re-deployment** — a single linear object with original-wavelength
   coefficients can be re-applied without re-running a preprocessing
   pipeline. A grid winner cannot.
5. **Even the simple AOM wins** — show that the plain compact-bank
   AOM-PLS (no ASLS, no fancy selector) already beats default
   PLS+grid on the cohort. This is the strongest argument and is
   what Block B provides numbers for.

Argument (5) must be the punchline at the end of the Introduction
and again in the Discussion summary.

### Block D — Fix supplement layout overlap

The user says supplementary tables "se chevauchent". Common causes
to fix:

- Long tables that exceed page height without `longtable` (use
  `longtable`, not `tabular` / `tabularx`).
- Tables that exceed page width without `landscape` (use
  `pdflscape` `landscape` env).
- Floats stacked at page-break boundary (insert `\FloatBarrier` from
  the `placeins` package, or `\clearpage` before the next section).
- Caption that overlaps with a figure underneath (move the
  `\caption{}` above the table, or use `\captionof{}` from
  `caption`).

Add the missing packages (`pdflscape`, `placeins`, `caption` if
needed) **only if they are required**. Do not bloat the preamble.

Check each supplement section visually after rebuild: open the
generated PDF page-by-page (you can `pdftoppm -r 100
paper_aom/supplement.pdf /tmp/supp_pg -png` and then `ls /tmp/`
to see which pages have suspicious bounding boxes; pdftotext does
not show overlaps, so you must rely on pixel inspection or on
LaTeX overfull-box warnings in the `.log` file — if the same
table triggers multiple overfull `\hbox` warnings of >20pt, treat
it as a real problem).

If a table still cannot fit in portrait, ship it in landscape via
`\begin{landscape} ... \end{landscape}`.

## Refresh + rebuild

```bash
# Refresh aggregations and figures
python paper_aom/review/aggregate_stats.py --partial
python paper_aom/review/selector_diagnostics.py \
    --aompls bench/scenarios/runs/paper_aom_aompls_seeds012/results.csv \
    --aomridge bench/AOM_v0/Ridge/benchmark_runs/paper_aom_aomridge_seeds012/results.csv \
    --out paper_aom/review/ --tables paper_aom/tables/
python paper_aom/review/build_paper_figures.py

# Rebuild PDFs
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
# v4 cleanliness preserved
grep -ciE "catboost|cnn|deep learning|gradient boosting|talanta|tbd|placeholder|pending|in progress" paper_aom/main.tex paper_aom/supplement.tex   # → 0

# v5 additions present
grep -c "AOM-compact-cv5" paper_aom/main.tex                          # ≥ 2 (Methods + Results)
grep -c "AOMRidge-global-compact-none" paper_aom/main.tex             # ≥ 2
grep -c "table_dataset_statistics" paper_aom/main.tex                 # ≥ 1
grep -c "fig_dataset_diversity" paper_aom/main.tex                    # ≥ 1
grep -c "longtable" paper_aom/supplement.tex                          # ≥ 1

# repos still announced
grep -c "gbeurier/aom" paper_aom/main.tex                             # ≥ 1
grep -c "gbeurier/pls4all" paper_aom/main.tex                         # ≥ 1
grep -c "GBeurier/nirs4all" paper_aom/main.tex                        # ≥ 1

# no broken refs
grep -c "undefined" paper_aom/main.log paper_aom/supplement.log       # 0 each

# no overlapping tables (best heuristic: overfull \hbox > 20pt in supplement.log)
awk '/Overfull \\hbox/ {gsub(/[(),pt]/,""); if ($3+0 > 20) print}' paper_aom/supplement.log | wc -l   # ≤ 3

# PDFs exist and were rebuilt
test -f paper_aom/main.pdf && test -f paper_aom/supplement.pdf
```

## v5 report

Append a `## v5 update (2026-05-17)` section to
`paper_aom/review/codex_report.md` with:
- The new dataset summary statistics and what supplementary table
  layout you chose (longtable / landscape / both).
- The two simple-baseline headline numbers (vs PLS-default,
  vs PLS-HPO, vs Ridge-default, vs Ridge-HPO).
- The list of figures regenerated and the new
  `fig_dataset_diversity` description.
- The list of supplement layout fixes (which tables were converted
  to longtable, which were rotated, which packages added).
- Confirmation that all acceptance gate commands above return the
  expected value.

## Hard constraints

- Do NOT reintroduce CatBoost / CNN / Talanta / "tbd" / "to be
  completed" / "pending" wording. v4 ledger applies.
- Do NOT add deep learning baselines.
- Do NOT modify `fig_concept.pdf` or `fig_math.pdf` (vector
  schematics, May 13).
- Do NOT add new Python dependencies.
- Do NOT commit.
- If a data field needed for the dataset table is missing, derive
  it from the workspace CSVs (load the parquet/CSV and compute
  $n$, $p$ on the fly in `build_paper_figures.py`). Do not invent
  metadata.

Report back when done.
