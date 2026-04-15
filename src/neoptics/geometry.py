from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap

from .config import ensure_directory, load_yaml_config
from .constants import LABELS


def _geometry_config() -> dict[str, Any]:
    return load_yaml_config("geometry_profiles.yaml")


def _axis_coordinates(length_mm: float, voxel_size_mm: float, count: int) -> np.ndarray:
    return (np.arange(count, dtype=float) + 0.5) * voxel_size_mm - (length_mm / 2.0)


def _ellipse_mask(
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    center_x_mm: float,
    center_y_mm: float,
    semi_axis_x_mm: float,
    semi_axis_y_mm: float,
) -> np.ndarray:
    xx = x_coords[:, None]
    yy = y_coords[None, :]
    return (((xx - center_x_mm) / semi_axis_x_mm) ** 2 + ((yy - center_y_mm) / semi_axis_y_mm) ** 2) <= 1.0


def _circle_mask(
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    center_x_mm: float,
    center_y_mm: float,
    radius_mm: float,
) -> np.ndarray:
    xx = x_coords[:, None]
    yy = y_coords[None, :]
    return ((xx - center_x_mm) ** 2 + (yy - center_y_mm) ** 2) <= radius_mm**2


def _resolve_vessel_center_y(params: dict[str, Any], prefix: str) -> float:
    explicit_name = f"{prefix}_center_y_mm"
    depth_name = f"{prefix}_depth_mm"
    if explicit_name in params and params[explicit_name] is not None:
        return float(params[explicit_name])

    outer_half_thickness = float(params["outer_thickness_mm"]) / 2.0
    depth_mm = float(params[depth_name])
    return -outer_half_thickness + depth_mm


def _build_cross_section_masks(
    params: dict[str, Any],
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    include_vein: bool,
) -> dict[str, np.ndarray]:
    outer_a = float(params["outer_width_mm"]) / 2.0
    outer_b = float(params["outer_thickness_mm"]) / 2.0
    skin_thickness = float(params["skin_thickness_mm"])
    fat_thickness = float(params["fat_thickness_mm"])

    skin_inner_a = outer_a - skin_thickness
    skin_inner_b = outer_b - skin_thickness
    fat_inner_a = skin_inner_a - fat_thickness
    fat_inner_b = skin_inner_b - fat_thickness

    if min(skin_inner_a, skin_inner_b, fat_inner_a, fat_inner_b) <= 0:
        raise ValueError("Skin/fat thickness collapses the wrist profile.")

    outer_mask = _ellipse_mask(x_coords, y_coords, 0.0, 0.0, outer_a, outer_b)
    fat_inner_mask = _ellipse_mask(x_coords, y_coords, 0.0, 0.0, skin_inner_a, skin_inner_b)
    muscle_inner_mask = _ellipse_mask(x_coords, y_coords, 0.0, 0.0, fat_inner_a, fat_inner_b)

    radius_bone_mask = _ellipse_mask(
        x_coords,
        y_coords,
        float(params["radius_bone_center_xy_mm"][0]),
        float(params["radius_bone_center_xy_mm"][1]),
        float(params["radius_bone_semi_axes_mm"][0]),
        float(params["radius_bone_semi_axes_mm"][1]),
    )
    ulna_bone_mask = _ellipse_mask(
        x_coords,
        y_coords,
        float(params["ulna_bone_center_xy_mm"][0]),
        float(params["ulna_bone_center_xy_mm"][1]),
        float(params["ulna_bone_semi_axes_mm"][0]),
        float(params["ulna_bone_semi_axes_mm"][1]),
    )
    bone_mask = radius_bone_mask | ulna_bone_mask

    artery_center_y_mm = _resolve_vessel_center_y(params, "artery")
    artery_mask = _circle_mask(
        x_coords,
        y_coords,
        float(params["artery_center_x_mm"]),
        artery_center_y_mm,
        float(params["artery_radius_mm"]),
    )

    vein_center_y_mm = _resolve_vessel_center_y(params, "vein")
    vein_mask = _circle_mask(
        x_coords,
        y_coords,
        float(params["vein_center_x_mm"]),
        vein_center_y_mm,
        float(params["vein_radius_mm"]),
    ) if include_vein else np.zeros_like(artery_mask)

    return {
        "outer": outer_mask,
        "skin": outer_mask & ~fat_inner_mask,
        "fat": fat_inner_mask & ~muscle_inner_mask,
        "muscle": muscle_inner_mask,
        "bone": bone_mask,
        "artery": artery_mask,
        "vein": vein_mask,
        "artery_center_y_mm": artery_center_y_mm,
        "vein_center_y_mm": vein_center_y_mm,
    }


def build_wrist_volume(
    profile_name: str,
    overrides: dict[str, Any] | None = None,
    include_vein: bool | None = None,
    voxel_size_mm: float | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    config = _geometry_config()
    if profile_name not in config["profiles"]:
        raise KeyError(f"Unknown geometry profile: {profile_name}")

    params = copy.deepcopy(config["profiles"][profile_name])
    if overrides:
        params.update(copy.deepcopy(overrides))

    common = config["common"]
    resolved_voxel_size_mm = float(voxel_size_mm or params.get("voxel_size_mm") or common["voxel_size_mm_debug"])
    resolved_include_vein = bool(params.get("include_vein", False) if include_vein is None else include_vein)

    domain_mm = common["domain_mm"]
    shape = (
        int(round(float(domain_mm["x"]) / resolved_voxel_size_mm)),
        int(round(float(domain_mm["y"]) / resolved_voxel_size_mm)),
        int(round(float(domain_mm["z"]) / resolved_voxel_size_mm)),
    )
    x_coords = _axis_coordinates(float(domain_mm["x"]), resolved_voxel_size_mm, shape[0])
    y_coords = _axis_coordinates(float(domain_mm["y"]), resolved_voxel_size_mm, shape[1])
    z_coords = _axis_coordinates(float(domain_mm["z"]), resolved_voxel_size_mm, shape[2])

    masks = _build_cross_section_masks(params, x_coords, y_coords, resolved_include_vein)
    axial_half_length = float(params["axial_length_mm"]) / 2.0
    axial_mask = np.abs(z_coords) <= axial_half_length

    volume = np.zeros(shape, dtype=np.uint8)

    outer_3d = masks["outer"][:, :, None] & axial_mask[None, None, :]
    muscle_3d = masks["muscle"][:, :, None] & axial_mask[None, None, :]
    fat_3d = masks["fat"][:, :, None] & axial_mask[None, None, :]
    skin_3d = masks["skin"][:, :, None] & axial_mask[None, None, :]
    bone_3d = masks["bone"][:, :, None] & axial_mask[None, None, :]
    artery_3d = masks["artery"][:, :, None] & axial_mask[None, None, :]
    vein_3d = masks["vein"][:, :, None] & axial_mask[None, None, :]

    volume[outer_3d] = LABELS["soft_tissue_or_muscle"]
    volume[fat_3d] = LABELS["fat"]
    volume[skin_3d] = LABELS["skin"]
    volume[bone_3d] = LABELS["bone"]
    volume[artery_3d] = LABELS["arterial_blood"]
    if resolved_include_vein:
        volume[vein_3d] = LABELS["venous_blood_optional"]

    metadata = {
        "profile": profile_name,
        "include_vein": resolved_include_vein,
        "voxel_size_mm": resolved_voxel_size_mm,
        "shape": list(shape),
        "domain_mm": {
            "x": float(domain_mm["x"]),
            "y": float(domain_mm["y"]),
            "z": float(domain_mm["z"]),
        },
        "labels": copy.deepcopy(config["labels"]),
        "parameters": copy.deepcopy(params),
        "computed": {
            "artery_center_y_mm": float(masks["artery_center_y_mm"]),
            "vein_center_y_mm": float(masks["vein_center_y_mm"]),
            "palmar_surface_y_mm": -float(params["outer_thickness_mm"]) / 2.0,
            "dorsal_surface_y_mm": float(params["outer_thickness_mm"]) / 2.0,
        },
    }
    validate_geometry(volume, metadata)
    return volume, metadata


def validate_geometry(volume: np.ndarray, metadata: dict[str, Any]) -> dict[str, Any]:
    params = metadata["parameters"]
    voxel_size_mm = float(metadata["voxel_size_mm"])
    domain_mm = metadata["domain_mm"]
    shape = metadata["shape"]

    skin_thickness = float(params["skin_thickness_mm"])
    fat_thickness = float(params["fat_thickness_mm"])
    half_thickness = float(params["outer_thickness_mm"]) / 2.0

    if skin_thickness < 0 or fat_thickness < 0:
        raise ValueError("Layer thickness must be non-negative.")
    if skin_thickness + fat_thickness >= half_thickness:
        raise ValueError("skin + fat must stay shallower than the wrist center.")

    x_coords = _axis_coordinates(float(domain_mm["x"]), voxel_size_mm, int(shape[0]))
    y_coords = _axis_coordinates(float(domain_mm["y"]), voxel_size_mm, int(shape[1]))
    masks = _build_cross_section_masks(params, x_coords, y_coords, bool(metadata["include_vein"]))

    outer_a = float(params["outer_width_mm"]) / 2.0
    outer_b = half_thickness
    vessels = [
        ("artery", float(params["artery_center_x_mm"]), float(masks["artery_center_y_mm"]), float(params["artery_radius_mm"])),
    ]
    if metadata["include_vein"]:
        vessels.append(
            ("vein", float(params["vein_center_x_mm"]), float(masks["vein_center_y_mm"]), float(params["vein_radius_mm"])),
        )

    for vessel_name, center_x, center_y, radius in vessels:
        if radius <= 0:
            raise ValueError(f"{vessel_name} radius must be positive.")
        margin_a = outer_a - radius
        margin_b = outer_b - radius
        if min(margin_a, margin_b) <= 0:
            raise ValueError(f"{vessel_name} does not fit inside the outer contour.")
        if ((center_x / margin_a) ** 2 + (center_y / margin_b) ** 2) > 1.0:
            raise ValueError(f"{vessel_name} center/radius pushes the vessel outside the wrist contour.")

    if np.any(masks["artery"] & masks["bone"]):
        raise ValueError("Artery overlaps the bone region.")
    if metadata["include_vein"] and np.any(masks["vein"] & masks["bone"]):
        raise ValueError("Vein overlaps the bone region.")
    if metadata["include_vein"] and np.any(masks["vein"] & masks["artery"]):
        raise ValueError("Vein overlaps the artery.")

    artery_voxels = int(np.sum(volume == LABELS["arterial_blood"]))
    if artery_voxels <= 0:
        raise ValueError("Generated volume does not contain artery voxels.")
    if metadata["include_vein"] and int(np.sum(volume == LABELS["venous_blood_optional"])) <= 0:
        raise ValueError("Generated volume does not contain vein voxels.")

    return {
        "artery_voxels": artery_voxels,
        "vein_voxels": int(np.sum(volume == LABELS["venous_blood_optional"])),
        "bone_voxels": int(np.sum(volume == LABELS["bone"])),
        "soft_tissue_voxels": int(np.sum(volume == LABELS["soft_tissue_or_muscle"])),
    }


def save_volume_preview(volume: np.ndarray, out_dir: Path | str, metadata: dict[str, Any] | None = None) -> Path:
    output_dir = ensure_directory(Path(out_dir))
    figure_path = output_dir / "volume_preview.png"

    slices = [
        volume[volume.shape[0] // 2, :, :].T,
        volume[:, volume.shape[1] // 2, :].T,
        volume[:, :, volume.shape[2] // 2].T,
    ]
    titles = ["Sagittal", "Coronal", "Axial"]

    cmap = ListedColormap(
        [
            "#f6f7fb",
            "#f4b6c2",
            "#ffd8a8",
            "#d0d8ff",
            "#c0c0c0",
            "#d62728",
            "#7f1d1d",
        ]
    )

    fig, axes = plt.subplots(1, 3, figsize=(12, 4), constrained_layout=True)
    for axis, slice_2d, title in zip(axes, slices, titles):
        axis.imshow(slice_2d, origin="lower", cmap=cmap, interpolation="nearest")
        axis.set_title(title)
        axis.set_xticks([])
        axis.set_yticks([])
    if metadata:
        fig.suptitle(
            f"{metadata['profile']} | voxel={metadata['voxel_size_mm']} mm | vein={metadata['include_vein']}",
            fontsize=10,
        )
    fig.savefig(figure_path, dpi=150)
    plt.close(fig)
    return figure_path
