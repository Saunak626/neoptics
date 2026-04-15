from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pmcx

from .config import dump_json_file


def _as_array(data: Any) -> np.ndarray | None:
    if data is None:
        return None
    array = np.asarray(data)
    if array.size == 0:
        return None
    return array


def _per_photon_totals(data: np.ndarray | None, photon_count: int) -> np.ndarray | None:
    if data is None:
        return None
    array = np.asarray(data)
    if array.size == 0:
        return None
    if array.ndim == 1:
        return array.reshape(-1)
    if array.shape[0] == photon_count:
        return np.sum(array, axis=1).reshape(-1)
    if array.shape[-1] == photon_count:
        return np.sum(array, axis=0).reshape(-1)
    return array.reshape(-1)


def parse_detected_photons(raw_detp: Any, medium_count: int, savedetflag: str) -> dict[str, np.ndarray] | None:
    if raw_detp is None:
        return None
    if isinstance(raw_detp, dict):
        return {key: np.asarray(value) for key, value in raw_detp.items()}
    if isinstance(raw_detp, np.ndarray):
        parsed = pmcx.detphoton(raw_detp, medium_count, savedetflag)
        return {key: np.asarray(value) for key, value in parsed.items()}
    return None


def build_detector_summary(
    raw_detp: Any,
    sensor_config: dict[str, Any],
    medium_count: int,
    savedetflag: str,
    case_id: str,
) -> tuple[pd.DataFrame, dict[str, np.ndarray] | None]:
    parsed = parse_detected_photons(raw_detp, medium_count, savedetflag)
    detector_count = len(sensor_config["detpos"])
    rows: list[dict[str, Any]] = []

    if parsed and _as_array(parsed.get("detid")) is not None:
        detector_ids = np.asarray(parsed["detid"]).astype(int).reshape(-1)
        ppath = _as_array(parsed.get("ppath"))
        weights = _as_array(parsed.get("w0"))
        total_paths = _per_photon_totals(ppath, len(detector_ids))
        sample_weights = np.ones_like(detector_ids, dtype=float) if weights is None else np.asarray(weights).reshape(-1)
    else:
        detector_ids = np.asarray([], dtype=int)
        total_paths = np.asarray([], dtype=float)
        sample_weights = np.asarray([], dtype=float)

    for detector_index, detpos in enumerate(sensor_config["detpos"], start=1):
        mask = detector_ids == detector_index
        rows.append(
            {
                "case_id": case_id,
                "detector_id": detector_index,
                "detector_x_vox": float(detpos[0]),
                "detector_y_vox": float(detpos[1]),
                "detector_z_vox": float(detpos[2]),
                "detector_radius_vox": float(detpos[3]),
                "detected_photons": int(np.sum(mask)),
                "detected_weight": float(np.sum(sample_weights[mask])) if sample_weights.size else 0.0,
                "mean_total_pathlength_vox": float(np.mean(total_paths[mask])) if total_paths is not None and np.sum(mask) else 0.0,
                "max_total_pathlength_vox": float(np.max(total_paths[mask])) if total_paths is not None and np.sum(mask) else 0.0,
            }
        )

    return pd.DataFrame(rows), parsed


def save_detector_samples(path: Path | str, detector_samples: dict[str, np.ndarray] | None) -> Path | None:
    if not detector_samples:
        return None
    output_path = Path(path)
    np.savez_compressed(output_path, **detector_samples)
    return output_path


def summarize_runs(run_dir: Path | str) -> pd.DataFrame:
    run_path = Path(run_dir)
    summary_rows: list[dict[str, Any]] = []

    for metadata_path in sorted(run_path.glob("*/metadata.json")):
        case_dir = metadata_path.parent
        with metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)

        detector_summary_path = case_dir / "detector_summary.csv"
        if detector_summary_path.exists():
            detector_df = pd.read_csv(detector_summary_path)
        else:
            detector_df = pd.DataFrame()

        summary_rows.append(
            {
                "case_id": metadata["case_id"],
                "profile": metadata["profile"],
                "wavelength_nm": metadata["wavelength_nm"],
                "mode": metadata["mode"],
                "include_vein": metadata["include_vein"],
                "voxel_size_mm": metadata["voxel_size_mm"],
                "nphoton": metadata["nphoton"],
                "detected_photons_total": int(detector_df["detected_photons"].sum()) if not detector_df.empty else 0,
                "detected_weight_total": float(detector_df["detected_weight"].sum()) if not detector_df.empty else 0.0,
                "detector_count": int(len(detector_df)) if not detector_df.empty else 0,
                "has_trajectory_samples": bool(metadata.get("has_trajectory_samples", False)),
                "fluence_shape": metadata.get("fluence_shape"),
            }
        )

    summary_df = pd.DataFrame(summary_rows)
    if not summary_df.empty:
        summary_df = summary_df.sort_values(["profile", "wavelength_nm", "mode", "case_id"]).reset_index(drop=True)
    summary_path = run_path / "summary.csv"
    summary_df.to_csv(summary_path, index=False)
    dump_json_file(run_path / "summary_manifest.json", {"run_dir": str(run_path), "case_count": int(len(summary_df))})
    return summary_df
