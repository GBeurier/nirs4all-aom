#!/usr/bin/env bash
set -euo pipefail

demo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
aom_root="$(cd -- "$demo_dir/../.." && pwd)"
datasets_root="${NIRS4ALL_DATASETS_DIR:-$(cd -- "$aom_root/.." && pwd)/nirs4all-datasets}"
python_bin="${NIRS4ALL_DATASETS_PYTHON:-python3.11}"

if ! command -v "$python_bin" >/dev/null 2>&1; then
  echo "Missing Python interpreter: $python_bin" >&2
  exit 1
fi

"$python_bin" "$demo_dir/generate_demo_datasets.py" \
  --datasets-dir "$datasets_root/NIRS DB/v2.0" \
  --output-dir "$demo_dir/datasets"

echo "Regenerated public spectral examples from $datasets_root"
