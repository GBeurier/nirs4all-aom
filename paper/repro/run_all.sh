#!/usr/bin/env bash
# Reproduce the AOM / Talanta 2026 aggregation tables from the on-disk result CSVs.
# Each script reproduces a known value from paper/review/final_stats.md as a sanity
# check, then writes a LaTeX table fragment to the manuscript tables/ directory.
# NO model fitting — pure aggregation over committed benchmark CSVs.
#
# Override the interpreter with PYTHON=... (needs pandas + numpy + scipy):
#   PYTHON=/path/to/python ./run_all.sh
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3}"

"$PYTHON" check_artifacts.py

for s in \
  absolute_fom.py \
  classification_calibration.py \
  source_family_sensitivity.py \
  hpo_recipe_frequency.py \
  transfer_latency.py \
  hpo_union_coverage.py \
  seed_stability.py ; do
  echo "=== $s ==="
  "$PYTHON" "$s"
done
echo "All aggregation tables regenerated."
