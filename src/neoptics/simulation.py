from __future__ import annotations

import copy
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pmcx

from .analysis import build_detector_summary, save_detector_samples, summarize_runs
from .config import (
    OUTPUTS_DIR,
    deep_update,
    dump_json_file,
    dump_yaml_file,
    ensure_directory,
    load_yaml_config,
    stable_hash,
    to_serializable,
)
from .constants import SUPPORTED_MODES
from .geometry import build_wrist_volume, save_volume_preview
from .optics import build_prop_table
from .sensors import build_reflectance_sensor, build_transmittance_sensor
from .visualization import plot_cross_section, plot_detector_summary, plot_trajectories


@dataclass
class CaseConfig:
    profile: str
    wavelength_nm: int
    mode: str
    nphoton: int = 5000
    seed: int = 20260415
    voxel_size_mm: float = 0.2
    geometry_overrides: dict[str, Any] | None = None
    include_vein: bool = False
    sensor_overrides: dict[str, Any] | None = None
    save_fluence: bool = True
    save_detector: bool = True
    save_trajectory: bool = False
    tstart: float = 0.0
    tend: float = 5e-9
    tstep: float = 5e-9
    output_root: str | None = None
    case_id: str | None = None
    force_rerun: bool = False


def _coerce_case_config(case_config: CaseConfig | dict[str, Any]) -> CaseConfig:
    if isinstance(case_config, CaseConfig):
        return case_config
    return CaseConfig(**case_config)


def _build_case_id(case_config: CaseConfig) -> str:
    if case_config.case_id:
        return case_config.case_id
    descriptor = {
        "profile": case_config.profile,
        "wavelength_nm": case_config.wavelength_nm,
        "mode": case_config.mode,
        "voxel_size_mm": case_config.voxel_size_mm,
        "include_vein": case_config.include_vein,
        "geometry_overrides": case_config.geometry_overrides or {},
        "sensor_overrides": case_config.sensor_overrides or {},
        "nphoton": case_config.nphoton,
        "seed": case_config.seed,
    }
    digest = stable_hash(descriptor)[:8]
    return f"{case_config.profile}_{case_config.mode}_{case_config.wavelength_nm}nm_{digest}"


def _is_complete_case_dir(case_dir: Path) -> bool:
    required = [
        case_dir / "metadata.json",
        case_dir / "config_snapshot.yaml",
        case_dir / "fluence.npy",
        case_dir / "detector_summary.csv",
        case_dir / "fluence_z.png",
    ]
    return all(path.exists() for path in required)


def _load_existing_case(case_dir: Path) -> dict[str, Any]:
    metadata_path = case_dir / "metadata.json"
    detector_summary_path = case_dir / "detector_summary.csv"
    with metadata_path.open("r", encoding="utf-8") as handle:
        metadata = __import__("json").load(handle)
    detector_summary = pd.read_csv(detector_summary_path)
    fluence = np.load(case_dir / "fluence.npy")
    return {
        "metadata": metadata,
        "paths": {"case_dir": str(case_dir)},
        "pmcx_result": None,
        "detector_summary": detector_summary,
        "fluence_shape": tuple(fluence.shape),
        "case_id": metadata["case_id"],
        "skipped": True,
    }


def run_single_case(case_config: CaseConfig | dict[str, Any]) -> dict[str, Any]:
    case = _coerce_case_config(case_config)
    if case.mode not in SUPPORTED_MODES:
        raise ValueError(f"Unsupported mode: {case.mode}")

    case_id = _build_case_id(case)
    output_root = Path(case.output_root) if case.output_root else OUTPUTS_DIR / "single_cases"
    case_dir = ensure_directory(output_root / case_id)

    if not case.force_rerun and _is_complete_case_dir(case_dir):
        return _load_existing_case(case_dir)

    volume, geometry_metadata = build_wrist_volume(
        profile_name=case.profile,
        overrides=case.geometry_overrides,
        include_vein=case.include_vein,
        voxel_size_mm=case.voxel_size_mm,
    )
    prop = build_prop_table(case.wavelength_nm, include_vein=case.include_vein)
    sensor_builder = build_reflectance_sensor if case.mode == "reflectance" else build_transmittance_sensor
    sensor_config = sensor_builder(case.profile, case.wavelength_nm, geometry_metadata, case.sensor_overrides)

    savedetflag = "DPW"
    pmcx_config = {
        "vol": volume,
        "prop": prop,
        "nphoton": int(case.nphoton),
        "seed": int(case.seed),
        "unitinmm": float(case.voxel_size_mm),
        "tstart": float(case.tstart),
        "tend": float(case.tend),
        "tstep": float(case.tstep),
        "srcpos": sensor_config["srcpos"],
        "srcdir": sensor_config["srcdir"],
        "srctype": sensor_config["source_type"],
        "detpos": sensor_config["detpos"],
        "issavedet": 1,
        "savedetflag": savedetflag,
        "issaveexit": 1 if case.save_trajectory else 0,
    }
    if case.save_trajectory:
        savedetflag += "XV"
        pmcx_config["savedetflag"] = savedetflag
    if sensor_config["source_type"].lower() == "disk":
        pmcx_config["srcparam1"] = [sensor_config["source_radius_vox"], 0.0, 0.0, 0.0]

    pmcx_result = pmcx.run(**pmcx_config)
    fluence = np.asarray(pmcx_result["flux"])
    fluence = np.squeeze(fluence, axis=-1) if fluence.ndim == 4 and fluence.shape[-1] == 1 else fluence

    detector_summary_df, detector_samples = build_detector_summary(
        raw_detp=pmcx_result.get("detp"),
        sensor_config=sensor_config,
        medium_count=prop.shape[0] - 1,
        savedetflag=savedetflag,
        case_id=case_id,
    )

    paths = {
        "case_dir": str(case_dir),
        "config_snapshot": str(dump_yaml_file(case_dir / "config_snapshot.yaml", asdict(case))),
        "geometry_preview": str(save_volume_preview(volume, case_dir, geometry_metadata)),
        "metadata": str(case_dir / "metadata.json"),
        "fluence": str(case_dir / "fluence.npy"),
        "detector_summary": str(case_dir / "detector_summary.csv"),
    }

    if case.save_fluence:
        np.save(case_dir / "fluence.npy", fluence)
    detector_summary_df.to_csv(case_dir / "detector_summary.csv", index=False)

    parsed_samples_path = save_detector_samples(case_dir / "trajectory_samples.npz", detector_samples if case.save_trajectory else None)
    if parsed_samples_path:
        paths["trajectory_samples"] = str(parsed_samples_path)

    result_bundle = {
        "case_id": case_id,
        "fluence": fluence,
        "pmcx_result": pmcx_result,
        "trajectory_samples": detector_samples if case.save_trajectory else None,
    }
    paths["fluence_plot"] = str(plot_cross_section(result_bundle, axis="z", output_path=case_dir / "fluence_z.png"))
    paths["detector_plot"] = str(plot_detector_summary(detector_summary_df, output_path=case_dir / "detector_summary.png"))
    trajectory_plot_path = plot_trajectories(result_bundle, output_path=case_dir / "trajectory_samples.png")
    if trajectory_plot_path:
        paths["trajectory_plot"] = str(trajectory_plot_path)

    metadata = {
        "case_id": case_id,
        "profile": case.profile,
        "wavelength_nm": int(case.wavelength_nm),
        "mode": case.mode,
        "nphoton": int(case.nphoton),
        "seed": int(case.seed),
        "voxel_size_mm": float(case.voxel_size_mm),
        "include_vein": bool(case.include_vein),
        "geometry_overrides": case.geometry_overrides or {},
        "sensor_overrides": case.sensor_overrides or {},
        "fluence_shape": list(fluence.shape),
        "has_trajectory_samples": bool(parsed_samples_path),
        "detected_photons_total": int(detector_summary_df["detected_photons"].sum()),
        "detected_weight_total": float(detector_summary_df["detected_weight"].sum()),
        "pmcx_stat": to_serializable(pmcx_result.get("stat", {})),
        "geometry_metadata": geometry_metadata,
        "sensor_config": sensor_config,
    }
    dump_json_file(case_dir / "metadata.json", metadata)

    return {
        "metadata": metadata,
        "paths": paths,
        "pmcx_result": pmcx_result,
        "detector_summary": detector_summary_df,
        "fluence_shape": tuple(fluence.shape),
        "case_id": case_id,
        "trajectory_samples": detector_samples if case.save_trajectory else None,
    }


def _load_experiment_config(experiment_config: str | Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(experiment_config, (str, Path)):
        config_path = Path(experiment_config)
        relative_path = str(config_path.relative_to(config_path.parents[1])) if config_path.is_absolute() else str(config_path)
        if config_path.exists():
            import yaml

            with config_path.open("r", encoding="utf-8") as handle:
                return yaml.safe_load(handle)
        return load_yaml_config(relative_path)
    return copy.deepcopy(experiment_config)


def _base_case_dict(profile: str, wavelength_nm: int, mode: str, runtime_cfg: dict[str, Any], output_root: Path) -> dict[str, Any]:
    return {
        "profile": profile,
        "wavelength_nm": int(wavelength_nm),
        "mode": mode,
        "nphoton": int(runtime_cfg["nphoton"]),
        "seed": int(runtime_cfg["seed"]),
        "voxel_size_mm": float(runtime_cfg["voxel_size_mm"]),
        "save_trajectory": bool(runtime_cfg.get("save_trajectory", False)),
        "save_fluence": True,
        "save_detector": True,
        "output_root": str(output_root),
    }


def _expand_structure_sweeps(sweep_cfg: dict[str, Any], runtime_cfg: dict[str, Any], output_root: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for variable_name, variable_cfg in sweep_cfg.items():
        profiles = variable_cfg["profiles"]
        if isinstance(profiles, list):
            profile_map = {profile_name: variable_cfg["values"] for profile_name in profiles}
        else:
            profile_map = profiles
        for profile_name, values in profile_map.items():
            for wavelength_nm in variable_cfg["wavelengths_nm"]:
                for mode in variable_cfg["modes"]:
                    for value in values:
                        geometry_overrides = {}
                        if variable_name == "artery_diameter_mm":
                            geometry_overrides["artery_radius_mm"] = float(value) / 2.0
                        else:
                            geometry_overrides[variable_name] = float(value)
                        case_dict = _base_case_dict(profile_name, int(wavelength_nm), mode, runtime_cfg, output_root)
                        case_dict["geometry_overrides"] = geometry_overrides
                        cases.append(case_dict)
    return cases


def _expand_experiment_cases(config: dict[str, Any]) -> tuple[list[dict[str, Any]], Path]:
    stage = config["execution"].get("stage", "dev")
    runtime_cfg = config["runtime"][stage]
    output_root = Path(config["execution"].get("output_root", OUTPUTS_DIR / config.get("experiment_name", "experiment")))

    cases: list[dict[str, Any]] = []
    base_matrix = config["base_matrix"]
    mode_defaults = base_matrix.get("mode_defaults", {})
    for profile in base_matrix["profiles"]:
        for wavelength_nm in base_matrix["wavelengths_nm"]:
            for mode in base_matrix["modes"]:
                case_dict = _base_case_dict(profile, int(wavelength_nm), mode, runtime_cfg, output_root)
                sensor_defaults = mode_defaults.get(mode, {}).get(int(wavelength_nm), {})
                if sensor_defaults:
                    case_dict["sensor_overrides"] = sensor_defaults
                cases.append(case_dict)

    if config["execution"].get("include_sweeps", False):
        reflectance_cfg = config["sweeps"]["reflectance"]
        for profile in reflectance_cfg["profiles"]:
            for wavelength_nm in reflectance_cfg["wavelengths_nm"]:
                for separation_mm in reflectance_cfg["values_by_wavelength"][int(wavelength_nm)]:
                    case_dict = _base_case_dict(profile, int(wavelength_nm), "reflectance", runtime_cfg, output_root)
                    case_dict["sensor_overrides"] = {"separation_mm": float(separation_mm)}
                    cases.append(case_dict)

        transmittance_cfg = config["sweeps"]["transmittance"]
        for profile in transmittance_cfg["profiles"]:
            for wavelength_nm in transmittance_cfg["wavelengths_nm"]:
                for lateral_offset_mm in transmittance_cfg["lateral_offset_mm"]:
                    case_dict = _base_case_dict(profile, int(wavelength_nm), "transmittance", runtime_cfg, output_root)
                    case_dict["sensor_overrides"] = {"lateral_offset_mm": float(lateral_offset_mm)}
                    cases.append(case_dict)

        cases.extend(_expand_structure_sweeps(config["sweeps"]["structure"], runtime_cfg, output_root))

    return cases, output_root


def run_experiment_matrix(experiment_config: str | Path | dict[str, Any]) -> dict[str, Any]:
    config = _load_experiment_config(experiment_config)
    cases, output_root = _expand_experiment_cases(config)

    results = []
    for case_dict in cases:
        case_dict["force_rerun"] = bool(config["execution"].get("force_rerun", False))
        results.append(run_single_case(case_dict))

    summary_df = summarize_runs(output_root)
    if not summary_df.empty:
        plot_detector_summary(summary_df.rename(columns={"detected_photons_total": "detected_photons"}), output_root / "summary_detector_totals.png")

    return {
        "output_root": str(output_root),
        "case_count": len(cases),
        "results": results,
        "summary": summary_df,
    }
