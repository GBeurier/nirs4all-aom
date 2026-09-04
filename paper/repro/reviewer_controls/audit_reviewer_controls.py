#!/usr/bin/env python3
"""Read-only reviewer controls for the AOM Talanta revision.

This script performs no model fitting.  It only reads frozen CSV/log/code
artifacts already present in the repository and writes audit CSVs plus a short
Markdown report next to itself.
"""

from __future__ import annotations

import json
import hashlib
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUNS = ROOT / "benchmarks" / "runs"
SCEN = RUNS / "scenarios"

COHORT_SOURCE = ROOT / "benchmarks" / "pls" / "cohort_regression.csv"
COHORT_MANIFEST = ROOT / "paper" / "review" / "cohort_manifest.csv"
DEFAULT_RESULTS = SCEN / "paper_aom_linear_hpo_full_cartesian_default_cv5_all" / "results.csv"
AOMPLS_RESULTS = SCEN / "paper_aom_aompls_seeds012" / "results.csv"
AOMRIDGE_RESULTS = RUNS / "ridge" / "all54_headline" / "results.csv"

HPO = {
    "PLS": {
        "variant": "pls-tabpfn-hpo-25trials",
        "paths": [
            SCEN / f"paper_aom_linear_hpo_full_cartesian_pls-tabpfn-hpo-25trials_seed{s}" / "results.csv"
            for s in range(3)
        ],
        "log": ROOT / "paper" / "logs" / "linear_hpo_pls-tabpfn-hpo-25trials_s0.log",
    },
    "Ridge": {
        "variant": "ridge-tabpfn-hpo-60trials",
        "paths": [
            SCEN / f"paper_aom_linear_hpo_full_cartesian_ridge-tabpfn-hpo-60trials_seed{s}" / "results.csv"
            for s in range(3)
        ],
        "log": ROOT / "paper" / "logs" / "linear_hpo_ridge-tabpfn-hpo-60trials_s0.log",
    },
}

TA = "ta_groupSampleID_stratDateVar_balRows"
EXCLUDED = {"Quartz_spxy70"}
BOOTSTRAP_N = 20_000
BOOTSTRAP_SEED = 20260904


def base(value: object) -> str:
    return str(value).split("/")[-1].strip()


def ok_mask(df: pd.DataFrame) -> pd.Series:
    if "status" not in df:
        return pd.Series(True, index=df.index)
    return df["status"].fillna("").astype(str).str.lower().isin({"", "ok", "success", "completed"})


def per_dataset(
    path: Path,
    *,
    selector_col: str,
    selector_value: str,
    metric_col: str,
    r2_col: str | None = None,
) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    sub = df[df[selector_col].astype(str).str.lower().eq(selector_value.lower()) & ok_mask(df)].copy()
    sub["dataset"] = sub["dataset"].map(base)
    cols = [metric_col] + ([r2_col] if r2_col else [])
    out = sub.groupby("dataset", as_index=False)[cols].mean(numeric_only=True)
    rename = {metric_col: "rmsep"}
    if r2_col:
        rename[r2_col] = "r2"
    return out.rename(columns=rename)


def hpo_rows(family: str) -> pd.DataFrame:
    frames = []
    for path in HPO[family]["paths"]:
        d = pd.read_csv(path, low_memory=False)
        d["source_file"] = str(path.relative_to(ROOT))
        d["dataset"] = d["dataset"].map(base)
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def hpo_per_dataset(family: str) -> pd.DataFrame:
    d = hpo_rows(family)
    d = d[d["variant"].eq(HPO[family]["variant"]) & ok_mask(d)]
    return d.groupby("dataset", as_index=False).agg(
        rmsep=("rmsep", "mean"),
        r2=("r2", "mean"),
        total_time_s=("total_time_s", "mean"),
        seeds=("seed", "nunique"),
    )


def series(frame: pd.DataFrame, column: str) -> pd.Series:
    return frame.set_index("dataset")[column].astype(float)


def paired(candidate: pd.Series, reference: pd.Series) -> pd.DataFrame:
    common = candidate.index.intersection(reference.index).difference(list(EXCLUDED))
    out = pd.DataFrame({"candidate": candidate.loc[common], "reference": reference.loc[common]})
    out = out.replace([np.inf, -np.inf], np.nan).dropna()
    out = out[out["reference"] > 0]
    out["ratio"] = out["candidate"] / out["reference"]
    out.index.name = "dataset"
    return out.sort_index()


def summarise_pair(df: pd.DataFrame, *, label: str, comparison: str) -> dict[str, object]:
    values = df["ratio"].to_numpy(float)
    if not len(values):
        return {"comparison": comparison, "subset": label, "n": 0}
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = rng.choice(values, size=(BOOTSTRAP_N, len(values)), replace=True)
    med = np.median(draws, axis=1)
    signal = np.log(values)
    p = float(stats.wilcoxon(signal, alternative="two-sided", zero_method="wilcox").pvalue) if np.any(signal != 0) else math.nan
    return {
        "comparison": comparison,
        "subset": label,
        "n": len(values),
        "median_ratio": float(np.median(values)),
        "ci95_low": float(np.percentile(med, 2.5)),
        "ci95_high": float(np.percentile(med, 97.5)),
        "wins": int(np.sum(values < 1)),
        "losses": int(np.sum(values > 1)),
        "ties": int(np.sum(values == 1)),
        "wilcoxon_raw_two_sided_p": p,
    }


def build_inputs() -> dict[str, pd.DataFrame | pd.Series | set[str]]:
    pls_default = per_dataset(
        DEFAULT_RESULTS, selector_col="variant", selector_value="pls-default-cv5",
        metric_col="rmsep", r2_col="r2",
    )
    ridge_default = per_dataset(
        DEFAULT_RESULTS, selector_col="variant", selector_value="ridge-default-cv5",
        metric_col="rmsep", r2_col="r2",
    )
    aom_pls = per_dataset(
        AOMPLS_RESULTS, selector_col="result_label", selector_value="AOM-compact-cv5-numpy",
        metric_col="RMSEP", r2_col="r2_test",
    )
    asls_aom_pls = per_dataset(
        AOMPLS_RESULTS, selector_col="result_label", selector_value="ASLS-AOM-compact-cv5-numpy",
        metric_col="RMSEP", r2_col="r2_test",
    )
    aom_ridge = per_dataset(
        AOMRIDGE_RESULTS, selector_col="variant", selector_value="AOMRidge-global-compact-none",
        metric_col="rmsep", r2_col="r2",
    )
    blend_ridge = per_dataset(
        AOMRIDGE_RESULTS, selector_col="variant", selector_value="AOMRidge-Blender-headline-spxy3",
        metric_col="rmsep", r2_col="r2",
    )
    pls_hpo = hpo_per_dataset("PLS")
    ridge_hpo = hpo_per_dataset("Ridge")

    required_sets = [
        set(x["dataset"]) for x in (
            pls_default, ridge_default, aom_pls, asls_aom_pls,
            aom_ridge, blend_ridge, pls_hpo, ridge_hpo,
        )
    ]
    strict = set.intersection(*required_sets) - EXCLUDED
    return {
        "pls_default": pls_default,
        "ridge_default": ridge_default,
        "aom_pls": aom_pls,
        "asls_aom_pls": asls_aom_pls,
        "aom_ridge": aom_ridge,
        "blend_ridge": blend_ridge,
        "pls_hpo": pls_hpo,
        "ridge_hpo": ridge_hpo,
        "strict": strict,
    }


def audit_hpo_coverage(inputs: dict[str, object]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str]]:
    source = pd.read_csv(COHORT_SOURCE)
    source["dataset"] = source["dataset"].map(base)
    source["runner_eligible"] = source["status"].eq("ok")
    source.loc[source["runner_eligible"], "eligible_order"] = range(1, int(source["runner_eligible"].sum()) + 1)
    manifest = pd.read_csv(COHORT_MANIFEST)
    manifest = manifest[manifest["task"].eq("regression")].copy()
    manifest["dataset"] = manifest["dataset"].map(base)
    meta_cols = ["dataset", "source_family", "domain_group", "n_train", "n_test", "n_features", "p_over_n_train"]
    universe = manifest[meta_cols].merge(
        source[["dataset", "status", "runner_eligible", "eligible_order"]], on="dataset", how="left",
        suffixes=("", "_cohort"),
    )

    task_rows = []
    characteristic_rows = []
    summary_lines = []
    for family in ("PLS", "Ridge"):
        h = hpo_rows(family)
        by = h.groupby("dataset").agg(
            attempted_n_seeds=("seed", "nunique"),
            successful_n_seeds=("status", lambda s: int(s.astype(str).str.lower().eq("ok").sum())),
            statuses=("status", lambda s: ";".join(sorted(set(map(str, s))))),
        )
        attempted = set(by.index)
        success = set(by.index[by["successful_n_seeds"].eq(3)])
        rows = universe.copy()
        rows["hpo_family"] = family
        rows["attempted_n_seeds"] = rows["dataset"].map(by["attempted_n_seeds"]).fillna(0).astype(int)
        rows["successful_n_seeds"] = rows["dataset"].map(by["successful_n_seeds"]).fillna(0).astype(int)
        rows["hpo_result"] = np.select(
            [rows["successful_n_seeds"].eq(3), rows["attempted_n_seeds"].gt(0)],
            ["success_all_3_seeds", "attempted_error"],
            default="not_attempted",
        )
        task_rows.append(rows)

        attempted_orders = sorted(rows.loc[rows["dataset"].isin(attempted), "eligible_order"].dropna().astype(int))
        max_order = max(attempted_orders)
        contiguous = attempted_orders == list(range(1, max_order + 1))
        summary_lines.append(
            f"{family}: runner universe=60; attempted={len(attempted)} tasks x 3 seeds; "
            f"success={len(success)}; errors={len(attempted-success)}; maximum eligible order={max_order}; "
            f"attempted set is contiguous prefix={contiguous}."
        )

        for group_name, group_mask in {
            "attempted": rows["attempted_n_seeds"].gt(0),
            "runner_eligible_not_attempted": rows["runner_eligible"].fillna(False) & rows["attempted_n_seeds"].eq(0),
            "all_not_attempted": rows["attempted_n_seeds"].eq(0),
            "success_all_3_seeds": rows["hpo_result"].eq("success_all_3_seeds"),
            "no_success": ~rows["hpo_result"].eq("success_all_3_seeds"),
        }.items():
            g = rows[group_mask]
            characteristic_rows.append({
                "hpo_family": family,
                "group": group_name,
                "n_tasks": len(g),
                "n_source_families": g["source_family"].nunique(),
                "n_domains": g["domain_group"].nunique(),
                "median_n_train": g["n_train"].median(),
                "median_n_test": g["n_test"].median(),
                "median_n_features": g["n_features"].median(),
                "median_p_over_n_train": g["p_over_n_train"].median(),
            })

    task_audit = pd.concat(task_rows, ignore_index=True)
    task_audit.to_csv(HERE / "hpo_task_audit.csv", index=False)
    characteristics = pd.DataFrame(characteristic_rows)
    characteristics.to_csv(HERE / "hpo_group_characteristics.csv", index=False)

    comparisons = {
        "AOM-PLS simple vs PLS-default": (
            paired(series(inputs["aom_pls"], "rmsep"), series(inputs["pls_default"], "rmsep")), "PLS"
        ),
        "AOM-Ridge simple vs Ridge-default": (
            paired(series(inputs["aom_ridge"], "rmsep"), series(inputs["ridge_default"], "rmsep")), "Ridge"
        ),
    }
    strict = inputs["strict"]
    sensitivity = []
    for label, (pairs, family) in comparisons.items():
        f = task_audit[task_audit["hpo_family"].eq(family)].set_index("dataset")
        success = set(f.index[f["hpo_result"].eq("success_all_3_seeds")])
        attempted = set(f.index[f["attempted_n_seeds"].gt(0)])
        groups = {
            "largest_pair_all": set(pairs.index),
            "headline_strict_N32_included": set(pairs.index) & strict,
            "headline_excluded_but_pair_available": set(pairs.index) - strict,
            "method_hpo_success": set(pairs.index) & success,
            "method_hpo_no_success": set(pairs.index) - success,
            "method_hpo_attempted": set(pairs.index) & attempted,
            "method_hpo_not_attempted": set(pairs.index) - attempted,
        }
        for group, members in groups.items():
            sensitivity.append(summarise_pair(pairs.loc[pairs.index.intersection(members)], label=group, comparison=label))
    sensitivity_df = pd.DataFrame(sensitivity)
    sensitivity_df.to_csv(HERE / "hpo_included_excluded_sensitivity.csv", index=False)
    return task_audit, sensitivity_df, characteristics, summary_lines


def audit_quality_thresholds(inputs: dict[str, object]) -> pd.DataFrame:
    specs = [
        (
            "AOM-PLS simple vs PLS-default", inputs["aom_pls"], inputs["pls_default"],
        ),
        (
            "AOM-Ridge simple vs Ridge-default", inputs["aom_ridge"], inputs["ridge_default"],
        ),
    ]
    rows = []
    strict = inputs["strict"]
    for label, candidate_df, baseline_df in specs:
        pairs = paired(series(candidate_df, "rmsep"), series(baseline_df, "rmsep"))
        baseline_r2 = series(baseline_df, "r2")
        for scope_name, scope in {
            "largest_pair": set(pairs.index),
            "headline_strict_N32": set(pairs.index) & strict,
        }.items():
            scoped = pairs.loc[pairs.index.intersection(scope)]
            filters = {
                "all": set(scoped.index),
                "baseline_R2_gt_0": set(baseline_r2.index[baseline_r2.gt(0)]),
            }
            for filt, members in filters.items():
                summary = summarise_pair(
                    scoped.loc[scoped.index.intersection(members)],
                    label=f"{scope_name}:{filt}", comparison=label,
                )
                summary["baseline_rule"] = filt
                summary["scope"] = scope_name
                rows.append(summary)
    out = pd.DataFrame(rows)
    out.to_csv(HERE / "baseline_quality_sensitivity.csv", index=False)
    return out


def parse_config(value: object) -> dict[str, object]:
    try:
        return json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def audit_ta(inputs: dict[str, object]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    rows = []
    for family in ("PLS", "Ridge"):
        h = hpo_rows(family)
        sub = h[h["dataset"].eq(TA) & h["variant"].eq(HPO[family]["variant"])]
        for _, r in sub.iterrows():
            cfg = parse_config(r.get("best_config_json"))
            rows.append({
                "family": family,
                "variant": r["variant"],
                "seed": int(r["seed"]),
                "rmsep": r["rmsep"],
                "r2": r["r2"],
                "search_time_s": r["search_time_s"],
                "total_time_s": r["total_time_s"],
                "norm": cfg.get("norm"),
                "smooth": cfg.get("smooth"),
                "baseline": cfg.get("baseline"),
                "osc": cfg.get("osc"),
                "search_mean_score": cfg.get("search_mean_score"),
                "best_config_json": r.get("best_config_json"),
            })
    detail = pd.DataFrame(rows).sort_values(["family", "seed"])
    detail.to_csv(HERE / "ta_groupsampleid_hpo_audit.csv", index=False)

    strict = inputs["strict"]
    sensitivity_rows = []
    comparisons = [
        (
            "AOM-PLS simple vs PLS-HPO", inputs["aom_pls"], inputs["pls_hpo"],
        ),
        (
            "AOM-Ridge simple vs Ridge-HPO", inputs["aom_ridge"], inputs["ridge_hpo"],
        ),
    ]
    for label, candidate, reference in comparisons:
        p = paired(series(candidate, "rmsep"), series(reference, "rmsep"))
        p = p.loc[p.index.intersection(strict)]
        sensitivity_rows.append(summarise_pair(p, label="strict_N32_all", comparison=label))
        sensitivity_rows.append(summarise_pair(p.drop(index=TA, errors="ignore"), label="strict_without_ta", comparison=label))
    sensitivity = pd.DataFrame(sensitivity_rows)
    sensitivity.to_csv(HERE / "ta_leave_one_out_sensitivity.csv", index=False)

    diagnostics = {}
    for family in ("PLS", "Ridge"):
        h = hpo_rows(family)
        h = h[h["variant"].eq(HPO[family]["variant"]) & ok_mask(h)]
        per = h.groupby("dataset").agg(
            mean_rmsep=("rmsep", "mean"),
            min_rmsep=("rmsep", "min"),
            max_rmsep=("rmsep", "max"),
            mean_total_time_s=("total_time_s", "mean"),
        )
        per["runtime_rank_desc"] = per["mean_total_time_s"].rank(method="min", ascending=False)
        diagnostics[family] = per.loc[TA].to_dict()
        diagnostics[family]["successful_task_count"] = int(len(per))
    return detail, sensitivity, diagnostics


def audit_comparators() -> pd.DataFrame:
    generic = ROOT / "_archive" / "future_work" / "multiview" / "multiview" / "stacking.py"
    generic_results = ROOT / "_archive" / "future_work" / "multiview" / "results" / "full57.csv"
    stack5 = ROOT / "_archive" / "future_work" / "Multi-kernel" / "benchmarks" / "run_multikernel_smoke.py"
    stack5_results = ROOT / "_archive" / "future_work" / "Multi-kernel" / "benchmark_runs" / "diverse8_stack5" / "results.csv"

    generic_n = 0
    if generic_results.exists():
        d = pd.read_csv(generic_results, low_memory=False)
        generic_n = int(d[d["variant"].eq("ridge-stack-multiview") & ok_mask(d)]["dataset"].nunique())
    stack5_n = 0
    if stack5_results.exists():
        d = pd.read_csv(stack5_results, low_memory=False)
        stack5_n = int(d[d["variant"].eq("Stack") & ok_mask(d)]["dataset"].nunique())

    rows = [
        {
            "target_comparator": "SPORT",
            "faithful_existing_implementation": False,
            "code_path": "none found (only manuscript citations)",
            "results_path": "none",
            "successful_dataset_count": 0,
            "reuse_decision": "no",
            "reason": "No SPORT implementation or benchmark output exists in the audited repository.",
        },
        {
            "target_comparator": "Huang et al. 2024 SPRR (Ridge bases on separately preprocessed spectra + Ridge meta-model)",
            "faithful_existing_implementation": False,
            "code_path": str(generic.relative_to(ROOT)),
            "results_path": str(generic_results.relative_to(ROOT)),
            "successful_dataset_count": generic_n,
            "reuse_decision": "scaffold_only_not_results",
            "reason": "Existing StackingHybrid uses heterogeneous AOM/MoE/block-view base estimators, not one Ridge base learner per preprocessing view; full-cohort run stopped after six datasets.",
        },
        {
            "target_comparator": "Archived Multi-kernel Stack-5",
            "faithful_existing_implementation": False,
            "code_path": str(stack5.relative_to(ROOT)),
            "results_path": str(stack5_results.relative_to(ROOT)),
            "successful_dataset_count": stack5_n,
            "reuse_decision": "no_results_reuse",
            "reason": "Five heterogeneous raw/multi-kernel/mixed-model learners with Ridge meta-model; only one successful archived result, so it is not SPORT or SPRR.",
        },
    ]
    out = pd.DataFrame(rows)
    out.to_csv(HERE / "comparator_reuse_audit.csv", index=False)
    return out


def f(value: object, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "NA"
    return f"{float(value):.{digits}f}"


def p_fmt(value: object) -> str:
    value = float(value)
    if not math.isfinite(value):
        return "NA"
    return f"{value:.2e}" if value < 0.001 else f"{value:.3f}"


def make_report(
    inputs: dict[str, object], hpo_summary: list[str], group: pd.DataFrame,
    characteristics: pd.DataFrame,
    quality: pd.DataFrame, ta_detail: pd.DataFrame, ta_sens: pd.DataFrame,
    ta_diag: dict[str, object], comparators: pd.DataFrame,
) -> None:
    lines = [
        "# Reviewer controls: AOM Talanta targeted revision",
        "",
        "All findings are pure aggregations of frozen outputs; no model was fitted and no manuscript file was edited.",
        "",
        "## 1. HPO attempted/missing rule",
        "",
    ]
    lines += [f"- {x}" for x in hpo_summary]
    lines += [
        "- The source cohort has 61 rows, of which 60 have `status=ok`; Quartz is not runner-eligible. Both HPO campaigns therefore attempted a contiguous alphabetical/source-file prefix, not a prospectively sampled subset. PLS reached eligible row 38 (LUCAS SOC Cropland); Ridge stopped after row 37. The same prefix occurs for all three seeds.",
        "- The two attempted failures in both families are `FinalScore_grp70_30_scoreQ` and `Tleaf_grp70_30` (`Input X contains NaN`). Rows after the stopping point are absent, not fit failures.",
        "",
        "### Coverage-group characteristics",
        "",
        "| HPO | Group | Tasks | Families | Domains | Median n_train | Median p | Median p/n_train |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in characteristics.iterrows():
        if r["group"] in {"attempted", "runner_eligible_not_attempted"}:
            lines.append(
                f"| {r['hpo_family']} | {r['group']} | {int(r['n_tasks'])} | {int(r['n_source_families'])} | {int(r['n_domains'])} | {f(r['median_n_train'], 0)} | {f(r['median_n_features'], 0)} | {f(r['median_p_over_n_train'])} |"
            )
    lines += [
        "",
        "### Included-versus-excluded AOM/default sensitivity",
        "",
        "| Comparison | Subset | N | Median ratio | Wins | Raw Wilcoxon p |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for _, r in group.iterrows():
        if r["subset"] in {"headline_strict_N32_included", "headline_excluded_but_pair_available", "method_hpo_success", "method_hpo_not_attempted"}:
            lines.append(
                f"| {r['comparison']} | {r['subset']} | {int(r['n'])} | {f(r.get('median_ratio'))} | {int(r.get('wins', 0))}/{int(r['n'])} | {p_fmt(r.get('wilcoxon_raw_two_sided_p'))} |"
            )
    lines += [
        "",
        "Interpretation: because HPO coverage is an execution-order prefix, the strict panel is protocol-consistent but not a random or prospectively balanced sample. Report the prefix/truncation explicitly and keep the included/excluded AOM-vs-default sensitivity visible; do not describe missing HPO tasks as an analytically selected cohort.",
        "",
        "## 2. Baseline-defined task-quality sensitivity",
        "",
        "The sensitivity filter is baseline R2 > 0, defined only from the corresponding default model and never from AOM performance. We do not infer RPD from R2: the standard analytical definition is SD(y_test)/RMSEP and is regenerated separately from the response files.",
        "",
        "| Comparison | Scope/filter | N | Median ratio | 95% bootstrap CI | Wins | Raw Wilcoxon p |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for _, r in quality.iterrows():
        lines.append(
            f"| {r['comparison']} | {r['subset']} | {int(r['n'])} | {f(r.get('median_ratio'))} | {f(r.get('ci95_low'))}--{f(r.get('ci95_high'))} | {int(r.get('wins', 0))}/{int(r['n'])} | {p_fmt(r.get('wilcoxon_raw_two_sided_p'))} |"
        )
    lines += [
        "",
        "Minimal revision: add this as a sensitivity analysis, clearly labelled descriptive/raw-p unless incorporated into the manuscript's prespecified multiplicity family. Do not replace the full panel with an outcome-filtered panel.",
        "",
        "## 3. `ta_groupSampleID_stratDateVar_balRows`",
        "",
    ]
    for family in ("PLS", "Ridge"):
        d = ta_diag[family]
        lines.append(
            f"- {family}-HPO: mean RMSEP {f(d['mean_rmsep'])}, range {f(d['min_rmsep'])}--{f(d['max_rmsep'])}; mean total time {f(d['mean_total_time_s'], 1)} s; runtime rank {int(d['runtime_rank_desc'])}/{int(d['successful_task_count'])} (descending)."
        )
    pls_rows = ta_detail[ta_detail["family"].eq("PLS")]
    lines.append(
        "- PLS-HPO is the influential anomaly: seed RMSEP values are "
        + ", ".join(f"s{int(r.seed)}={r.rmsep:.3f} (R2={r.r2:.3f})" for r in pls_rows.itertuples())
        + ". Seeds 0 and 1 select EMSC2+ASLS and fail catastrophically on the external test despite ordinary inner-search scores."
    )
    lines += [
        "",
        "| Comparison | Sensitivity | N | Median ratio | Wins | Raw Wilcoxon p |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for _, r in ta_sens.iterrows():
        lines.append(
            f"| {r['comparison']} | {r['subset']} | {int(r['n'])} | {f(r.get('median_ratio'))} | {int(r.get('wins', 0))}/{int(r['n'])} | {p_fmt(r.get('wilcoxon_raw_two_sided_p'))} |"
        )
    lines += [
        "",
        "Minimal revision: retain the task in the primary analysis (avoid post-hoc deletion), disclose the seed-level instability, and add the leave-one-task-out row. If the HPO branch is rerun, diagnose the EMSC2+ASLS transform rather than silently replacing the archived result.",
        "",
        "## 4. SPORT / stacking+Ridge comparator reuse",
        "",
    ]
    for _, r in comparators.iterrows():
        lines.append(
            f"- **{r['target_comparator']}**: faithful={r['faithful_existing_implementation']}; reusable={r['reuse_decision']}; N={r['successful_dataset_count']}. {r['reason']}"
        )
    lines += [
        "- The archived generic OOF/Ridge stacking class may be reused only as engineering scaffolding. A faithful Huang-SPRR comparator still requires Ridge base learners trained separately on a declared preprocessing bank, leakage-safe OOF predictions, a Ridge meta-model, tuning rules, and new common-split benchmark results. SPORT likewise requires a new literature-faithful implementation and validation.",
        "- Minimal manuscript change now: keep the related-work distinction and state that no direct SPORT/SPRR comparison is available. Do not relabel or reuse the archived heterogeneous stacking results as either comparator.",
        "",
        "## Files",
        "",
        "- `hpo_task_audit.csv`: every regression task, execution order and HPO status.",
        "- `hpo_group_characteristics.csv`: attempted/not-attempted representativity summary.",
        "- `hpo_included_excluded_sensitivity.csv`: AOM/default sensitivity by coverage group.",
        "- `baseline_quality_sensitivity.csv`: baseline-defined R2 control.",
        "- `ta_groupsampleid_hpo_audit.csv` and `ta_leave_one_out_sensitivity.csv`: outlier evidence.",
        "- `comparator_reuse_audit.csv`: code/result inventory and reuse decision.",
        "- `input_sha256.csv`: exact hashes of every primary artifact consumed by the audit.",
    ]
    (HERE / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_input_hashes() -> None:
    paths = [COHORT_SOURCE, COHORT_MANIFEST, DEFAULT_RESULTS, AOMPLS_RESULTS, AOMRIDGE_RESULTS]
    for family in ("PLS", "Ridge"):
        paths.extend(HPO[family]["paths"])
        paths.append(HPO[family]["log"])
    rows = []
    for path in paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append({
            "path": str(path.relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "sha256": digest,
        })
    pd.DataFrame(rows).drop_duplicates("path").to_csv(HERE / "input_sha256.csv", index=False)


def main() -> None:
    inputs = build_inputs()
    assert len(inputs["strict"]) == 32, f"Expected strict N=32, got {len(inputs['strict'])}"
    _, group, characteristics, hpo_summary = audit_hpo_coverage(inputs)
    quality = audit_quality_thresholds(inputs)
    ta_detail, ta_sens, ta_diag = audit_ta(inputs)
    comparators = audit_comparators()
    make_report(inputs, hpo_summary, group, characteristics, quality, ta_detail, ta_sens, ta_diag, comparators)
    write_input_hashes()
    print(f"Wrote reviewer controls to {HERE}")


if __name__ == "__main__":
    main()
