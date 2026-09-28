# AOM research benchmarks

This directory contains generic research runners for PLS, Ridge and FastAOM.
Provide explicit cohort, data and output paths. Local outputs under `runs/`
and `workspaces/` are ignored.

Publication-specific runners, frozen cohorts, outputs and editorial aggregation
scripts are maintained in the private `nirs4all-drafts/aom_talanta_26` workspace
until submission. Historical paths in generic runners refer to developer data
layouts; select the appropriate command-line options for your own inputs.

Timing comparisons must use the same resource limits and numerical environment
within each pair, measure the full search/refit/predict workflow, and record
candidate budgets, precision, memory and failures. Model-fit counts alone are
not wall-clock speedups.
