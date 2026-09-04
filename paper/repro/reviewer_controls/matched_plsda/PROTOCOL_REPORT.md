# Matched PLS-DA reviewer control

## Protocol

- Protocol ID: `matched-plsda-cv5-v1`.
- External train/test files are preserved exactly; labels are learned from training only.
- Both arms use fold-local class-balanced one-hot coding `1/sqrt(training-fold prior)`, covariance-SIMPLS, logistic regression (`class_weight=balanced`, `lbfgs`, `max_iter=2000`), the same stratified 5-fold partitions for each seed, and `k=1..15`.
- Identity arm searches only identity x k; AOM arm searches the nine compact strict-linear operators x the identical k-grid. Selection minimizes mean class-balanced validation log-loss. Seeds: `0,1,2`.
- CPU-only execution: 5 worker processes maximum and one BLAS/OpenMP thread per worker.

## Archived-protocol audit

Archived classification selection used holdout, not five-fold CV; n_splits=5 is metadata only for these rows. The headline contrast also changes both operator set and PLS engine. The archive has 240 rows (204 successful); successful criterion values are ['holdout'] while `n_splits` is logged as [5.0].

## Matched result

On the exact 13-task intersection used by the archived headline contrast (9 source families), median AOM-minus-identity balanced accuracy is 0.000000 (task bootstrap 95% CI -0.006759 to 0.006481); wins/ties/losses = 5/2/6; two-sided Wilcoxon p = 0.764648. Median balanced accuracy is 0.610354 for identity and 0.624589 for AOM. Median log-loss is 1.126429 and 1.141498, respectively.

Source-family sensitivity on that intersection: median delta 0.000000, wins/ties/losses 3/2/4, one-sided sign p = 0.773438 over 9 families. Including the now-resolvable `Species_56_Bagnall` task gives N=14, median delta 0.000000, wins/ties/losses 5/3/6, and two-sided Wilcoxon p=0.764648.

## Run exclusions

9 task-seed jobs failed. These are recorded in `run_failures.csv`; the observed blockers are non-finite spectra in `Group9_1856` and both FUSARIUM classification tasks.

## InOut_1264 audit

The files contain 884 train + 379 test = 1263 rows (one fewer than the dataset name). Train has 0 exact duplicate excess; test has 40 excess rows in 32 duplicate groups (largest group 3); 0 duplicate groups have conflicting labels. Exact train/test spectral overlap is 0. No `M*.csv` group metadata is present and the cohort split type is `unspecified`, so specimen/group leakage cannot be assessed. Per-run metrics include a sensitivity that collapses exact test-spectrum duplicates.

## Outputs and environment

- `matched_results.csv`: raw method x task x seed results and hashes.
- `per_seed_paired_results.csv`, `per_task_results.csv`: paired results.
- `paired_summary.csv/json`, `source_family_results.csv`: task and family summaries, including the exact archived-headline intersection.
- `archived_protocol_counts.csv/json`: holdout-vs-CV audit.
- `inout_duplicate_group_audit.json`: duplicate/provenance audit.
- Python 3.11.15, NumPy 2.1.3, SciPy 1.17.1, scikit-learn 1.7.2, pandas 3.0.3.
