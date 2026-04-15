from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from neoptics import plot_interactive_case


def main() -> None:
    parser = argparse.ArgumentParser(description="Open or export a NeoOptics 3D case scene.")
    parser.add_argument("--case-dir", required=True, help="Path to a case output directory.")
    parser.add_argument("--screenshot", default=None, help="Optional path to save a 3D preview screenshot.")
    parser.add_argument("--no-fluence", action="store_true", help="Hide fluence isosurface.")
    parser.add_argument("--no-samples", action="store_true", help="Hide detected photon sample points.")
    parser.add_argument("--no-interactive", action="store_true", help="Only export screenshot without opening a window.")
    args = parser.parse_args()

    screenshot_path = args.screenshot
    if screenshot_path is None:
        screenshot_path = str(Path(args.case_dir) / "scene_3d_preview.png")

    preview_path = plot_interactive_case(
        case_result_or_dir=args.case_dir,
        show_fluence=not args.no_fluence,
        show_samples=not args.no_samples,
        screenshot_path=screenshot_path,
        open_interactive=not args.no_interactive,
    )
    print(f"preview={preview_path}")


if __name__ == "__main__":
    main()
