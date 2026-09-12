#!/usr/bin/env bash
set -euo pipefail

demo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
target_dir="$demo_dir/n4m"
n4m_version="${N4M_DEMO_VERSION:-latest}"
stage_root="$(mktemp -d)"
cleanup() {
  find "$stage_root" -depth -mindepth 1 -delete
  rmdir "$stage_root"
}
trap cleanup EXIT

cd "$stage_root"
npm pack "@nirs4all/methods@$n4m_version" --ignore-scripts --json > pack.json
archive="$(node -p 'JSON.parse(require("fs").readFileSync("pack.json", "utf8"))[0].filename')"
tar -xzf "$archive"
dist_dir="$stage_root/package/dist"
if [[ ! -f "$dist_dir/index.js" || ! -f "$dist_dir/n4m.js" || ! -f "$dist_dir/n4m.wasm" ]]; then
  echo "The published @nirs4all/methods archive is incomplete" >&2
  exit 1
fi
if ! grep -q 'fitAomChain' "$dist_dir/index.js"; then
  echo "The published bundle lacks the configurable AOM chain API" >&2
  exit 1
fi

mkdir -p "$target_dir"
find "$target_dir" -maxdepth 1 -type f \( -name '*.js' -o -name '*.wasm' \) -delete
cp "$dist_dir"/*.js "$dist_dir"/*.wasm "$target_dir"/
node - "$target_dir" <<'JS'
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const target = process.argv[2];
const pkg = JSON.parse(fs.readFileSync('package/package.json', 'utf8'));
const pack = JSON.parse(fs.readFileSync('pack.json', 'utf8'))[0];
const files = Object.fromEntries(fs.readdirSync(target).filter(f => /\.(js|wasm)$/.test(f)).sort().map(f => [f, crypto.createHash('sha256').update(fs.readFileSync(path.join(target, f))).digest('hex')]));
fs.writeFileSync(path.join(target, 'version.json'), JSON.stringify({ package: pkg.name, version: pkg.version, source: 'npm', archive_integrity: pack.integrity, files }, null, 2) + '\n');
console.log(`Staged ${pkg.name}@${pkg.version} in ${target}`);
JS
