#!/usr/bin/env bash
set -euo pipefail

demo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
aom_root="$(cd -- "$demo_dir/../.." && pwd)"
nirs4all_datasets_root="${NIRS4ALL_DATASETS_DIR:-$(cd -- "$aom_root/.." && pwd)/nirs4all-datasets}"
python_bin="${NIRS4ALL_PYTHON:-python3}"

if [[ ! -d "$nirs4all_datasets_root/datasets" ]]; then
  echo "Missing nirs4all-datasets checkout: $nirs4all_datasets_root" >&2
  exit 1
fi

"$python_bin" "$demo_dir/generate_demo_datasets.py" \
  --datasets-dir "$nirs4all_datasets_root" \
  --output-dir "$demo_dir/datasets"

echo "Regenerated public measured-data snapshots from $nirs4all_datasets_root"
