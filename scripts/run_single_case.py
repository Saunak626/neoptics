from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from neoptics import run_single_case


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a single NeoOptics PMCX case.")
    parser.add_argument("--profile", required=True, choices=["preterm_wrist", "term_wrist"])
    parser.add_argument("--wavelength", required=True, type=int, choices=[530, 660, 940])
    parser.add_argument("--mode", required=True, choices=["reflectance", "transmittance"])
    parser.add_argument("--nphoton", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260415)
    parser.add_argument("--voxel-size", dest="voxel_size_mm", type=float, default=0.2)
    parser.add_argument("--output-root", default="outputs/manual_runs")
    parser.add_argument("--include-vein", action="store_true")
    parser.add_argument("--save-trajectory", action="store_true")
    parser.add_argument("--separation-mm", type=float)
    parser.add_argument("--lateral-offset-mm", type=float)
    parser.add_argument("--force-rerun", action="store_true")
    args = parser.parse_args()

    sensor_overrides = {}
    if args.separation_mm is not None:
        sensor_overrides["separation_mm"] = args.separation_mm
    if args.lateral_offset_mm is not None:
        sensor_overrides["lateral_offset_mm"] = args.lateral_offset_mm

    result = run_single_case(
        {
            "profile": args.profile,
            "wavelength_nm": args.wavelength,
            "mode": args.mode,
            "nphoton": args.nphoton,
            "seed": args.seed,
            "voxel_size_mm": args.voxel_size_mm,
            "output_root": args.output_root,
            "include_vein": args.include_vein,
            "save_trajectory": args.save_trajectory,
            "sensor_overrides": sensor_overrides or None,
            "force_rerun": args.force_rerun,
        }
    )
    print(f"case_id={result['case_id']}")
    print(f"output_dir={result['paths']['case_dir']}")


if __name__ == "__main__":
    main()
