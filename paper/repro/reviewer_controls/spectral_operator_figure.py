#!/usr/bin/env python3
"""Create the manuscript spectral illustration from a real cohort task.

The script uses the ALPINE phosphorus calibration task and exact operators from
the compact AOM bank. It exports the plotted summaries as CSV so the figure has
a structured text/data alternative.
"""

# ruff: noqa: E402 -- the non-interactive plotting backend precedes local imports.

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
plt.rcParams["svg.fonttype"] = "none"

from aom_nirs.pls.operators import DetrendProjectionOperator, SavitzkyGolayOperator


DATASET = "ALPINE_P_291_KS"
COLORS = {"Alps": "#0072B2", "Fennoscandia": "#D55E00"}
LINESTYLES = {"Alps": "-", "Fennoscandia": "--"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("/home/delete/nirs4all/nirs4all-data"),
        help="Root containing regression/ALPINE (default: local companion checkout).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "figures",
    )
    return parser.parse_args()


def load_data(data_root: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    task = data_root / "regression" / "ALPINE" / DATASET
    xframe = pd.read_csv(task / "Xtrain.csv", sep=";")
    metadata = pd.read_csv(task / "Mtrain.csv", sep=";")
    if len(xframe) != len(metadata):
        raise ValueError(f"spectra/metadata length mismatch: {len(xframe)} != {len(metadata)}")
    wavelengths = np.asarray([float(column) for column in xframe.columns], dtype=float)
    spectra = xframe.to_numpy(dtype=float)
    origin = metadata["Origin"].astype(str).to_numpy()
    return wavelengths, spectra, origin


def summarize(
    wavelengths: np.ndarray,
    values: np.ndarray,
    groups: np.ndarray,
    operator: str,
) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for group in ("Alps", "Fennoscandia"):
        selected = values[groups == group]
        if not len(selected):
            continue
        rows.append(
            pd.DataFrame(
                {
                    "wavelength_nm": wavelengths,
                    "operator": operator,
                    "origin": group,
                    "n_spectra": len(selected),
                    "q10": np.quantile(selected, 0.10, axis=0),
                    "median": np.median(selected, axis=0),
                    "q90": np.quantile(selected, 0.90, axis=0),
                }
            )
        )
    return pd.concat(rows, ignore_index=True)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    wavelengths, spectra, origin = load_data(args.data_root.expanduser().resolve())

    transforms = [
        ("Raw", spectra, "Reflectance"),
        (
            "SG smooth (w=21, p=3)",
            SavitzkyGolayOperator(window_length=21, polyorder=3, deriv=0).transform(spectra),
            "Smoothed reflectance",
        ),
        (
            "SG first derivative (w=21, p=3)",
            SavitzkyGolayOperator(window_length=21, polyorder=3, deriv=1).transform(spectra),
            "First derivative (a.u.)",
        ),
        (
            "Linear detrend (degree=1)",
            DetrendProjectionOperator(degree=1).transform(spectra),
            "Detrended reflectance",
        ),
    ]

    summaries = pd.concat(
        [summarize(wavelengths, values, origin, name) for name, values, _ in transforms],
        ignore_index=True,
    )
    display = summaries.query("1000 <= wavelength_nm <= 2450").copy()
    source_path = args.output_dir / "fig_spectral_operators_source_data.csv"
    display.to_csv(source_path, index=False)

    plt.rcParams.update(
        {
            "font.size": 7.0,
            "axes.titlesize": 8.0,
            "axes.labelsize": 7.2,
            "xtick.labelsize": 6.5,
            "ytick.labelsize": 6.5,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.7,
            "pdf.fonttype": 42,
        }
    )
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.05), sharex=True)
    for label, ax, (name, _, ylabel) in zip("abcd", axes.flat, transforms, strict=True):
        panel = display[display["operator"] == name]
        for group in ("Alps", "Fennoscandia"):
            rows = panel[panel["origin"] == group]
            x = rows["wavelength_nm"].to_numpy(float)
            med = rows["median"].to_numpy(float)
            lo = rows["q10"].to_numpy(float)
            hi = rows["q90"].to_numpy(float)
            n = int(rows["n_spectra"].iloc[0])
            ax.fill_between(x, lo, hi, color=COLORS[group], alpha=0.13, linewidth=0)
            ax.plot(
                x,
                med,
                color=COLORS[group],
                linestyle=LINESTYLES[group],
                linewidth=1.05,
                label=f"{group} (n={n})",
            )
        ax.set_title(name, loc="left", fontweight="bold")
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", color="#d9dee3", linewidth=0.45, alpha=0.7)
        ax.text(-0.12, 1.08, label, transform=ax.transAxes, fontweight="bold", fontsize=8.5)
    for ax in axes[-1, :]:
        ax.set_xlabel("Wavelength (nm)")
    axes[0, 0].legend(loc="best", fontsize=6.5)
    fig.suptitle(
        "Real NIR spectra under three strict-linear AOM operators",
        x=0.075,
        y=0.985,
        ha="left",
        fontsize=9.0,
        fontweight="bold",
    )
    fig.subplots_adjust(left=0.095, right=0.985, bottom=0.105, top=0.86, hspace=0.38, wspace=0.24)

    base = args.output_dir / "fig_spectral_operators"
    svg_path = base.with_suffix(".svg")
    fig.savefig(svg_path, bbox_inches="tight")
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_path.read_text(encoding="utf-8").splitlines()) + "\n",
        encoding="utf-8",
    )
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".tiff"), dpi=600, bbox_inches="tight")
    fig.savefig(base.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)

    counts = pd.Series(origin).value_counts().sort_index()
    summary_path = args.output_dir / "fig_spectral_operators_summary.txt"
    summary_path.write_text(
        "Representative raw and transformed spectra from the real ALPINE phosphorus task.\n"
        f"Total training spectra: {len(spectra)}; "
        + "; ".join(f"{group}: {count}" for group, count in counts.items())
        + ".\n"
        "SG smoothing suppresses high-frequency variation while retaining broad bands; "
        "the first derivative emphasizes local slopes and reduces offsets; degree-1 "
        "detrending removes constant and linear wavelength backgrounds.\n"
        f"Structured source data: {source_path.name}.\n",
        encoding="utf-8",
    )
    print(f"wrote {base.with_suffix('.svg')}")
    print(f"wrote {base.with_suffix('.pdf')}")
    print(f"wrote {base.with_suffix('.tiff')}")
    print(f"wrote {source_path}")


if __name__ == "__main__":
    main()
