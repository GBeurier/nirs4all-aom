#!/usr/bin/env python3
"""Fast, read-only integrity check for the paper and WebAssembly artifacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from paths import COHORT_MANIFEST, REPO_ROOT, RUNS


def paper_runs() -> list[Path]:
    manifest = RUNS / "PAPER_MANIFEST.txt"
    paths: list[Path] = []
    for raw in manifest.read_text(encoding="utf-8").splitlines():
        entry = raw.split("#", 1)[0].strip()
        if entry:
            paths.append(RUNS / entry / "results.csv")
    return paths


def check_csv(path: Path) -> int:
    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f"missing or empty CSV: {path}")
    with path.open("rb") as handle:
        header = handle.readline().decode("utf-8", errors="replace")
        fieldnames = next(csv.reader([header]), [])
        if "dataset" not in fieldnames:
            raise SystemExit(f"invalid results schema: {path}")
        # Some archived diagnostic JSON fields contain legacy NUL bytes. They
        # are preserved as provenance, so this integrity check counts records
        # without asking the strict text CSV parser to reinterpret those bytes.
        rows = 0
        while chunk := handle.read(1024 * 1024):
            rows += chunk.count(b"\n")
        return rows


def check_cohort() -> tuple[int, int]:
    with COHORT_MANIFEST.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    n_reg = sum(row.get("task") == "regression" for row in rows)
    n_cls = sum(row.get("task") == "classification" for row in rows)
    if (n_reg, n_cls) != (61, 17):
        raise SystemExit(f"unexpected cohort counts: regression={n_reg}, classification={n_cls}")
    return n_reg, n_cls


def check_wasm() -> int:
    root = REPO_ROOT / "demo" / "wasm"
    required = [root / "index.html", root / "demo.js", root / "n4m" / "n4m.wasm"]
    for path in required:
        if not path.is_file() or path.stat().st_size == 0:
            raise SystemExit(f"missing WebAssembly companion asset: {path}")
    manifest_path = root / "datasets" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    datasets = manifest.get("datasets", [])
    if not datasets:
        raise SystemExit("the WebAssembly dataset manifest is empty")
    for dataset in datasets:
        dataset_dir = root / "datasets" / dataset["id"]
        for name in ("Xcal.csv", "Ycal.csv", "Xval.csv", "Yval.csv"):
            path = dataset_dir / name
            if not path.is_file() or path.stat().st_size == 0:
                raise SystemExit(f"missing WebAssembly example input: {path}")
    return len(datasets)


def main() -> None:
    n_reg, n_cls = check_cohort()
    run_counts = {path.relative_to(REPO_ROOT).as_posix(): check_csv(path) for path in paper_runs()}
    n_demo = check_wasm()
    print(f"cohort: {n_reg} regression + {n_cls} classification task rows")
    print(f"paper runs: {len(run_counts)} result files, {sum(run_counts.values())} rows")
    print(f"WebAssembly companion: bundle present, {n_demo} example datasets")
    print("browser self-test URL after serving the repository: /demo/wasm/?selftest=1")
    print("artifact check: PASS")


if __name__ == "__main__":
    main()
