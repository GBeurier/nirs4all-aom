"""Regenerate ``fig_paired_rmsep_scatter`` only.

``build_paper_figures.py`` is the canonical figure builder, but its
``main()`` also rewrites tables that depend on files (e.g.
``compact_bank_justification.md``) which are not always present in this
checkout.  This helper imports the module and calls only the regression
stats loader plus the scatter builder so the figure can be refreshed
without running the rest of the pipeline.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "paper" / "review"))

import build_paper_figures as bpf  # noqa: E402


def main() -> None:
    rows, dfs = bpf.build_regression_stats()
    bpf.build_paired_rmsep_scatter(rows, dfs)
    print(f"wrote {bpf.FIGURES / 'fig_paired_rmsep_scatter.pdf'}")


if __name__ == "__main__":
    main()
