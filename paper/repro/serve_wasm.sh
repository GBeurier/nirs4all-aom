#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/../.." && pwd)"
port="${AOM_WEB_PORT:-8765}"

echo "Serving http://127.0.0.1:$port/demo/wasm/"
echo "Smoke test: http://127.0.0.1:$port/demo/wasm/?selftest=1"
exec "${PYTHON:-python3}" -m http.server "$port" --directory "$repo_root"
