#!/usr/bin/env bash
set -euo pipefail

demo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
aom_root="$(cd -- "$demo_dir/../.." && pwd)"
nirs4all_root="${NIRS4ALL_DIR:-$(cd -- "$aom_root/.." && pwd)/nirs4all}"
python_bin="${NIRS4ALL_PYTHON:-$nirs4all_root/.venv/bin/python}"

if [[ ! -x "$python_bin" ]]; then
  echo "Missing nirs4all Python environment: $python_bin" >&2
  exit 1
fi

"$python_bin" "$demo_dir/generate_demo_datasets.py" \
  --nirs4all-dir "$nirs4all_root" \
  --output-dir "$demo_dir/datasets"

echo "Regenerated bundled spectral examples with nirs4all from $nirs4all_root"
