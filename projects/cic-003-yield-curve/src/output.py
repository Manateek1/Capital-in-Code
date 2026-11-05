"""Write machine-readable analysis results and website-ready summary data."""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any

from .data import MonthlyObservation


def _json_safe(value: Any) -> Any:
    if isinstance(value, date):
        return value.strftime("%Y-%m")
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(
    observations: list[MonthlyObservation],
    analysis: dict[str, Any],
    metadata: dict[str, object],
    results_dir: Path,
    site_summary_path: Path,
) -> dict[str, Path]:
    """Write reproducible CSV/JSON output and the site summary module."""

    summary = {
        "project": "CIC-003 — The Yield Curve's Warning Window",
        "method": {
            "confirmation_months": 3,
            "post_inversion_follow_up_months": 12,
            "primary_threshold_percent": 0.0,
            "sensitivity_thresholds_percent": [-0.25, 0.0, 0.25],
        },
        "metadata": metadata,
        **analysis,
    }
    summary_path = results_dir / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(_json_safe(summary), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    monthly_rows = [
        {
            "month": observation.month.strftime("%Y-%m"),
            "mean_spread_percent": f"{observation.spread_percent:.6f}",
            "nber_recession_indicator": observation.recession,
        }
        for observation in observations
    ]
    monthly_path = results_dir / "monthly_observations.csv"
    _write_csv(
        monthly_path,
        ["month", "mean_spread_percent", "nber_recession_indicator"],
        monthly_rows,
    )

    episode_rows = []
    for episode in analysis["primary"]["episodes"]:
        episode_rows.append(
            {
                "episode": episode["episode"],
                "threshold_percent": episode["threshold_percent"],
                "inversion_start": episode["inversion_start"],
                "confirmation_month": episode["confirmation_month"],
                "inversion_end": episode["inversion_end"],
                "duration_months": episode["duration_months"],
                "evaluation_end": episode["evaluation_end"],
                "status": episode["status"],
                "recession_onsets_in_window": ",".join(
                    month.strftime("%Y-%m")
                    for month in episode["recession_onsets_in_window"]
                ),
                "months_from_confirmation_to_first_onset": episode[
                    "months_from_confirmation_to_first_onset"
                ],
                "months_from_inversion_end_to_first_onset": episode[
                    "months_from_inversion_end_to_first_onset"
                ],
            }
        )
    episodes_path = results_dir / "inversion_episodes.csv"
    _write_csv(
        episodes_path,
        list(episode_rows[0]) if episode_rows else ["episode"],
        episode_rows,
    )

    sensitivity_path = results_dir / "threshold_sensitivity.csv"
    _write_csv(
        sensitivity_path,
        list(analysis["threshold_sensitivity"][0]),
        analysis["threshold_sensitivity"],
    )

    site_summary_path.parent.mkdir(parents=True, exist_ok=True)
    site_summary_path.write_text(
        json.dumps(_json_safe(summary), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "summary": summary_path,
        "monthly": monthly_path,
        "episodes": episodes_path,
        "sensitivity": sensitivity_path,
        "site_summary": site_summary_path,
    }
