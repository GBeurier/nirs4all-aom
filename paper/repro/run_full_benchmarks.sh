#!/usr/bin/env bash
# Explicit, resumable full-cohort launcher. It never overwrites the frozen paper runs.
set -euo pipefail

if [[ "${AOM_FULL_RUN:-0}" != "1" ]]; then
  echo "Full reproduction is multi-hour. Re-run with AOM_FULL_RUN=1 and AOM_REPRO_OUTPUT=/absolute/output/path." >&2
  exit 2
fi
if [[ -z "${AOM_REPRO_OUTPUT:-}" || "${AOM_REPRO_OUTPUT}" != /* ]]; then
  echo "AOM_REPRO_OUTPUT must be an explicit absolute directory outside benchmarks/runs." >&2
  exit 2
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/../.." && pwd)"
if [[ -n "${PYTHON:-}" ]]; then
  python_bin="$PYTHON"
elif command -v python3.11 >/dev/null 2>&1; then
  python_bin="python3.11"
else
  python_bin="python3"
fi
nirs4all_dir="${NIRS4ALL_DIR:-$(cd -- "$repo_root/../nirs4all" 2>/dev/null && pwd || true)}"
lab_dir="${NIRS4ALL_LAB_DIR:-$(cd -- "$repo_root/../nirs4all-lab" 2>/dev/null && pwd || true)}"
data_dir="${NIRS4ALL_DATA_DIR:-$(cd -- "$repo_root/../nirs4all-data" 2>/dev/null && pwd || true)}"
out="$(realpath -m -- "$AOM_REPRO_OUTPUT")"

if [[ ! -d "$nirs4all_dir" ]]; then
  echo "Set NIRS4ALL_DIR to the companion nirs4all checkout." >&2
  exit 2
fi
if [[ ! -d "$lab_dir" ]]; then
  echo "Set NIRS4ALL_LAB_DIR to the companion nirs4all-lab checkout." >&2
  exit 2
fi
if [[ ! -d "$data_dir" ]]; then
  echo "Set NIRS4ALL_DATA_DIR to the local root containing regression/ and classification/." >&2
  exit 2
fi
case "$out/" in
  "$repo_root/benchmarks/runs/"*)
    echo "AOM_REPRO_OUTPUT must not be inside the frozen benchmarks/runs tree." >&2
    exit 2
    ;;
esac
if [[ "${AOM_DRY_RUN:-0}" != "1" ]]; then
  mkdir -p "$out"
fi
export PYTHONPATH="$repo_root:$nirs4all_dir:$lab_dir${PYTHONPATH:+:$PYTHONPATH}"

run_cmd() {
  if [[ "${AOM_DRY_RUN:-0}" == "1" ]]; then
    printf 'DRY RUN:'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

regression_cohort="$out/cohorts/regression.csv"
classification_cohort="$out/cohorts/classification.csv"
run_cmd "$python_bin" "$script_dir/prepare_cohort.py" \
  --input "$repo_root/benchmarks/pls/cohort_regression.csv" \
  --output "$regression_cohort" --data-root "$data_dir"
run_cmd "$python_bin" "$script_dir/prepare_cohort.py" \
  --input "$repo_root/benchmarks/pls/cohort_classification.csv" \
  --output "$classification_cohort" --data-root "$data_dir"

cd "$lab_dir"
for seed in 0 1 2; do
  run_cmd "$python_bin" "$repo_root/benchmarks/pls/run_extended_benchmark.py" \
    --workspace "$out/aom_pls_seed$seed" \
    --cohort "$regression_cohort" \
    --limit 0 --max-n-train 1000000000 \
    --seed "$seed" --criterion cv --max-components 15 --cv 5 \
    --variants AOM-compact-cv5-numpy,ASLS-AOM-compact-cv5-numpy
done

run_cmd "$python_bin" "$repo_root/benchmarks/ridge/run_aomridge_benchmark.py" \
  --workspace "$out/aom_ridge" --cohort full --variants headline \
  --cv 3 --cv-kind spxy --seeds 0 1 2 \
  --cohort-path "$regression_cohort"

run_cmd "$python_bin" "$repo_root/benchmarks/pls/run_aompls_benchmark.py" \
  --task classification --cohort "$classification_cohort" \
  --workspace "$out/aom_pls_da" --seeds 0,1,2 --criterion cv \
  --max-components 15 --cv 5

run_cmd "$python_bin" "$repo_root/benchmarks/fast/run_fast_aom_benchmark.py" \
  --cohort "$regression_cohort" \
  --workspace "$out/fastaom" --seeds 0 --max-components 15

if [[ -f "$lab_dir/tabpfn/paper/run_linear_hpo_paper_aom.py" ]]; then
  run_cmd "$python_bin" "$lab_dir/tabpfn/paper/run_linear_hpo_paper_aom.py" \
    --cohort-path "$regression_cohort" \
    --workspace "$out/linear_hpo" --seeds 0 1 2 \
    --variants pls-default-cv5,pls-tabpfn-hpo-25trials,ridge-default-cv5,ridge-tabpfn-hpo-60trials \
    --project-root "$nirs4all_dir"
else
  echo "HPO launcher not found; set NIRS4ALL_LAB_DIR to the companion nirs4all-lab checkout." >&2
  exit 2
fi

if [[ "${AOM_DRY_RUN:-0}" == "1" ]]; then
  echo "Dry run complete; no output directory was created and no model was fitted."
else
  echo "Full rerun outputs written under $out; frozen paper runs were not modified."
fi
