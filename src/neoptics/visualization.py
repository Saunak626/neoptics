from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyvista as pv

from .config import ensure_directory
from .geometry import build_wrist_volume


TISSUE_COLORS = {
    "outer": "#d9dde8",
    "skin": "#f4b6c2",
    "fat": "#ffd8a8",
    "bone": "#b8b8b8",
    "artery": "#d62728",
    "vein": "#7f1d1d",
}

TISSUE_LABELS = {
    "outer": None,
    "skin": 1,
    "fat": 2,
    "bone": 4,
    "artery": 5,
    "vein": 6,
}


def _extract_fluence(result: dict[str, Any]) -> np.ndarray:
    if "fluence" in result:
        return np.asarray(result["fluence"])
    pmcx_result = result["pmcx_result"]
    flux = np.asarray(pmcx_result["flux"])
    return np.squeeze(flux, axis=-1) if flux.ndim == 4 and flux.shape[-1] == 1 else flux


def _build_cell_grid(data: np.ndarray, voxel_size_mm: float, array_name: str, origin_mm: tuple[float, float, float]) -> pv.ImageData:
    grid = pv.ImageData(
        dimensions=np.array(data.shape, dtype=int) + 1,
        spacing=(voxel_size_mm, voxel_size_mm, voxel_size_mm),
        origin=origin_mm,
    )
    grid.cell_data[array_name] = np.asarray(data).flatten(order="F")
    return grid


def _build_point_grid(data: np.ndarray, voxel_size_mm: float, array_name: str, origin_mm: tuple[float, float, float]) -> pv.ImageData:
    grid = pv.ImageData(
        dimensions=np.array(data.shape, dtype=int),
        spacing=(voxel_size_mm, voxel_size_mm, voxel_size_mm),
        origin=origin_mm,
    )
    grid.point_data[array_name] = np.asarray(data).flatten(order="F")
    return grid


def _load_case_bundle(case_result_or_dir: dict[str, Any] | Path | str) -> dict[str, Any]:
    if isinstance(case_result_or_dir, dict):
        bundle = dict(case_result_or_dir)
        metadata = bundle.get("metadata")
        if metadata is None:
            raise ValueError("Case result dictionary must include metadata.")
        fluence = bundle.get("fluence")
        if fluence is None:
            fluence = _extract_fluence(bundle)
        trajectory_samples = bundle.get("trajectory_samples")
        detector_summary = bundle.get("detector_summary")
        case_dir = Path(bundle.get("paths", {}).get("case_dir", Path.cwd()))
    else:
        case_dir = Path(case_result_or_dir)
        with (case_dir / "metadata.json").open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)
        fluence = np.load(case_dir / "fluence.npy")
        detector_summary_path = case_dir / "detector_summary.csv"
        detector_summary = pd.read_csv(detector_summary_path) if detector_summary_path.exists() else pd.DataFrame()
        trajectory_samples_path = case_dir / "trajectory_samples.npz"
        if trajectory_samples_path.exists():
            with np.load(trajectory_samples_path) as handle:
                trajectory_samples = {key: np.asarray(handle[key]) for key in handle.files}
        else:
            trajectory_samples = None

    geometry_metadata = metadata["geometry_metadata"]
    volume, rebuilt_metadata = build_wrist_volume(
        profile_name=metadata["profile"],
        overrides=metadata.get("geometry_overrides") or None,
        include_vein=metadata.get("include_vein", False),
        voxel_size_mm=float(metadata["voxel_size_mm"]),
    )

    return {
        "case_dir": case_dir,
        "metadata": metadata,
        "fluence": np.asarray(fluence),
        "trajectory_samples": trajectory_samples,
        "detector_summary": detector_summary,
        "volume": volume,
        "geometry_metadata": rebuilt_metadata if rebuilt_metadata else geometry_metadata,
    }


def _make_detector_sphere(detector_mm: list[float], radius_mm: float) -> pv.PolyData:
    return pv.Sphere(radius=max(radius_mm, 0.25), center=detector_mm[:3], theta_resolution=24, phi_resolution=24)


def _make_source_arrow(source_mm: list[float], source_dir: list[float], scale: float) -> pv.PolyData:
    direction = np.asarray(source_dir[:3], dtype=float)
    norm = np.linalg.norm(direction)
    if norm <= 0:
        direction = np.array([0.0, 1.0, 0.0], dtype=float)
    else:
        direction = direction / norm
    return pv.Arrow(start=source_mm[:3], direction=direction, scale=scale, tip_radius=0.2, shaft_radius=0.08)


def _add_scene_geometry(plotter: pv.Plotter, case_bundle: dict[str, Any], show_samples: bool, show_fluence: bool) -> None:
    metadata = case_bundle["metadata"]
    geometry_metadata = case_bundle["geometry_metadata"]
    volume = np.asarray(case_bundle["volume"])
    fluence = np.asarray(case_bundle["fluence"])
    sensor_config = metadata["sensor_config"]
    voxel_size_mm = float(metadata["voxel_size_mm"])
    domain_mm = geometry_metadata["domain_mm"]
    origin = (
        -float(domain_mm["x"]) / 2.0,
        -float(domain_mm["y"]) / 2.0,
        -float(domain_mm["z"]) / 2.0,
    )

    label_grid = _build_cell_grid(volume, voxel_size_mm, "label", origin)
    for tissue_name in ("outer", "skin", "fat", "bone", "artery", "vein"):
        label_value = TISSUE_LABELS[tissue_name]
        if tissue_name == "vein" and not metadata.get("include_vein", False):
            continue
        if tissue_name == "outer":
            tissue_mesh = label_grid.threshold([0.5, float(np.max(volume)) + 0.5], scalars="label")
            opacity = 0.10
        else:
            tissue_mesh = label_grid.threshold(
                [float(label_value) - 0.1, float(label_value) + 0.1],
                scalars="label",
            )
            opacity = {"skin": 0.22, "fat": 0.16, "bone": 0.35, "artery": 0.70, "vein": 0.55}[tissue_name]
        if tissue_mesh.n_cells > 0:
            plotter.add_mesh(
                tissue_mesh.extract_surface(algorithm="dataset_surface").smooth(n_iter=10),
                color=TISSUE_COLORS[tissue_name],
                opacity=opacity,
                name=f"{tissue_name}_mesh",
                show_scalar_bar=False,
                render_lines_as_tubes=True,
            )

    source_mm = sensor_config["source_mm"]
    detector_mm = sensor_config["detectors_mm"][0]
    plotter.add_mesh(
        pv.Sphere(radius=max(float(sensor_config.get("source_radius_mm", 0.4)), 0.25), center=source_mm[:3]),
        color="#f4a259",
        opacity=1.0,
        name="source_marker",
        show_scalar_bar=False,
    )
    plotter.add_mesh(
        _make_source_arrow(source_mm, sensor_config["srcdir"], scale=1.5),
        color="#ff7f0e",
        opacity=1.0,
        name="source_arrow",
        show_scalar_bar=False,
    )
    plotter.add_mesh(
        _make_detector_sphere(detector_mm, float(detector_mm[3])),
        color="#2f6db3",
        opacity=0.95,
        name="detector_marker",
        show_scalar_bar=False,
    )

    if show_fluence:
        fluence_grid = _build_point_grid(fluence, voxel_size_mm, "fluence", origin)
        positive = fluence[fluence > 0]
        if positive.size:
            contour_levels = np.quantile(positive, [0.85, 0.95]).tolist()
            contour_levels = sorted({float(level) for level in contour_levels if level > 0})
            if contour_levels:
                fluence_mesh = fluence_grid.contour(isosurfaces=contour_levels, scalars="fluence")
                if fluence_mesh.n_cells > 0:
                    plotter.add_mesh(
                        fluence_mesh,
                        scalars="fluence",
                        cmap="magma",
                        opacity=0.35,
                        name="fluence_isosurface",
                        scalar_bar_args={"title": "Fluence"},
                    )

    if show_samples and case_bundle["trajectory_samples"]:
        sample_positions = case_bundle["trajectory_samples"].get("p")
        if sample_positions is not None and np.asarray(sample_positions).size > 0:
            sample_array = np.asarray(sample_positions, dtype=float)
            if sample_array.ndim == 1:
                sample_array = sample_array.reshape(3, -1)
            if sample_array.shape[0] != 3 and sample_array.shape[1] == 3:
                sample_array = sample_array.T
            sample_points = sample_array[:, : min(sample_array.shape[1], 300)].T
            cloud = pv.PolyData(sample_points)
            plotter.add_mesh(
                cloud,
                color="#6a00f4",
                point_size=8,
                render_points_as_spheres=True,
                opacity=0.85,
                name="detected_samples",
                show_scalar_bar=False,
            )

    display_text = "\n".join(
        [
            f"Profile: {metadata['profile']}",
            f"Mode: {metadata['mode']}",
            f"Wavelength: {metadata['wavelength_nm']} nm",
            f"Detected photons: {metadata['detected_photons_total']}",
            "3D mode: stable approximate view",
        ]
    )
    plotter.add_text(display_text, position="upper_left", font_size=10, color="black", name="scene_text")
    plotter.add_axes()
    plotter.show_grid()
    plotter.camera_position = "yz"


def build_case_scene(
    case_result_or_dir: dict[str, Any] | Path | str,
    show_fluence: bool = True,
    show_samples: bool = True,
    off_screen: bool = False,
) -> pv.Plotter:
    case_bundle = _load_case_bundle(case_result_or_dir)
    plotter = pv.Plotter(off_screen=off_screen, window_size=(1400, 900))
    _add_scene_geometry(plotter, case_bundle, show_samples=show_samples, show_fluence=show_fluence)
    return plotter


def plot_interactive_case(
    case_result_or_dir: dict[str, Any] | Path | str,
    show_fluence: bool = True,
    show_samples: bool = True,
    screenshot_path: Path | str | None = None,
    open_interactive: bool = True,
) -> Path | None:
    interactive_allowed = open_interactive and bool(os.environ.get("DISPLAY")) and not getattr(pv, "OFF_SCREEN", False)
    plotter = build_case_scene(
        case_result_or_dir,
        show_fluence=show_fluence,
        show_samples=show_samples,
        off_screen=not interactive_allowed or screenshot_path is not None,
    )

    preview_path = None
    if screenshot_path is not None:
        preview_path = Path(screenshot_path)
        ensure_directory(preview_path.parent)
        plotter.screenshot(str(preview_path))

    if interactive_allowed:
        plotter.show()
    else:
        plotter.close()
    return preview_path


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
