from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import ensure_directory


def _extract_fluence(result: dict[str, Any]) -> np.ndarray:
    if "fluence" in result:
        return np.asarray(result["fluence"])
    pmcx_result = result["pmcx_result"]
    flux = np.asarray(pmcx_result["flux"])
    return np.squeeze(flux, axis=-1) if flux.ndim == 4 and flux.shape[-1] == 1 else flux


def plot_cross_section(result: dict[str, Any], axis: str = "z", output_path: Path | str | None = None) -> Path:
    fluence = _extract_fluence(result)
    axis_map = {"x": 0, "y": 1, "z": 2}
    if axis not in axis_map:
        raise ValueError(f"Unsupported axis: {axis}")

    axis_index = axis_map[axis]
    slice_index = fluence.shape[axis_index] // 2
    if axis_index == 0:
        slice_2d = fluence[slice_index, :, :].T
    elif axis_index == 1:
        slice_2d = fluence[:, slice_index, :].T
    else:
        slice_2d = fluence[:, :, slice_index].T

    figure_path = Path(output_path or Path.cwd() / f"fluence_{axis}.png")
    ensure_directory(figure_path.parent)

    fig, ax = plt.subplots(figsize=(5, 4), constrained_layout=True)
    image = ax.imshow(slice_2d, origin="lower", cmap="magma")
    ax.set_title(f"Fluence {axis}-slice @ {slice_index}")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    fig.colorbar(image, ax=ax, shrink=0.8)
    fig.savefig(figure_path, dpi=150)
    plt.close(fig)
    return figure_path


def plot_detector_summary(results_df: pd.DataFrame, output_path: Path | str | None = None) -> Path:
    figure_path = Path(output_path or Path.cwd() / "detector_summary.png")
    ensure_directory(figure_path.parent)

    fig, ax = plt.subplots(figsize=(8, 4), constrained_layout=True)
    if results_df.empty:
        ax.text(0.5, 0.5, "No detector data", ha="center", va="center")
        ax.set_axis_off()
    else:
        grouped = results_df.groupby("case_id", as_index=False)["detected_photons"].sum()
        x_positions = np.arange(len(grouped))
        ax.bar(x_positions, grouped["detected_photons"], color="#2f6db3")
        ax.set_ylabel("Detected photons")
        ax.set_xlabel("Case ID")
        ax.set_xticks(x_positions)
        ax.set_xticklabels(grouped["case_id"], rotation=45, ha="right")
    fig.savefig(figure_path, dpi=150)
    plt.close(fig)
    return figure_path


def plot_trajectories(result: dict[str, Any], output_path: Path | str | None = None) -> Path | None:
    detector_samples = result.get("trajectory_samples")
    if not detector_samples:
        return None
    positions = detector_samples.get("p")
    directions = detector_samples.get("v")
    if positions is None or np.asarray(positions).size == 0:
        return None

    positions_array = np.asarray(positions)
    if positions_array.ndim == 1:
        positions_array = positions_array.reshape(3, -1)

    max_points = min(200, positions_array.shape[1])
    positions_array = positions_array[:, :max_points]
    directions_array = None if directions is None else np.asarray(directions)[:, :max_points]

    figure_path = Path(output_path or Path.cwd() / "trajectory_samples.png")
    ensure_directory(figure_path.parent)

    fig = plt.figure(figsize=(6, 5), constrained_layout=True)
    ax = fig.add_subplot(111, projection="3d")
    ax.scatter(positions_array[0], positions_array[1], positions_array[2], s=8, alpha=0.8, c="#d62728")
    if directions_array is not None and directions_array.size:
        ax.quiver(
            positions_array[0],
            positions_array[1],
            positions_array[2],
            directions_array[0],
            directions_array[1],
            directions_array[2],
            length=0.5,
            normalize=True,
            color="#1f77b4",
            alpha=0.6,
        )
    ax.set_title("Detected photon exit samples")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    fig.savefig(figure_path, dpi=150)
    plt.close(fig)
    return figure_path
