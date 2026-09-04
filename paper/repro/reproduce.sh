#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/../.." && pwd)"
python_bin="${PYTHON:-python3}"
mode="${1:-check}"

case "$mode" in
  check)
    "$python_bin" "$script_dir/check_artifacts.py"
    ;;
  tables)
    "$script_dir/run_all.sh"
    ;;
  figures)
    "$python_bin" "$repo_root/paper/review/aggregate_stats.py" --partial
    ;;
  paper)
    "$python_bin" "$repo_root/paper/review/aggregate_stats.py" --partial
    "$script_dir/run_all.sh"
    build_script="${AOM_MANUSCRIPT_BUILD:-$repo_root/paper/build.sh}"
    if [[ ! -f "$build_script" ]]; then
      echo "Manuscript build script not found: $build_script" >&2
      exit 2
    fi
    bash "$build_script"
    ;;
  web)
    exec "$script_dir/serve_wasm.sh"
    ;;
  reviewer-controls)
    export CUDA_VISIBLE_DEVICES=""
    export PYTHONPATH="$repo_root${PYTHONPATH:+:$PYTHONPATH}"
    export OMP_NUM_THREADS=1
    export OPENBLAS_NUM_THREADS=1
    export MKL_NUM_THREADS=1
    export BLIS_NUM_THREADS=1
    export NUMEXPR_NUM_THREADS=1
    "$python_bin" "$script_dir/reviewer_controls/spectral_operator_figure.py"
    "$python_bin" "$script_dir/absolute_fom.py"
    bash "$script_dir/reviewer_controls/run.sh"
    "$python_bin" "$script_dir/reviewer_controls/matched_plsda_control.py" --max-workers 5
    "$python_bin" "$script_dir/reviewer_controls/folded_materialized_control.py" --cpu-limit 5
    "$python_bin" "$script_dir/reviewer_controls/full_matched_hpo_control.py" --max-workers 5
    "$python_bin" "$script_dir/reviewer_controls/analyze_full_matched_hpo.py"
    ;;
  full)
    exec "$script_dir/run_full_benchmarks.sh"
    ;;
  *)
    echo "usage: $0 {check|tables|figures|paper|web|reviewer-controls|full}" >&2
    exit 2
    ;;
esac
