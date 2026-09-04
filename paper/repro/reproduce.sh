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
  full)
    exec "$script_dir/run_full_benchmarks.sh"
    ;;
  *)
    echo "usage: $0 {check|tables|figures|paper|web|full}" >&2
    exit 2
    ;;
esac
