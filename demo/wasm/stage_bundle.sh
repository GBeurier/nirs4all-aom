#!/usr/bin/env bash
set -euo pipefail

demo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
target_dir="$demo_dir/n4m"
n4m_version="${N4M_DEMO_VERSION:-1.0.13}"
stage_root="$(mktemp -d)"

cleanup() {
  find "$stage_root" -depth -mindepth 1 -delete
  rmdir "$stage_root"
}
trap cleanup EXIT

cd "$stage_root"
archive="$(npm pack "@nirs4all/methods@$n4m_version" --silent)"
tar -xzf "$archive"
dist_dir="$stage_root/package/dist"

if [[ ! -f "$dist_dir/index.js" || ! -f "$dist_dir/n4m.js" || ! -f "$dist_dir/n4m.wasm" ]]; then
  echo "The published @nirs4all/methods@$n4m_version archive is incomplete" >&2
  exit 1
fi

mkdir -p "$target_dir"
find "$target_dir" -maxdepth 1 -type f \( -name '*.js' -o -name '*.wasm' \) -delete
cp "$dist_dir"/*.js "$dist_dir"/*.wasm "$target_dir"/
echo "Staged @nirs4all/methods@$n4m_version in $target_dir"
