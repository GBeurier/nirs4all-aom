#!/usr/bin/env python3
"""RPD>=2 sensitivity for the strict N=32 AOM-Ridge comparison.

This is a pure aggregation over frozen prediction metrics and local Ytest
files.  The inclusion rule is defined from the Ridge-default baseline using
the standard analytical RPD = sample SD(y_test) / RMSEP, so selection does not
depend on whether AOM wins.  The AOM-defined set is emitted only as an audit.
"""

# ruff: noqa: E402 -- the repository path is inserted before local imports.

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
REPRO_DIR = REPO_ROOT / "paper" / "repro"
if str(REPRO_DIR) not in sys.path:
    sys.path.insert(0, str(REPRO_DIR))

from paper.repro.absolute_fom import (
    AOMRIDGE_SIMPLE,
    RIDGE_DEFAULT,
    collect_rpd,
    median_ratio,
    per_dataset_metric,
    strict_intersection,
)


HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "rpd_quality_sensitivity"
BOOTSTRAP_SEED = 20260904
N_BOOTSTRAP = 20_000


def summarise(
    datasets: list[str],
    candidate: dict[str, float],
    reference: dict[str, float],
    *,
    subset: str,
) -> dict[str, object]:
    _, rows = median_ratio(candidate, reference, datasets)
    ratios = np.asarray([float(row["ratio"]) for row in rows])
    differences = np.asarray(
        [float(row["candidate"]) - float(row["reference"]) for row in rows]
    )
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = rng.choice(ratios, size=(N_BOOTSTRAP, len(ratios)), replace=True)
    medians = np.median(draws, axis=1)
    p = (
        float(stats.wilcoxon(differences, alternative="two-sided", zero_method="wilcox").pvalue)
        if np.any(differences != 0)
        else math.nan
    )
    return {
        "comparison": "AOM-Ridge simple vs Ridge-default",
        "subset": subset,
        "n": len(ratios),
        "median_ratio": float(np.median(ratios)),
        "ci95_low": float(np.percentile(medians, 2.5)),
        "ci95_high": float(np.percentile(medians, 97.5)),
        "wins": int(np.sum(differences < 0)),
        "ties": int(np.sum(differences == 0)),
        "losses": int(np.sum(differences > 0)),
        "wilcoxon_raw_two_sided_p": p,
    }


def main() -> int:
    datasets, _ = strict_intersection()
    dataset_set = set(datasets)
    candidate = per_dataset_metric(
        AOMRIDGE_SIMPLE,
        AOMRIDGE_SIMPLE.rmsep_column,
        dataset_set,
    )
    reference = per_dataset_metric(
        RIDGE_DEFAULT,
        RIDGE_DEFAULT.rmsep_column,
        dataset_set,
    )
    baseline_rpd = collect_rpd(dataset_set, reference)
    aom_rpd = collect_rpd(dataset_set, candidate)
    baseline_keep = sorted(ds for ds in datasets if baseline_rpd[ds] >= 2.0)
    aom_keep = sorted(ds for ds in datasets if aom_rpd[ds] >= 2.0)

    summaries = [
        summarise(datasets, candidate, reference, subset="strict_N32_all"),
        summarise(
            baseline_keep,
            candidate,
            reference,
            subset="baseline_RPD_ge_2",
        ),
        summarise(
            aom_keep,
            candidate,
            reference,
            subset="AOM_RPD_ge_2_audit_only",
        ),
    ]
    rows = pd.DataFrame(
        {
            "dataset": datasets,
            "ridge_default_rmsep": [reference[ds] for ds in datasets],
            "aom_ridge_rmsep": [candidate[ds] for ds in datasets],
            "ridge_default_rpd": [baseline_rpd[ds] for ds in datasets],
            "aom_ridge_rpd": [aom_rpd[ds] for ds in datasets],
            "baseline_rpd_ge_2": [ds in baseline_keep for ds in datasets],
            "aom_rpd_ge_2": [ds in aom_keep for ds in datasets],
        }
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows.to_csv(OUT_DIR / "per_task.csv", index=False)
    pd.DataFrame(summaries).to_csv(OUT_DIR / "summary.csv", index=False)
    metadata = {
        "definition": "sample SD(y_test) / RMSEP",
        "primary_filter": "Ridge-default RPD >= 2",
        "post_hoc": True,
        "baseline_and_aom_sets_identical": baseline_keep == aom_keep,
        "baseline_keep": baseline_keep,
        "aom_keep": aom_keep,
        "summaries": summaries,
    }
    (OUT_DIR / "summary.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# RPD>=2 task-quality sensitivity",
        "",
        "Post-hoc sensitivity using the standard RPD = sample SD(y_test) / RMSEP. The primary inclusion rule is defined from Ridge-default, independently of the AOM result.",
        "",
        "| Subset | N | Median AOM/default RMSEP ratio | 95% bootstrap CI | Wins/ties/losses | Raw two-sided Wilcoxon p |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in summaries:
        p = float(row["wilcoxon_raw_two_sided_p"])
        p_text = f"{p:.2e}" if p < 0.001 else f"{p:.3f}"
        lines.append(
            f"| {row['subset']} | {row['n']} | {row['median_ratio']:.3f} | "
            f"{row['ci95_low']:.3f}--{row['ci95_high']:.3f} | "
            f"{row['wins']}/{row['ties']}/{row['losses']} | {p_text} |"
        )
    lines += [
        "",
        f"Baseline- and AOM-defined RPD>=2 sets identical: {baseline_keep == aom_keep}.",
    ]
    (OUT_DIR / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    tex = [
        r"\begin{tabularx}{\linewidth}{Xrrrrr}",
        r"\toprule",
        r"Subset & $N$ & Median ratio & 95\% CI & Wins & Raw $p_2$ \\",
        r"\midrule",
    ]
    labels = {
        "strict_N32_all": r"Strict $N=32$ panel",
        "baseline_RPD_ge_2": r"Ridge-default RPD $\geq 2$",
        "AOM_RPD_ge_2_audit_only": r"AOM-Ridge RPD $\geq 2$ (audit only)",
    }
    for row in summaries:
        p = float(row["wilcoxon_raw_two_sided_p"])
        p_text = f"{p:.1e}" if p < 0.001 else f"{p:.3f}"
        tex.append(
            f"{labels[row['subset']]} & {row['n']} & {row['median_ratio']:.3f} & "
            f"{row['ci95_low']:.3f}--{row['ci95_high']:.3f} & "
            f"{row['wins']}/{row['n']} & {p_text} \\\\"
        )
    tex += [r"\bottomrule", r"\end{tabularx}", ""]
    table_path = REPO_ROOT / "paper" / "tables" / "table_rpd_quality_sensitivity.tex"
    table_path.write_text("\n".join(tex), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
