#!/usr/bin/env bash
set -euo pipefail

demo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
aom_root="$(cd -- "$demo_dir/../.." && pwd)"
ui_root="${NIRS4ALL_UI_DIR:-$(cd -- "$aom_root/.." && pwd)/nirs4all-ui}"
target="$demo_dir/assets/nirs4all-ui"

required=(
  "assets/styles/nirs4all-default.css"
  "assets/viz.css"
  "assets/brands/nirs4all-methods/horizontal.svg"
  "assets/brands/nirs4all-formats/icon.svg"
)

for relative_path in "${required[@]}"; do
  if [[ ! -f "$ui_root/$relative_path" ]]; then
    echo "Missing nirs4all-ui asset: $ui_root/$relative_path" >&2
    exit 1
  fi
done

mkdir -p \
  "$target/styles" \
  "$target/brands/nirs4all-methods" \
  "$target/brands/nirs4all-formats"
cp "$ui_root/assets/styles/nirs4all-default.css" "$target/styles/"
cp "$ui_root/assets/viz.css" "$target/"
cp "$ui_root/assets/brands/nirs4all-methods/horizontal.svg" "$target/brands/nirs4all-methods/"
cp "$ui_root/assets/brands/nirs4all-formats/icon.svg" "$target/brands/nirs4all-formats/"

echo "Synchronized canonical assets from $ui_root"
