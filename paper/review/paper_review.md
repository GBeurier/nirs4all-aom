# Talanta-targeted review dossier for the AOM manuscript

> **Status — 2026-05-28 (revised after benchmark audit).**  This dossier was
> authored on 2026-05-17 against an earlier manuscript revision and an
> incomplete view of the available benchmark workspaces.  After auditing
> `nirs4all-aom/benchmarks/runs/` *and* `nirs4all-aom/_archive/trashed_runs/`
> plus the cross-project master CSV `nirs4all-lab/benchmark_master_results.csv`
> (35 930 rows), several "blocker" items turn out to be **data-aggregation
> issues, not missing compute**.  Updated per-item status:
>
> - §4.1 *Denominator 61→32* — **partially resolved.**  `N_{\cap}=32` is now
>   explicit in abstract, §3.2 (`main.tex:381`), and table captions.  The
>   missingness audit `missing_datasets_per_variant.md` is still internal,
>   not promoted to a supplement table with reason codes (NaN, fit error,
>   not attempted).
> - §4.2 *AOM-Ridge headline single-seed* — **DATA EXISTS, NOT YET AGGREGATED,
>   but the framing must be nuanced.**  Both `AOMRidge-Blender-headline-spxy3`
>   and `AOMRidge-AutoSelect-headline-spxy3` were run with seeds 0/1/2 on a
>   union of 26 datasets in
>   `_archive/trashed_runs/AOM_v0_legacy/Ridge/benchmark_runs/da001_audit20_seeds012/`
>   and `.../da001_partial_fast12_seeds012/`.  RMSEP is identical across
>   seeds 0/1/2 in every dataset.  **Caveat (Codex 2026-05-28):**
>   `SPXYFold` only consumes `random_state` when `pca_components` is set;
>   with SPXY3 in its current configuration the split itself is deterministic,
>   so "zero seed-variance" is mostly a *protocol determinism* result, not a
>   robustness-to-repeated-partitions result.  In addition, the union covers
>   **26 of the strict N_cap=32 datasets** — the remaining 6 still need
>   either a re-run or an explicit "multi-seed audit on N=26 subset" caption.
>   The two workspaces also overlap on some datasets; dedupe by
>   `(dataset, variant, seed)` before computing summary stats so common
>   datasets are not double-counted.
>   *Action: re-point `aggregate_stats.py` at these archived workspaces,
>   dedupe, fill the 6 missing rows or scope the claim to N=26, and add a
>   table entry phrased as "zero variance observed across seeds 0/1/2 on
>   N=26 audit subset; SPXY3 split deterministic by protocol".  Avoid the
>   stronger "headline survives seeds" wording.*
> - §4.3 *Strong conventional baseline (PLS + SNV + SG + 1st derivative,
>   tuned components)* — **LARGELY ADDRESSED, with framing caveat.**
>   `pls-tabpfn-hpo-25trials` (already in the paper) does HPO over
>   `norm ∈ {none, snv}`, `smooth ∈ {Savitzky-Golay multiple windows/orders,
>   Gaussian}`, `baseline ∈ {detrend, ASLS, none}`, `osc ∈ {osc_1, osc_3}`
>   and `n_components`, driven by 25 TabPFN-guided trials.  That covers the
>   strong-conventional space **under HPO**, not as a fixed-recipe baseline.
>   Frame it as *"strong conventional preprocessing search under HPO"* in
>   the paper (not as *"fixed SNV+SG+OSC recipe applied systematically"*).
>   The remaining edit is making the paper text explicit about what the HPO
>   search space covers (`main.tex:398-410` currently glosses over this).
>   A reviewer who insists on a fixed-recipe baseline in addition can be
>   answered by reporting the *most-frequently-selected* HPO configuration
>   across datasets as the de-facto fixed recipe.
> - §4.5 *Code availability* — **resolved.**  Repo URL at `main.tex:638`.
>   Reproducibility smoke-test still to verify by clean clone.
> - §4.6 *Auditability/redeployment claims* — unchanged.
> - §4.7 *Compact-bank derivation* — unchanged.
> - §4.8 *Classification underpowered (N=13)* — unchanged.
> - §4.9 *Failure-mode table* — **NOT resolved.**  `failure_mode_table.csv`
>   still not promoted into the supplement.
> - §4.10 *Math exposition density* — unchanged.
> - §4.11 *Figure 5 layout* — **NOT resolved.**  Layout pending.
> - §6 *Missing literature (SPORT / PORTO / PROSAC, Mishra, Engel,
>   Cawley-Talbot, Varma-Simon, Bergstra-Bengio, Roger-Mallet-Marini
>   aquaphotomics)* — **NOT resolved.**  `references.bib` still missing
>   these entries.
>
> **Revised Talanta-readiness summary.**  arXiv v2 is uploadable as-is.  For
> Talanta, all remaining work is *writing / aggregation / citations / one
> figure relayout*: no new benchmark runs are required.  Estimated total
> effort ≈ 2-3 human-days, ≈ 0 additional compute:
> (a) re-aggregate Blender/AutoSelect seeds 0/1/2 from archived workspaces;
> (b) write the empirical-determinism note in the supplement;
> (c) promote the missingness audit and the failure-mode table into the
>     supplement;
> (d) add SPORT/PORTO/PROSAC + ML-bias citations and related-work paragraphs;
> (e) relayout Figure 5;
> (f) clarify the HPO search space in main text §3.2;
> (g) verify clean-clone smoke test.
>
> The 2026-05-17 review text below remains authoritative for everything not
> flagged in this header.  The "missing experiments" list in §5 of the
> original review is **largely obsolete** — the AOM-Ridge multi-seed and
> the strong-conventional-baseline experiments already exist.

## 1. Executive summary

The manuscript claims that strict linear spectral preprocessing can be moved inside PLS and Ridge calibration, replacing much of the external preprocessing search by an operator-adaptive model that is faster, auditable, and broadly competitive on heterogeneous NIRS regression and classification datasets. The claim is scientifically plausible and, if positioned carefully, is a good fit for Talanta because it addresses a recurring analytical-chemistry workflow problem: how to select preprocessing without turning calibration into a large, unstable grid-search exercise.

The strongest evidence is the paired regression benchmark on the strict intersection of 32 datasets: AOM-Ridge Blender improves over Ridge-default with a median RMSEP ratio of 0.918 and over Ridge-HPO with 0.966, while AOM-PLS variants are close to PLS-HPO and much cheaper to run (`main.tex:416-460`, `main.tex:507-565`, `table_main_results.tex`, `table_time_budget.tex`). The time-budget story is especially compelling for AOM-PLS: 45 top-level fits and about 1-2 seconds versus 3000 fits and 710.81 seconds for PLS-HPO on the same 32-row intersection (`main.tex:511-525`).

The weakest evidence is not the mathematics; it is the validation surface. The paper repeatedly invokes a 61-row regression cohort and a 17-row classification cohort, but the central paired claims are made on `N_cap=32`, the AOM-Ridge headline is currently a single deterministic/random-state-0 run, and the classification result is only `N=13` paired datasets (`main.tex:69-80`, `main.tex:376-381`, `main.tex:489-505`, `supplement.tex:433-443`). A Talanta reviewer will likely accept a strict intersection if it is honestly framed, but they will ask whether the missing HPO rows and single-seed AOM-Ridge result bias the headline.

The single most important fix before submission is to close or neutralize the denominator problem: run the missing HPO/AOM-Ridge rows where feasible, add seeds 1 and 2 for the AOM-Ridge headline, and rewrite the results so every headline has an explicit denominator, seed policy, and missingness explanation. Without that, the paper reads as strong work that is not yet submission-stable. With it, the manuscript becomes a credible chemometrics methods paper rather than a promising internal benchmark.

## 2. Talanta fit and scope

The paper is in scope for Talanta if it is framed as analytical chemometrics for NIR calibration, not as a generic machine-learning benchmark. The current introduction mostly succeeds because it begins from NIRS calibration practice, preprocessing, fold-local operators, and multivariate calibration (`main.tex:90-132`). The danger is that the Ridge kernel derivation and variant naming can drift toward generic ML. Keep the abstract, introduction, and discussion anchored to analytical workflow: calibration, preprocessing, sample partitioning, external deployment, and reproducible spectroscopy software.

The closest published Talanta precedent already in `references.bib` is Galvao et al. 2005, "A method for calibration and validation subset partitioning", Talanta 67, 736-740, DOI 10.1016/j.talanta.2005.03.025 (`references.bib:178-186`). That precedent supports the SPXY split protocol, not the AOM-PLS/AOM-Ridge contribution. For the operator-adaptive framing, the closer literature is outside Talanta and is currently missing: SPORT, PORTO, PROSAC, and preprocessing-ensemble reviews. The paper should explicitly cite those in related work and then state how AOM differs: it uses strict linear identities to integrate operator mixtures into one PLS/Ridge calibration rather than fusing several preprocessed blocks through multiblock PLS.

Expected reviewers:

- Chemometricians will test the algebra, compare AOM to SPORT/PORTO/PROSAC, ask whether fold-local fitted preprocessors violate the "strict linear" assumption, and object if HPO comparisons are underpowered.
- NIRS practitioners will ask whether the compact 9-operator bank covers their standard recipes, especially SNV + Savitzky-Golay + first derivative, MSC/EMSC, and baseline correction. They will care about failure cases and redeployment.
- ML-oriented chemometricians will push on model-selection bias, repeated/nested validation, missing rows, code release, and whether "default-cv5" baselines are strong enough.

## 3. Strengths

- Methodological: The strict-linear-operator scope is cleanly defined and prevents leakage-prone claims around SNV, MSC, EMSC, and ASLS (`main.tex:176-210`). This boundary is essential and should be preserved.
- Methodological: The AOM-PLS covariance identity and Ridge summed-kernel derivation give the contribution a real mathematical core rather than presenting it as a wrapper around preprocessing search (`main.tex:214-256`, `main.tex:276-305`, `supplement.tex:47-189`).
- Methodological: The manuscript distinguishes simple variants from selected variants and states that selected ASLS-AOM and Blender are chosen from a larger family explored in the supplement (`main.tex:258-265`, `main.tex:299-305`).
- Empirical: The cohort is broad for a chemometrics methods paper: 61 regression manifest rows and 17 classification manifest rows spanning plant, food, soil, petroleum, pharmaceutical, and disease tasks (`main.tex:326-353`, `table_dataset_statistics.tex`, `table_dataset_overview_supp.tex`).
- Empirical: The strict paired intersection is explicitly named (`N_cap=32`) rather than hidden, and paired Wilcoxon/Holm tests are used for the main benchmark (`main.tex:376-396`, `table_main_results.tex`).
- Empirical: The AOM-Ridge Blender result is a real performance result, not only a speed result: median RMSEP ratio 0.918 versus Ridge-default and 0.966 versus Ridge-HPO on the strict intersection (`main.tex:437-446`).
- Empirical: The AOM-PLS speed result is highly legible: roughly the same RMSEP as PLS-HPO at a tiny fraction of the search budget (`main.tex:511-525`, `fig_budget.pdf`, `fig_accuracy_time_pareto.pdf`).
- Empirical: The supplement contains useful diagnostic artifacts: family tables, operator-frequency diagnostics, seed-stability diagnostics, long per-dataset results, and gain-per-dataset plots (`supplement.tex:207-247`, `supplement.tex:249-414`).
- Writing/positioning: The paper already avoids an overclaim that AOM always wins; it says the result is strongest where operators are strict and deployment simplicity matters (`main.tex:575-611`).

## 4. Weaknesses, ranked by likelihood of being cited by a Talanta reviewer

1. **Headline denominator collapses from 61 to 32**
   - The abstract advertises 61 regression rows, but all main paired regression conclusions use `N_cap=32` because the strict intersection requires all selected variants and HPO rows (`main.tex:69-76`, `main.tex:376-381`). This is defensible only if the missingness is shown to be non-cherry-picked; `missing_datasets_per_variant.md` shows many HPO gaps.
   - Place: `main.tex:69-76`, `main.tex:326-381`, `supplement.tex:193-196`, `paper_aom/review/missing_datasets_per_variant.md`.
   - Severity: **blocker**.
   - Recommended fix: Fill the missing HPO rows where feasible and add a transparent missingness table plus a sensitivity analysis on the largest complete denominator per comparison.

2. **AOM-Ridge headline is single-seed while the paper leans on multi-seed language**
   - The best Ridge result is central to the paper, but the supplement states that the AOM-Ridge headline is a deterministic/random-state-0 run, whereas AOM-PLS, PLS-default, Ridge-default, PLS-HPO, and Ridge-HPO have seeds 0/1/2 (`supplement.tex:433-443`). Reviewers will ask whether the 0.918/0.966 headline survives seeds.
   - Place: `main.tex:74-76`, `main.tex:437-446`, `supplement.tex:399-414`, `supplement.tex:433-443`.
   - Severity: **blocker**.
   - Recommended fix: Run seeds 0/1/2 for AOM-Ridge Blender and AutoSelect on the strict intersection, then report median-by-dataset ratios and seed variance.

3. **Comparator strength is still vulnerable**
   - PLS-default and Ridge-default are honest software baselines, and PLS-HPO/Ridge-HPO are useful, but a Talanta reviewer may expect a strong conventional recipe such as PLS + SNV + Savitzky-Golay smoothing + first derivative with tuned components. The current "simple baseline" argument may look too easy if the default baseline is raw-ish PLS/Ridge (`main.tex:134-139`, `main.tex:398-400`).
   - Place: `main.tex:134-139`, `main.tex:398-400`, `main.tex:416-460`, `main.tex:507-525`.
   - Severity: **major**.
   - Recommended fix: Add one strong conventional preprocessing baseline, preferably fixed before seeing results and run across the strict intersection and the largest feasible denominator.

4. **Single train/test split per dataset limits statistical power**
   - The protocol uses SPXY or stratified-SPXY train/test splits, then repeats seeds mostly around internal CV/search rather than independent external splits (`main.tex:366-396`). Reviewers may argue that dataset-level Wilcoxon tests over 32 rows do not replace repeated train/test partition uncertainty.
   - Place: `main.tex:366-396`, `supplement.tex:399-414`.
   - Severity: **major**.
   - Recommended fix: Add either repeated split sensitivity on a representative subset or a clear limitation paragraph stating that inference is across datasets, not across random train/test partitions.

5. **Code availability is promised, not available**
   - The manuscript says `gbeurier/aom` and `gbeurier/pls4all` will be released upon publication (`main.tex:630-637`). Talanta reviewers increasingly expect code and minimal data at submission, especially for a methods/software benchmark.
   - Place: `main.tex:630-645`, `table_software.tex`, `supplement.tex:416-428`.
   - Severity: **blocker** or high **major**, depending on editorial policy.
   - Recommended fix: Make both repositories live before submission, with commit hashes, archived releases, a smoke-test dataset, and one command that reproduces a small subset of the benchmark.

6. **"Auditability" and "redeployment" are claims, not demonstrations**
   - The introduction and discussion argue that AOM has auditability and redeployment advantages, but the manuscript does not quantify operator-log size, saved artifacts, latency, or performance under an external campaign/instrument transfer (`main.tex:111-115`, `main.tex:591-597`). A reviewer can accept this as motivation but not as a result.
   - Place: `main.tex:111-115`, `main.tex:591-597`, `main.tex:618-628`.
   - Severity: **major**.
   - Recommended fix: Add a small redeployment demonstration or downgrade the claim to "implementation advantage" and report concrete artifact and inference-time numbers.

7. **Compact bank derivation is too compressed in the main text**
   - The main text says the 9-operator bank came from frequency diagnostics and that the top three operators account for 54.7% of selections, but the decision rule is not fully transparent (`main.tex:267-274`). `compact_bank_justification.md` is clearer than the paper.
   - Place: `main.tex:267-274`, `supplement.tex:207-247`, `paper_aom/review/compact_bank_justification.md`.
   - Severity: **major**.
   - Recommended fix: Add a two-sentence decision rule and a compact table in the supplement showing candidate bank size, frequency cutoff, and retained operators.

8. **Classification claim is underpowered**
   - The classification result is attractive, with balanced-accuracy gain 0.159 on 12/13 datasets (`main.tex:489-505`), but `N=13` is small and not necessarily representative of the regression cohort. The full classification table also shows AOM-Ridge classification variants doing well on 14 datasets, which raises a question about why the paper promotes only AOM-PLS-DA.
   - Place: `main.tex:489-505`, `table_classification_main.tex`, `supplement.tex:382-397`.
   - Severity: **major**.
   - Recommended fix: Keep classification as secondary evidence unless more datasets/seeds are added, and explicitly state why AOM-PLS-DA is the promoted classification model.

9. **Failure modes are not given enough manuscript space**
   - The paper shows wins, CDFs, and gain plots, but does not dedicate text to where AOM loses or fails. `failure_mode_table.csv` and `table_failure_modes.tex` exist but are not included in the current paper.
   - Place: results/discussion around `main.tex:416-565` and `main.tex:567-616`; `table_failure_modes.tex` unused.
   - Severity: **major**.
   - Recommended fix: Add a short "Failure modes" paragraph and include either the failure table or a small supplement table describing losses and non-finite rows.

10. **Mathematical exposition may still be too dense for analytical chemists**
   - Sections 4-5 are mathematically correct in spirit, but an analytical chemist may need more dimensions, algorithm boxes, and a "what is fitted once versus per fold" explanation (`main.tex:212-314`, `supplement.tex:47-189`). This is especially important for the strict-linear/fold-local distinction.
   - Place: `main.tex:212-314`, `supplement.tex:47-189`.
   - Severity: **major**.
   - Recommended fix: Add one algorithm box for AOM-PLS and one dimensions table in the supplement.

11. **Figure quality has one submission-level defect**
   - `fig_paired_rmsep_scatter.png` is the best evidence figure but has visible title/x-label collisions between rows. `fig_dataset_diversity.png` has cramped/clipped inset labels, and the supplement heatmaps are dense.
   - Place: `main.tex:462-486`, `fig_paired_rmsep_scatter.png`, `fig_dataset_diversity.png`, `supplement.tex:241-247`, `supplement.tex:352-365`.
   - Severity: **major** for Figure 5, **minor** for the others.
   - Recommended fix: Re-layout Figure 5 with more vertical spacing and fix the dataset-diversity inset before submission.

12. **Variant naming and artifact naming are too implementation-colored**
   - The paper still exposes runner keys and labels such as `pls-tabpfn-hpo-25trials` to bridge internal artifacts to paper labels (`main.tex:402-410`). This is useful for reproducibility but distracts from the chemometric story.
   - Place: `main.tex:402-410`, `table_aompls_family.tex`, `table_aomridge_family.tex`.
   - Severity: **minor**.
   - Recommended fix: Move runner-key mapping entirely to a supplement reproducibility table and keep main-text labels purely paper-facing.

## 5. Missing experiments / data

- **Fill the cartesian-HPO gap.** Run missing PLS-HPO and Ridge-HPO rows listed in `missing_datasets_per_variant.md`, prioritizing datasets that are already present for AOM variants. Effort: 150-300 core-hours, potentially more for LUCAS-scale rows; 6-10 human-hours for queueing, monitoring, and reconciliation. Required for acceptance if the paper keeps the 61-row cohort as a headline. Dependencies: `missing_datasets_per_variant.md`, HPO result CSVs feeding `final_stats.md`, `v3_stats.md`, and `table_main_results.tex`.
- **Add multi-seed AOM-Ridge headline.** Run AOM-Ridge Blender and AutoSelect for seeds 1 and 2 on at least the strict `N_cap=32`, ideally all available 53 rows. Effort: 50-120 core-hours; 4-6 human-hours. Required for acceptance because the Ridge result is the strongest empirical claim. Dependencies: AOM-Ridge headline CSVs, `final_stats.md`, `table_aomridge_family.tex`, `table_seed_stability.tex`.
- **Add a strong conventional baseline.** Implement PLS + SNV + Savitzky-Golay + first derivative + tuned component count, with one pre-registered recipe or a small conventional grid. Effort: 10-30 core-hours for fixed recipe; 50-100 core-hours for a small grid; 6-12 human-hours. Required or near-required for Talanta because it answers the practitioner baseline critique. Dependencies: default linear result workspace, cohort manifest, PLS pipeline.
- **External split or transfer validation.** Use an instrument/campaign/site split where already possible, for example campaign-blocked plant traits or the existing Rd25 source-family split, to test the redeployment claim. Effort: 20-80 core-hours; 2-4 human-days to define a defensible split and write it clearly. Strengthens the paper; required only if "redeployment" remains a headline claim. Dependencies: `cohort_manifest.csv`, existing split metadata, AOM/PLS result scripts.
- **Latency and inference-time measurements.** Report fit/search time separately from final-model prediction latency and stored artifact size. Effort: under 5 core-hours; 3-5 human-hours. Strengthens the runtime argument and is cheap. Dependencies: final fitted models, timing wrappers, `table_time_budget.tex`.
- **Failure-mode analysis.** Promote `failure_mode_table.csv` into a supplement table and discuss non-finite rows, large losses, and datasets where AOM fails to beat HPO. Effort: no meaningful core-hours; 4-6 human-hours. Required for reviewer confidence. Dependencies: `failure_mode_table.csv`, `fig_gain_per_dataset.png`, long result tables.
- **Repeated split sensitivity on a subset.** Repeat train/test partitioning for a stratified subset of 8-12 datasets representing small/large n, low/high p, and several domains. Effort: 80-250 core-hours depending on HPO inclusion; 1-2 human-days. Strengthens statistical credibility but can be deferred if denominator and seed issues are fixed first. Dependencies: splitters, cohort manifest, default/HPO/AOM runners.

## 6. Missing or weak literature citations

- **Preprocessing selection and preprocessing-ensemble context.** Add Engel et al. 2013, "Breaking with trends in pre-processing?", TrAC 50, 96-106, DOI 10.1016/j.trac.2013.04.015; Mishra et al. 2020, "New data preprocessing trends based on ensemble of multiple preprocessing techniques", TrAC 132, 116045, DOI 10.1016/j.trac.2020.116045; Roger, Mallet and Marini 2022, "Preprocessing NIR Spectra for Aquaphotomics", Molecules 27, 6795, DOI 10.3390/molecules27206795. Cite in related work after `main.tex:153-161` and in the discussion of preprocessing search.
- **Direct precedents for combining multiple preprocessed blocks.** Add Roger, Biancolillo and Marini 2020, SPORT, Chemometrics and Intelligent Laboratory Systems 199, 103975, DOI 10.1016/j.chemolab.2020.103975; Mishra et al. 2021, PORTO, Chemometrics and Intelligent Laboratory Systems 212, 104190, DOI 10.1016/j.chemolab.2020.104190; Mishra et al. 2022, PROSAC, Chemometrics and Intelligent Laboratory Systems 222, 104497, DOI 10.1016/j.chemolab.2022.104497. Cite in `main.tex:171-174` and before the AOM-PLS derivation to clarify novelty.
- **Per-component/operator attempts.** The paper uses POP-PLS internally (`supplement.tex:330-348`) but `references.bib` has no POP-PLS or per-component preprocessing citation. If POP is an internal method, say so and define it as an ablation; if it is inspired by prior work, cite that work. Cite near `supplement.tex:330-348`.
- **Sample selection.** Kennard-Stone and SPXY are already present (`references.bib:168-186`), but the method text should explicitly tie SPXY to Galvao et al. 2005 and KS to Kennard and Stone 1969 (`main.tex:366-372`). No new citation is mandatory, but make the current citations visible at the split-protocol sentence.
- **Model-selection bias and compute-cost framing.** Add Cawley and Talbot 2010, JMLR 11, 2079-2107; Varma and Simon 2006, BMC Bioinformatics 7:91, DOI 10.1186/1471-2105-7-91; Bergstra and Bengio 2012, JMLR 13, 281-305; and optionally Snoek, Larochelle and Adams 2012, NeurIPS. Cite around `main.tex:107-115` and `main.tex:392-400` to support the critique of large HPO loops and model-selection variance.

## 7. Writing-level corrections

- The abstract mixes the 61/17 cohort headline with `N=32` and `N=13` paired evidence in a way that is technically honest but easy to misread (`main.tex:69-78`). Rewrite as "We assembled..." followed by "The strict paired regression benchmark contains...".
- The term "single fit" should be used carefully. AOM-PLS may avoid external operator refits, but `table_time_budget.tex` still counts 45 cells and AOM-Ridge Blender has selector/refit logic (`main.tex:507-540`). Use "single calibration object" or "no external preprocessing grid" where more accurate.
- The strict-linear paragraph should define whether fixed detrending projections are considered strict linear once fitted, because `table_operator_bank.tex` says polynomial detrending is "fitted inside calibration folds" while the text defines strict operators as fixed matrices (`main.tex:178-186`, `table_operator_bank.tex`).
- `fig_r2_cdf` uses R2 clipped at -0.5, but the body/caption should explain the clipping (`main.tex:479-486`).
- Acronyms and variant names should be made uniform: AOM-PLS simple, ASLS-AOM, AOM-Ridge global, AOM-Ridge Blender, PLS-HPO, Ridge-HPO. Avoid exposing CSV keys in the main text (`main.tex:402-410`).
- No obvious French residues were found in `main.tex` or `supplement.tex`, but internal artifacts such as `claim_ledger.md` and prompts are bilingual/stale. Do not let those phrases leak into manuscript text.
- The conclusion's "same or better" language is slightly stronger than the PLS selected result permits, since ASLS-AOM is 1.002 versus PLS-HPO on `N=32` (`main.tex:623-625`). Use "comparable to" for AOM-PLS and "better than" only where supported by paired statistics.

## 8. Figures and tables audit

- **Figure 1 concept (`fig_concept.pdf`)**: Caption and body match; good first-view contribution figure. Information density is appropriate. Suggested improvement: add a small visual cue that SNV/MSC/EMSC are outside strict-linear AOM.
- **Figure 2 math (`fig_math.pdf`)**: Caption matches the derivations. Useful for chemometricians, dense for practitioners. Suggested improvement: pair it with an algorithm box or dimensions table.
- **Figure 3 dataset diversity (`fig_dataset_diversity.png`)**: Good Talanta-facing evidence of heterogeneity. The inset labels are cramped/clipped. Suggested improvement: enlarge the inset or move domain counts to a separate supplement panel.
- **Figure 4 results (`fig_results.pdf`)**: Right story for the main results. Suggested improvement: ensure the denominator `N=32` is visible in the graphic itself, not only the caption.
- **Figure 5 paired scatter (`fig_paired_rmsep_scatter.png`)**: Excellent evidence figure but not submission-ready because row titles and x-axis labels overlap. Fix layout before submission.
- **Figure 6 R2 CDF (`fig_r2_cdf.png`)**: Good supplementary-style view in the main paper. Suggested improvement: mention clipping at -0.5 and avoid implying direct family comparability across PLS and Ridge.
- **Figure 7 budget (`fig_budget.pdf`)**: Clear count story. Suggested improvement: clarify that counts are top-level fits/cells and not identical computational units across PLS and Ridge.
- **Figure 8 Pareto (`fig_accuracy_time_pareto.png`)**: Useful visual summary. Suggested improvement: note that median ratios are within-family references.
- **Figure 9 runtime distribution (`fig_runtime_distribution.png`)**: OK as-is.
- **Supplement operator heatmap**: Useful but dense. OK as supplement; not main.
- **Supplement dataset-variant heatmap**: Useful for missingness/per-dataset behavior. Suggested improvement: add a failure/missing legend that distinguishes missing, error, and not attempted if possible.
- **Supplement gain-per-dataset figure**: Strong diagnostic. Suggested improvement: cite it from the main discussion when discussing failures.
- **Main tables 1-6**: Mostly match body claims. `table_time_budget.tex` should avoid "0.0h" formatting for tiny runtimes and clarify budget-count units.
- **Supplement family/seed tables**: Valuable but denominator shifts must be more explicit in captions. `table_aomridge_family.tex` is especially vulnerable because selected variants have 53-row single-state evidence while seeds012 rows have smaller denominators.
- **Unused tables**: `table_budget.tex`, `table_selector_diagnostics.tex`, `table_failure_modes.tex`, `table_cohort_manifest.tex`, and `table_paired_stats.tex` are not currently included. Remove stale unused tables from submission packaging or clearly mark them internal; consider including `table_failure_modes.tex`.

## 9. Repository readiness

The current "will be released upon publication" wording is risky for a computational methods paper (`main.tex:630-637`). At submission, Talanta reviewers should be able to inspect code or at minimum access an anonymized/private review link. If the repositories are not live, the availability statement should not sound as if the benchmark is already independently reproducible.

Minimum content for `gbeurier/aom` at submission: installation instructions, a pinned environment file or Dockerfile, a minimal smoke-test dataset, one script that reproduces a small AOM-PLS and AOM-Ridge run, saved expected outputs for that smoke test, the exact operator-bank definitions, and a release tag/commit hash used in the manuscript. The full 61-row benchmark can be heavier, but the smoke test must run in minutes.

Minimum content for `gbeurier/pls4all`: API documentation for PLS/Ridge components used by AOM, versioned bindings, tests, license, citation file, and a clear relationship to `nirs4all`. A quick `ls` of `/home/delete/nirs4all/pls4all` shows a substantial repository already: `README.md`, `CITATION.cff`, `LICENSE`, `CMakeLists.txt`, `CMakePresets.json`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `ARCHITECTURE.md`, `.github`, `benchmarks`, `bindings`, `cpp`, `docs`, and `parity`. That is promising, but submission readiness depends on public accessibility, build success from a clean clone, and a manuscript-linked release.

## 10. Recommended priorities for the next 1-2 weeks

1. **Must-do: Run AOM-Ridge Blender/AutoSelect seeds 1 and 2.** Impact: high. Effort: 50-120 core-hours and 4-6 human-hours. Dependencies: AOM-Ridge runner and headline CSV pipeline.
2. **Must-do: Resolve the `N_cap=32` denominator story.** Impact: high. Effort: 150-300 core-hours if filling HPO gaps; 1 human-day for missingness and sensitivity tables. Dependencies: `missing_datasets_per_variant.md`, HPO workspaces, stats scripts.
3. **Must-do: Make code repositories submission-visible.** Impact: high. Effort: 1-3 human-days, low compute. Dependencies: `gbeurier/aom`, `/home/delete/nirs4all/pls4all`, release/tag decisions.
4. **Near must-do: Add a strong conventional PLS preprocessing baseline.** Impact: high. Effort: 10-100 core-hours depending on fixed versus small-grid recipe; 1 human-day. Dependencies: PLS pipeline and cohort manifest.
5. **Must-do writing/figure pass: Fix Figure 5 and rewrite all headline denominator language.** Impact: high. Effort: 0.5-1 human-day. Dependencies: regenerated figures/tables after stats freeze.
6. **Should-do: Add failure-mode paragraph/table.** Impact: medium-high. Effort: 4-6 human-hours. Dependencies: `failure_mode_table.csv`, `fig_gain_per_dataset`.
7. **Should-do: Add SPORT/PORTO/PROSAC and model-selection-bias citations.** Impact: medium-high. Effort: 3-5 human-hours. Dependencies: `references.bib` update and related-work edit.
8. **Should-do: Add inference latency/artifact-size numbers.** Impact: medium. Effort: under 5 core-hours and 3-5 human-hours. Dependencies: final model artifacts.
9. **Nice-to-have: Add an external split/transfer demonstration.** Impact: medium-high if clean, but risky if rushed. Effort: 20-80 core-hours and 2-4 human-days. Dependencies: defensible split metadata.
10. **Nice-to-have: Repeated split sensitivity subset.** Impact: medium. Effort: 80-250 core-hours and 1-2 human-days. Dependencies: stable splitters and runner automation.

## 11. Self-review caveats

I did not re-run LaTeX, regenerate figures, or run any benchmark pipeline. The review is based on the current TeX/PDF sources, tables, figures, stats markdown/CSV artifacts, and a quick filesystem inventory of `pls4all`.

I visually checked available PNG figures and text-extracted the PDFs, but I did not inspect every PDF graphic at publisher proof resolution. Before submission, re-check all figure panels in the compiled PDF at 100-150% zoom, especially Figure 5.

The literature audit verified the key missing reference categories and several specific papers through current web searches, but the final bibliography should still be checked manually for exact author initials, accents, page/article numbers, and BibTeX formatting.

The internal artifacts contain stale histories and older denominators. I used the v7 manuscript, `final_stats.md`, `classification_stats*.md`, and current TeX files as authoritative when conflicts appeared.
