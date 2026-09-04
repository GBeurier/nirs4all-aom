"""Portable paths shared by the paper reproduction scripts."""

from __future__ import annotations

import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS = REPO_ROOT / "benchmarks" / "runs"
SCENARIOS = RUNS / "scenarios"
COHORT_MANIFEST = REPO_ROOT / "paper" / "review" / "cohort_manifest.csv"
BENCHMARK_MASTER = Path(
    os.environ.get(
        "AOM_BENCHMARK_MASTER",
        REPO_ROOT / "_archive" / "nirs4all-lab_benchmark_master" / "benchmark_master_results.csv",
    )
).expanduser().resolve()
MANUSCRIPT_TABLES = Path(
    os.environ.get("AOM_MANUSCRIPT_TABLES", REPO_ROOT / "paper" / "tables")
).expanduser().resolve()


def table_path(name: str) -> Path:
    """Return an output table path and ensure its parent exists."""

    MANUSCRIPT_TABLES.mkdir(parents=True, exist_ok=True)
    return MANUSCRIPT_TABLES / name
