#!/usr/bin/env bash
set -euo pipefail

demo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
aom_root="$(cd -- "$demo_dir/../.." && pwd)"
nirs4all_root="${NIRS4ALL_DIR:-$(cd -- "$aom_root/.." && pwd)/nirs4all}"

datasets=(B02_wavenumber B03_wavelength B04_reflectance)
files=(Xcal.csv Ycal.csv Xval.csv Yval.csv)

for dataset in "${datasets[@]}"; do
  source_dir="$nirs4all_root/examples/sample_datasets/$dataset"
  target_dir="$demo_dir/datasets/$dataset"
  for filename in "${files[@]}"; do
    if [[ ! -f "$source_dir/$filename" ]]; then
      echo "Missing nirs4all fixture: $source_dir/$filename" >&2
      exit 1
    fi
  done
  mkdir -p "$target_dir"
  for filename in "${files[@]}"; do
    cp "$source_dir/$filename" "$target_dir/$filename"
  done
done

echo "Synchronized bundled format fixtures from $nirs4all_root"
