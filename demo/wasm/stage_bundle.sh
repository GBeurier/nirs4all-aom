#!/usr/bin/env bash
set -euo pipefail

demo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
target_dir="$demo_dir/n4m"
n4m_source="${N4M_METHODS_DIR:-$(cd -- "$demo_dir/../../.." && pwd)/nirs4all-methods}"
dist_dir="$n4m_source/bindings/js/dist"

if [[ ! -f "$dist_dir/index.js" || ! -f "$dist_dir/n4m.js" || ! -f "$dist_dir/n4m.wasm" ]]; then
  echo "Build and stage the sibling nirs4all-methods JS/WASM package first (expected $dist_dir)" >&2
  exit 1
fi
if ! grep -q "fitAomChain" "$dist_dir/index.js"; then
  echo "The staged nirs4all-methods bundle lacks the configurable AOM chain API" >&2
  exit 1
fi

mkdir -p "$target_dir"
find "$target_dir" -maxdepth 1 -type f \( -name '*.js' -o -name '*.wasm' \) -delete
cp "$dist_dir"/*.js "$dist_dir"/*.wasm "$target_dir"/
echo "Staged the source-built nirs4all-methods JS/WASM bundle in $target_dir"
