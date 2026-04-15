from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from neoptics import plot_detector_summary, summarize_runs


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize an output directory and save detector plots.")
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    summary_df = summarize_runs(run_dir)
    plot_path = plot_detector_summary(
        summary_df.rename(columns={"detected_photons_total": "detected_photons"}),
        run_dir / "summary_detector_totals.png",
    )
    print(f"summary_csv={run_dir / 'summary.csv'}")
    print(f"plot={plot_path}")


if __name__ == "__main__":
    main()
