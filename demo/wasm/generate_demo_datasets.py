#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Generate the documented, visually rich spectra bundled with the WASM demo."""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Recipe:
    dataset_id: str
    seed: int
    complexity: str
    target_index: int
    target_name: str
    include_batch_effects: bool = False
    n_batches: int = 1


RECIPES = (
    Recipe("food_composition", 101, "realistic", 1, "Protein (%)"),
    Recipe("grain_starch", 713, "realistic", 3, "Starch (%)"),
    Recipe("batch_process", 303, "realistic", 0, "Water (%)", True, 4),
)


def write_matrix(path: Path, data: np.ndarray, header: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(header)
        writer.writerows((f"{value:.8f}" for value in row) for row in data)


def write_target(path: Path, data: np.ndarray, name: str) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow([name])
        writer.writerows([f"{value:.8f}"] for value in data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--nirs4all-dir",
        type=Path,
        required=True,
        help="Checkout containing the nirs4all synthesis package.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "datasets",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(args.nirs4all_dir.resolve()))
    from nirs4all.synthesis import SyntheticNIRSGenerator

    wavelengths = np.arange(1000.0, 2500.0 + 5.0, 5.0)
    header = [f"{value:g}" for value in wavelengths]
    for recipe in RECIPES:
        generator = SyntheticNIRSGenerator(
            wavelengths=wavelengths,
            complexity=recipe.complexity,
            random_state=recipe.seed,
        )
        spectra, concentrations, _, _ = generator.generate(
            n_samples=120,
            concentration_method="dirichlet",
            include_batch_effects=recipe.include_batch_effects,
            n_batches=recipe.n_batches,
            return_metadata=True,
        )
        target = concentrations[:, recipe.target_index] * 100.0
        order = np.random.default_rng(recipe.seed + 10_000).permutation(len(target))
        calibration, validation = order[:90], order[90:]
        dataset_dir = args.output_dir / recipe.dataset_id
        dataset_dir.mkdir(parents=True, exist_ok=True)
        write_matrix(dataset_dir / "Xcal.csv", spectra[calibration], header)
        write_target(dataset_dir / "Ycal.csv", target[calibration], recipe.target_name)
        write_matrix(dataset_dir / "Xval.csv", spectra[validation], header)
        write_target(dataset_dir / "Yval.csv", target[validation], recipe.target_name)
        print(
            f"{recipe.dataset_id}: 90 calibration + 30 validation, "
            f"{spectra.shape[1]} wavelengths, target {target.min():.2f}–{target.max():.2f}%"
        )


if __name__ == "__main__":
    main()
