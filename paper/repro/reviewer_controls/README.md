# Reviewer controls

Corrective aggregation and matched-fitting controls prepared for the targeted
Talanta revision. They never write to the canonical manuscript. The full
folded/materialized control writes only below `full_matched_hpo/` and uses the
frozen strict 32-task intersection.

Run from any directory:

```bash
bash paper/repro/reviewer_controls/run.sh
```

The lightweight audit wrapper pins the process to logical CPUs 10--13, fixes all
common numerical-library thread pools to one thread, and hides GPUs. The fitting
controls enforce the same single-thread and no-GPU policy and allow at most five
workers. Outputs are deterministic CSV/JSON files and Markdown reports in this
directory.

Run the full matched compact-bank control and its validation with:

```bash
python paper/repro/reviewer_controls/full_matched_hpo_control.py --max-workers 5
python paper/repro/reviewer_controls/analyze_full_matched_hpo.py
```

This evaluates folded AOM and explicit-materialization HPO with the same nine
operators, folds, exhaustive component/alpha grids and selection rule. It runs
five folds as the primary protocol and three folds as a sensitivity analysis.

Run the matched ensemble and task-quality controls with:

```bash
python paper/repro/reviewer_controls/matched_ridge_stacking_control.py --max-workers 5
python paper/repro/reviewer_controls/ridge_identity_inference.py
python paper/repro/reviewer_controls/rpd_quality_sensitivity.py
```

The first command is an SPRR-inspired same-bank comparison: nine separately
fitted Ridge views are combined by a Ridge meta-model trained on out-of-fold
predictions. It is not labelled as a faithful SPRR or PROSAC reproduction. The
second command aggregates the same matched runs into task- and source-family
inference for AOM-Ridge versus identity-only Ridge; it ranks log RMSEP ratios
and treats source family as the primary unit. The third command is a pure aggregation using the standard
`SD(y_test) / RMSEP` definition and a Ridge-default-defined threshold.
