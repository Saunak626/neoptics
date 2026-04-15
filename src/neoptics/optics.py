from __future__ import annotations

from typing import Any

import numpy as np

from .config import load_yaml_config
from .constants import LABEL_ORDER, SUPPORTED_WAVELENGTHS


def _resolve_wavelength_key(wavelength_nm: int) -> str:
    wavelength = int(wavelength_nm)
    if wavelength not in SUPPORTED_WAVELENGTHS:
        raise ValueError(f"Unsupported wavelength: {wavelength_nm}")
    return str(wavelength)


def load_optical_properties(wavelength_nm: int) -> dict[str, dict[str, float]]:
    wavelength_key = int(_resolve_wavelength_key(wavelength_nm))
    tissue_config = load_yaml_config("optics_tissue.yaml")
    blood_config = load_yaml_config("optics_blood.yaml")

    optical_properties: dict[str, dict[str, float]] = {}
    for tissue_name, wavelength_map in tissue_config["tissues"].items():
        optical_properties[tissue_name] = {key: float(value) for key, value in wavelength_map[wavelength_key].items()}
    for tissue_name, wavelength_map in blood_config["blood"].items():
        optical_properties[tissue_name] = {key: float(value) for key, value in wavelength_map[wavelength_key].items()}
    return optical_properties


def build_prop_table(wavelength_nm: int, include_vein: bool = False) -> np.ndarray:
    del include_vein
    properties = load_optical_properties(wavelength_nm)
    rows: list[list[float]] = []
    for label_name in LABEL_ORDER:
        row = properties[label_name]
        rows.append([row["mua"], row["mus"], row["g"], row["n"]])
    return np.asarray(rows, dtype=float)
