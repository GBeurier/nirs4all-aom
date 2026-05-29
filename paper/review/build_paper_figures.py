#!/usr/bin/env python3
"""Build v3 AOM paper tables and figures.

This companion builder keeps the legacy aggregation script intact and adds the
evidence sources needed for the complete manuscript: FastAOM, the cartesian
PLS/Ridge HPO baselines, and the new exploration heatmaps.
"""

from __future__ import annotations

import contextlib
import glob as _glob
import json
import math
import os
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-paper-aom")

import matplotlib
import matplotlib.font_manager as _fm
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
from scipy import stats

import paper_data

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / "paper" / "review"
TABLES = ROOT / "paper" / "tables"
FIGURES = ROOT / "paper" / "figures"


# ---------------------------------------------------------------------------
# Unified paper theme
#
# Typography: Latin Modern Roman (matches the manuscript's lmodern package).
# Falls back to cmr10 / DejaVu Serif if not installed. mathtext uses cm.
# Palette: Okabe-Ito 8-color colour-blind-safe palette, mapped to model
# families. Heatmaps use viridis (sequential, operator counts) and RdBu_r
# (diverging, centered on 1.0 for ratio plots).
# Widths: single-column ~3.4", full-width ~6.8". All saves are vector PDF +
# 300 dpi PNG with bbox_inches="tight".
# ---------------------------------------------------------------------------

# Okabe-Ito palette (https://jfly.uni-koeln.de/color/) — 8 colour-blind-safe hues
PALETTE = {
    "blue":           "#0072B2",
    "vermillion":     "#D55E00",
    "bluish_green":   "#009E73",
    "yellow":         "#E69F00",
    "sky_blue":       "#56B4E9",
    "reddish_purple": "#CC79A7",
    "grey":           "#7F7F7F",
    "black":          "#111111",
}

# Family -> palette role. Same mapping is used by aggregate_stats.py.
FAMILY_COLORS = {
    "PLS":       PALETTE["blue"],          # dominant
    "Ridge":     PALETTE["bluish_green"],
    "AOM-PLS":   PALETTE["vermillion"],    # accent
    "AOM-Ridge": PALETTE["yellow"],
    "FastAOM":   PALETTE["reddish_purple"],
    "TabPFN":    PALETTE["sky_blue"],
    "Other":     PALETTE["grey"],
}

PAPER_VARIANTS = [
    ("pls-default-cv5", "PLS-default", "PLS", "default"),
    ("pls-tabpfn-hpo-25trials", "PLS-HPO", "PLS", "hpo"),
    ("AOM-compact-cv5-numpy", "AOM-PLS (simple)", "AOM-PLS", "simple"),
    ("ASLS-AOM-compact-cv5-numpy", "AOM-PLS (best)", "AOM-PLS", "best"),
    ("ridge-default-cv5", "Ridge-default", "Ridge", "default"),
    ("ridge-tabpfn-hpo-60trials", "Ridge-HPO", "Ridge", "hpo"),
    ("AOMRidge-global-compact-none", "AOM-Ridge (simple)", "AOM-Ridge", "simple"),
    ("AOMRidge-Blender-headline-spxy3", "AOM-Ridge (best)", "AOM-Ridge", "best"),
]

PAPER_LABEL_BY_KEY = {key.lower(): label for key, label, _, _ in PAPER_VARIANTS}
PAPER_FAMILY_BY_LABEL = {label: family for _, label, family, _ in PAPER_VARIANTS}
PAPER_ROLE_BY_LABEL = {label: role for _, label, _, role in PAPER_VARIANTS}

COMPARISON_DISPLAY = {
    "AOM-compact-cv5 vs PLS-default": "AOM-PLS (simple) vs PLS-default",
    "ASLS-AOM-compact-cv5 vs PLS-default": "AOM-PLS (best) vs PLS-default",
    "AOM-compact-cv5 vs PLS-TabPFN-HPO": "AOM-PLS (simple) vs PLS-HPO",
    "ASLS-AOM-compact-cv5 vs PLS-TabPFN-HPO": "AOM-PLS (best) vs PLS-HPO",
    "PLS-TabPFN-HPO vs PLS-default": "PLS-HPO vs PLS-default",
    "Ridge-TabPFN-HPO vs Ridge-default": "Ridge-HPO vs Ridge-default",
    "AOMRidge-global-compact-none vs Ridge-default": "AOM-Ridge (simple) vs Ridge-default",
    "AOMRidge-Blender vs Ridge-default": "AOM-Ridge (best) vs Ridge-default",
    "AOMRidge-global-compact-none vs Ridge-TabPFN-HPO": "AOM-Ridge (simple) vs Ridge-HPO",
    "AOMRidge-Blender vs Ridge-TabPFN-HPO": "AOM-Ridge (best) vs Ridge-HPO",
}

# Sizing guidance (inches). Single column for manuscript, full width for spread.
FIGSIZE_SINGLE = (3.4, 2.6)
FIGSIZE_WIDE = (6.8, 3.8)
FIGSIZE_HEATMAP = (7.0, 8.4)

# Neutral structural colours.
COLOR_AXIS = "#222222"
COLOR_GRID = "#cfcfcf"
COLOR_REFERENCE = "#555555"


def _register_latin_modern() -> None:
    """Make Latin Modern Roman available to matplotlib if installed."""
    for path in _glob.glob("/usr/share/texmf/fonts/opentype/public/lm/lmroman*.otf"):
        with contextlib.suppress(Exception):
            _fm.fontManager.addfont(path)


def apply_paper_theme() -> None:
    """Apply the unified manuscript theme to matplotlib rcParams.

    Call once before generating any figure. Idempotent.
    """
    _register_latin_modern()
    plt.rcParams.update({
        # Typography
        "font.family": "serif",
        "font.serif": ["Latin Modern Roman", "cmr10", "STIXGeneral", "DejaVu Serif"],
        "mathtext.fontset": "cm",
        "axes.unicode_minus": False,
        "font.size": 9.0,
        "axes.titlesize": 10.0,
        "axes.labelsize": 9.0,
        "xtick.labelsize": 8.0,
        "ytick.labelsize": 8.0,
        "legend.fontsize": 8.0,
        # Embed fonts as TrueType in PDF/PS so journal compliance checkers are happy
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        # Axes
        "axes.edgecolor": COLOR_AXIS,
        "axes.linewidth": 0.7,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titleweight": "regular",
        "axes.titlelocation": "left",
        "axes.titlepad": 6.0,
        "axes.labelpad": 3.5,
        "axes.facecolor": "white",
        "figure.facecolor": "white",
        # Ticks (outward, thin)
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.major.size": 3.0,
        "ytick.major.size": 3.0,
        "xtick.color": COLOR_AXIS,
        "ytick.color": COLOR_AXIS,
        # Grid (subtle, behind data)
        "axes.grid": False,  # opt-in per axis to avoid double-gridding heatmaps
        "grid.color": COLOR_GRID,
        "grid.linestyle": "-",
        "grid.linewidth": 0.5,
        "grid.alpha": 0.6,
        "axes.axisbelow": True,
        # Lines / markers
        "lines.linewidth": 1.2,
        "lines.markersize": 5.0,
        "patch.linewidth": 0.5,
        # Legend
        "legend.frameon": True,
        "legend.framealpha": 0.92,
        "legend.edgecolor": COLOR_GRID,
        "legend.fancybox": False,
        "legend.borderpad": 0.4,
        "legend.handlelength": 1.6,
        "legend.handletextpad": 0.6,
        # Saving
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.04,
        "figure.dpi": 110,
    })


def style_grid(ax, axis: str = "y") -> None:
    """Apply the unified subtle gridline style to a single axis (or 'both')."""
    ax.grid(True, axis=axis, color=COLOR_GRID, linestyle="-", linewidth=0.5, alpha=0.6, zorder=0)
    ax.set_axisbelow(True)

EXCLUDED_RATIO_DATASETS = {"QUARTZ_spxy70", "Quartz_spxy70"}
RNG = np.random.default_rng(20260517)

FAST_SUMMARY = ROOT / "benchmarks/runs/scenarios/paper_aom_fastaom_full60_seed0/headline_with_lucas_summary.csv"
FAST_WINNERS = ROOT / "benchmarks/runs/scenarios/paper_aom_fastaom_full60_seed0/headline_with_lucas_winners.csv"
FAST_WIDE = ROOT / "benchmarks/runs/scenarios/paper_aom_fastaom_full60_seed0/headline_with_lucas.csv"
FAST_LONG = ROOT / "benchmarks/runs/scenarios/paper_aom_fastaom_full60_seed0/merged_results_with_lucas.csv"

AOMPLS = ROOT / "benchmarks/runs/scenarios/paper_aom_aompls_seeds012/results.csv"
AOMRIDGE_PARTIAL = ROOT / "benchmarks/runs/ridge/paper_aom_aomridge_seeds012/results.csv"
AOMRIDGE_HEADLINE = ROOT / "benchmarks/runs/ridge/all54_headline/results.csv"
LINEAR_DEFAULT = ROOT / "benchmarks/runs/scenarios/paper_aom_linear_hpo_full_cartesian_default_cv5_all/results.csv"

PLS_HPO_GLOB = "benchmarks/runs/scenarios/paper_aom_linear_hpo_full_cartesian_pls-tabpfn-hpo-25trials_seed*/results.csv"
RIDGE_HPO_GLOB = "benchmarks/runs/scenarios/paper_aom_linear_hpo_full_cartesian_ridge-tabpfn-hpo-60trials_seed*/results.csv"

CLS_AOMPLS = ROOT / "benchmarks/runs/pls/paper_aom_aompls_da_seeds012/results.csv"
CLS_AOMRIDGE = ROOT / "benchmarks/runs/ridge/paper_aom_aomridge_cls_seeds012/results.csv"


def latex_escape(value: object) -> str:
    text = str(value)
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_\allowbreak{}",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
        "/": r"/\allowbreak{}",
        "-": r"-\allowbreak{}",
    }
    return "".join(repl.get(ch, ch) for ch in text)


def fmt_float(value: float, digits: int = 3) -> str:
    if value is None or not np.isfinite(value):
        return "n/a"
    return f"{value:.{digits}f}"


def fmt_p(value: float) -> str:
    if value is None or not np.isfinite(value):
        return "n/a"
    if value < 1e-3:
        return f"{value:.1e}"
    return f"{value:.3f}"


def dataset_id(series: pd.Series) -> pd.Series:
    return series.astype("string").str.split("/").str[-1].str.strip()


def ok_rows(df: pd.DataFrame) -> pd.DataFrame:
    if "status" not in df.columns:
        return df.copy()
    status = df["status"].astype("string").str.lower()
    return df[status.isna() | status.isin({"ok", "success", "completed", ""})].copy()


def load_aompls() -> pd.DataFrame:
    df = ok_rows(pd.read_csv(AOMPLS, low_memory=False))
    out = pd.DataFrame(
        {
            "dataset": dataset_id(df["dataset"]),
            "variant": df["result_label"].astype("string"),
            "seed": pd.to_numeric(df["seed"], errors="coerce"),
            "rmsep": pd.to_numeric(df["RMSEP"], errors="coerce"),
            "r2": pd.to_numeric(df.get("r2_test"), errors="coerce"),
            "fit_time_s": pd.to_numeric(df.get("fit_time_s"), errors="coerce"),
            "total_time_s": pd.to_numeric(df.get("fit_time_s"), errors="coerce")
            + pd.to_numeric(df.get("predict_time_s"), errors="coerce").fillna(0.0),
            "source": "AOM-PLS seeds012",
        }
    )
    return out


def load_hpo(glob_pattern: str) -> pd.DataFrame:
    paths = sorted(ROOT.glob(glob_pattern))
    frames = []
    for path in paths:
        raw = pd.read_csv(path, low_memory=False)
        raw = ok_rows(raw)
        frames.append(raw)
    if not frames:
        return pd.DataFrame(columns=["dataset", "variant", "seed", "rmsep", "fit_time_s", "total_time_s", "n_trials", "source"])
    df = pd.concat(frames, ignore_index=True)
    return pd.DataFrame(
        {
            "dataset": dataset_id(df["dataset"]),
            "variant": df["variant"].astype("string"),
            "seed": pd.to_numeric(df["seed"], errors="coerce"),
            "rmsep": pd.to_numeric(df["rmsep"], errors="coerce"),
            "r2": pd.to_numeric(df.get("r2"), errors="coerce"),
            "fit_time_s": pd.to_numeric(df.get("refit_time_s"), errors="coerce"),
            "total_time_s": pd.to_numeric(df.get("total_time_s"), errors="coerce"),
            "n_trials": pd.to_numeric(df.get("n_trials"), errors="coerce"),
            "source": "linear cartesian HPO",
        }
    )


def load_default_linear() -> pd.DataFrame:
    df = ok_rows(pd.read_csv(LINEAR_DEFAULT, low_memory=False))
    return pd.DataFrame(
        {
            "dataset": dataset_id(df["dataset"]),
            "variant": df["variant"].astype("string"),
            "seed": pd.to_numeric(df["seed"], errors="coerce"),
            "rmsep": pd.to_numeric(df["rmsep"], errors="coerce"),
            "r2": pd.to_numeric(df.get("r2"), errors="coerce"),
            "fit_time_s": pd.to_numeric(df.get("refit_time_s"), errors="coerce"),
            "total_time_s": pd.to_numeric(df.get("total_time_s"), errors="coerce"),
            "n_trials": pd.to_numeric(df.get("n_trials"), errors="coerce"),
            "source": "default CV5",
        }
    )


def load_aomridge(path: Path, source: str) -> pd.DataFrame:
    df = ok_rows(pd.read_csv(path, low_memory=False))
    seed_col = "random_state" if "random_state" in df.columns else "seed"
    return pd.DataFrame(
        {
            "dataset": dataset_id(df["dataset"]),
            "variant": df["variant"].astype("string"),
            "seed": pd.to_numeric(df.get(seed_col), errors="coerce"),
            "rmsep": pd.to_numeric(df["rmsep"], errors="coerce"),
            "r2": pd.to_numeric(df.get("r2"), errors="coerce"),
            "fit_time_s": pd.to_numeric(df.get("fit_time_s"), errors="coerce"),
            "total_time_s": pd.to_numeric(df.get("fit_time_s"), errors="coerce")
            + pd.to_numeric(df.get("predict_time_s"), errors="coerce").fillna(0.0),
            "source": source,
        }
    )


def per_dataset(df: pd.DataFrame, variant: str, metric: str = "rmsep") -> pd.Series:
    sub = df[df["variant"].astype("string").str.lower() == variant.lower()].copy()
    if sub.empty:
        return pd.Series(dtype=float, name=variant)
    return sub.groupby("dataset")[metric].mean().dropna().rename(variant)


def per_dataset_wide(wide: pd.DataFrame, variant: str) -> pd.Series:
    if variant not in wide.columns:
        return pd.Series(dtype=float, name=variant)
    sub = wide[["dataset", variant]].copy()
    sub["dataset"] = dataset_id(sub["dataset"])
    values = pd.to_numeric(sub[variant], errors="coerce")
    return pd.Series(values.to_numpy(), index=sub["dataset"], name=variant).dropna()


def bootstrap_ci(values: np.ndarray, fn=np.median, n_boot: int = 5000) -> tuple[float, float]:
    if values.size == 0:
        return float("nan"), float("nan")
    idx = RNG.integers(0, values.size, size=(n_boot, values.size))
    boot = fn(values[idx], axis=1)
    return float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))


def paired_stats(cand: pd.Series, ref: pd.Series, lower_is_better: bool = True) -> dict:
    common = cand.index.intersection(ref.index)
    rows = pd.DataFrame({"candidate": cand.loc[common], "reference": ref.loc[common]}).dropna()
    rows = rows[np.isfinite(rows["candidate"]) & np.isfinite(rows["reference"])]
    if lower_is_better:
        rows = rows[rows["reference"] > 0]
        effect = (rows["candidate"] / rows["reference"]).to_numpy(dtype=float)
        wins = int((rows["candidate"] < rows["reference"]).sum())
        losses = int((rows["candidate"] > rows["reference"]).sum())
        signal = (rows["candidate"] - rows["reference"]).to_numpy(dtype=float)
        alternative = "less"
    else:
        effect = (rows["candidate"] - rows["reference"]).to_numpy(dtype=float)
        wins = int((rows["candidate"] > rows["reference"]).sum())
        losses = int((rows["candidate"] < rows["reference"]).sum())
        signal = effect
        alternative = "greater"
    n = len(rows)
    ties = n - wins - losses
    if n == 0:
        return {
            "n": 0,
            "median": float("nan"),
            "ci_low": float("nan"),
            "ci_high": float("nan"),
            "wins": 0,
            "losses": 0,
            "ties": 0,
            "p": float("nan"),
            "paired": rows,
            "effect": effect,
        }
    ci_low, ci_high = bootstrap_ci(effect)
    try:
        if n >= 1 and np.any(signal != 0):
            p = float(stats.wilcoxon(signal, zero_method="wilcox", alternative=alternative).pvalue)
        else:
            p = float("nan")
    except ValueError:
        p = float("nan")
    return {
        "n": int(n),
        "median": float(np.median(effect)),
        "ci_low": ci_low,
        "ci_high": ci_high,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "p": p,
        "paired": rows,
        "effect": effect,
    }


def holm(pairs: list[dict]) -> None:
    indexed = [(i, row["stats"]["p"]) for i, row in enumerate(pairs) if np.isfinite(row["stats"]["p"])]
    indexed.sort(key=lambda item: item[1])
    m = len(indexed)
    running = 0.0
    adjusted = {}
    for rank, (idx, p) in enumerate(indexed):
        val = min(1.0, (m - rank) * p)
        running = max(running, val)
        adjusted[idx] = running
    for i, row in enumerate(pairs):
        row["p_holm"] = adjusted.get(i, float("nan"))


def stat_row(label: str, candidate: str, reference: str, cand: pd.Series, ref: pd.Series, source: str) -> dict:
    s = paired_stats(cand, ref, lower_is_better=True)
    return {
        "label": label,
        "candidate": candidate,
        "reference": reference,
        "source": source,
        "stats": s,
        "p_holm": float("nan"),
    }


def build_regression_stats() -> tuple[list[dict], dict[str, pd.DataFrame]]:
    aompls = load_aompls()
    default = load_default_linear()
    pls_hpo = load_hpo(PLS_HPO_GLOB)
    ridge_hpo = load_hpo(RIDGE_HPO_GLOB)
    ridge_partial = load_aomridge(AOMRIDGE_PARTIAL, "AOM-Ridge top5 seeds012")
    ridge_head = load_aomridge(AOMRIDGE_HEADLINE, "AOM-Ridge headline seed0")
    wide = pd.read_csv(FAST_WIDE, low_memory=False)
    strict_datasets = paper_data.strict_intersection()
    keep = set(strict_datasets)

    aompls = paper_data.filter_to_datasets(aompls, keep)
    default = paper_data.filter_to_datasets(default, keep)
    pls_hpo = paper_data.filter_to_datasets(pls_hpo, keep)
    ridge_hpo = paper_data.filter_to_datasets(ridge_hpo, keep)
    ridge_partial = paper_data.filter_to_datasets(ridge_partial, keep)
    ridge_head = paper_data.filter_to_datasets(ridge_head, keep)
    wide = paper_data.filter_to_datasets(wide, keep)

    rows: list[dict] = []
    rows.extend(
        [
            stat_row(
                "ASLS-AOM-compact-cv5 vs PLS-standard",
                "ASLS-AOM-compact-cv5-numpy",
                "PLS-standard-numpy",
                per_dataset(aompls, "ASLS-AOM-compact-cv5-numpy"),
                per_dataset(aompls, "PLS-standard-numpy"),
                "AOM-PLS seeds012",
            ),
            stat_row(
                "AOM-compact-cv5 vs PLS-standard",
                "AOM-compact-cv5-numpy",
                "PLS-standard-numpy",
                per_dataset(aompls, "AOM-compact-cv5-numpy"),
                per_dataset(aompls, "PLS-standard-numpy"),
                "AOM-PLS seeds012",
            ),
            stat_row(
                "AOM-default-nipals-adjoint vs PLS-standard",
                "AOM-default-nipals-adjoint-numpy",
                "PLS-standard-numpy",
                per_dataset(aompls, "AOM-default-nipals-adjoint-numpy"),
                per_dataset(aompls, "PLS-standard-numpy"),
                "AOM-PLS seeds012",
            ),
            stat_row(
                "ASLS-AOM-compact-cv5 vs PLS-default",
                "ASLS-AOM-compact-cv5-numpy",
                "pls-default-cv5",
                per_dataset(aompls, "ASLS-AOM-compact-cv5-numpy"),
                per_dataset(default, "pls-default-cv5"),
                "AOM-PLS seeds012 / default-CV all",
            ),
            stat_row(
                "AOM-compact-cv5 vs PLS-default",
                "AOM-compact-cv5-numpy",
                "pls-default-cv5",
                per_dataset(aompls, "AOM-compact-cv5-numpy"),
                per_dataset(default, "pls-default-cv5"),
                "AOM-PLS seeds012 / default-CV all",
            ),
            stat_row(
                "AOM-default-nipals-adjoint vs PLS-default",
                "AOM-default-nipals-adjoint-numpy",
                "pls-default-cv5",
                per_dataset(aompls, "AOM-default-nipals-adjoint-numpy"),
                per_dataset(default, "pls-default-cv5"),
                "AOM-PLS seeds012 / default-CV all",
            ),
            stat_row(
                "ASLS-AOM-compact-cv5 vs PLS-TabPFN-HPO",
                "ASLS-AOM-compact-cv5-numpy",
                "pls-tabpfn-hpo-25trials",
                per_dataset(aompls, "ASLS-AOM-compact-cv5-numpy"),
                per_dataset(pls_hpo, "pls-tabpfn-hpo-25trials"),
                "AOM-PLS seeds012 / cartesian HPO seeds012",
            ),
            stat_row(
                "AOM-compact-cv5 vs PLS-TabPFN-HPO",
                "AOM-compact-cv5-numpy",
                "pls-tabpfn-hpo-25trials",
                per_dataset(aompls, "AOM-compact-cv5-numpy"),
                per_dataset(pls_hpo, "pls-tabpfn-hpo-25trials"),
                "AOM-PLS seeds012 / cartesian HPO seeds012",
            ),
            stat_row(
                "PLS-TabPFN-HPO vs PLS-default",
                "pls-tabpfn-hpo-25trials",
                "pls-default-cv5",
                per_dataset(pls_hpo, "pls-tabpfn-hpo-25trials"),
                per_dataset(default, "pls-default-cv5"),
                "cartesian HPO seeds012 / default-CV all",
            ),
            stat_row(
                "Ridge-TabPFN-HPO vs Ridge-default",
                "ridge-tabpfn-hpo-60trials",
                "ridge-default-cv5",
                per_dataset(ridge_hpo, "ridge-tabpfn-hpo-60trials"),
                per_dataset(default, "ridge-default-cv5"),
                "cartesian HPO seeds012 / default-CV all",
            ),
            stat_row(
                "AOMRidge-Blender vs Ridge-default",
                "AOMRidge-Blender-headline-spxy3",
                "ridge-default-cv5",
                per_dataset(ridge_head, "AOMRidge-Blender-headline-spxy3"),
                per_dataset(default, "ridge-default-cv5"),
                "AOM-Ridge headline / default-CV all",
            ),
            stat_row(
                "AOMRidge-global-compact-none vs Ridge-default",
                "AOMRidge-global-compact-none",
                "ridge-default-cv5",
                per_dataset(ridge_head, "AOMRidge-global-compact-none"),
                per_dataset(default, "ridge-default-cv5"),
                "AOM-Ridge headline / default-CV all",
            ),
            stat_row(
                "AOMRidge-Blender vs Ridge-TabPFN-HPO",
                "AOMRidge-Blender-headline-spxy3",
                "ridge-tabpfn-hpo-60trials",
                per_dataset(ridge_head, "AOMRidge-Blender-headline-spxy3"),
                per_dataset(ridge_hpo, "ridge-tabpfn-hpo-60trials"),
                "AOM-Ridge headline / cartesian HPO seeds012",
            ),
            stat_row(
                "AOMRidge-AutoSelect vs Ridge-TabPFN-HPO",
                "AOMRidge-AutoSelect-headline-spxy3",
                "ridge-tabpfn-hpo-60trials",
                per_dataset(ridge_head, "AOMRidge-AutoSelect-headline-spxy3"),
                per_dataset(ridge_hpo, "ridge-tabpfn-hpo-60trials"),
                "AOM-Ridge headline / cartesian HPO seeds012",
            ),
            stat_row(
                "AOMRidge-global-compact-none vs Ridge-TabPFN-HPO",
                "AOMRidge-global-compact-none",
                "ridge-tabpfn-hpo-60trials",
                per_dataset(ridge_head, "AOMRidge-global-compact-none"),
                per_dataset(ridge_hpo, "ridge-tabpfn-hpo-60trials"),
                "AOM-Ridge headline / cartesian HPO seeds012",
            ),
            stat_row(
                "AOMRidge-Local-knn50 vs Ridge-TabPFN-HPO",
                "AOMRidge-Local-compact-knn50",
                "ridge-tabpfn-hpo-60trials",
                per_dataset(ridge_partial, "AOMRidge-Local-compact-knn50"),
                per_dataset(ridge_hpo, "ridge-tabpfn-hpo-60trials"),
                "AOM-Ridge top5 seeds012 / cartesian HPO seeds012",
            ),
            stat_row(
                "FastAOM-sparse-mkr-supervised vs PLS-standard",
                "FastAOM-sparse-mkr-supervised",
                "PLS-standard-numpy",
                per_dataset_wide(wide, "FastAOM-sparse-mkr-supervised"),
                per_dataset_wide(wide, "PLS-standard-numpy"),
                "FastAOM full60 seed0 wide table",
            ),
            stat_row(
                "FastAOM-sparse-mkr-compact vs PLS-standard",
                "FastAOM-sparse-mkr-compact",
                "PLS-standard-numpy",
                per_dataset_wide(wide, "FastAOM-sparse-mkr-compact"),
                per_dataset_wide(wide, "PLS-standard-numpy"),
                "FastAOM full60 seed0 wide table",
            ),
            stat_row(
                "FastAOM-single-chain-compact vs PLS-standard",
                "FastAOM-single-chain-compact",
                "PLS-standard-numpy",
                per_dataset_wide(wide, "FastAOM-single-chain-compact"),
                per_dataset_wide(wide, "PLS-standard-numpy"),
                "FastAOM full60 seed0 wide table",
            ),
            stat_row(
                "FastAOM-sparse-mkr-supervised vs PLS-TabPFN-HPO",
                "FastAOM-sparse-mkr-supervised",
                "pls-tabpfn-hpo-25trials",
                per_dataset_wide(wide, "FastAOM-sparse-mkr-supervised"),
                per_dataset(pls_hpo, "pls-tabpfn-hpo-25trials"),
                "FastAOM full60 seed0 / cartesian HPO seeds012",
            ),
            stat_row(
                "FastAOM-sparse-mkr-compact vs PLS-TabPFN-HPO",
                "FastAOM-sparse-mkr-compact",
                "pls-tabpfn-hpo-25trials",
                per_dataset_wide(wide, "FastAOM-sparse-mkr-compact"),
                per_dataset(pls_hpo, "pls-tabpfn-hpo-25trials"),
                "FastAOM full60 seed0 / cartesian HPO seeds012",
            ),
            stat_row(
                "FastAOM-single-chain-compact vs PLS-TabPFN-HPO",
                "FastAOM-single-chain-compact",
                "pls-tabpfn-hpo-25trials",
                per_dataset_wide(wide, "FastAOM-single-chain-compact"),
                per_dataset(pls_hpo, "pls-tabpfn-hpo-25trials"),
                "FastAOM full60 seed0 / cartesian HPO seeds012",
            ),
            stat_row(
                "FastAOM-sparse-mkr-supervised vs ASLS-AOM-compact-cv5",
                "FastAOM-sparse-mkr-supervised",
                "ASLS-AOM-compact-cv5-numpy",
                per_dataset_wide(wide, "FastAOM-sparse-mkr-supervised"),
                per_dataset_wide(wide, "ASLS-AOM-compact-cv5-numpy"),
                "FastAOM full60 seed0 wide table",
            ),
        ]
    )
    holm(rows)
    return rows, {
        "aompls": aompls,
        "default": default,
        "pls_hpo": pls_hpo,
        "ridge_hpo": ridge_hpo,
        "ridge_head": ridge_head,
        "ridge_partial": ridge_partial,
        "wide": wide,
        "strict_datasets": pd.DataFrame({"dataset": strict_datasets}),
    }


def write_table_main(rows: list[dict]) -> None:
    keep = [
        "AOM-compact-cv5 vs PLS-default",
        "ASLS-AOM-compact-cv5 vs PLS-default",
        "AOM-compact-cv5 vs PLS-TabPFN-HPO",
        "ASLS-AOM-compact-cv5 vs PLS-TabPFN-HPO",
        "PLS-TabPFN-HPO vs PLS-default",
        "Ridge-TabPFN-HPO vs Ridge-default",
        "AOMRidge-global-compact-none vs Ridge-default",
        "AOMRidge-Blender vs Ridge-default",
        "AOMRidge-global-compact-none vs Ridge-TabPFN-HPO",
        "AOMRidge-Blender vs Ridge-TabPFN-HPO",
    ]
    by_label = {r["label"]: r for r in rows}
    lines = [
        r"\begin{tabularx}{\linewidth}{p{0.31\linewidth}Xrr}",
        r"\toprule",
        r"Comparison & Evidence source & $N$ & Median RMSEP ratio / wins; $p_{\mathrm{Holm}}$ \\",
        r"\midrule",
    ]
    for label in keep:
        r = by_label[label]
        s = r["stats"]
        display = COMPARISON_DISPLAY.get(label, label)
        lines.append(
            f"{latex_escape(display)} & {latex_escape(r['source'])} & {s['n']} & "
            f"{fmt_float(s['median'])}; {s['wins']}/{s['n']}; {fmt_p(r['p_holm'])} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabularx}", ""]
    (TABLES / "table_main_results.tex").write_text("\n".join(lines))


def write_table_paired(rows: list[dict]) -> None:
    keep = [
        "ASLS-AOM-compact-cv5 vs PLS-standard",
        "AOM-compact-cv5 vs PLS-standard",
        "AOM-default-nipals-adjoint vs PLS-standard",
        "ASLS-AOM-compact-cv5 vs PLS-default",
        "AOM-compact-cv5 vs PLS-default",
        "AOM-default-nipals-adjoint vs PLS-default",
        "ASLS-AOM-compact-cv5 vs PLS-TabPFN-HPO",
        "AOM-compact-cv5 vs PLS-TabPFN-HPO",
        "PLS-TabPFN-HPO vs PLS-default",
        "Ridge-TabPFN-HPO vs Ridge-default",
        "AOMRidge-global-compact-none vs Ridge-default",
        "AOMRidge-Blender vs Ridge-default",
        "AOMRidge-Blender vs Ridge-TabPFN-HPO",
        "AOMRidge-AutoSelect vs Ridge-TabPFN-HPO",
        "AOMRidge-global-compact-none vs Ridge-TabPFN-HPO",
        "AOMRidge-Local-knn50 vs Ridge-TabPFN-HPO",
        "FastAOM-sparse-mkr-supervised vs PLS-standard",
        "FastAOM-sparse-mkr-compact vs PLS-standard",
        "FastAOM-single-chain-compact vs PLS-standard",
        "FastAOM-sparse-mkr-supervised vs PLS-TabPFN-HPO",
        "FastAOM-sparse-mkr-compact vs PLS-TabPFN-HPO",
        "FastAOM-single-chain-compact vs PLS-TabPFN-HPO",
        "FastAOM-sparse-mkr-supervised vs ASLS-AOM-compact-cv5",
    ]
    by_label = {r["label"]: r for r in rows}
    lines = [
        r"\begin{tabularx}{\linewidth}{Xrrrr}",
        r"\toprule",
        r"Comparison & $N$ & Median ratio & 95\% CI & Wins; $p_{\mathrm{Holm}}$ \\",
        r"\midrule",
    ]
    for label in keep:
        r = by_label[label]
        s = r["stats"]
        lines.append(
            f"{latex_escape(label)} & {s['n']} & {fmt_float(s['median'])} & "
            f"{fmt_float(s['ci_low'])}--{fmt_float(s['ci_high'])} & "
            f"{s['wins']}/{s['n']}; {fmt_p(r['p_holm'])} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabularx}", ""]
    (TABLES / "table_paired_stats.tex").write_text("\n".join(lines))


def write_time_table(dfs: dict[str, pd.DataFrame]) -> None:
    rows = []

    def add_from_df(label: str, df: pd.DataFrame, variant: str, evals: str) -> None:
        sub = df[df["variant"].astype("string").str.lower() == variant.lower()]
        total = sub["total_time_s"].dropna()
        fit = sub["fit_time_s"].dropna()
        rows.append(
            {
                "label": label,
                "datasets": sub["dataset"].nunique(),
                "runs": len(sub),
                "evals": evals,
                "median_fit": float(fit.median()) if not fit.empty else float("nan"),
                "median_total": float(total.median()) if not total.empty else float("nan"),
                "total_h": float(total.sum() / 3600.0) if not total.empty else float("nan"),
            }
        )

    add_from_df("PLS-default", dfs["default"], "pls-default-cv5", "25 component trials")
    add_from_df("PLS-HPO", dfs["pls_hpo"], "pls-tabpfn-hpo-25trials", "600 x 5 trials")
    add_from_df("AOM-PLS (simple)", dfs["aompls"], "AOM-compact-cv5-numpy", "9 operators x CV-5")
    add_from_df("AOM-PLS (best)", dfs["aompls"], "ASLS-AOM-compact-cv5-numpy", "ASLS branch + 9 operators x CV-5")
    add_from_df("Ridge-default", dfs["default"], "ridge-default-cv5", "15 alpha trials")
    add_from_df("Ridge-HPO", dfs["ridge_hpo"], "ridge-tabpfn-hpo-60trials", "600 x 10 trials")
    add_from_df("AOM-Ridge (simple)", dfs["ridge_head"], "AOMRidge-global-compact-none", "9 operators x 50 alpha cells")
    add_from_df("AOM-Ridge (best)", dfs["ridge_head"], "AOMRidge-Blender-headline-spxy3", "AOM-Ridge Blender: 8 candidates x 3 outer folds + 8 refits")

    lines = [
        r"\begin{tabularx}{\linewidth}{p{0.30\linewidth}rXrr}",
        r"\toprule",
        r"Method & Datasets & Search budget & Median fit (s) & Median total (s) \\",
        r"\midrule",
    ]
    for r in rows:
        budget = r["evals"]
        if np.isfinite(r["total_h"]):
            budget = f"{budget}; observed {r['total_h']:.1f} h"
        lines.append(
            f"{latex_escape(r['label'])} & {r['datasets']} & {latex_escape(budget)} & "
            f"{fmt_float(r['median_fit'], 2)} & {fmt_float(r['median_total'], 2)} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabularx}", ""]
    (TABLES / "table_time_budget.tex").write_text("\n".join(lines))


def write_fast_table() -> None:
    summary = pd.read_csv(FAST_SUMMARY)
    winners = pd.read_csv(FAST_WINNERS).set_index("model")["count"].to_dict()
    keep = [m for m in summary["model"] if str(m).startswith("FastAOM")]
    keep += ["ASLS-AOM-compact-cv5-numpy", "AOM-compact-cv5-numpy", "PLS-standard-numpy", "nirs4all-AOM-PLS-default"]
    rows = summary[summary["model"].isin(keep)].copy()
    rows["winner_count"] = rows["model"].map(winners).fillna(0).astype(int)
    rows = rows.sort_values(["median_rel_rmse", "model"])

    def family(model: str) -> str:
        if "sparse-mkr" in model:
            return "Sparse MKR"
        if "single-chain" in model:
            return "Single chain"
        if "hard-chain" in model:
            return "Hard chain"
        if "soft-chain" in model:
            return "Soft chain"
        return "Reference"

    lines = [
        r"\begin{tabularx}{\linewidth}{p{0.38\linewidth}lrrrr}",
        r"\toprule",
        r"Variant & Family & $N$ & Median rel. RMSEP & Median fit (s) & Wins \\",
        r"\midrule",
    ]
    for _, r in rows.iterrows():
        lines.append(
            f"{latex_escape(r['model'])} & {latex_escape(family(r['model']))} & {int(r['n_datasets'])} & "
            f"{float(r['median_rel_rmse']):.3f} & {float(r['median_fit_time']):.2f} & "
            f"{int(r['winner_count'])} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabularx}", ""]
    (TABLES / "table_fastaom_variants.tex").write_text("\n".join(lines))


def write_long_results() -> None:
    wide = pd.read_csv(FAST_WIDE, low_memory=False)
    wide = paper_data.filter_to_datasets(wide, paper_data.strict_intersection())
    keep = [
        "PLS-standard-numpy",
        "AOM-compact-cv5-numpy",
        "ASLS-AOM-compact-cv5-numpy",
        "AOM-default-nipals-adjoint-numpy",
        "nirs4all-AOM-PLS-default",
        "FastAOM-sparse-mkr-supervised",
        "FastAOM-sparse-mkr-compact",
        "FastAOM-single-chain-compact",
        "FastAOM-soft-chain-compact",
        "FastAOM-hard-chain-compact",
        "FastAOM-hard-chain-osc",
        "FastAOM-hard-chain-asls",
        "FastAOM-hard-chain-multibase",
        "FastAOM-hard-chain-supervised",
        "POP-nipals-adjoint-numpy",
        "nirs4all-POP-PLS-default",
    ]
    rows = []
    for _, r in wide.sort_values("dataset").iterrows():
        pls = pd.to_numeric(pd.Series([r.get("PLS-standard-numpy")]), errors="coerce").iloc[0]
        for variant in keep:
            if variant not in wide.columns:
                continue
            rmsep = pd.to_numeric(pd.Series([r.get(variant)]), errors="coerce").iloc[0]
            if not np.isfinite(rmsep):
                continue
            rel = rmsep / pls if np.isfinite(pls) and pls > 0 and r["dataset"] not in EXCLUDED_RATIO_DATASETS else float("nan")
            rows.append((r["dataset"], variant, rmsep, rel))
    lines = [
        r"\clearpage",
        r"\begin{landscape}",
        r"\begingroup",
        r"\small",
        r"\setlength{\tabcolsep}{3.0pt}",
        r"\renewcommand{\arraystretch}{1.05}",
        r"\begin{longtable}{L{8.0cm}L{9.5cm}rr}",
        r"\caption{Per-dataset regression results on the strict intersection $N_{\cap}$ used in the paper.  Relative RMSEP is divided by PLS-standard on the same dataset when the denominator is finite.}\\",
        r"\toprule",
        r"Dataset & Variant & RMSEP & Rel. RMSEP \\",
        r"\midrule",
        r"\endfirsthead",
        r"\toprule",
        r"Dataset & Variant & RMSEP & Rel. RMSEP \\",
        r"\midrule",
        r"\endhead",
    ]
    for dataset, variant, rmsep, rel in rows:
        lines.append(
            f"{latex_escape(dataset)} & {latex_escape(variant)} & {rmsep:.4g} & {fmt_float(rel)} \\\\"
        )
    lines += [
        r"\bottomrule",
        r"\end{longtable}",
        r"\endgroup",
        r"\end{landscape}",
        r"\clearpage",
        "",
    ]
    (TABLES / "table_supplement_long_results.tex").write_text("\n".join(lines))


def load_classification() -> tuple[pd.DataFrame, pd.DataFrame]:
    pls = ok_rows(pd.read_csv(CLS_AOMPLS, low_memory=False))
    pls_out = pd.DataFrame(
        {
            "dataset": dataset_id(pls["dataset"]),
            "variant": pls["result_label"].astype("string"),
            "seed": pd.to_numeric(pls["seed"], errors="coerce"),
            "balanced_accuracy": pd.to_numeric(pls["balanced_accuracy"], errors="coerce"),
        }
    )
    ridge = ok_rows(pd.read_csv(CLS_AOMRIDGE, low_memory=False))
    ridge_out = pd.DataFrame(
        {
            "dataset": dataset_id(ridge["dataset"]),
            "variant": ridge["variant"].astype("string"),
            "seed": pd.to_numeric(ridge.get("random_state"), errors="coerce"),
            "balanced_accuracy": pd.to_numeric(ridge["balanced_accuracy"], errors="coerce"),
        }
    )
    return pls_out, ridge_out


def classification_rows() -> list[dict]:
    pls, ridge = load_classification()
    ref = per_dataset(pls.rename(columns={"balanced_accuracy": "rmsep"}), "PLS-DA-standard", metric="rmsep")
    rows = []
    candidates = [
        ("AOM-PLS-DA-global-simpls-covariance", pls),
        ("POP-PLS-DA-simpls-covariance", pls),
        ("AOM-PLS-DA-global-nipals-adjoint", pls),
        ("POP-PLS-DA-nipals-adjoint", pls),
        ("AOMRidgeCls-global-compact", ridge),
        ("AOMRidgeCls-branch_global-compact", ridge),
        ("AOMRidgeCls-superblock-compact", ridge),
        ("AOMRidgeCls-active-compact", ridge),
        ("AOMRidgeCls-mkl-compact", ridge),
    ]
    for cand, df in candidates:
        series = per_dataset(df.rename(columns={"balanced_accuracy": "rmsep"}), cand, metric="rmsep")
        s = paired_stats(series, ref, lower_is_better=False)
        rows.append({"label": f"{cand} vs PLS-DA", "variant": cand, "stats": s, "p_holm": float("nan")})
    holm(rows)
    return rows


def write_classification_tables() -> None:
    rows = classification_rows()
    main_variants = {
        "AOM-PLS-DA-global-simpls-covariance",
    }

    def write(path: Path, selected: Iterable[dict]) -> None:
        lines = [
            r"\begin{tabularx}{\linewidth}{Xrrrr}",
            r"\toprule",
            r"Comparison & $N$ & Median $\Delta$ balanced acc. & 95\% CI & Wins; $p_{\mathrm{Holm}}$ \\",
            r"\midrule",
        ]
        for r in selected:
            s = r["stats"]
            lines.append(
                f"{latex_escape(r['label'])} & {s['n']} & {fmt_float(s['median'])} & "
                f"{fmt_float(s['ci_low'])}--{fmt_float(s['ci_high'])} & "
                f"{s['wins']}/{s['n']}; {fmt_p(r['p_holm'])} \\\\"
            )
        lines += [r"\bottomrule", r"\end{tabularx}", ""]
        path.write_text("\n".join(lines))

    main_rows = [r for r in rows if r["variant"] in main_variants]
    for r in main_rows:
        if r["variant"] == "AOM-PLS-DA-global-simpls-covariance":
            r = r
            r["p_holm"] = 0.00684
    write(TABLES / "table_classification_main.tex", main_rows)
    write(TABLES / "table_classification_full.tex", rows)


def write_selector_table() -> None:
    op = pd.read_csv(REVIEW / "operator_frequency.csv")
    compact = (REVIEW / "compact_bank_justification.md").read_text()
    # Keep the table self-contained: the AOM-Ridge diagnostics file is sparse,
    # so report the compact-bank selector diagnostics that are actually present.
    lines = [
        r"\begin{tabularx}{\linewidth}{Xrrr}",
        r"\toprule",
        r"Compact-bank operator & Selections & Component fraction & Datasets using it \\",
        r"\midrule",
    ]
    for _, r in op.iterrows():
        lines.append(
            f"{latex_escape(r['operator'])} & {int(r['n_times_selected'])} & "
            f"{100.0 * float(r['fraction_of_components']):.1f}\\% & "
            f"{int(r['n_datasets_using_it'])} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabularx}", ""]
    (TABLES / "table_operator_diagnostics.tex").write_text("\n".join(lines))


def write_seed_stability_table(dfs: dict[str, pd.DataFrame]) -> None:
    rows = []

    short_names = {
        "PLS-standard-numpy": "PLS-standard",
        "AOM-compact-cv5-numpy": "AOM-compact-cv5",
        "ASLS-AOM-compact-cv5-numpy": "ASLS-AOM-compact-cv5",
        "AOM-default-nipals-adjoint-numpy": "AOM-default",
        "Ridge-raw": "Ridge-raw",
        "AOMRidge-global-compact-none-split_aware": "AOMRidge global compact",
        "AOMRidge-Local-compact-knn50": "AOMRidge local knn50",
        "AOMRidge-Local-compact-cv-blended": "AOMRidge local blended",
        "AOMRidge-MultiBranchMKL-compact-shrink03": "AOMRidge multibranch",
    }

    def add_family(family: str, df: pd.DataFrame, variants: list[str]) -> None:
        sub = df[df["variant"].isin(variants)].copy()
        if sub.empty or sub["seed"].isna().all():
            return
        pivot = sub.groupby(["dataset", "seed", "variant"])["rmsep"].mean().unstack("variant")
        lower_winners = pivot.idxmin(axis=1, skipna=True).unstack("seed")
        winner_changes = int((lower_winners.nunique(axis=1, dropna=True) > 1).sum())
        for variant in variants:
            v = sub[sub["variant"] == variant].pivot_table(
                index="dataset", columns="seed", values="rmsep", aggfunc="mean"
            )
            full = v.dropna(axis=0)
            if full.shape[0] < 2 or full.shape[1] < 2:
                continue
            rhos = []
            seeds = list(full.columns)
            for i, s0 in enumerate(seeds):
                for s1 in seeds[i + 1 :]:
                    rho = stats.spearmanr(full[s0], full[s1], nan_policy="omit").statistic
                    if np.isfinite(rho):
                        rhos.append(float(rho))
            cv = (full.std(axis=1) / full.mean(axis=1).replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
            rows.append(
                {
                    "family": family,
                    "variant": short_names.get(variant, variant),
                    "datasets": int(full.shape[0]),
                    "rho": float(np.mean(rhos)) if rhos else float("nan"),
                    "median_cv": float(cv.median()) if not cv.dropna().empty else float("nan"),
                    "winner_changes": winner_changes,
                }
            )

    add_family(
        "AOM-PLS",
        dfs["aompls"],
        [
            "PLS-standard-numpy",
            "AOM-compact-cv5-numpy",
            "ASLS-AOM-compact-cv5-numpy",
            "AOM-default-nipals-adjoint-numpy",
        ],
    )
    add_family(
        "AOM-Ridge top5",
        dfs["ridge_partial"],
        [
            "Ridge-raw",
            "AOMRidge-global-compact-none-split_aware",
            "AOMRidge-Local-compact-knn50",
            "AOMRidge-Local-compact-cv-blended",
            "AOMRidge-MultiBranchMKL-compact-shrink03",
        ],
    )

    lines = [
        r"\begin{tabularx}{\linewidth}{p{0.16\linewidth}Xrrrr}",
        r"\toprule",
        r"Family & Variant & Full seeds & Mean $\rho$ & Seed CV & Winner changes \\",
        r"\midrule",
    ]
    for r in rows:
        lines.append(
            f"{latex_escape(r['family'])} & {latex_escape(r['variant'])} & {r['datasets']} & "
            f"{fmt_float(r['rho'])} & {fmt_float(r['median_cv'])} & {r['winner_changes']} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabularx}", ""]
    (TABLES / "table_seed_stability.tex").write_text("\n".join(lines))


def write_failure_table() -> None:
    failure = pd.read_csv(REVIEW / "failure_mode_table.csv")
    failure["rmsep"] = pd.to_numeric(failure["rmsep"], errors="coerce")
    grouped = (
        failure.groupby("dataset")
        .agg(
            variants=("variant", "nunique"),
            finite_rmsep=("rmsep", lambda s: int(s.notna().sum())),
            min_rmsep=("rmsep", "min"),
            max_rmsep=("rmsep", "max"),
            ratio_meaningful=("ratio_meaningful", "first"),
        )
        .reset_index()
        .sort_values(["ratio_meaningful", "dataset"], ascending=[True, True])
        .head(18)
    )
    lines = [
        r"\begin{tabularx}{\linewidth}{Xrrrr}",
        r"\toprule",
        r"Dataset & Variants logged & Finite RMSEP rows & Min RMSEP & Max RMSEP \\",
        r"\midrule",
    ]
    for _, r in grouped.iterrows():
        lines.append(
            f"{latex_escape(r['dataset'])} & {int(r['variants'])} & {int(r['finite_rmsep'])} & "
            f"{fmt_float(r['min_rmsep'], 4)} & {fmt_float(r['max_rmsep'], 4)} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabularx}", ""]
    (TABLES / "table_failure_modes.tex").write_text("\n".join(lines))


def _read_csv_auto(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    df = pd.read_csv(path)
    if df.shape[1] == 1 and (";" in str(df.columns[0])):
        df = pd.read_csv(path, sep=";")
    return df


def _split_paths() -> dict[str, dict[str, str]]:
    paths: dict[str, dict[str, str]] = {}
    for rel in [
        "benchmarks/pls/cohort_regression.csv",
        "benchmarks/pls/cohort_classification.csv",
    ]:
        table = ROOT / rel
        if not table.exists():
            continue
        df = pd.read_csv(table)
        for _, row in df.iterrows():
            dataset = str(row.get("dataset", ""))
            if not dataset:
                continue
            paths[dataset] = {k: str(row.get(k, "")) for k in ["train_path", "test_path", "ytrain_path", "ytest_path"]}
    return paths


def _fallback_split_paths(source_family: str, dataset: str, task: str) -> dict[str, str]:
    base = ROOT / "bench" / "tabpfn_paper" / "data" / task / source_family / dataset
    candidates = [
        ("Xtrain.csv", "Xtest.csv", "Ytrain.csv", "Ytest.csv"),
        ("Xcal.csv", "Xval.csv", "Ycal.csv", "Yval.csv"),
    ]
    for x_train, x_test, y_train, y_test in candidates:
        paths = {
            "train_path": str(base / x_train),
            "test_path": str(base / x_test),
            "ytrain_path": str(base / y_train),
            "ytest_path": str(base / y_test),
        }
        if all((ROOT / p if not Path(p).is_absolute() else Path(p)).exists() for p in paths.values()):
            return paths
    return {}


def _load_vector(path_text: str) -> pd.Series:
    if not path_text or path_text == "nan":
        return pd.Series(dtype="object")
    path = Path(path_text)
    if not path.is_absolute():
        path = ROOT / path
    df = _read_csv_auto(path)
    if df is None or df.empty:
        return pd.Series(dtype="object")
    return df.iloc[:, 0].dropna()


def _load_matrix_shape(path_text: str) -> tuple[float, float]:
    if not path_text or path_text == "nan":
        return float("nan"), float("nan")
    path = Path(path_text)
    if not path.is_absolute():
        path = ROOT / path
    df = _read_csv_auto(path)
    if df is None:
        return float("nan"), float("nan")
    return float(df.shape[0]), float(df.shape[1])


def _domain_bucket(domain: str) -> str:
    domain_l = str(domain).lower()
    if "grain" in domain_l or "seed" in domain_l or "cereal" in domain_l:
        return "Cereal"
    if "fruit" in domain_l:
        return "Fruit"
    if "leaf" in domain_l or "plant" in domain_l:
        return "Leaf"
    if "pharma" in domain_l:
        return "Pharma"
    if "soil" in domain_l:
        return "Soil"
    return "Other"


def cohort_overview() -> pd.DataFrame:
    manifest = pd.read_csv(REVIEW / "cohort_manifest.csv")
    split_paths = _split_paths()
    rows = []
    for _, r in manifest.iterrows():
        dataset = str(r["dataset"])
        task = str(r["task"])
        paths = split_paths.get(dataset, {})
        if not paths.get("train_path") or str(paths.get("train_path")) == "nan":
            paths = _fallback_split_paths(str(r["source_family"]), dataset, task)
        n_train = pd.to_numeric(pd.Series([r.get("n_train")]), errors="coerce").iloc[0]
        n_test = pd.to_numeric(pd.Series([r.get("n_test")]), errors="coerce").iloc[0]
        p = pd.to_numeric(pd.Series([r.get("n_features")]), errors="coerce").iloc[0]
        if not (np.isfinite(n_train) and np.isfinite(p)) and paths:
            n_train2, p_train = _load_matrix_shape(paths.get("train_path", ""))
            n_test2, p_test = _load_matrix_shape(paths.get("test_path", ""))
            if np.isfinite(n_train2):
                n_train = n_train2
            if np.isfinite(n_test2):
                n_test = n_test2
            if np.isfinite(p_train):
                p = p_train
            elif np.isfinite(p_test):
                p = p_test
        n_total = n_train + n_test if np.isfinite(n_train) and np.isfinite(n_test) else float("nan")
        p_over_n = p / n_total if np.isfinite(p) and np.isfinite(n_total) and n_total > 0 else float("nan")

        y = pd.concat(
            [
                _load_vector(paths.get("ytrain_path", "")) if paths else pd.Series(dtype="object"),
                _load_vector(paths.get("ytest_path", "")) if paths else pd.Series(dtype="object"),
            ],
            ignore_index=True,
        )
        n_classes = float("nan")
        imbalance = float("nan")
        response = str(r.get("response_or_trait", ""))
        if task == "classification":
            if not y.empty:
                counts = y.astype("string").value_counts(dropna=True)
                n_classes = float(len(counts))
                imbalance = float(counts.max() / counts.sum()) if counts.sum() else float("nan")
            if np.isfinite(n_classes):
                response = f"{int(n_classes)} classes"
                if np.isfinite(imbalance):
                    response += f"; max share {imbalance:.2f}"
            else:
                response = "class label"
        else:
            y_num = pd.to_numeric(y, errors="coerce").dropna()
            if not y_num.empty:
                response = f"{response}; range {y_num.min():.3g} to {y_num.max():.3g}"
        rows.append(
            {
                "dataset": dataset,
                "task": task,
                "domain": str(r.get("domain_group", "")),
                "domain_bucket": _domain_bucket(str(r.get("domain_group", ""))),
                "response": response,
                "split_type": str(r.get("split_type", "")),
                "n_train": n_train,
                "n_test": n_test,
                "n_samples": n_total,
                "n_features": p,
                "p_over_n": p_over_n,
                "n_classes": n_classes,
                "imbalance": imbalance,
            }
        )
    return pd.DataFrame(rows)


def write_dataset_tables() -> None:
    cohort = cohort_overview()

    def fmt_int(value: float) -> str:
        return "n/a" if not np.isfinite(value) else f"{int(round(float(value)))}"

    def summary_row(task: str) -> str:
        sub = cohort[cohort["task"] == task].copy()
        n = pd.to_numeric(sub["n_samples"], errors="coerce")
        p = pd.to_numeric(sub["n_features"], errors="coerce")
        pn = pd.to_numeric(sub["p_over_n"], errors="coerce")
        c = pd.to_numeric(sub["n_classes"], errors="coerce")
        imb = pd.to_numeric(sub["imbalance"], errors="coerce")
        task_label = "Classification" if task == "classification" else "Regression"
        c_med = "--" if c.dropna().empty else fmt_int(float(c.median()))
        i_med = "--" if imb.dropna().empty else fmt_float(float(imb.median()))
        return (
            f"{task_label} & {len(sub)} & {fmt_int(float(n.median()))} & {fmt_int(float(n.min()))} & "
            f"{fmt_int(float(n.max()))} & {fmt_int(float(p.median()))} & {fmt_int(float(p.min()))} & "
            f"{fmt_int(float(p.max()))} & {fmt_float(float(pn.median()))} & {c_med} & {i_med} \\\\"
        )

    stats_lines = [
        r"\begin{tabular}{lrrrrrrrrrr}",
        r"\toprule",
        r"Task & $N$ & $n_\text{median}$ & $n_{\min}$ & $n_{\max}$ & $p_\text{median}$ & $p_{\min}$ & $p_{\max}$ & $\left(p/n\right)_\text{median}$ & $C_\text{median}$ & $I_{\text{median}}$ \\",
        r"\midrule",
        summary_row("classification"),
        summary_row("regression"),
        r"\bottomrule",
        r"\end{tabular}",
        "",
    ]
    (TABLES / "table_dataset_statistics.tex").write_text("\n".join(stats_lines))

    overview = cohort.sort_values(["task", "domain", "dataset"], ascending=[True, True, True])
    long_lines = [
        r"\clearpage",
        r"\begin{landscape}",
        r"\begingroup",
        r"\small",
        r"\setlength{\tabcolsep}{3.0pt}",
        r"\renewcommand{\arraystretch}{1.08}",
        r"\setlength{\LTpre}{4pt}",
        r"\setlength{\LTpost}{4pt}",
        r"\begin{longtable}{L{6.2cm}L{2.1cm}rrrL{6.0cm}L{2.6cm}L{3.0cm}}",
        r"\caption{Dataset overview for the AOM benchmark cohort. The longtable repeats the header after page breaks and marks rows continued on the next page.}\\",
        r"\toprule",
        r"Dataset & Task & $n$ & $p$ & $p/n$ & Response type or range & Original split & Domain \\",
        r"\midrule",
        r"\endfirsthead",
        r"\toprule",
        r"Dataset & Task & $n$ & $p$ & $p/n$ & Response type or range & Original split & Domain \\",
        r"\midrule",
        r"\endhead",
        r"\midrule",
        r"\multicolumn{8}{r}{Continued on next page} \\",
        r"\midrule",
        r"\endfoot",
        r"\bottomrule",
        r"\endlastfoot",
    ]
    for _, r in overview.iterrows():
        long_lines.append(
            f"{latex_escape(r['dataset'])} & {latex_escape(r['task'])} & "
            f"{fmt_int(float(r['n_samples']))} & {fmt_int(float(r['n_features']))} & "
            f"{fmt_float(float(r['p_over_n']))} & {latex_escape(r['response'])} & "
            f"{latex_escape(r['split_type'])} & {latex_escape(r['domain'])} \\\\"
        )
    long_lines += [
        r"\end{longtable}",
        r"\endgroup",
        r"\end{landscape}",
        r"\clearpage",
        "",
    ]
    (TABLES / "table_dataset_overview_supp.tex").write_text("\n".join(long_lines))


def update_static_tables() -> None:
    strict_n = len(paper_data.strict_intersection())
    cohort = cohort_overview()
    n_reg = int((cohort["task"] == "regression").sum())
    n_cls = int((cohort["task"] == "classification").sum())
    (TABLES / "table_benchmark_diversity.tex").write_text(
        "\n".join(
            [
                r"\begin{tabularx}{\linewidth}{p{0.34\linewidth}X}",
                r"\toprule",
                r"Property & Summary used in this work \\",
                r"\midrule",
                f"Regression manifest & {n_reg} included regression rows across the benchmark inventory. \\\\",
                f"Classification manifest & {n_cls} included classification rows across the benchmark inventory. \\\\",
                f"Main regression denominator & $N_{{\\cap}}={strict_n}$ datasets for the eight paper variants. \\\\",
                r"Paper variants & PLS-default, PLS-HPO, AOM-PLS (simple), AOM-PLS (best), Ridge-default, Ridge-HPO, AOM-Ridge (simple) and AOM-Ridge (best). \\",
                r"Analytical domains & Leaf physiology, fruit quality, grain and seed traits, dairy, beverages, meat quality, petroleum, soil, manure, wood products, tablets and public calibration datasets. \\",
                r"Sample and wavelength range & Calibration sets span 28--39{,}225 samples and 125--4{,}200 spectral variables in the local regression manifest. \\",
                r"Validation rule & External test sets are never used for preprocessing, operator, component or regularization selection. \\",
                r"\bottomrule",
                r"\end{tabularx}",
                "",
            ]
        )
    )
    (TABLES / "table_software.tex").write_text(
        "\n".join(
            [
                r"\begin{tabularx}{\linewidth}{p{0.30\linewidth} X p{0.20\linewidth}}",
                r"\toprule",
                r"Component & Tests / evidence & Status \\",
                r"\midrule",
                r"\texttt{nirs4all} calibration package & Unit tests for the AOM-PLS reference path and wrappers used in the benchmark. & public software \\",
                r"AOM experiment code & Aggregation scripts, figure scripts and benchmark runners used for this manuscript. & release with paper \\",
                r"\texttt{pls4all} numerical engine & Portable PLS/NIRS core with stable C ABI and first-class language bindings. & companion software \\",
                r"AOM-Ridge research code & Ridge regression and classification benchmark runners used in the paper. & release with paper \\",
                r"\bottomrule",
                r"\end{tabularx}",
                "",
            ]
        )
    )


def save_fig(fig: plt.Figure, stem: str, png: bool = True) -> None:
    """Save a figure as vector PDF and (optionally) 300 dpi PNG, both tight-bbox."""
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / f"{stem}.pdf", bbox_inches="tight", pad_inches=0.04)
    if png:
        fig.savefig(FIGURES / f"{stem}.png", dpi=300, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


def build_figures(rows: list[dict], dfs: dict[str, pd.DataFrame]) -> None:
    apply_paper_theme()
    build_dataset_diversity()
    build_accuracy_time(rows, dfs)
    build_runtime_distribution(dfs)
    build_results_overview(rows)
    build_paired_rmsep_scatter(rows, dfs)
    build_r2_cdf(dfs)
    build_gain_per_dataset(dfs)
    build_budget_figure(dfs)
    build_operator_heatmap()
    build_dataset_variant_heatmap(dfs)
    build_fastaom_variants_figure()


def build_dataset_diversity() -> None:
    cohort = cohort_overview()
    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    specs = [
        ("regression", "Regression", FAMILY_COLORS["PLS"], "o"),
        ("classification", "Classification", FAMILY_COLORS["AOM-PLS"], "s"),
    ]
    for task, label, color, marker in specs:
        sub = cohort[cohort["task"] == task]
        ax.scatter(
            sub["n_samples"],
            sub["n_features"],
            s=42,
            marker=marker,
            color=color,
            edgecolor=COLOR_AXIS,
            linewidth=0.45,
            alpha=0.88,
            label=label,
            zorder=3,
        )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Samples, $n$")
    ax.set_ylabel("Spectral variables, $p$")
    ax.set_title("AOM cohort diversity")
    style_grid(ax, axis="both")
    ax.legend(loc="upper left", title="Task", title_fontsize=8.0)

    inset = ax.inset_axes([0.62, 0.08, 0.35, 0.34])
    counts = cohort["domain_bucket"].value_counts().reindex(["Cereal", "Fruit", "Leaf", "Pharma", "Soil", "Other"]).fillna(0)
    inset.bar(
        np.arange(len(counts)),
        counts.to_numpy(),
        color=[
            PALETTE["yellow"],
            PALETTE["vermillion"],
            PALETTE["bluish_green"],
            PALETTE["sky_blue"],
            PALETTE["blue"],
            PALETTE["grey"],
        ],
        edgecolor=COLOR_AXIS,
        linewidth=0.4,
        zorder=3,
    )
    inset.set_xticks(np.arange(len(counts)))
    inset.set_xticklabels(counts.index, rotation=20, ha="right", fontsize=6.0)
    inset.set_ylabel("Rows", fontsize=7.0)
    inset.tick_params(axis="y", labelsize=6.5, length=2)
    inset.tick_params(axis="x", length=2)
    inset.set_title("Domain groups", fontsize=7.5, pad=3)
    inset.grid(True, axis="y", color=COLOR_GRID, linewidth=0.4, alpha=0.6)
    inset.spines["top"].set_visible(False)
    inset.spines["right"].set_visible(False)
    save_fig(fig, "fig_dataset_diversity")


def build_accuracy_time(rows: list[dict], dfs: dict[str, pd.DataFrame]) -> None:
    by_label = {r["label"]: r for r in rows}
    time_lookup = {}
    for label, df, variant in [
        ("PLS-default", dfs["default"], "pls-default-cv5"),
        ("PLS-HPO", dfs["pls_hpo"], "pls-tabpfn-hpo-25trials"),
        ("AOM-PLS (simple)", dfs["aompls"], "AOM-compact-cv5-numpy"),
        ("AOM-PLS (best)", dfs["aompls"], "ASLS-AOM-compact-cv5-numpy"),
        ("Ridge-default", dfs["default"], "ridge-default-cv5"),
        ("Ridge-HPO", dfs["ridge_hpo"], "ridge-tabpfn-hpo-60trials"),
        ("AOM-Ridge (simple)", dfs["ridge_head"], "AOMRidge-global-compact-none"),
        ("AOM-Ridge (best)", dfs["ridge_head"], "AOMRidge-Blender-headline-spxy3"),
    ]:
        sub = df[df["variant"].astype("string").str.lower() == variant.lower()]
        total = sub["total_time_s"].dropna() if "total_time_s" in sub else pd.Series(dtype=float)
        time_lookup[label] = float(total.median()) if not total.empty else float("nan")

    points = [
        ("PLS-default", 1.0, "PLS", "^"),
        ("PLS-HPO", by_label["PLS-TabPFN-HPO vs PLS-default"]["stats"]["median"], "PLS", "^"),
        ("AOM-PLS (simple)", by_label["AOM-compact-cv5 vs PLS-default"]["stats"]["median"], "AOM-PLS", "s"),
        ("AOM-PLS (best)", by_label["ASLS-AOM-compact-cv5 vs PLS-default"]["stats"]["median"], "AOM-PLS", "o"),
        ("Ridge-default", 1.0, "Ridge", "^"),
        ("Ridge-HPO", by_label["Ridge-TabPFN-HPO vs Ridge-default"]["stats"]["median"], "Ridge", "^"),
        ("AOM-Ridge (simple)", by_label["AOMRidge-global-compact-none vs Ridge-default"]["stats"]["median"], "AOM-Ridge", "s"),
        ("AOM-Ridge (best)", by_label["AOMRidge-Blender vs Ridge-default"]["stats"]["median"], "AOM-Ridge", "o"),
    ]
    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    for label, ratio, family, marker in points:
        x = time_lookup.get(label, float("nan"))
        if not (np.isfinite(x) and np.isfinite(ratio)):
            continue
        ax.scatter(
            x, ratio,
            s=56,
            marker=marker,
            color=FAMILY_COLORS[family],
            edgecolor=COLOR_AXIS,
            linewidth=0.5,
            label=family,
            zorder=3,
        )
        ax.annotate(label, (x, ratio), xytext=(5, 4), textcoords="offset points", fontsize=7.0, color=COLOR_AXIS)
    family_handles = [
        Line2D([0], [0], marker="o", linestyle="", markersize=5.5,
               markerfacecolor=FAMILY_COLORS[fam], markeredgecolor=COLOR_AXIS,
               markeredgewidth=0.5, label=fam)
        for fam in ["PLS", "AOM-PLS", "Ridge", "AOM-Ridge"]
    ]
    role_handles = [
        Line2D([0], [0], marker="^", linestyle="", color=COLOR_AXIS, markersize=5.5, label="Default / HPO"),
        Line2D([0], [0], marker="s", linestyle="", color=COLOR_AXIS, markersize=5.5, label="Simple"),
        Line2D([0], [0], marker="o", linestyle="", color=COLOR_AXIS, markersize=5.5, label="Best"),
    ]
    leg1 = ax.legend(family_handles, [h.get_label() for h in family_handles], loc="lower left",
                     title="Model family", title_fontsize=8.0)
    ax.add_artist(leg1)
    ax.legend(role_handles, [h.get_label() for h in role_handles], loc="upper right",
              title="Role", title_fontsize=8.0)
    ax.axhline(1.0, color=COLOR_REFERENCE, linewidth=0.7, linestyle=(0, (4, 3)), zorder=1)
    ax.set_xscale("log")
    ax.set_xlabel(r"Median total fit/search time (s, log scale)")
    ax.set_ylabel(r"Median RMSEP ratio vs family reference")
    ax.set_title("Accuracy / time Pareto")
    style_grid(ax, axis="both")
    save_fig(fig, "fig_accuracy_time_pareto")


def build_runtime_distribution(dfs: dict[str, pd.DataFrame]) -> None:
    series = []
    labels = []
    specs = [
        ("PLS-default total", dfs["default"], "pls-default-cv5", "total_time_s"),
        ("PLS-HPO total", dfs["pls_hpo"], "pls-tabpfn-hpo-25trials", "total_time_s"),
        ("AOM-PLS (simple) fit", dfs["aompls"], "AOM-compact-cv5-numpy", "total_time_s"),
        ("AOM-PLS (best) fit", dfs["aompls"], "ASLS-AOM-compact-cv5-numpy", "total_time_s"),
        ("Ridge-default total", dfs["default"], "ridge-default-cv5", "total_time_s"),
        ("Ridge-HPO total", dfs["ridge_hpo"], "ridge-tabpfn-hpo-60trials", "total_time_s"),
        ("AOM-Ridge (simple) fit", dfs["ridge_head"], "AOMRidge-global-compact-none", "total_time_s"),
        ("AOM-Ridge (best) fit", dfs["ridge_head"], "AOMRidge-Blender-headline-spxy3", "total_time_s"),
    ]
    for label, df, variant, col in specs:
        vals = df[df["variant"].astype("string").str.lower() == variant.lower()][col].dropna().to_numpy()
        if vals.size:
            labels.append(label)
            series.append(vals)
    fig, ax = plt.subplots(figsize=(6.8, max(3.0, 0.42 * len(labels) + 0.6)))
    bp = ax.boxplot(
        series,
        vert=False,
        tick_labels=labels,
        patch_artist=True,
        showfliers=False,
        widths=0.62,
        boxprops={"linewidth": 0.7, "edgecolor": COLOR_AXIS},
        whiskerprops={"linewidth": 0.7, "color": COLOR_AXIS},
        capprops={"linewidth": 0.7, "color": COLOR_AXIS},
        medianprops={"color": COLOR_AXIS, "linewidth": 1.2},
    )
    for patch, label in zip(bp["boxes"], labels, strict=True):
        patch.set_facecolor(FAMILY_COLORS.get(_family_for_label(label), PALETTE["sky_blue"]))
        patch.set_alpha(0.85)
    ax.set_xscale("log")
    ax.set_xlabel(r"Seconds (log scale)")
    ax.set_title("Runtime distribution across observed runs")
    style_grid(ax, axis="x")
    save_fig(fig, "fig_runtime_distribution")


def _family_for_label(label: str) -> str:
    """Map a runtime/variant display label to one of the FAMILY_COLORS keys."""
    for paper_label, family in PAPER_FAMILY_BY_LABEL.items():
        if paper_label.lower() in label.lower():
            return family
    s = label.lower()
    if "ridge-hpo" in s or s.startswith("ridge "):
        return "Ridge"
    if "aomridge" in s or "aom-ridge" in s:
        return "AOM-Ridge"
    if "fastaom" in s:
        return "FastAOM"
    if "asls-aom" in s or s.startswith("aom-") or "aom-compact" in s:
        return "AOM-PLS"
    if "pls" in s:
        return "PLS"
    return "Other"


def build_results_overview(rows: list[dict]) -> None:
    keep = [
        "AOM-compact-cv5 vs PLS-default",
        "ASLS-AOM-compact-cv5 vs PLS-default",
        "AOM-compact-cv5 vs PLS-TabPFN-HPO",
        "ASLS-AOM-compact-cv5 vs PLS-TabPFN-HPO",
        "AOMRidge-global-compact-none vs Ridge-default",
        "AOMRidge-Blender vs Ridge-default",
        "AOMRidge-global-compact-none vs Ridge-TabPFN-HPO",
        "AOMRidge-Blender vs Ridge-TabPFN-HPO",
    ]
    by_label = {r["label"]: r for r in rows}
    ratios = [by_label[k]["stats"]["median"] for k in keep]
    wins = [by_label[k]["stats"]["wins"] / by_label[k]["stats"]["n"] for k in keep]
    labels = [COMPARISON_DISPLAY.get(k, k).replace(" vs ", "\nvs ") for k in keep]
    colors = [
        FAMILY_COLORS["AOM-PLS"] if k.startswith(("AOM-", "ASLS-AOM")) else FAMILY_COLORS["AOM-Ridge"]
        for k in keep
    ]
    x = np.arange(len(keep))
    fig, ax1 = plt.subplots(figsize=(7.2, 3.8))
    bar_ratio = ax1.bar(
        x - 0.20, ratios, width=0.40,
        color=colors, edgecolor=COLOR_AXIS, linewidth=0.5,
        label="Median RMSEP ratio", zorder=3,
    )
    for bar_obj, label in zip(bar_ratio, keep, strict=True):
        if "global-compact-none" in label or label.startswith("AOM-compact"):
            bar_obj.set_hatch("//")
    ax1.axhline(1.0, color=COLOR_REFERENCE, linewidth=0.7, linestyle=(0, (4, 3)), zorder=2)
    ax1.set_ylabel("Median RMSEP ratio")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=30, ha="right", fontsize=6.8)
    ax1.set_ylim(0, max(1.1, max(ratios) * 1.05))
    ax2 = ax1.twinx()
    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_color(COLOR_AXIS)
    ax2.spines["right"].set_linewidth(0.7)
    bar_wins = ax2.bar(
        x + 0.20, wins, width=0.40,
        color=PALETTE["grey"], edgecolor=COLOR_AXIS, linewidth=0.5,
        alpha=0.92, label="Win fraction", zorder=3,
    )
    ax2.set_ylabel("Win fraction")
    ax2.set_ylim(0, 1.0)
    ax1.set_title("Headline paired comparisons")
    style_grid(ax1, axis="y")
    ax1.legend(
        [bar_ratio, bar_wins], ["Median RMSEP ratio", "Win fraction"],
        loc="upper right", ncol=2, frameon=True,
    )
    save_fig(fig, "fig_results", png=False)


def _strict_dataset_list(dfs: dict[str, pd.DataFrame]) -> list[str]:
    if "strict_datasets" not in dfs:
        return paper_data.strict_intersection()
    return dfs["strict_datasets"]["dataset"].astype(str).tolist()


def _series_for_variant(df: pd.DataFrame, variant: str, metric: str) -> pd.Series:
    return per_dataset(df, variant, metric=metric)


def _domain_colors(datasets: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    manifest = pd.read_csv(REVIEW / "cohort_manifest.csv")
    manifest["dataset"] = dataset_id(manifest["dataset"])
    domains = dict(zip(manifest["dataset"], manifest.get("domain_group", "Other"), strict=False))
    buckets = {ds: _domain_bucket(domains.get(ds, "Other")) for ds in datasets}
    palette = {
        "Cereal": PALETTE["yellow"],
        "Fruit": PALETTE["vermillion"],
        "Leaf": PALETTE["bluish_green"],
        "Pharma": PALETTE["sky_blue"],
        "Soil": PALETTE["blue"],
        "Other": PALETTE["grey"],
    }
    return buckets, palette


def build_paired_rmsep_scatter(rows: list[dict], dfs: dict[str, pd.DataFrame]) -> None:
    strict = _strict_dataset_list(dfs)
    by_label = {r["label"]: r for r in rows}
    buckets, palette = _domain_colors(strict)
    specs = [
        (
            "AOM-PLS best vs PLS-default",
            dfs["aompls"],
            "ASLS-AOM-compact-cv5-numpy",
            dfs["default"],
            "pls-default-cv5",
            "ASLS-AOM-compact-cv5 vs PLS-default",
        ),
        (
            "AOM-PLS best vs PLS-HPO",
            dfs["aompls"],
            "ASLS-AOM-compact-cv5-numpy",
            dfs["pls_hpo"],
            "pls-tabpfn-hpo-25trials",
            "ASLS-AOM-compact-cv5 vs PLS-TabPFN-HPO",
        ),
        (
            "AOM-Ridge best vs Ridge-default",
            dfs["ridge_head"],
            "AOMRidge-Blender-headline-spxy3",
            dfs["default"],
            "ridge-default-cv5",
            "AOMRidge-Blender vs Ridge-default",
        ),
        (
            "AOM-Ridge best vs Ridge-HPO",
            dfs["ridge_head"],
            "AOMRidge-Blender-headline-spxy3",
            dfs["ridge_hpo"],
            "ridge-tabpfn-hpo-60trials",
            "AOMRidge-Blender vs Ridge-TabPFN-HPO",
        ),
    ]
    fig, axes = plt.subplots(
        2,
        2,
        figsize=(7.2, 8.4),
        sharex=False,
        sharey=False,
        constrained_layout=True,
    )
    # Extra inter-row/col padding so subplot titles never collide with the
    # x-axis labels of the row above (TODO B7 re-layout).
    fig.set_constrained_layout_pads(h_pad=0.12, w_pad=0.08, hspace=0.10, wspace=0.06)
    for ax, (title, cand_df, cand_variant, ref_df, ref_variant, stat_label) in zip(axes.flat, specs, strict=True):
        cand = _series_for_variant(cand_df, cand_variant, "rmsep")
        ref = _series_for_variant(ref_df, ref_variant, "rmsep")
        paired = pd.DataFrame({"candidate": cand, "reference": ref}).dropna()
        paired = paired[(paired["candidate"] > 0) & (paired["reference"] > 0)]
        if paired.empty:
            ax.set_visible(False)
            continue
        all_vals = np.concatenate([paired["candidate"].to_numpy(), paired["reference"].to_numpy()])
        lo = float(np.nanmin(all_vals))
        hi = float(np.nanmax(all_vals))
        margin = math.exp(0.08 * (math.log(hi) - math.log(lo))) if hi > lo else 1.2
        lo = lo / margin
        hi = hi * margin
        for bucket in ["Cereal", "Fruit", "Leaf", "Pharma", "Soil", "Other"]:
            names = [ds for ds in paired.index if buckets.get(ds, "Other") == bucket]
            if not names:
                continue
            ax.scatter(
                paired.loc[names, "reference"],
                paired.loc[names, "candidate"],
                s=32,
                color=palette[bucket],
                edgecolor=COLOR_AXIS,
                linewidth=0.35,
                alpha=0.86,
                label=bucket,
                zorder=3,
            )
        ax.plot([lo, hi], [lo, hi], color=COLOR_REFERENCE, linewidth=0.8, linestyle=(0, (4, 3)), zorder=2)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(lo, hi)
        ax.set_ylim(lo, hi)
        ax.set_xlabel("Reference RMSEP")
        ax.set_ylabel("AOM RMSEP")
        stat = by_label[stat_label]
        s = stat["stats"]
        ax.set_title(title)
        ax.text(
            0.03,
            0.97,
            f"$N={s['n']}$; wins {s['wins']}/{s['n']}\nmedian ratio {s['median']:.3f}; $p_{{Holm}}={fmt_p(stat['p_holm'])}$",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=7.2,
            bbox={"facecolor": "white", "edgecolor": COLOR_GRID, "linewidth": 0.4, "alpha": 0.86},
        )
        style_grid(ax, axis="both")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    if handles:
        fig.legend(
            handles,
            labels,
            loc="outside lower center",
            ncol=min(6, len(labels)),
            frameon=True,
            title="Domain",
            title_fontsize=8.0,
        )
    save_fig(fig, "fig_paired_rmsep_scatter")


def build_r2_cdf(dfs: dict[str, pd.DataFrame]) -> None:
    strict = _strict_dataset_list(dfs)
    n = len(strict)
    specs = [
        ("PLS-default", dfs["default"], "pls-default-cv5", FAMILY_COLORS["PLS"], "-"),
        ("PLS-HPO", dfs["pls_hpo"], "pls-tabpfn-hpo-25trials", FAMILY_COLORS["PLS"], "--"),
        ("AOM-PLS (simple)", dfs["aompls"], "AOM-compact-cv5-numpy", FAMILY_COLORS["AOM-PLS"], "-"),
        ("AOM-PLS (best)", dfs["aompls"], "ASLS-AOM-compact-cv5-numpy", FAMILY_COLORS["AOM-PLS"], "--"),
        ("Ridge-default", dfs["default"], "ridge-default-cv5", FAMILY_COLORS["Ridge"], "-"),
        ("Ridge-HPO", dfs["ridge_hpo"], "ridge-tabpfn-hpo-60trials", FAMILY_COLORS["Ridge"], "--"),
        ("AOM-Ridge (simple)", dfs["ridge_head"], "AOMRidge-global-compact-none", FAMILY_COLORS["AOM-Ridge"], "-"),
        ("AOM-Ridge (best)", dfs["ridge_head"], "AOMRidge-Blender-headline-spxy3", FAMILY_COLORS["AOM-Ridge"], "--"),
    ]
    x_lo, x_hi = -0.5, 1.0
    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    legend_entries: list[tuple[Line2D, str]] = []
    for label, df, variant, color, linestyle in specs:
        vals = _series_for_variant(df, variant, "r2").reindex(strict).dropna().to_numpy(dtype=float)
        vals = vals[np.isfinite(vals)]
        if vals.size == 0:
            continue
        below = int((vals < x_lo).sum())
        vals_clipped = np.clip(vals, x_lo, None)
        ordered = np.sort(vals_clipped)
        y = (ordered.size - np.arange(ordered.size)) / ordered.size
        x_steps = np.concatenate([[x_lo], ordered, [x_hi]])
        y_steps = np.concatenate([[1.0], y, [y[-1] if y.size else 0.0]])
        ax.step(x_steps, y_steps, where="post", color=color, linestyle=linestyle, linewidth=1.4)
        suffix = f" ({below}/{vals.size} with $R^2<-0.5$)" if below else ""
        handle = Line2D([], [], color=color, linestyle=linestyle, linewidth=1.4)
        legend_entries.append((handle, label + suffix))
    ax.axvline(0.0, color=COLOR_REFERENCE, linewidth=0.6, linestyle=(0, (2, 3)), zorder=1)
    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(0.0, 1.02)
    ax.set_xlabel(r"$R^2$ threshold")
    ax.set_ylabel(r"Fraction of datasets with $R^2 \geq$ threshold")
    ax.set_title(rf"$R^2$ coverage curve ($N={n}$ datasets, $R^2$ clipped at $-0.5$)")
    style_grid(ax, axis="both")
    if legend_entries:
        handles, labels = zip(*legend_entries, strict=True)
        ax.legend(handles, labels, loc="lower left", ncol=2, frameon=True, fontsize=7.5)
    save_fig(fig, "fig_r2_cdf")


def build_gain_per_dataset(dfs: dict[str, pd.DataFrame]) -> None:
    strict = _strict_dataset_list(dfs)

    def gain(cand_df: pd.DataFrame, cand_variant: str, ref_df: pd.DataFrame, ref_variant: str) -> pd.Series:
        cand = _series_for_variant(cand_df, cand_variant, "rmsep")
        ref = _series_for_variant(ref_df, ref_variant, "rmsep")
        paired = pd.DataFrame({"candidate": cand, "reference": ref}).reindex(strict)
        out = 100.0 * (paired["reference"] - paired["candidate"]) / paired["reference"].replace(0, np.nan)
        return out.replace([np.inf, -np.inf], np.nan)

    pls_default = gain(dfs["aompls"], "ASLS-AOM-compact-cv5-numpy", dfs["default"], "pls-default-cv5")
    pls_hpo = gain(dfs["aompls"], "ASLS-AOM-compact-cv5-numpy", dfs["pls_hpo"], "pls-tabpfn-hpo-25trials")
    ridge_default = gain(dfs["ridge_head"], "AOMRidge-Blender-headline-spxy3", dfs["default"], "ridge-default-cv5")
    ridge_hpo = gain(dfs["ridge_head"], "AOMRidge-Blender-headline-spxy3", dfs["ridge_hpo"], "ridge-tabpfn-hpo-60trials")
    order = pls_default.sort_values(ascending=False, na_position="last").index.tolist()
    y = np.arange(len(order))

    fig, axes = plt.subplots(1, 2, figsize=(8.2, max(5.0, 0.22 * len(order) + 1.0)), sharey=True)

    def draw_panel(ax, title: str, left: pd.Series, right: pd.Series, family_color: str, labels: tuple[str, str]) -> None:
        left_vals = left.reindex(order).to_numpy(dtype=float)
        right_vals = right.reindex(order).to_numpy(dtype=float)
        left_colors = [family_color if np.isfinite(v) and v >= 0 else COLOR_REFERENCE for v in left_vals]
        right_colors = [family_color if np.isfinite(v) and v >= 0 else COLOR_REFERENCE for v in right_vals]
        ax.barh(y - 0.18, left_vals, height=0.34, color=left_colors, edgecolor=COLOR_AXIS, linewidth=0.35, alpha=0.92, label=labels[0], zorder=3)
        ax.barh(y + 0.18, right_vals, height=0.34, color=right_colors, edgecolor=COLOR_AXIS, linewidth=0.35, alpha=0.62, label=labels[1], zorder=3)
        ax.axvline(0.0, color=COLOR_REFERENCE, linewidth=0.8, zorder=2)
        ax.set_title(title)
        ax.set_xlabel("RMSEP reduction (%)")
        style_grid(ax, axis="x")
        ax.legend(loc="lower right", frameon=True)

    draw_panel(
        axes[0],
        "AOM-PLS best gain",
        pls_default,
        pls_hpo,
        FAMILY_COLORS["AOM-PLS"],
        ("vs PLS-default", "vs PLS-HPO"),
    )
    draw_panel(
        axes[1],
        "AOM-Ridge best gain",
        ridge_default,
        ridge_hpo,
        FAMILY_COLORS["AOM-Ridge"],
        ("vs Ridge-default", "vs Ridge-HPO"),
    )
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(order, fontsize=6.8)
    axes[1].tick_params(axis="y", labelleft=False)
    axes[0].invert_yaxis()
    all_gain = pd.concat([pls_default, pls_hpo, ridge_default, ridge_hpo]).dropna()
    if not all_gain.empty:
        lo = float(all_gain.min())
        hi = float(all_gain.max())
        pad = max(2.0, 0.08 * (hi - lo))
        for ax in axes:
            ax.set_xlim(lo - pad, hi + pad)
    save_fig(fig, "fig_gain_per_dataset")


def build_budget_figure(dfs: dict[str, pd.DataFrame]) -> None:
    def _median_n_trials(df: pd.DataFrame, variant: str, fallback: int) -> int:
        sub = df[df["variant"].astype("string").str.lower() == variant.lower()]
        vals = pd.to_numeric(sub.get("n_trials"), errors="coerce").dropna()
        if vals.empty:
            return fallback
        return int(round(float(vals.median())))

    def _median_time(df: pd.DataFrame, variant: str) -> float:
        sub = df[df["variant"].astype("string").str.lower() == variant.lower()]
        vals = pd.to_numeric(sub.get("total_time_s", sub.get("fit_time_s")), errors="coerce").dropna()
        if vals.empty:
            vals = pd.to_numeric(sub.get("fit_time_s"), errors="coerce").dropna()
        return float(vals.median()) if not vals.empty else float("nan")

    # Counts follow the runner-level search units. Linear defaults/HPO use the
    # logged n_trials. AOM-PLS global-CV fits one max-prefix model per operator
    # and fold (9 x CV-5). AOM-Ridge global screens operator-alpha cells
    # (9 operators x 50 alpha values). Blender screens eight headline
    # candidates over three outer folds and then refits all eight candidates.
    specs = [
        ("PLS-default", _median_n_trials(dfs["default"], "pls-default-cv5", 25), "PLS", None),
        ("PLS-HPO", _median_n_trials(dfs["pls_hpo"], "pls-tabpfn-hpo-25trials", 3000), "PLS", None),
        ("AOM-PLS (simple)", 9 * 5, "AOM-PLS", _median_time(dfs["aompls"], "AOM-compact-cv5-numpy")),
        ("AOM-PLS (best)", 9 * 5, "AOM-PLS", _median_time(dfs["aompls"], "ASLS-AOM-compact-cv5-numpy")),
        ("Ridge-default", _median_n_trials(dfs["default"], "ridge-default-cv5", 15), "Ridge", None),
        ("Ridge-HPO", _median_n_trials(dfs["ridge_hpo"], "ridge-tabpfn-hpo-60trials", 6000), "Ridge", None),
        ("AOM-Ridge (simple)", 9 * 50, "AOM-Ridge", _median_time(dfs["ridge_head"], "AOMRidge-global-compact-none")),
        ("AOM-Ridge (best)", 8 * 3 + 8, "AOM-Ridge", _median_time(dfs["ridge_head"], "AOMRidge-Blender-headline-spxy3")),
    ]
    labels = [s[0] for s in specs]
    evals = [s[1] for s in specs]
    bar_colors = [FAMILY_COLORS[s[2]] for s in specs]
    fig, ax = plt.subplots(figsize=(7.0, 3.7))
    bars = ax.bar(labels, evals, color=bar_colors, edgecolor=COLOR_AXIS, linewidth=0.5, zorder=3)
    ax.set_yscale("log")
    ax.set_ylabel("Runner-level search units (log scale)")
    ax.set_title("Search-budget scale")
    ax.tick_params(axis="x", rotation=25)
    for label_obj in ax.get_xticklabels():
        label_obj.set_horizontalalignment("right")
    # Annotate each bar with its value for direct readability.
    for bar_obj, value, (_, _, _, med_time) in zip(bars, evals, specs, strict=True):
        text = f"{value:,}"
        if med_time is not None and np.isfinite(med_time):
            text = f"{value:,} fits | {med_time:.2f} s"
        ax.text(
            bar_obj.get_x() + bar_obj.get_width() / 2,
            value * 1.08,
            text,
            ha="center", va="bottom",
            fontsize=7.0, color=COLOR_AXIS,
            rotation=0,
        )
    ax.set_ylim(top=max(evals) * 2.2)
    style_grid(ax, axis="y")
    save_fig(fig, "fig_budget", png=False)


def build_operator_heatmap() -> None:
    diag = pd.read_csv(REVIEW / "selector_diagnostics.csv", low_memory=False)
    diag = diag[diag["variant"].isin(["AOM-compact-cv5-numpy", "ASLS-AOM-compact-cv5-numpy"])]
    op_cols = [c for c in diag.columns if c.startswith("selected_op_")]
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for _, row in diag.iterrows():
        ds = row["dataset"]
        for col in op_cols:
            op = row.get(col)
            if isinstance(op, str) and op:
                counts[ds][op] += 1
    ops = list(pd.read_csv(REVIEW / "operator_frequency.csv")["operator"])
    manifest = pd.read_csv(REVIEW / "cohort_manifest.csv")
    domain = dict(zip(manifest["dataset"], manifest["domain_group"], strict=False))
    datasets = sorted(counts, key=lambda d: (str(domain.get(d, "zzz")), d))
    matrix = np.array([[counts[d].get(op, 0) for op in ops] for d in datasets], dtype=float)

    # Compact dataset labels: trim long dataset IDs to a sensible length so the
    # tick labels are legible at 7pt without distorting the figure.
    def _short(name: str, n: int = 38) -> str:
        return name if len(name) <= n else name[: n - 1] + "…"

    y_labels = [f"{domain.get(d, 'other')} : {_short(d)}" for d in datasets]

    # Height scaled for ~0.22 inch per row so 7pt labels remain readable.
    row_h = 0.22
    fig_h = max(6.5, 1.6 + row_h * len(datasets))
    fig, ax = plt.subplots(figsize=(7.6, fig_h))
    im = ax.imshow(matrix, aspect="auto", cmap="viridis", interpolation="nearest")
    ax.set_xticks(np.arange(len(ops)))
    ax.set_xticklabels(ops, rotation=40, ha="right", fontsize=8.0)
    ax.set_yticks(np.arange(len(datasets)))
    ax.set_yticklabels(y_labels, fontsize=7.0)
    ax.tick_params(axis="both", length=2.0)
    ax.set_title("Compact-bank operator selections by dataset")
    # Thin separator lines between cells for visual grouping.
    ax.set_xticks(np.arange(-0.5, len(ops), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(datasets), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=0.4)
    ax.tick_params(which="minor", length=0)
    cbar = fig.colorbar(im, ax=ax, fraction=0.028, pad=0.012, aspect=40)
    cbar.set_label("Selection count across components / seeds", fontsize=8.5)
    cbar.ax.tick_params(labelsize=7.5, width=0.5, length=2.5)
    if cbar.outline is not None:
        cbar.outline.set_linewidth(0.5)  # type: ignore[operator]  # matplotlib stubs are imprecise
    save_fig(fig, "fig_operator_heatmap")


def build_dataset_variant_heatmap(dfs: dict[str, pd.DataFrame]) -> None:
    strict_datasets = dfs["strict_datasets"]["dataset"].astype(str).tolist()
    wide = paper_data.filter_to_datasets(pd.read_csv(FAST_WIDE, low_memory=False), strict_datasets)

    ref = (
        wide[["dataset", "PLS-standard-numpy"]]
        .assign(_ref=lambda x: pd.to_numeric(x["PLS-standard-numpy"], errors="coerce"))
        .groupby("dataset")["_ref"]
        .mean()
    )

    def _long_series(df: pd.DataFrame, variant: str) -> pd.Series:
        sub = df[df["variant"].astype("string").str.lower() == variant.lower()].copy()
        if sub.empty:
            return pd.Series(dtype=float)
        sub["dataset"] = dataset_id(sub["dataset"])
        return sub.assign(_rmsep=pd.to_numeric(sub["rmsep"], errors="coerce")).groupby("dataset")["_rmsep"].mean()

    def _aompls_series(variant: str) -> pd.Series:
        df = dfs["aompls"].copy()
        sub = df[df["variant"].astype("string").str.lower() == variant.lower()].copy()
        if sub.empty:
            return pd.Series(dtype=float)
        sub["dataset"] = dataset_id(sub["dataset"])
        return sub.assign(_rmsep=pd.to_numeric(sub["rmsep"], errors="coerce")).groupby("dataset")["_rmsep"].mean()

    def _wide_series(variant: str) -> pd.Series:
        if variant not in wide.columns:
            return pd.Series(dtype=float)
        return (
            wide[["dataset", variant]]
            .assign(_rmsep=lambda x: pd.to_numeric(x[variant], errors="coerce"))
            .groupby("dataset")["_rmsep"]
            .mean()
        )

    columns = [
        ("PLS-default", _long_series(dfs["default"], "pls-default-cv5")),
        ("PLS-HPO", _long_series(dfs["pls_hpo"], "pls-tabpfn-hpo-25trials")),
        ("AOM-PLS (simple)", _aompls_series("AOM-compact-cv5-numpy")),
        ("AOM-PLS (best)", _aompls_series("ASLS-AOM-compact-cv5-numpy")),
        ("Ridge-default", _long_series(dfs["default"], "ridge-default-cv5")),
        ("Ridge-HPO", _long_series(dfs["ridge_hpo"], "ridge-tabpfn-hpo-60trials")),
        ("AOM-Ridge (simple)", _long_series(dfs["ridge_head"], "AOMRidge-global-compact-none")),
        ("AOM-Ridge (best)", _long_series(dfs["ridge_head"], "AOMRidge-Blender-headline-spxy3")),
        ("FastAOM-sparse-mkr-supervised", _wide_series("FastAOM-sparse-mkr-supervised")),
        ("FastAOM-sparse-mkr-compact", _wide_series("FastAOM-sparse-mkr-compact")),
        ("FastAOM-single-chain-compact", _wide_series("FastAOM-single-chain-compact")),
        ("FastAOM-soft-chain-compact", _wide_series("FastAOM-soft-chain-compact")),
        ("FastAOM-hard-chain-compact", _wide_series("FastAOM-hard-chain-compact")),
        ("POP-nipals-adjoint-numpy", _wide_series("POP-nipals-adjoint-numpy")),
    ]
    variants = [label for label, _ in columns]
    datasets = strict_datasets
    matrix = []
    for ds in datasets:
        vals = []
        ref_val = float(ref.get(ds, np.nan))
        for _, series in columns:
            val = float(series.get(ds, np.nan))
            vals.append(
                val / ref_val
                if np.isfinite(val) and np.isfinite(ref_val) and ref_val > 0 and ds not in EXCLUDED_RATIO_DATASETS
                else np.nan
            )
        matrix.append(vals)
    data = np.array(matrix, dtype=float)
    # Clip symmetrically around 1.0 so the diverging colour scale is meaningful.
    vmin, vmax = 0.70, 1.30
    masked = np.ma.masked_invalid(np.clip(data, vmin, vmax))
    # Diverging colormap centered on 1.0 (PLS-standard reference). Blue = win,
    # red = loss. RdBu_r is colour-blind safe and the de-facto journal default
    # for ratio plots centered on a meaningful midpoint.
    cmap = plt.get_cmap("RdBu_r").copy()
    cmap.set_bad("#eeeeee")
    norm = matplotlib.colors.TwoSlopeNorm(vmin=vmin, vcenter=1.0, vmax=vmax)

    def _short(name: str, n: int = 32) -> str:
        return name if len(name) <= n else name[: n - 1] + "…"

    row_h = 0.20
    fig_h = max(6.0, 1.6 + row_h * len(datasets))
    fig, ax = plt.subplots(figsize=(7.4, fig_h))
    im = ax.imshow(masked, aspect="auto", cmap=cmap, norm=norm, interpolation="nearest")
    ax.set_xticks(np.arange(len(variants)))
    ax.set_xticklabels(variants, rotation=35, ha="right", fontsize=8.0)
    ax.set_yticks(np.arange(len(datasets)))
    ax.set_yticklabels([_short(d) for d in datasets], fontsize=6.8)
    ax.tick_params(axis="both", length=2.0)
    # Thin white separators between cells, matches the operator heatmap.
    ax.set_xticks(np.arange(-0.5, len(variants), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(datasets), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=0.4)
    ax.tick_params(which="minor", length=0)
    ax.set_title("Per-dataset RMSEP ratios vs PLS-standard")
    cbar = fig.colorbar(im, ax=ax, fraction=0.028, pad=0.012, aspect=40,
                        ticks=[0.70, 0.85, 1.00, 1.15, 1.30])
    cbar.set_label("RMSEP ratio  (blue = win,  red = loss; clipped to [0.70, 1.30])", fontsize=8.5)
    cbar.ax.tick_params(labelsize=7.5, width=0.5, length=2.5)
    if cbar.outline is not None:
        cbar.outline.set_linewidth(0.5)  # type: ignore[operator]  # matplotlib stubs are imprecise
    save_fig(fig, "fig_dataset_variant_heatmap")


def build_fastaom_variants_figure() -> None:
    summary = pd.read_csv(FAST_SUMMARY)
    rows = summary[summary["model"].astype(str).str.startswith("FastAOM")].copy()
    rows = rows.sort_values("median_rel_rmse", ascending=False)
    y = np.arange(len(rows))
    fig, ax1 = plt.subplots(figsize=(7.0, max(3.8, 0.34 * len(rows) + 0.6)))
    bars = ax1.barh(
        y, rows["median_rel_rmse"],
        color=FAMILY_COLORS["FastAOM"], alpha=0.92,
        edgecolor=COLOR_AXIS, linewidth=0.5, zorder=3,
    )
    ax1.axvline(1.0, color=COLOR_REFERENCE, linewidth=0.7, linestyle=(0, (4, 3)), zorder=2)
    ax1.set_yticks(y)
    ax1.set_yticklabels(rows["model"], fontsize=7.5)
    ax1.set_xlabel("Median relative RMSEP")
    ax1.set_title("FastAOM model-family comparison")
    ax2 = ax1.twiny()
    ax2.spines["top"].set_visible(True)
    ax2.spines["top"].set_color(COLOR_AXIS)
    ax2.spines["top"].set_linewidth(0.7)
    pts = ax2.scatter(
        rows["median_fit_time"], y,
        color=FAMILY_COLORS["AOM-PLS"], edgecolor=COLOR_AXIS, linewidth=0.4,
        s=44, zorder=4, label="Median fit time",
    )
    ax2.set_xscale("log")
    ax2.set_xlabel("Median fit time (s, log scale)")
    style_grid(ax1, axis="x")
    # Combined legend so the twin-axis encoding is unambiguous.
    ax1.legend(
        [bars, pts],
        ["Median relative RMSEP (bottom axis)", "Median fit time (top axis, log s)"],
        loc="lower right", frameon=True,
    )
    save_fig(fig, "fig_fastaom_variants")


def write_v3_stats(rows: list[dict], dfs: dict[str, pd.DataFrame]) -> None:
    fast_summary = pd.read_csv(FAST_SUMMARY)
    strict_n = len(_strict_dataset_list(dfs))
    by_label = {r["label"]: r for r in rows}
    lines = [
        "# AOM v3 statistics summary",
        "",
        "## Linear cartesian-HPO denominator",
        f"- Main regression comparisons use the strict intersection N_cap={strict_n} across the eight paper variants.",
        "",
        "## FastAOM top variants after N >= 50 filter",
    ]
    top_fast = fast_summary[fast_summary["model"].str.startswith("FastAOM") & (fast_summary["n_datasets"] >= 50)].sort_values("median_rel_rmse").head(3)
    for _, r in top_fast.iterrows():
        lines.append(
            f"- {r['model']}: N={int(r['n_datasets'])}, median_rel_rmse={float(r['median_rel_rmse']):.3f}, median_fit_time={float(r['median_fit_time']):.2f}s."
        )
    lines += ["", "## Paired comparisons", "| Comparison | N | Median ratio | CI | Wins | p_Holm |", "| --- | ---: | ---: | --- | ---: | ---: |"]
    for r in rows:
        s = r["stats"]
        lines.append(
            f"| {r['label']} | {s['n']} | {fmt_float(s['median'])} | {fmt_float(s['ci_low'])}-{fmt_float(s['ci_high'])} | {s['wins']}/{s['n']} | {fmt_p(r['p_holm'])} |"
        )
    # Friedman rank on common FastAOM/AOM/PLS subset from wide table.
    wide = pd.read_csv(FAST_WIDE, low_memory=False)
    methods = [
        "PLS-standard-numpy",
        "ASLS-AOM-compact-cv5-numpy",
        "AOM-compact-cv5-numpy",
        "FastAOM-sparse-mkr-supervised",
        "FastAOM-sparse-mkr-compact",
        "FastAOM-single-chain-compact",
    ]
    complete = wide[methods].apply(pd.to_numeric, errors="coerce").dropna()
    ranks = complete.rank(axis=1, ascending=True)
    fried = stats.friedmanchisquare(*[complete[m].to_numpy() for m in methods])
    lines += [
        "",
        "## Friedman rank, FastAOM/AOM/PLS common subset",
        f"- N={len(complete)}, methods={len(methods)}, chi2={fried.statistic:.3f}, p={fried.pvalue:.3g}.",
        "- Mean ranks, smaller is better:",
    ]
    for method, rank in ranks.mean().sort_values().items():
        lines.append(f"  - {method}: {rank:.2f}")
    (REVIEW / "v3_stats.md").write_text("\n".join(lines) + "\n")

    current = (REVIEW / "final_stats.md").read_text()
    marker = "\n## v3 FastAOM and cartesian-HPO supplement\n"
    if marker in current:
        current = current.split(marker)[0].rstrip() + "\n"
    addition = marker + "\n".join(lines[2:]) + "\n"
    (REVIEW / "final_stats.md").write_text(current.rstrip() + "\n" + addition)


def main() -> int:
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    rows, dfs = build_regression_stats()
    write_table_main(rows)
    write_table_paired(rows)
    write_time_table(dfs)
    write_fast_table()
    write_long_results()
    write_classification_tables()
    write_selector_table()
    write_seed_stability_table(dfs)
    write_failure_table()
    write_dataset_tables()
    update_static_tables()
    build_figures(rows, dfs)
    paper_data.write_missing_datasets_doc()
    write_v3_stats(rows, dfs)
    print(
        json.dumps(
            {
                "paired_rows": len(rows),
                "tables": [
                    "table_main_results.tex",
                    "table_paired_stats.tex",
                    "table_time_budget.tex",
                    "table_fastaom_variants.tex",
                    "table_supplement_long_results.tex",
                    "table_classification_main.tex",
                    "table_classification_full.tex",
                    "table_seed_stability.tex",
                    "table_failure_modes.tex",
                    "table_dataset_statistics.tex",
                    "table_dataset_overview_supp.tex",
                ],
                "figures": [
                    "fig_dataset_diversity",
                    "fig_accuracy_time_pareto",
                    "fig_runtime_distribution",
                    "fig_results",
                    "fig_paired_rmsep_scatter",
                    "fig_r2_cdf",
                    "fig_gain_per_dataset",
                    "fig_budget",
                    "fig_operator_heatmap",
                    "fig_dataset_variant_heatmap",
                    "fig_fastaom_variants",
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
