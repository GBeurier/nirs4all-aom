# Codex v4 — Full paper rewrite, focused AOM narrative

Working directory: `/home/delete/nirs4all/nirs4all`. You have full
write authority on `paper_aom/`. Do not commit.

This is a deep rewrite, not a patch. The current `paper_aom/main.tex`
and `paper_aom/supplement.tex` were written iteratively and have
accumulated too many threads (FastAOM exploration, CatBoost/CNN
baselines, multiple AOM variants in main, journal-style framing).
The user wants a focused, scientific, simple paper.

## The user's brief — verbatim

> Le discours: cribler les preprocessings pour ridge et pls ca marche
> mais c'est lent. On peut simplifier pour les pp linéaires et faire
> one shot. Math, etudes, simu, comparaisons résults et temps. C'est
> tout. PAs de cnn, pas de catboost, rien d'autre. Et le tout avec
> toutes les données lancées pour AOM. ET on garde d'aom que le
> meilleur, le reste passe en supplémentary material. Des belles
> figs, des manips, des maths, de la science utile. Et on link
> nirs4all c'et tout et on annonce le repo bientot dispo. gbeurier/aom
> avec le code de manip et la lib multilangage (pls4all - /home/delete/nirs4all/pls4all).
> Discours cadré et simple.

Translated: the story is "preprocessing screening for ridge/PLS works
but is slow; for linear preprocessings we can simplify it to a single
fit. Math, experiments, simulations, results and time comparisons.
That's all. No CNN, no CatBoost, nothing else. Use every AOM data run
we have. Keep only the **best** AOM variant in main; everything else
goes to supplementary. Beautiful figures, experiments, math, useful
science. Link `nirs4all` only and announce the upcoming
`github.com/gbeurier/aom` repo with the experiment code, plus the
multilanguage `pls4all` library (local source at
`/home/delete/nirs4all/pls4all`). Framed and simple discourse."

## Hard rules

1. **Strip CatBoost and CNN entirely** from main, supplement, every
   table, every figure, every bib entry, every figure-generation
   script, every helper script that owns figures. This includes:
   - `paper_aom/tables/table_budget.tex` (lines 7-8 contain
     `CatBoost` and `CNN-1D`).
   - `paper_aom/review/build_paper_figures.py` line 1277 contains
     `labels = ["PLS-HPO", "Ridge-HPO", "CNN-1D", "CatBoost", ...]`.
   - any `\cite{}` to a CNN or CatBoost paper in `main.tex` /
     `supplement.tex` (drop the cite and the surrounding sentence;
     do not leave dangling citations or orphan claims).
   - any narrative sentence comparing AOM to "CNN/CatBoost
     baselines" — rewrite it to compare only against PLS-HPO and
     Ridge-HPO.
2. **No deep learning, no gradient boosting, no transformer**
   anywhere in the paper. The only comparators are:
   - PLS with default settings (`PLS-default-cv5`),
   - PLS with full cartesian preprocessing HPO (`PLS-TabPFN-HPO`),
   - Ridge with default settings (`Ridge-default-cv5`),
   - Ridge with full cartesian preprocessing HPO
     (`Ridge-TabPFN-HPO`).
3. **Keep ONLY the best AOM variant in the main manuscript.** Best
   is determined per task (regression / classification / Ridge) by
   the win-rate × median-ratio over the largest paired denominator.
   Use `paper_aom/review/final_stats.md`, `v3_stats.md` and the
   FastAOM summary CSVs to verify. As of v3:
   - Regression: `ASLS-AOM-compact-cv5` (vs PLS-default 0.962, 37/53;
     vs PLS-HPO 0.987, 16/31).
   - Ridge: `AOMRidge-Blender-headline-spxy3` (vs Ridge-default
     0.913, 44/52; vs Ridge-HPO 0.956, 27/34).
   - Classification: `AOM-PLS-DA-global-simpls-covariance` (Δ=+0.159,
     12/13 wins, $p_{\text{Holm}}=0.007$).
   You may pick a different best variant if the refreshed data
   supports it; document your choice.

   **All other AOM variants** — `AOM-default-nipals-adjoint`,
   `AOM-compact-cv5` (when ASLS variant beats it), every FastAOM
   variant (single-chain, hard-chain, soft-chain, sparse-MKR
   compact/supervised, etc.), every POP variant — move to the
   supplement as exploration.
4. **Cohesive narrative.** Five beats only:
   1. preprocessing screening for linear models works but is slow,
   2. for strict-linear operators we can fold the choice inside the
      calibration via covariance identities and operator-induced
      kernels,
   3. math derivations,
   4. simulations + benchmark on the full cohort,
   5. accuracy comparable to full HPO, fit time orders of magnitude
      smaller.
   Do not introduce extra threads. Drop "paradigm change" framing if
   it is filler; lead with the engineering story.
5. **Use every AOM data row available.** The workspaces are:
   - `bench/scenarios/runs/paper_aom_aompls_seeds012/results.csv`
   - `bench/AOM_v0/Ridge/benchmark_runs/all54_headline/results.csv`
   - `bench/AOM_v0/Ridge/benchmark_runs/paper_aom_aomridge_seeds012/results.csv`
   - `bench/scenarios/runs/paper_aom_fastaom_full60_seed0/`
     (use ONLY for the supplement exploration of alternative AOM
     forms; do not promote FastAOM to main unless one of its
     variants beats the v3 best on the same denominator)
   - `bench/scenarios/runs/paper_aom_aompls_da_seeds012/results.csv`
     and `bench/AOM_v0/Ridge/benchmark_runs/paper_aom_aomridge_cls_seeds012/results.csv`
   - `bench/scenarios/runs/paper_aom_linear_hpo_full_cartesian_pls-tabpfn-hpo-25trials_seed{0,1,2}/results.csv`
   - `bench/scenarios/runs/paper_aom_linear_hpo_full_cartesian_ridge-tabpfn-hpo-60trials_seed{0,1,2}/results.csv`
   - `bench/scenarios/runs/paper_aom_linear_hpo_full_cartesian_default_cv5_all/results.csv`
6. **Repository links** — keep only `https://github.com/GBeurier/nirs4all`
   (and the docs URL `https://nirs4all.readthedocs.io`). Announce the
   two upcoming companion repos exactly once, in the Data and Code
   Availability section near the end:
   - `https://github.com/gbeurier/aom` — the experiment code for
     this paper, to be released upon publication.
   - `https://github.com/gbeurier/pls4all` — a portable PLS / NIRS
     engine with stable C ABI and first-class bindings for Python,
     R, MATLAB, JavaScript/WebAssembly and Android (read
     `/home/delete/nirs4all/pls4all/README.md` for the one-line
     positioning; do not embed roadmap details).
   Drop the existing `nirs4all-webapp` link unless it adds direct
   value to the paper (it does not — strip it).
7. **Beautiful figures + cohesive style.** The v3 unified theme is
   live in `paper_aom/review/build_paper_figures.py` via
   `apply_paper_theme()` (Latin Modern, Okabe-Ito palette). Keep
   that theme. Regenerate every matplotlib figure with current
   data. Do not touch `fig_concept.pdf` or `fig_math.pdf` (vector
   schematics, May 13 mtime).
8. **No CatBoost / CNN ANYWHERE in figures**. Specifically, rewrite
   `fig_budget` so it shows only PLS-default, PLS-HPO, Ridge-default,
   Ridge-HPO, and the chosen best AOM variant. Same for any other
   figure that currently includes deep-learning baselines.
9. **No section titled "Open items" or "Remaining experiments"**;
   the paper is presented as finished.
10. **No "Talanta" framing, no "for journal X submission" wording**.
    The paper is a complete manuscript draft; nothing more.
11. **Rebuild both PDFs at the end.** Two pdflatex passes for each.
    Run `bibtex` after the first pass for each. Confirm both files
    were produced and that no fatal LaTeX errors remain.

## What the main manuscript looks like after the rewrite

Target ~12-15 pages. Sections in order:

1. Abstract — five-beat story above, with three concrete headline
   numbers from the refreshed data (median RMSEP ratio + N + win
   count for regression vs PLS-HPO; same for Ridge; one fit-time
   number showing the order-of-magnitude gap).
2. Introduction — the problem (cost of linear-PP screening) framed
   in 4-6 paragraphs. No "paradigm shift" rhetoric; keep it tight.
3. Linear-operator scope — what "strict linear preprocessing" means;
   what falls inside (smoothing, derivative, detrend, finite-diff)
   and what falls outside (SNV, MSC, ASLS, EMSC — these are kept as
   fold-local branches, not absorbed into the AOM algebra).
4. Methods
   - 4.1 Covariance identity that makes AOM-PLS one-shot.
   - 4.2 AOM-PLS: NIPALS-adjoint and SIMPLS-covariance solvers,
     original-space coefficient recovery, compact operator bank
     justification (cite the operator-frequency CSV briefly).
   - 4.3 AOM-Ridge: operator-induced kernel, GCV / Blender / Local
     selectors — but in main keep only the variant chosen as best.
5. Simulation / Cohort and protocol — refresh from
   `paper_aom/review/cohort_manifest.csv` (paired
   denominators, dataset count, multi-seed protocol). The cohort
   manifest source-of-truth lives in `paper_aom/review/cohort_manifest.md`.
6. Results
   - 6.1 Regression: best AOM-PLS vs PLS-default and vs PLS-HPO.
     Paired median ratio, win counts, Wilcoxon-Holm $p$.
   - 6.2 Ridge regression: best AOM-Ridge vs Ridge-default and vs
     Ridge-HPO. Paired median ratio, win counts, Wilcoxon-Holm $p$.
   - 6.3 Classification: best AOM-PLS-DA vs PLS-DA. Δ-score, win
     count, $p$.
   - 6.4 Time budget: candidate fits per dataset (HPO vs AOM) and
     wall-clock fit-time distributions. Make the order-of-magnitude
     gap explicit in prose.
7. Discussion — where AOM wins (linear, fixed operators, small N),
   where it loses (sample-adaptive transforms outside its scope),
   and the explicit caveat that the cartesian-HPO baselines were
   evaluated on the subset of datasets that completed within the
   compute budget (cite the N for each comparison).
8. Reproducibility (brief) — refer to the software table and to
   the upcoming `gbeurier/aom` repo.
9. Conclusion — one short paragraph.
10. Data and code availability — `nirs4all` + the two announced
    repos (gbeurier/aom and gbeurier/pls4all).
11. References.

The current main.tex has a "Related work" section. Keep it but
trim every CatBoost / CNN / TabPFN-paper-deep-learning citation; the
only references that remain are PLS, Ridge, NIRS preprocessing
references, and any prior operator-adaptive PLS or POP-PLS work that
is genuinely cited.

## What the supplement looks like after the rewrite

Target ~25-30 pages. Sections in order:

1. Notation, linear-operator scope (math), complete derivations of
   AOM-PLS (covariance identity, original-space coefficients,
   NIPALS-adjoint, SIMPLS-covariance) and AOM-Ridge (operator-
   induced kernels, GCV, Blender, Local selectors), including the
   AOM variants that did **not** make the main text.
2. Cohort manifest (full per-dataset listing).
3. Operator bank exploration: compact-vs-default, full operator-
   frequency table, per-dataset selector heatmap.
4. Full AOM-PLS family table (every variant tested on every dataset).
5. Full AOM-Ridge family table (Blender, AutoSelect, Local-knn50,
   global-compact-none, etc.).
6. **FastAOM exploration** — math derivations + benchmark of the
   four model families (single-chain, hard-chain, soft-chain,
   sparse-MKR variants). This is "alternative AOM forms"; explicitly
   say it is exploration, not the main result.
7. POP-PLS exploration with its weaknesses on regression.
8. Per-dataset long-form RMSEP table.
9. Classification full results (every AOM-PLS-DA variant + AOM-
   Ridge-Cls variants).
10. Failure modes, seed stability.
11. Software / artifacts table (without CatBoost / CNN rows).
12. AI-assistance statement.

## Specific edits to start from

1. **Strip `CatBoost` and `CNN-1D`**:
   - In `paper_aom/tables/table_budget.tex`, delete the two
     corresponding rows. If the table is unused after that, delete
     the file and remove the `\input{}` call. If still used,
     refresh the comparator list to `PLS-default`, `PLS-HPO`,
     `Ridge-default`, `Ridge-HPO`, `AOM (best)`.
   - In `paper_aom/review/build_paper_figures.py` near line 1277,
     remove `"CNN-1D"` and `"CatBoost"` from the `labels` list and
     drop their values. Same for any other figure that lists them.
   - In `paper_aom/main.tex` and `paper_aom/supplement.tex`, find
     every sentence mentioning CNN or CatBoost (string search
     `"CNN"`, `"catboost"`, `"CatBoost"`, `"deep learning"`,
     `"gradient boosting"`) and rewrite to remove them. If a
     `\cite{}` was attached, drop it from `references.bib` too
     IFF it is not used anywhere else.
2. **Refresh the aggregator** so it ingests every available AOM
   workspace and emits the paired statistics tables the main text
   cites. Run:
   ```bash
   python paper_aom/review/aggregate_stats.py --partial
   python paper_aom/review/selector_diagnostics.py \
       --aompls bench/scenarios/runs/paper_aom_aompls_seeds012/results.csv \
       --aomridge bench/AOM_v0/Ridge/benchmark_runs/paper_aom_aomridge_seeds012/results.csv \
       --out paper_aom/review/ --tables paper_aom/tables/
   python paper_aom/review/build_paper_figures.py
   ```
   Cross-check the refreshed `paper_aom/review/final_stats.md`
   against the v3 numbers. If a number moves materially (>0.5pp on
   a ratio or >2 on a win count), use the refreshed value.
3. **Determine "best AOM variant" per task** before writing the
   abstract. Use the largest paired denominator first; in case of a
   tie, use the higher win rate; in case of a further tie, use the
   lower median ratio. Document your final choice in
   `paper_aom/review/codex_report.md` (a new `## v4 update` section).
4. **Rewrite abstract, introduction, methods, results, discussion**
   per the structure above.
5. **Rewrite the Data and Code Availability section** with the
   three repos exactly (the existing `nirs4all` link + the two
   announced repos). Drop the `nirs4all-webapp` URL.
6. **Update bibliography** — drop any deep-learning / gradient-
   boosting citation that no longer has a textual reference. Run
   `grep -nE "cite{.+}" main.tex supplement.tex` and confirm every
   key still resolves.
7. **Regenerate every matplotlib figure** with the refreshed data
   and the v3 unified theme (`apply_paper_theme()`). Keep the
   Okabe-Ito palette; FastAOM keeps its "reddish purple" only in
   the supplement.
8. **Verify `\ref{sec:datasets}` resolves** (the label was added
   inline; do not break it).
9. **Two pdflatex passes for main and supplement**, with `bibtex`
   in between as needed. Confirm both PDFs were produced.
10. **Final acceptance checks**:
    ```bash
    grep -iE "catboost|cnn-?1?d|talanta|tbd|to be completed|placeholder|pending|in progress" paper_aom/main.tex paper_aom/supplement.tex
    grep -nE "cite\{[^}]+\}" paper_aom/main.tex paper_aom/supplement.tex | awk -F'cite{' '{print $2}' | tr ',' '\n' | tr -d '} ' | sort -u
    ```
    Both must look clean (the first empty; the second showing only
    real bibtex keys that resolve in `references.bib`).
11. **Append a `## v4 update (2026-05-17)` section** to
    `paper_aom/review/codex_report.md` listing every file touched,
    the chosen best-AOM variant per task, the refreshed headline
    numbers, the cleanup confirmation, and any decision you had to
    make under partial data.

## Notes / pitfalls

- The previous `aggregate_stats.py` does NOT read the cartesian
  linear-HPO workspaces directly; the v3 add-on
  `build_paper_figures.py` reads them via `v3_stats.md`. If you
  refactor, keep the same data flow (or simplify it). Do not break
  the figure regeneration.
- The cohort has known caveats: `Quartz_spxy70` is `missing_data`,
  two FUSARIUM rows fail estimator checks (NaN targets), and
  `LUCAS_SOC_all_26650` exceeded the cartesian-HPO compute budget
  (~24 datasets unfinished per cell on PLS, ~25 on Ridge). Report
  comparisons honestly on their completed N; never extrapolate.
- The user does not want a `Acknowledgements` boilerplate. If one
  is currently there, keep it minimal (one sentence on funding
  affiliation if applicable, otherwise drop the section).
- The user owns the writing tone — do NOT add overconfident
  marketing claims ("breakthrough", "state of the art"). Stick to
  measured, neutral chemometrics prose.
- Use the LaTeX `\citet{}` / `\citep{}` macros consistently (the
  paper uses `natbib`).
- Do NOT add new LaTeX packages. The existing preamble is
  sufficient.

## Acceptance gate

The task is done iff, after your run, the following all hold:

```bash
test -f paper_aom/main.pdf
test -f paper_aom/supplement.pdf
grep -ciE "catboost|cnn|deep learning|gradient boosting" paper_aom/main.tex paper_aom/supplement.tex       # → 0
grep -ciE "talanta" paper_aom/main.tex paper_aom/supplement.tex                                            # → 0
grep -ciE "tbd|to be completed|placeholder|pending|in progress" paper_aom/main.tex paper_aom/supplement.tex # → 0
grep -c "gbeurier/aom"   paper_aom/main.tex                                                                # ≥ 1
grep -c "gbeurier/pls4all" paper_aom/main.tex                                                              # ≥ 1
grep -c "GBeurier/nirs4all" paper_aom/main.tex                                                             # ≥ 1
```

Report back with:
- the chosen best-AOM variant per task,
- the three abstract headline numbers,
- the list of figures regenerated,
- the list of CatBoost/CNN occurrences you removed and where,
- final PDF sizes and page counts.
