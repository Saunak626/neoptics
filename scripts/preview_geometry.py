from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from neoptics import build_wrist_volume, save_volume_preview


def _parse_override(entry: str) -> tuple[str, float]:
    if "=" not in entry:
        raise ValueError(f"Invalid override: {entry}")
    key, value = entry.split("=", 1)
    return key, float(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview a NeoOptics wrist geometry.")
    parser.add_argument("--profile", required=True, choices=["preterm_wrist", "term_wrist"])
    parser.add_argument("--voxel-size", dest="voxel_size_mm", type=float, default=0.2)
    parser.add_argument("--include-vein", action="store_true")
    parser.add_argument("--output-dir", default="outputs/geometry_preview")
    parser.add_argument("--set", dest="overrides", action="append", default=[])
    args = parser.parse_args()

    overrides = dict(_parse_override(item) for item in args.overrides)
    volume, metadata = build_wrist_volume(
        profile_name=args.profile,
        overrides=overrides or None,
        include_vein=args.include_vein,
        voxel_size_mm=args.voxel_size_mm,
    )
    output_dir = Path(args.output_dir)
    preview_path = save_volume_preview(volume, output_dir, metadata)
    print(f"preview={preview_path}")


if __name__ == "__main__":
    main()
