from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from neoptics import run_experiment_matrix


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the NeoOptics base experiment matrix.")
    parser.add_argument("--config", default="configs/experiments/base_matrix.yaml")
    parser.add_argument("--stage", choices=["dev", "final"], default=None)
    parser.add_argument("--include-sweeps", action="store_true")
    parser.add_argument("--force-rerun", action="store_true")
    parser.add_argument("--output-root", default=None)
    args = parser.parse_args()

    config_path = REPO_ROOT / args.config
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    if args.stage:
        config["execution"]["stage"] = args.stage
    if args.include_sweeps:
        config["execution"]["include_sweeps"] = True
    if args.force_rerun:
        config["execution"]["force_rerun"] = True
    if args.output_root:
        config["execution"]["output_root"] = args.output_root

    result = run_experiment_matrix(config)
    print(f"case_count={result['case_count']}")
    print(f"output_root={result['output_root']}")
    print(f"summary_csv={Path(result['output_root']) / 'summary.csv'}")


if __name__ == "__main__":
    main()
