#!/usr/bin/env python3
"""Matched identity-only and source-family inference for AOM-Ridge.

The primary corrective contrast uses the already completed five-fold matched
control: AOM-Ridge and identity-only Ridge share tasks, seeds, folds, centering,
the 50-value trace-relative alpha grid, selection rule and external split.
Inference is performed on log RMSEP ratios so it is invariant to response units.

A broader N=52 comparison against the archived Ridge-default workflow is also
reported as a secondary robustness analysis.  It is not interpreted causally
because that workflow used a different fold and alpha-grid protocol.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
MATCHED = HERE / "matched_ridge_stacking" / "per_run_results.csv"
HEADLINE = REPO_ROOT / "benchmarks" / "runs" / "ridge" / "all54_headline" / "results.csv"
DEFAULT = (
    REPO_ROOT
    / "benchmarks"
    / "runs"
    / "scenarios"
    / "paper_aom_linear_hpo_full_cartesian_default_cv5_all"
    / "results.csv"
)
MANIFEST = REPO_ROOT / "paper" / "review" / "cohort_manifest.csv"
OUTPUT = HERE / "ridge_identity_inference"
TABLE = REPO_ROOT / "paper" / "tables" / "table_ridge_identity_inference.tex"
BOOTSTRAP_SEED = 20260904
BOOTSTRAP_N = 20_000


def dataset_id(values: pd.Series) -> pd.Series:
    return values.astype("string").str.split("/").str[-1].str.strip()


def summarise(ratios: pd.Series, *, scope: str, unit: str) -> dict[str, object]:
    ratios = ratios.astype(float)
    ratios = ratios[np.isfinite(ratios) & (ratios > 0)]
    values = ratios.to_numpy()
    log_ratios = np.log(values)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = rng.choice(values, size=(BOOTSTRAP_N, len(values)), replace=True)
    boot = np.median(draws, axis=1)
    non_ties = values != 1.0
    wins = int(np.sum(values < 1.0))
    losses = int(np.sum(values > 1.0))
    ties = int(np.sum(~non_ties))
    wilcoxon_p = (
        float(stats.wilcoxon(log_ratios, alternative="two-sided", zero_method="wilcox").pvalue)
        if np.any(log_ratios != 0)
        else math.nan
    )
    sign_p = (
        float(stats.binomtest(wins, wins + losses, 0.5, alternative="two-sided").pvalue)
        if wins + losses
        else math.nan
    )
    return {
        "scope": scope,
        "unit": unit,
        "n": len(values),
        "median_ratio": float(np.median(values)),
        "ci95_low": float(np.percentile(boot, 2.5)),
        "ci95_high": float(np.percentile(boot, 97.5)),
        "wins": wins,
        "ties": ties,
        "losses": losses,
        "wilcoxon_log_ratio_raw_two_sided_p": wilcoxon_p,
        "sign_raw_two_sided_p": sign_p,
    }


def attach_families(frame: pd.DataFrame) -> pd.DataFrame:
    manifest = pd.read_csv(MANIFEST, low_memory=False)
    manifest = manifest[manifest["task"].astype(str).str.lower().eq("regression")].copy()
    manifest["task_id"] = dataset_id(manifest["dataset"])
    mapping = manifest.drop_duplicates("task_id").set_index("task_id")["source_family"]
    out = frame.copy()
    out["source_family"] = out.index.map(mapping)
    if out["source_family"].isna().any():
        missing = out.index[out["source_family"].isna()].tolist()
        raise RuntimeError(f"missing source-family mapping: {missing}")
    return out


def matched_pair() -> pd.DataFrame:
    frame = pd.read_csv(MATCHED, low_memory=False)
    frame = frame[frame["status"].astype(str).str.lower().eq("ok")]
    pair = frame.groupby("task")[["folded_test_rmse", "raw_ridge_test_rmse"]].mean()
    pair.columns = ["candidate", "reference"]
    pair = pair[(pair["candidate"] > 0) & (pair["reference"] > 0)].copy()
    pair["ratio"] = pair["candidate"] / pair["reference"]
    return attach_families(pair)


def broader_pair() -> pd.DataFrame:
    aom = pd.read_csv(HEADLINE, low_memory=False)
    aom = aom[
        aom["variant"].eq("AOMRidge-global-compact-none")
        & aom["status"].astype(str).str.lower().eq("ok")
    ].copy()
    aom["task_id"] = dataset_id(aom["dataset"])
    aom = aom.groupby("task_id")["rmsep"].mean()

    reference = pd.read_csv(DEFAULT, low_memory=False)
    reference = reference[
        reference["variant"].eq("ridge-default-cv5")
        & reference["status"].astype(str).str.lower().eq("ok")
    ].copy()
    reference["task_id"] = dataset_id(reference["dataset"])
    reference = reference.groupby("task_id")["rmsep"].mean()

    pair = pd.concat([aom.rename("candidate"), reference.rename("reference")], axis=1).dropna()
    pair = pair[(pair["candidate"] > 0) & (pair["reference"] > 0)].copy()
    pair["ratio"] = pair["candidate"] / pair["reference"]
    return attach_families(pair)


def analyse_pair(pair: pd.DataFrame, *, scope: str) -> tuple[list[dict[str, object]], pd.DataFrame]:
    family = pair.groupby("source_family")["ratio"].median().rename("ratio").to_frame()
    rows = [
        summarise(family["ratio"], scope=scope, unit="source family"),
        summarise(pair["ratio"], scope=scope, unit="task row"),
    ]
    return rows, family


def p_fmt(value: float) -> str:
    return f"{value:.2e}" if value < 0.01 else f"{value:.3f}"


def p_tex(value: float) -> str:
    if value >= 0.01:
        return f"{value:.3f}"
    exponent = math.floor(math.log10(value))
    coefficient = value / (10**exponent)
    return rf"${coefficient:.2f}\times10^{{{exponent}}}$"


def write_report(rows: list[dict[str, object]]) -> None:
    lines = [
        "# AOM-Ridge identity-only corrective inference",
        "",
        "The matched contrast changes only the operator bank: compact nine-operator AOM-Ridge versus identity-only Ridge. Both arms use the same five folds, seeds, centering, trace-relative alpha grid, selection rule and external test split. The source-family row is the primary inferential unit; task-row inference is a sensitivity. Tests rank log RMSEP ratios.",
        "",
        "The broader archived-default comparison uses the largest available pair but differs in tuning protocol and is therefore secondary.",
        "",
        "| Scope | Unit | N | Median ratio | 95% bootstrap CI | W/T/L | Wilcoxon log-ratio p2 | Sign p2 |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['scope']} | {row['unit']} | {row['n']} | {row['median_ratio']:.3f} | "
            f"{row['ci95_low']:.3f}--{row['ci95_high']:.3f} | "
            f"{row['wins']}/{row['ties']}/{row['losses']} | "
            f"{p_fmt(float(row['wilcoxon_log_ratio_raw_two_sided_p']))} | "
            f"{p_fmt(float(row['sign_raw_two_sided_p']))} |"
        )
    (OUTPUT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_table(rows: list[dict[str, object]]) -> None:
    display_scope = {
        "matched_identity": "Matched AOM-Ridge vs identity Ridge",
        "broader_archived_default": "AOM-Ridge vs archived Ridge-default",
    }
    lines = [
        r"\begin{tabularx}{\linewidth}{XXrrrr}",
        r"\toprule",
        r"Comparison & Unit & $N$ & Median ratio (95\% CI) & W/T/L & Raw log-ratio $p_2$ \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            f"{display_scope[str(row['scope'])]} & {row['unit']} & {row['n']} & "
            f"{row['median_ratio']:.3f} ({row['ci95_low']:.3f}--{row['ci95_high']:.3f}) & "
            f"{row['wins']}/{row['ties']}/{row['losses']} & "
            f"{p_tex(float(row['wilcoxon_log_ratio_raw_two_sided_p']))} " + r"\\"
        )
    lines += [r"\bottomrule", r"\end{tabularx}", ""]
    TABLE.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    matched = matched_pair()
    broader = broader_pair()
    matched_rows, matched_family = analyse_pair(matched, scope="matched_identity")
    broader_rows, broader_family = analyse_pair(broader, scope="broader_archived_default")
    rows = matched_rows + broader_rows

    task_rows = pd.concat(
        [
            matched.assign(scope="matched_identity"),
            broader.assign(scope="broader_archived_default"),
        ],
        names=["scope_source", "task_id"],
    )
    task_rows.rename_axis("task_id").to_csv(OUTPUT / "per_task.csv")
    family_rows = pd.concat(
        [
            matched_family.assign(scope="matched_identity"),
            broader_family.assign(scope="broader_archived_default"),
        ],
        names=["scope_source", "source_family"],
    )
    family_rows.to_csv(OUTPUT / "per_family.csv")
    pd.DataFrame(rows).to_csv(OUTPUT / "summary.csv", index=False)
    (OUTPUT / "summary.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    write_report(rows)
    write_table(rows)
    print((OUTPUT / "REPORT.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
