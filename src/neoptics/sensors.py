from __future__ import annotations

from typing import Any

from .config import load_yaml_config
from .constants import SUPPORTED_MODES, SUPPORTED_WAVELENGTHS


def _sensor_config() -> dict[str, Any]:
    return load_yaml_config("sensor_defaults.yaml")


def _mm_to_voxel(coord_mm: float, axis_length_mm: float, voxel_size_mm: float) -> float:
    return (coord_mm + axis_length_mm / 2.0) / voxel_size_mm


def _radius_to_voxel(radius_mm: float, voxel_size_mm: float) -> float:
    return radius_mm / voxel_size_mm


def _merge_wavelength_defaults(mode: str, wavelength_nm: int) -> dict[str, Any]:
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"Unsupported mode: {mode}")
    if int(wavelength_nm) not in SUPPORTED_WAVELENGTHS:
        raise ValueError(f"Unsupported wavelength: {wavelength_nm}")

    config = _sensor_config()
    mode_config = config[mode]
    resolved = dict(mode_config["common"])
    resolved.update(mode_config["wavelengths"][int(wavelength_nm)])
    return resolved


def build_reflectance_sensor(
    profile: str,
    wavelength_nm: int,
    geometry_metadata: dict[str, Any],
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del profile
    resolved = _merge_wavelength_defaults("reflectance", wavelength_nm)
    if overrides:
        resolved.update(overrides)

    params = geometry_metadata["parameters"]
    computed = geometry_metadata["computed"]
    domain_mm = geometry_metadata["domain_mm"]
    voxel_size_mm = float(geometry_metadata["voxel_size_mm"])

    source_x_mm = float(params["artery_center_x_mm"]) if resolved["center_on_artery_projection"] else 0.0
    source_y_mm = float(computed["palmar_surface_y_mm"]) + float(resolved["surface_inset_mm"])
    source_z_mm = 0.0

    separation_mm = float(resolved["separation_mm"] if "separation_mm" in resolved else resolved["default_separation_mm"])
    detector_axis = str(resolved.get("detector_axis", "x")).lower()
    detector_x_mm = source_x_mm + (separation_mm if detector_axis == "x" else 0.0)
    detector_z_mm = source_z_mm + (separation_mm if detector_axis == "z" else 0.0)
    detector_y_mm = float(computed["palmar_surface_y_mm"])

    detector_radius_mm = float(resolved["detector_radius_mm"])
    source_radius_mm = float(resolved["source_radius_mm"])

    return {
        "mode": "reflectance",
        "source_type": str(resolved["source_type"]),
        "source_radius_mm": source_radius_mm,
        "detector_radius_mm": detector_radius_mm,
        "source_mm": [source_x_mm, source_y_mm, source_z_mm],
        "detectors_mm": [[detector_x_mm, detector_y_mm, detector_z_mm, detector_radius_mm]],
        "srcpos": [
            _mm_to_voxel(source_x_mm, float(domain_mm["x"]), voxel_size_mm),
            _mm_to_voxel(source_y_mm, float(domain_mm["y"]), voxel_size_mm),
            _mm_to_voxel(source_z_mm, float(domain_mm["z"]), voxel_size_mm),
        ],
        "srcdir": [0.0, 1.0, 0.0],
        "source_radius_vox": _radius_to_voxel(source_radius_mm, voxel_size_mm),
        "detpos": [[
            _mm_to_voxel(detector_x_mm, float(domain_mm["x"]), voxel_size_mm),
            _mm_to_voxel(detector_y_mm, float(domain_mm["y"]), voxel_size_mm),
            _mm_to_voxel(detector_z_mm, float(domain_mm["z"]), voxel_size_mm),
            _radius_to_voxel(detector_radius_mm, voxel_size_mm),
        ]],
        "sensor_overrides": resolved,
    }


def build_transmittance_sensor(
    profile: str,
    wavelength_nm: int,
    geometry_metadata: dict[str, Any],
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del profile
    resolved = _merge_wavelength_defaults("transmittance", wavelength_nm)
    if overrides:
        resolved.update(overrides)

    params = geometry_metadata["parameters"]
    computed = geometry_metadata["computed"]
    domain_mm = geometry_metadata["domain_mm"]
    voxel_size_mm = float(geometry_metadata["voxel_size_mm"])

    source_x_mm = float(params["artery_center_x_mm"]) if resolved["center_on_artery_projection"] else 0.0
    source_y_mm = float(computed["palmar_surface_y_mm"]) + float(resolved["surface_inset_mm"])
    source_z_mm = 0.0

    lateral_offset_mm = float(
        resolved["lateral_offset_mm"] if "lateral_offset_mm" in resolved else resolved["default_lateral_offset_mm"]
    )
    detector_x_mm = source_x_mm + lateral_offset_mm
    detector_y_mm = float(computed["dorsal_surface_y_mm"])
    detector_z_mm = source_z_mm
    detector_radius_mm = float(resolved["detector_radius_mm"])
    source_radius_mm = float(resolved["source_radius_mm"])

    return {
        "mode": "transmittance",
        "source_type": str(resolved["source_type"]),
        "source_radius_mm": source_radius_mm,
        "detector_radius_mm": detector_radius_mm,
        "source_mm": [source_x_mm, source_y_mm, source_z_mm],
        "detectors_mm": [[detector_x_mm, detector_y_mm, detector_z_mm, detector_radius_mm]],
        "srcpos": [
            _mm_to_voxel(source_x_mm, float(domain_mm["x"]), voxel_size_mm),
            _mm_to_voxel(source_y_mm, float(domain_mm["y"]), voxel_size_mm),
            _mm_to_voxel(source_z_mm, float(domain_mm["z"]), voxel_size_mm),
        ],
        "srcdir": [0.0, 1.0, 0.0],
        "source_radius_vox": _radius_to_voxel(source_radius_mm, voxel_size_mm),
        "detpos": [[
            _mm_to_voxel(detector_x_mm, float(domain_mm["x"]), voxel_size_mm),
            _mm_to_voxel(detector_y_mm, float(domain_mm["y"]), voxel_size_mm),
            _mm_to_voxel(detector_z_mm, float(domain_mm["z"]), voxel_size_mm),
            _radius_to_voxel(detector_radius_mm, voxel_size_mm),
        ]],
        "sensor_overrides": resolved,
    }
