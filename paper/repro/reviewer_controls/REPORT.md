# Reviewer controls: AOM Talanta targeted revision

Sections 1--4 aggregate frozen outputs and do not fit models. Separate matched-fitting controls are documented in `matched_plsda/PROTOCOL_REPORT.md`, `full_matched_hpo/REPORT.md` and `matched_ridge_stacking/PROTOCOL_REPORT.md`.
The full matched HPO control covers the strict 32-task panel, three seeds and both five- and three-fold compact-bank searches; it found complete folded/materialized selection and prediction parity in all 384 model-runs.

## 1. HPO attempted/missing rule

- PLS: runner universe=60; attempted=38 tasks x 3 seeds; success=36; errors=2; maximum eligible order=38; attempted set is contiguous prefix=True.
- Ridge: runner universe=60; attempted=37 tasks x 3 seeds; success=35; errors=2; maximum eligible order=37; attempted set is contiguous prefix=True.
- The source cohort has 61 rows, of which 60 have `status=ok`; Quartz is not runner-eligible. Both HPO campaigns therefore attempted a contiguous alphabetical/source-file prefix, not a prospectively sampled subset. PLS reached eligible row 38 (LUCAS SOC Cropland); Ridge stopped after row 37. The same prefix occurs for all three seeds.
- The two attempted failures in both families are `FinalScore_grp70_30_scoreQ` and `Tleaf_grp70_30` (`Input X contains NaN`). Rows after the stopping point are absent, not fit failures.

### Coverage-group characteristics

| HPO | Group | Tasks | Families | Domains | Median n_train | Median p | Median p/n_train |
|---|---|---:|---:|---:|---:|---:|---:|
| PLS | attempted | 38 | 16 | 11 | 322 | 862 | 3.410 |
| PLS | runner_eligible_not_attempted | 22 | 9 | 8 | 216 | 1020 | 4.190 |
| Ridge | attempted | 37 | 15 | 10 | 319 | 700 | 3.450 |
| Ridge | runner_eligible_not_attempted | 23 | 9 | 8 | 216 | 1038 | 3.574 |

### Included-versus-excluded AOM/default sensitivity

| Comparison | Subset | N | Median ratio | Wins | Raw Wilcoxon p |
|---|---|---:|---:|---:|---:|
| AOM-PLS simple vs PLS-default | headline_strict_N32_included | 32 | 0.991 | 22/32 | 0.084 |
| AOM-PLS simple vs PLS-default | headline_excluded_but_pair_available | 20 | 1.000 | 10/20 | 0.927 |
| AOM-PLS simple vs PLS-default | method_hpo_success | 32 | 0.991 | 22/32 | 0.084 |
| AOM-PLS simple vs PLS-default | method_hpo_not_attempted | 20 | 1.000 | 10/20 | 0.927 |
| AOM-Ridge simple vs Ridge-default | headline_strict_N32_included | 32 | 0.974 | 25/32 | 3.06e-04 |
| AOM-Ridge simple vs Ridge-default | headline_excluded_but_pair_available | 20 | 0.977 | 16/20 | 0.004 |
| AOM-Ridge simple vs Ridge-default | method_hpo_success | 34 | 0.974 | 26/34 | 2.28e-04 |
| AOM-Ridge simple vs Ridge-default | method_hpo_not_attempted | 18 | 0.977 | 15/18 | 0.006 |

Interpretation: because HPO coverage is an execution-order prefix, the strict panel is protocol-consistent but not a random or prospectively balanced sample. Report the prefix/truncation explicitly and keep the included/excluded AOM-vs-default sensitivity visible; do not describe missing HPO tasks as an analytically selected cohort.

## 2. Baseline-defined task-quality sensitivity

The sensitivity filter is baseline R2 > 0, defined only from the corresponding default model and never from AOM performance. We do not infer RPD from R2: the standard analytical definition is SD(y_test)/RMSEP and is regenerated separately from the response files.

| Comparison | Scope/filter | N | Median ratio | 95% bootstrap CI | Wins | Raw Wilcoxon p |
|---|---|---:|---:|---:|---:|---:|
| AOM-PLS simple vs PLS-default | largest_pair:all | 52 | 0.996 | 0.976--1.004 | 32/52 | 0.131 |
| AOM-PLS simple vs PLS-default | largest_pair:baseline_R2_gt_0 | 40 | 0.994 | 0.974--1.004 | 25/40 | 0.216 |
| AOM-PLS simple vs PLS-default | headline_strict_N32:all | 32 | 0.991 | 0.970--1.000 | 22/32 | 0.084 |
| AOM-PLS simple vs PLS-default | headline_strict_N32:baseline_R2_gt_0 | 27 | 0.991 | 0.970--1.009 | 18/27 | 0.220 |
| AOM-Ridge simple vs Ridge-default | largest_pair:all | 52 | 0.974 | 0.951--0.991 | 41/52 | 1.04e-05 |
| AOM-Ridge simple vs Ridge-default | largest_pair:baseline_R2_gt_0 | 40 | 0.974 | 0.935--0.991 | 33/40 | 1.04e-05 |
| AOM-Ridge simple vs Ridge-default | headline_strict_N32:all | 32 | 0.974 | 0.869--0.993 | 25/32 | 3.06e-04 |
| AOM-Ridge simple vs Ridge-default | headline_strict_N32:baseline_R2_gt_0 | 28 | 0.974 | 0.799--0.992 | 23/28 | 3.81e-04 |

Minimal revision: add this as a sensitivity analysis, clearly labelled descriptive/raw-p unless incorporated into the manuscript's prespecified multiplicity family. Do not replace the full panel with an outcome-filtered panel.

## 3. `ta_groupSampleID_stratDateVar_balRows`

- PLS-HPO: mean RMSEP 17.770, range 2.239--27.289; mean total time 4496.7 s; runtime rank 5/36 (descending).
- Ridge-HPO: mean RMSEP 1.977, range 1.914--2.029; mean total time 11120.1 s; runtime rank 4/35 (descending).
- PLS-HPO is the influential anomaly: seed RMSEP values are s0=27.289 (R2=-123.270), s1=23.783 (R2=-93.386), s2=2.239 (R2=0.163). Seeds 0 and 1 select EMSC2+ASLS and fail catastrophically on the external test despite ordinary inner-search scores.

| Comparison | Sensitivity | N | Median ratio | Wins | Raw Wilcoxon p |
|---|---|---:|---:|---:|---:|
| AOM-PLS simple vs PLS-HPO | strict_N32_all | 32 | 0.990 | 19/32 | 0.875 |
| AOM-PLS simple vs PLS-HPO | strict_without_ta | 31 | 0.992 | 18/31 | 0.900 |
| AOM-Ridge simple vs Ridge-HPO | strict_N32_all | 32 | 0.984 | 19/32 | 0.246 |
| AOM-Ridge simple vs Ridge-HPO | strict_without_ta | 31 | 0.980 | 19/31 | 0.217 |

Minimal revision: retain the task in the primary analysis (avoid post-hoc deletion), disclose the seed-level instability, and add the leave-one-task-out row. If the HPO branch is rerun, diagnose the EMSC2+ASLS transform rather than silently replacing the archived result.

## 4. SPORT / stacking+Ridge comparator reuse

- **SPORT**: faithful=False; reusable=no; N=0. No SPORT implementation or benchmark output exists in the audited repository.
- **Huang et al. 2024 SPRR (Ridge bases on separately preprocessed spectra + Ridge meta-model)**: faithful=False; reusable=scaffold_only_not_results; N=6. Existing StackingHybrid uses heterogeneous AOM/MoE/block-view base estimators, not one Ridge base learner per preprocessing view; full-cohort run stopped after six datasets.
- **Archived Multi-kernel Stack-5**: faithful=False; reusable=no_results_reuse; N=1. Five heterogeneous raw/multi-kernel/mixed-model learners with Ridge meta-model; only one successful archived result, so it is not SPORT or SPRR.
- **Matched compact-bank Ridge stacking (SPRR-inspired control)**: faithful=False; reusable=new_matched_control; N=32. Out-of-fold Ridge base predictions and a Ridge meta-model use the same nine operators, five folds, seeds and alpha grid as the matched AOM-Ridge control; the external test split remains untouched. This isolates a practical compact-bank ensemble but is not presented as a faithful reproduction of published SPRR or PROSAC.
- **SPRR-inspired Ridge stacking vs matched AOM-Ridge**: N=32; median ratio=0.991 (95% bootstrap CI 0.981--1.011); wins=18/32; raw two-sided Wilcoxon p=0.561.
- **SPRR-inspired Ridge stacking vs matched raw Ridge**: N=32; median ratio=0.968 (95% bootstrap CI 0.931--0.991); wins=25/32; raw two-sided Wilcoxon p=0.002.
- The new matched compact-bank control answers the practical ensemble objection on common splits. It does not reproduce the full published SPRR or PROSAC algorithms, and no numerical superiority claim over those methods is made. SPORT and a literature-faithful SPRR/PROSAC comparison remain future scope rather than a submission-critical omission.

## Files

- `hpo_task_audit.csv`: every regression task, execution order and HPO status.
- `hpo_group_characteristics.csv`: attempted/not-attempted representativity summary.
- `hpo_included_excluded_sensitivity.csv`: AOM/default sensitivity by coverage group.
- `baseline_quality_sensitivity.csv`: baseline-defined R2 control.
- `ta_groupsampleid_hpo_audit.csv` and `ta_leave_one_out_sensitivity.csv`: outlier evidence.
- `comparator_reuse_audit.csv`: code/result inventory and reuse decision.
- `matched_ridge_stacking/`: matched compact-bank Ridge stacking protocol, per-run outputs and summary.
- `rpd_quality_sensitivity/`: standard baseline-defined RPD sensitivity and task audit.
- `input_sha256.csv`: exact hashes of every primary artifact consumed by the audit.
