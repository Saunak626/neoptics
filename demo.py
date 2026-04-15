from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from neoptics import run_single_case


def main() -> None:
    result = run_single_case(
        {
            "profile": "preterm_wrist",
            "wavelength_nm": 660,
            "mode": "reflectance",
            "nphoton": 100000,
            "seed": 20260415,
            "voxel_size_mm": 0.2,
            "output_root": str(REPO_ROOT / "outputs" / "demo"),
            "save_trajectory": True,
            "force_rerun": True,
        }
    )
    print(f"case_id={result['case_id']}")
    print(f"output_dir={result['paths']['case_dir']}")


if __name__ == "__main__":
    main()
