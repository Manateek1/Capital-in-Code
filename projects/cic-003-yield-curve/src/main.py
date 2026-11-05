"""Run the complete CIC-003 data, analysis, chart, and output pipeline."""

from __future__ import annotations

import argparse
import json
from typing import Sequence

from .analysis import analyze
from .charts import generate_charts
from .config import (
    CHARTS_DIR,
    PRIMARY_THRESHOLD_PERCENT,
    RAW_DATA_DIR,
    RESULTS_DIR,
    SENSITIVITY_THRESHOLDS_PERCENT,
    SITE_IMAGE_DIR,
    SITE_SUMMARY_PATH,
)
from .data import DataError, load_monthly_data
from .output import write_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.main",
        description=(
            "Analyze confirmed 10-year/3-month spread inversion episodes and "
            "NBER-based recession starts."
        ),
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="download fresh FRED source files even when a local cache exists",
    )
    return parser


def run(*, refresh: bool = False) -> dict[str, object]:
    observations, metadata = load_monthly_data(RAW_DATA_DIR, refresh=refresh)
    thresholds = tuple(
        sorted(
            set(SENSITIVITY_THRESHOLDS_PERCENT)
            | {PRIMARY_THRESHOLD_PERCENT}
        )
    )
    analysis = analyze(observations, thresholds)
    generate_charts(
        observations,
        analysis["primary"],
        CHARTS_DIR,
        SITE_IMAGE_DIR,
    )
    files = write_outputs(
        observations,
        analysis,
        metadata,
        RESULTS_DIR,
        SITE_SUMMARY_PATH,
    )
    return {"analysis": analysis, "metadata": metadata, "files": files}


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run(refresh=args.refresh)
    except (DataError, OSError, ValueError) as exc:
        raise SystemExit(f"CIC-003 analysis failed: {exc}") from exc

    primary = result["analysis"]["primary"]
    print(
        json.dumps(
            {
                "sample": (
                    f"{result['analysis']['sample_start']} through "
                    f"{result['analysis']['sample_end']}"
                ),
                "monthly_observations": result["analysis"]["monthly_observations"],
                "recession_onsets": result["analysis"]["recession_onsets"],
                "primary_threshold_percent": PRIMARY_THRESHOLD_PERCENT,
                "confirmed_episodes": primary["confirmed_episodes"],
                "hit_episodes": primary["hit_episodes"],
                "false_alarm_episodes": primary["false_alarm_episodes"],
                "right_censored_episodes": primary["right_censored_episodes"],
                "covered_recession_onsets": primary[
                    "covered_recession_onsets"
                ],
                "missed_recession_onsets": primary["missed_recession_onsets"],
                "output_files": {
                    name: str(path) for name, path in result["files"].items()
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
