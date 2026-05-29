"""Aggregate AOM-Ridge Blender / AutoSelect seed-stability evidence from the
archived workspaces under ``_archive/trashed_runs/AOM_v0_legacy/Ridge/``.

The headline ``all54_headline`` run is deterministic / random-state-0.  Two
auxiliary workspaces re-ran the Blender and AutoSelector selectors with seeds
0, 1 and 2 on a partial cohort:

- ``da001_audit20_seeds012`` — 20 datasets, 9 ridge/PLS variants per seed.
- ``da001_partial_fast12_seeds012`` — 12 datasets, similar coverage.

This script:

* unions the two archived CSVs and dedupes by ``(dataset, variant, seed)``;
* restricts the result to the strict N_cap=32 main-text denominator;
* computes per-(dataset, variant) min/max RMSEP across seeds 0/1/2 and the
  per-variant maximum span, plus winner-change counts;
* writes ``ridge_seed_audit.md`` (human-readable) and
  ``../tables/table_ridge_seed_audit.tex`` (the supplement-ready summary).

The output is intentionally narrow.  The full aggregation pipeline in
``aggregate_stats.py`` is left untouched; this script is a focused
addendum that backs the "empirical determinism" paragraph in the supplement.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DIR = REPO_ROOT / "paper" / "review"
TABLES_DIR = REPO_ROOT / "paper" / "tables"

ARCHIVE_RIDGE = (
    REPO_ROOT / "_archive" / "trashed_runs" / "AOM_v0_legacy" / "Ridge" / "benchmark_runs"
)
AUDIT_WORKSPACES = {
    "da001_audit20_seeds012": ARCHIVE_RIDGE / "da001_audit20_seeds012" / "results.csv",
    "da001_partial_fast12_seeds012": ARCHIVE_RIDGE / "da001_partial_fast12_seeds012" / "results.csv",
}

# Strict main-text denominator (N_cap = 32) — frozen from
# `missing_datasets_per_variant.md`.
N_CAP_DATASETS: list[str] = [
    "ALPINE_P_291_KS",
    "An_spxyG70_30_byCultivar_ASD",
    "An_spxyG70_30_byCultivar_MicroNIR",
    "An_spxyG70_30_byCultivar_MicroNIR_NeoSpectra",
    "An_spxyG70_30_byCultivar_NeoSpectra",
    "Beef_Marbling_RandomSplit",
    "Beer_OriginalExtract_60_KS",
    "Beer_OriginalExtract_60_YbaseSplit",
    "Biscuit_Fat_40_RandomSplit",
    "Biscuit_Sucrose_40_RandomSplit",
    "C_woOutlier",
    "Ccar_spxyG_block2deg",
    "Corn_Oil_80_ZhengChenPelegYbaseSplit",
    "Corn_Starch_80_ZhengChenPelegYbaseSplit",
    "DIESEL_bp50_246_b-a",
    "DIESEL_bp50_246_hla-b",
    "DIESEL_bp50_246_hlb-a",
    "Fv_Fm_grp70_30",
    "LMA_spxyG70_30_byCultivar_ASD",
    "N_wOutlier",
    "N_woOutlier",
    "Rd25_CBtestSite",
    "Rd25_GTtestSite",
    "Rd25_XSBNtestSite",
    "Rd25_spxy70",
    "Rice_Amylose_313_YbasedSplit",
    "TIC_spxy70",
    "WUEinst_spxyG70_30_byCultivar_MicroNIR_NeoSpectra",
    "brix_groupSampleID_stratDateVar_balRows",
    "grapevine_chloride_556_KS",
    "ph_groupSampleID_stratDateVar_balRows",
    "ta_groupSampleID_stratDateVar_balRows",
]

VARIANTS_OF_INTEREST = [
    "AOMRidge-Blender-headline-spxy3",
    "AOMRidge-AutoSelect-headline-spxy3",
]


AGREEMENT_TOLERANCE = 1e-8


def load_archive() -> pd.DataFrame:
    """Concatenate the audit workspaces, dropping fit-error rows."""
    frames: list[pd.DataFrame] = []
    for name, path in AUDIT_WORKSPACES.items():
        if not path.exists():
            raise FileNotFoundError(f"missing archive workspace: {path}")
        df = pd.read_csv(path)
        df["workspace"] = name
        frames.append(df)
    combined = pd.concat(frames, ignore_index=True)
    ok = combined["status"].fillna("ok").str.lower() == "ok"
    return combined.loc[ok].copy()


def check_cross_workspace_agreement(df: pd.DataFrame) -> dict[str, float | int]:
    """Compare RMSEP for ``(dataset, variant, seed)`` triples present in both
    workspaces, restricted to the variants this audit actually reports.

    The "deterministic, should agree" assumption in the supplement is only
    safe if cross-workspace duplicates do actually agree.  This function
    converts that assumption into an explicit assertion and returns the count
    of overlapping triples and the maximum observed absolute difference so the
    audit trail can be inspected.  Scoping to ``VARIANTS_OF_INTEREST`` matters:
    the two workspaces also ran background variants (e.g. ASLS-AOM-compact-cv5)
    that legitimately differ across workspaces due to version skew, and those
    differences are not relevant to the Blender/AutoSelect seed-stability
    claim we report.
    """
    sub = df[df["canonical_name"].isin(VARIANTS_OF_INTEREST)]
    sub = sub[["dataset", "canonical_name", "seed", "rmsep", "workspace"]].dropna(subset=["rmsep"])
    grouped = (
        sub.groupby(["dataset", "canonical_name", "seed"])
        .agg(n=("workspace", "nunique"), rmsep_min=("rmsep", "min"), rmsep_max=("rmsep", "max"))
        .reset_index()
    )
    overlap = grouped[grouped["n"] > 1]
    if overlap.empty:
        return {"n_overlap_triples": 0, "max_abs_rmsep_diff": 0.0}
    diffs = (overlap["rmsep_max"] - overlap["rmsep_min"]).abs()
    max_diff = float(diffs.max())
    if max_diff > AGREEMENT_TOLERANCE:
        worst = overlap.loc[diffs.idxmax()]
        raise AssertionError(
            "cross-workspace disagreement above tolerance "
            f"{AGREEMENT_TOLERANCE}: max |Δrmsep|={max_diff:.3e} on "
            f"dataset={worst['dataset']!r}, variant={worst['canonical_name']!r}, "
            f"seed={worst['seed']!r}"
        )
    return {"n_overlap_triples": int(len(overlap)), "max_abs_rmsep_diff": max_diff}


def dedupe(df: pd.DataFrame) -> pd.DataFrame:
    """Drop overlapping ``(dataset, variant, seed)`` keys.

    Cross-workspace agreement is asserted by :func:`check_cross_workspace_agreement`
    before this is called, so any tiebreak here is on values that match within
    ``AGREEMENT_TOLERANCE``.  We keep the workspace-ordered first row.
    """
    sub = df[["dataset", "canonical_name", "seed", "rmsep", "fit_time_s", "workspace"]].copy()
    sub = sub.dropna(subset=["rmsep"])
    return sub.drop_duplicates(subset=["dataset", "canonical_name", "seed"], keep="first")


def per_dataset_seed_table(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot to one row per (dataset, variant) with columns rmsep_seed0/1/2."""
    sub = df[df["canonical_name"].isin(VARIANTS_OF_INTEREST)]
    seed_card = sub.groupby(["dataset", "canonical_name"])["seed"].agg(["nunique", "size"])
    assert (
        seed_card["nunique"] == seed_card["size"]
    ).all(), "duplicate (dataset, variant, seed) survived dedup"
    pivot = sub.pivot_table(
        index=["dataset", "canonical_name"],
        columns="seed",
        values="rmsep",
        aggfunc="first",
    ).reset_index()
    pivot.columns = [
        f"rmsep_seed{c}" if isinstance(c, (int, np.integer)) else c for c in pivot.columns
    ]
    return pivot


def per_variant_summary(pivot: pd.DataFrame, n_cap: set[str]) -> pd.DataFrame:
    """Per-variant summary on the N_cap overlap subset."""
    seed_cols = [c for c in pivot.columns if c.startswith("rmsep_seed")]
    sub = pivot[pivot["dataset"].isin(n_cap)].copy()
    sub["rmsep_min"] = sub[seed_cols].min(axis=1)
    sub["rmsep_max"] = sub[seed_cols].max(axis=1)
    sub["rmsep_span"] = sub["rmsep_max"] - sub["rmsep_min"]
    sub["rmsep_relative_span"] = sub["rmsep_span"] / sub["rmsep_min"].replace(0, np.nan)
    sub["complete_seeds"] = sub[seed_cols].notna().sum(axis=1)

    out_rows = []
    for variant, g in sub.groupby("canonical_name"):
        out_rows.append(
            {
                "variant": variant,
                "n_audit_datasets": int(len(g)),
                "n_full_seeds": int((g["complete_seeds"] == 3).sum()),
                "max_rmsep_span": float(np.nanmax(g["rmsep_span"].values)) if len(g) else float("nan"),
                "median_rmsep_span": float(np.nanmedian(g["rmsep_span"].values)) if len(g) else float("nan"),
                "max_relative_span": float(np.nanmax(g["rmsep_relative_span"].values)) if len(g) else float("nan"),
                "datasets_with_nonzero_span": int((g["rmsep_span"] > 0).sum()),
            }
        )
    return pd.DataFrame(out_rows)


def render_latex(summary: pd.DataFrame, n_audit_overlap: int) -> str:
    """Render the supplement-ready LaTeX snippet."""
    pretty = {
        "AOMRidge-Blender-headline-spxy3": "AOMRidge-Blender",
        "AOMRidge-AutoSelect-headline-spxy3": "AOMRidge-AutoSelect",
    }
    lines = [
        r"\begin{tabularx}{\linewidth}{Xrrrr}",
        r"\toprule",
        r"Variant & Audit datasets & Seeds 0/1/2 complete & Max RMSEP span across seeds & Datasets with non-zero span \\",
        r"\midrule",
    ]
    for _, r in summary.iterrows():
        label = pretty.get(r["variant"], r["variant"])
        span = f"{r['max_rmsep_span']:.2e}" if r["max_rmsep_span"] > 0 else "0"
        lines.append(
            f"{label.replace('_', r'\_').replace('-', r'-\allowbreak{}')} & "
            f"{int(r['n_audit_datasets'])} & "
            f"{int(r['n_full_seeds'])} & "
            f"{span} & "
            f"{int(r['datasets_with_nonzero_span'])} \\\\"
        )
    lines += [
        r"\bottomrule",
        r"\end{tabularx}",
    ]
    return "\n".join(lines) + "\n"


def render_markdown(
    summary: pd.DataFrame,
    pivot: pd.DataFrame,
    n_audit_overlap: int,
    n_audit_total: int,
    n_cap_total: int,
    agreement: dict[str, float | int],
) -> str:
    """Render the human-readable companion report."""
    pretty = {
        "AOMRidge-Blender-headline-spxy3": "AOMRidge-Blender",
        "AOMRidge-AutoSelect-headline-spxy3": "AOMRidge-AutoSelect",
    }
    lines = [
        "# AOM-Ridge headline seed audit",
        "",
        f"Source workspaces: `{', '.join(AUDIT_WORKSPACES)}`.",
        f"Audit datasets (union): {n_audit_total}.  "
        f"N_cap (main text): {n_cap_total}.  "
        f"Overlap used for the summary: {n_audit_overlap}.",
        "",
        f"Cross-workspace agreement on duplicated (dataset, variant, seed) "
        f"triples: {agreement['n_overlap_triples']} triples checked, "
        f"max |Δrmsep| = {agreement['max_abs_rmsep_diff']:.3e} "
        f"(tolerance {AGREEMENT_TOLERANCE:.0e}).",
        "",
        "## Per-variant summary on the audit-overlap subset",
        "",
        "| Variant | Audit datasets | Seeds 0/1/2 complete | Max RMSEP span | Median RMSEP span | Datasets with non-zero span |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _, r in summary.iterrows():
        label = pretty.get(r["variant"], r["variant"])
        span_max = f"{r['max_rmsep_span']:.3e}" if r["max_rmsep_span"] > 0 else "0"
        span_med = f"{r['median_rmsep_span']:.3e}" if r["median_rmsep_span"] > 0 else "0"
        lines.append(
            f"| {label} | {int(r['n_audit_datasets'])} | "
            f"{int(r['n_full_seeds'])} | {span_max} | {span_med} | "
            f"{int(r['datasets_with_nonzero_span'])} |"
        )

    lines += [
        "",
        "## Per-dataset values on the audit-overlap subset",
        "",
        "RMSEP at seeds 0 / 1 / 2 for the two headline variants on the datasets where the audit "
        "workspaces overlap with N_cap.",
        "",
        "| Dataset | Variant | seed 0 | seed 1 | seed 2 |",
        "|---|---|---:|---:|---:|",
    ]
    pivot_in = pivot[pivot["dataset"].isin(N_CAP_DATASETS)].copy()
    pivot_in = pivot_in.sort_values(["dataset", "canonical_name"])
    seed_cols = [c for c in pivot_in.columns if c.startswith("rmsep_seed")]
    assert seed_cols == ["rmsep_seed0", "rmsep_seed1", "rmsep_seed2"], (
        f"unexpected seed columns: {seed_cols}"
    )
    for _, r in pivot_in.iterrows():
        cells = [
            "---" if pd.isna(r[c]) else f"{r[c]:.6g}" for c in seed_cols
        ]
        label = pretty.get(r["canonical_name"], r["canonical_name"])
        lines.append(
            f"| {r['dataset']} | {label} | {cells[0]} | {cells[1]} | {cells[2]} |"
        )

    return "\n".join(lines) + "\n"


def main() -> None:
    df = load_archive()
    agreement = check_cross_workspace_agreement(df)
    df = dedupe(df)
    pivot = per_dataset_seed_table(df)
    n_audit_total = pivot["dataset"].nunique()
    overlap_datasets = sorted(set(pivot["dataset"]) & set(N_CAP_DATASETS))
    summary = per_variant_summary(pivot, set(overlap_datasets))

    md = render_markdown(
        summary=summary,
        pivot=pivot,
        n_audit_overlap=len(overlap_datasets),
        n_audit_total=n_audit_total,
        n_cap_total=len(N_CAP_DATASETS),
        agreement=agreement,
    )
    tex = render_latex(summary=summary, n_audit_overlap=len(overlap_datasets))

    md_path = REVIEW_DIR / "ridge_seed_audit.md"
    tex_path = TABLES_DIR / "table_ridge_seed_audit.tex"
    md_path.write_text(md)
    tex_path.write_text(tex)

    report = {
        "cross_workspace_agreement": agreement,
        "n_audit_total_datasets": n_audit_total,
        "n_cap_total": len(N_CAP_DATASETS),
        "n_overlap": len(overlap_datasets),
        "overlap_datasets": overlap_datasets,
        "per_variant": summary.to_dict(orient="records"),
    }
    print(json.dumps(report, indent=2, default=float))


if __name__ == "__main__":
    main()
