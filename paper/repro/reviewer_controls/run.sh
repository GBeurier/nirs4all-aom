#!/usr/bin/env bash
set -euo pipefail

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export CUDA_VISIBLE_DEVICES=""

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec taskset -c 10-13 python3 "$script_dir/audit_reviewer_controls.py"
