from __future__ import annotations

from pathlib import Path

import yaml

from neoptics import build_case_scene, plot_interactive_case, run_experiment_matrix, run_single_case


def test_run_single_case_reflectance_smoke(temp_output_dir: Path) -> None:
    result = run_single_case(
        {
            "profile": "preterm_wrist",
            "wavelength_nm": 530,
            "mode": "reflectance",
            "nphoton": 4000,
            "seed": 20260415,
            "voxel_size_mm": 0.2,
            "output_root": str(temp_output_dir),
            "save_trajectory": True,
            "force_rerun": True,
        }
    )

    case_dir = Path(result["paths"]["case_dir"])
    assert result["fluence_shape"] == (160, 140, 80)
    assert case_dir.joinpath("metadata.json").exists()
    assert case_dir.joinpath("fluence.npy").exists()
    assert case_dir.joinpath("detector_summary.csv").exists()
    assert case_dir.joinpath("fluence_z.png").exists()
    assert case_dir.joinpath("scene_3d_preview.png").exists()
    assert case_dir.joinpath("case_overview.txt").exists()


def test_run_single_case_transmittance_smoke(temp_output_dir: Path) -> None:
    result = run_single_case(
        {
            "profile": "term_wrist",
            "wavelength_nm": 940,
            "mode": "transmittance",
            "nphoton": 4000,
            "seed": 20260415,
            "voxel_size_mm": 0.2,
            "output_root": str(temp_output_dir),
            "force_rerun": True,
        }
    )

    detector_summary = result["detector_summary"]
    assert "detected_photons" in detector_summary.columns
    assert len(detector_summary) == 1


def test_build_case_scene_and_export_preview(temp_output_dir: Path) -> None:
    result = run_single_case(
        {
            "profile": "preterm_wrist",
            "wavelength_nm": 660,
            "mode": "reflectance",
            "nphoton": 3000,
            "seed": 20260415,
            "voxel_size_mm": 0.2,
            "output_root": str(temp_output_dir),
            "force_rerun": True,
        }
    )

    case_dir = Path(result["paths"]["case_dir"])
    plotter = build_case_scene(case_dir, off_screen=True)
    assert plotter.actors
    plotter.close()

    preview_path = plot_interactive_case(
        case_dir,
        screenshot_path=case_dir / "scene_3d_preview_test.png",
        open_interactive=False,
    )
    assert Path(preview_path).exists()


def test_run_experiment_matrix_base_smoke(temp_output_dir: Path) -> None:
    config_path = Path(__file__).resolve().parents[1] / "configs" / "experiments" / "base_matrix.yaml"
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    config["execution"]["output_root"] = str(temp_output_dir / "base_matrix")
    config["execution"]["include_sweeps"] = False
    config["execution"]["force_rerun"] = True
    config["runtime"]["dev"]["nphoton"] = 1500
    config["runtime"]["dev"]["save_trajectory"] = False

    result = run_experiment_matrix(config)
    summary = result["summary"]

    assert result["case_count"] == 12
    assert len(summary) == 12
    assert Path(result["output_root"]).joinpath("summary.csv").exists()
