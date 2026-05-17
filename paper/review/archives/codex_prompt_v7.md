# Codex v7 — Prediction-quality figures + strict intersection (no dev-incident wording)

Working directory: `/home/delete/nirs4all/nirs4all`. Full write
authority on `paper_aom/`. Do not commit.

Tight revision pass on the v6 draft. Three blocks to do, plus a
short self-review. Preserve everything else (v4 cleanliness, v5
Datasets subsection + simple AOM baselines + supplement layout,
v6 figure variant coverage + Reproducibility cleanup).

## User's brief — verbatim (combined from two messages)

> je trouve dommage qu'on ait aucune figure avec les performances en
> terme de prédictions. Toutes les figures sont orientées temps,
> mais aucune ne montre que AOM ca marche bien (et focus sur la
> qualité ed prédiction). [...] fais les 3 mais ne les intgre pas
> tous.
>
> Autre problème, le nombre de datasets varie selon les modèles.
> Il me semblait que HPO c'était fait entièrement (57 datasets).
> [...] ne conserve que les datasets intersection entre le modèles
> [...]. Et donc update le papier en fonction.
>
> pas de note dans les supplément sur le crash. Tu fais
> l'intersection et je rajouerai les manquants plus tard quand
> j'aurais tous les scores. Mais tu me fais un doc avec les
> manquants par modèles.
>
> mais stop parler des aleas dev dans le papiers!

Translation: (1) Add prediction-quality figures — build three,
integrate two in main, one in supplement. (2) Dataset counts
differ across variants; keep only the strict intersection of
successful runs across all paper variants and update the paper
accordingly. (3) **DO NOT mention crashes, partial cohorts, or
any development incidents in the paper.** Strip every existing
sentence that does. (4) The user will rerun the missing datasets
later. Produce a **separate** markdown document for the user
listing the missing datasets per model — this doc is NOT cited
from the paper; it is purely a working artifact.

## Hard rule on tone

**Nothing in `paper_aom/main.tex` or `paper_aom/supplement.tex`
may mention any development incident.** Forbidden wording:

- "LUCAS_SOC" or any sentence stating that a specific dataset
  failed to complete
- "compute budget" / "within the compute budget" / "compute-budget"
- "did not complete" / "completed subset" / "completed runs"
- "partial cohort" / "partial coverage" / "partial completion"
- "attempted but unsuccessful" / "stalled" / "OOM"
- "FUSARIUM rows failed estimator checks"
- "crash" / "queue" / "blocker"
- "in this workspace" / "the workspaces that completed"

The current paper still has at least these sentences to remove or
rewrite neutrally:

- `main.tex:88` — "exhaustive preprocessing screening on the
  completed subset" → drop the "on the completed subset" qualifier.
- `main.tex:409-410` — the whole "...evaluated on the subset of
  datasets that completed within the compute budget; the
  LUCAS_SOC rows did not complete, and two FUSARIUM rows failed
  estimator checks..." paragraph must be deleted. Replace with at
  most one neutral sentence such as "All paired comparisons are
  computed on the strict intersection $N_{\cap}$ of cohort rows
  available for every paper variant." (no further detail, no
  dataset names, no failure language).
- `supplement.tex:200` — "...compute budget or failed estimator
  checks..." must be removed similarly.

Run `grep -niE "lucas|compute.budget|completed.subset|did not complete|partial.cohort|stall|crash|oom|fusarium.*fail|attempt"` on the
final `main.tex` and `supplement.tex` and ensure it returns nothing
matching dev-incident language. If "attempt" appears in a non-
incident context (e.g. "we attempt to characterize") that is fine.

## Block A — Strict-intersection denominator

The user wants a single `N` per comparison so that every figure /
table / paired stat is on the same denominator.

Define the canonical intersection set:

```
DATASETS_KEEP = (
    OK_datasets(pls-default-cv5)         ∩
    OK_datasets(ridge-default-cv5)       ∩
    OK_datasets(pls-tabpfn-hpo-25trials) ∩  # all 3 seeds present
    OK_datasets(ridge-tabpfn-hpo-60trials) ∩  # all 3 seeds present
    OK_datasets(ASLS-AOM-compact-cv5-numpy) ∩
    OK_datasets(AOM-compact-cv5-numpy)      ∩
    OK_datasets(AOMRidge-global-compact-none)   ∩  # from all54_headline
    OK_datasets(AOMRidge-Blender-headline-spxy3)   # from all54_headline
)
```

Compute this set in `paper_aom/review/build_paper_figures.py`
(extend an existing helper or add one). For HPO variants, require
`status=='ok'` AND the dataset appears in all three seed CSVs
(seed0/seed1/seed2). For AOM seeds012 variants, likewise require
the dataset to be present in all three seeds. For single-seed
AOM-Ridge headline, require `status=='ok'` only.

Apply this intersection to every paired statistic, every figure,
every table that compares variants:

- `aggregate_stats.py --partial` and `build_paper_figures.py` load
  each variant then inner-join on the intersection before
  computing medians, win counts, p-values, ratios.
- The paired regression summary table (Table 4 in v5) and the
  classification table recompute on the strict intersection.
- The Pareto, runtime distribution, results overview, dataset-
  variant heatmap, and supplement long-form table all use the
  same row set.
- Headline numbers in the abstract are recomputed on the strict
  intersection. The abstract sentence should now read with a
  single `N=NN` value across the regression and Ridge comparisons.

Add a one-sentence neutral mention in the Datasets and protocol
section of the main:

> All paired comparisons reported below are computed on the
> strict intersection $N_{\cap}$ of cohort rows available for
> every paper variant, so that ratios and win counts are
> directly comparable across variant pairs.

That is the **only** main-text reference to the intersection
mechanic. No discussion of why or which datasets fall out. The
intersection size $N_{\cap}=NN$ is the number cited in tables and
captions.

In the supplement, the existing "Per-dataset" section may state
the intersection size $N_{\cap}$ and a neutral note that the
per-dataset long table only includes rows in the intersection.
**Do not include a per-variant coverage matrix in the supplement.
Do not include any dataset-name list of missing rows. Do not
include any cause-of-missing prose.** The supplement is silent on
provenance gaps.

## Block B — Separate doc for the user (NOT in paper)

Create `paper_aom/review/missing_datasets_per_variant.md` with the
information that used to be the supplement coverage section but
now lives **outside** the paper. This file is the user's working
artifact for filling the gaps later.

Structure:

```markdown
# Missing datasets per paper variant

Generated by Codex v7 on 2026-05-17 from the current workspace
CSVs.  This file is a working artifact for filling the gaps; it
is not referenced from the paper.

## Reference cohort

Source: `paper_aom/review/cohort_manifest.csv` — N attempted = NN.

## Strict intersection used in the paper

N_∩ = NN datasets.  Full list:

- DATASET_1
- DATASET_2
- ...

## Per-variant status

| Variant key | Workspace path | OK seeds=3 | OK seeds<3 | error | not attempted |
| --- | --- | ---: | ---: | ---: | ---: |
| pls-default-cv5 | ... | NN | -- | NN | NN |
| ridge-default-cv5 | ... | NN | -- | NN | NN |
| pls-tabpfn-hpo-25trials | ... | NN | NN | NN | NN |
| ridge-tabpfn-hpo-60trials | ... | NN | NN | NN | NN |
| AOM-compact-cv5-numpy | ... | NN | NN | NN | NN |
| ASLS-AOM-compact-cv5-numpy | ... | NN | NN | NN | NN |
| AOMRidge-global-compact-none | ... | NN | -- | NN | NN |
| AOMRidge-Blender-headline-spxy3 | ... | NN | -- | NN | NN |

## Missing rows per variant (vs reference cohort)

### pls-default-cv5 — missing NN

| Dataset | status | error message (truncated to 120 chars) |
| --- | --- | --- |
| ... | ... | ... |

(repeat for each of the 8 variants)
```

Populate every cell from the actual CSVs. For HPO variants the
"not attempted" column should list datasets that are absent from
the results.csv entirely (the runner never reached them).

## Block C — Three prediction-quality figures

Build all three. Then integrate the two strongest into the main
and the third into the supplement.

### C.1 fig_paired_rmsep_scatter (recommended for main)

Four sub-panels in a single figure (2×2):

1. AOM-PLS (best) RMSEP vs PLS-default RMSEP — each point is a
   dataset from $N_{\cap}$, x=PLS-default RMSEP, y=AOM RMSEP,
   diagonal = parity, points below = AOM wins. Colour-code points
   by dataset domain if the manifest has a domain column;
   otherwise use a single family colour.
2. AOM-PLS (best) RMSEP vs PLS-HPO RMSEP — same.
3. AOM-Ridge (best) RMSEP vs Ridge-default RMSEP — same.
4. AOM-Ridge (best) RMSEP vs Ridge-HPO RMSEP — same.

Each panel reports in its title or annotation:
- $N$ datasets (= $N_{\cap}$),
- $W/N$ wins for AOM,
- median RMSEP ratio,
- Wilcoxon-Holm $p$.

Use log-log axes (RMSEP ranges span 3-4 decades across the
cohort) and the v6 Okabe-Ito palette.

Save to `paper_aom/figures/fig_paired_rmsep_scatter.{pdf,png}`.
Place in the **Results** section of main, just before or after the
`fig_results` overview.

### C.2 fig_r2_cdf (recommended for main)

One panel: cumulative distribution function of test R² (on
$N_{\cap}$ datasets) for each of the 8 paper variants. X-axis =
R² threshold, Y-axis = fraction of datasets with R² ≥ threshold.

Use the family colour scheme with solid vs dashed lines for
simple vs best within each family:
- PLS-default: solid blue
- PLS-HPO: dashed blue
- AOM-PLS (simple): solid vermillion
- AOM-PLS (best): dashed vermillion
- Ridge-default: solid bluish_green
- Ridge-HPO: dashed bluish_green
- AOM-Ridge (simple): solid yellow
- AOM-Ridge (best): dashed yellow

Title: `R² coverage curve (N=NN datasets)`.

Save to `paper_aom/figures/fig_r2_cdf.{pdf,png}`.

### C.3 fig_gain_per_dataset (recommended for supplement)

Horizontal bar chart, one row per dataset (sorted by AOM-PLS-best
gain descending), bars showing `(RMSEP_baseline - RMSEP_AOM_best)
/ RMSEP_baseline * 100` (= % RMSEP reduction). Two columns of
bars per dataset: gain vs PLS-default and gain vs PLS-HPO. Same
construction for AOM-Ridge in a separate sub-panel.

Colour bars by sign: positive (AOM gain) in the AOM-PLS / AOM-
Ridge family colour, negative (AOM loss) in the COLOR_REFERENCE
grey.

Save to `paper_aom/figures/fig_gain_per_dataset.{pdf,png}` (one
file with two side-by-side sub-panels — PLS family and Ridge
family).

### Placement

- Main Results section gets: `fig_paired_rmsep_scatter` (after
  the existing fig_results) and `fig_r2_cdf`.
- Supplement gets `fig_gain_per_dataset` under a section
  `\section{Per-dataset prediction quality}`.

## Block D — Strip dev-incident wording

Run this final sweep:

```bash
grep -niE "lucas|compute.budget|completed subset|did not complete|partial cohort|stall|crash|oom|fusarium.*fail|workspace.*completed|workspaces that completed|attempted but unsuccessful" paper_aom/main.tex paper_aom/supplement.tex
```

Every match must be removed or rewritten with neutral language.
The acceptance gate below repeats this check.

Specifically delete/rewrite:

- `main.tex:88` — "...exhaustive preprocessing screening on the
  completed subset, with..." → "...exhaustive preprocessing
  screening, with..." (drop the qualifier).
- `main.tex:409-410` — the entire LUCAS/FUSARIUM disclosure
  paragraph → replace with a single neutral sentence about the
  intersection denominator (as quoted in Block A).
- `supplement.tex:200` — drop the "compute budget or failed
  estimator checks" clause.

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

# Cleanliness preserved
grep -ciE "catboost|cnn|deep learning|gradient boosting|talanta|tbd|placeholder|pending|in progress" paper_aom/main.tex paper_aom/supplement.tex   # → 0
grep -nE "paper_aom/review|paper_aom/scripts|aggregate_stats|selector_diagnostics|build_paper_figures" paper_aom/main.tex paper_aom/supplement.tex   # → empty

# NO DEV-INCIDENT WORDING anywhere in paper
grep -ciE "lucas|compute.budget|completed.subset|did not complete|partial cohort|stall|crash|oom|fusarium.*fail|workspace.*completed|workspaces that completed|attempted but unsuccessful" paper_aom/main.tex paper_aom/supplement.tex   # → 0

# v7 new figures
test -f paper_aom/figures/fig_paired_rmsep_scatter.pdf
test -f paper_aom/figures/fig_r2_cdf.pdf
test -f paper_aom/figures/fig_gain_per_dataset.pdf

# 2 new figs present in main
grep -c "fig_paired_rmsep_scatter" paper_aom/main.tex   # ≥ 1
grep -c "fig_r2_cdf"               paper_aom/main.tex   # ≥ 1
# 1 new fig in supplement
grep -c "fig_gain_per_dataset"     paper_aom/supplement.tex   # ≥ 1

# intersection language present (one neutral sentence)
grep -c "intersection" paper_aom/main.tex   # ≥ 1

# 8 runner keys still present
for v in pls-default-cv5 pls-tabpfn-hpo AOM-compact-cv5 ASLS-AOM-compact-cv5 ridge-default-cv5 ridge-tabpfn-hpo AOMRidge-global-compact-none AOMRidge-Blender; do
  n=$(grep -c "$v" paper_aom/main.tex)
  echo "$v : $n"   # each ≥ 1
done

# repos still announced
grep -c "gbeurier/aom"      paper_aom/main.tex   # ≥ 1
grep -c "gbeurier/pls4all"  paper_aom/main.tex   # ≥ 1
grep -c "GBeurier/nirs4all" paper_aom/main.tex   # ≥ 1

# no broken refs
grep -c "undefined" paper_aom/main.log paper_aom/supplement.log   # 0 each

# the separate working-artifact doc exists and lists at least 8 variants
test -f paper_aom/review/missing_datasets_per_variant.md
grep -ciE "pls-default-cv5|ridge-default-cv5|pls-tabpfn-hpo|ridge-tabpfn-hpo|AOM-compact-cv5|ASLS-AOM|AOMRidge-global|AOMRidge-Blender" paper_aom/review/missing_datasets_per_variant.md   # ≥ 8
```

## v7 report

Append a `## v7 update (2026-05-17)` section to
`paper_aom/review/codex_report.md` with:
- The intersection size $N_{\cap}$ and how it was computed
  (CSV joins).
- The refreshed headline numbers on the strict intersection
  (vs PLS-default, vs PLS-HPO, vs Ridge-default, vs Ridge-HPO;
  one number per simple-AOM and one per best-AOM).
- The three new figures' descriptions and their placement.
- Confirmation that every dev-incident sentence was removed (paste
  the result of the `grep -ciE "lucas|compute.budget..."` command
  showing zero hits).
- The path to `missing_datasets_per_variant.md` and its size.
- Confirmation that all acceptance gates pass.
- A short self-review note: anything you noticed but did not fix.

## Hard constraints

- No new LaTeX packages. No new Python deps.
- Do not commit.
- The simple AOM baselines (v5), the Datasets subsection (v5),
  the Reproducibility/Data-Code merger (v6), and the 8-bar
  fig_budget (v6) must all remain.
- Vector schematics `fig_concept.pdf` and `fig_math.pdf` are
  preserved.
- Use `apply_paper_theme()` and `FAMILY_COLORS` for any new figure.
- `missing_datasets_per_variant.md` lives under `paper_aom/review/`
  and is NEVER referenced from `main.tex` or `supplement.tex`.

Report back when done.
