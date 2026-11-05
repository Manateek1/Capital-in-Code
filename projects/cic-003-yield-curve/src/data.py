"""Download, validate, and align FRED data for CIC-003."""

from __future__ import annotations

import csv
import math
import shutil
import subprocess
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from .config import FRED_T10Y3M_URL, FRED_USREC_URL


class DataError(ValueError):
    """Raised when a source file cannot support the declared analysis."""


@dataclass(frozen=True)
class MonthlyObservation:
    """One calendar month's mean spread and recession indicator."""

    month: date
    spread_percent: float
    recession: int


def _download(url: str, destination: Path) -> None:
    """Download one FRED CSV using curl when available, otherwise urllib."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".download")
    curl = shutil.which("curl")
    if curl:
        try:
            result = subprocess.run(
                [
                    curl,
                    "--fail",
                    "--location",
                    "--silent",
                    "--show-error",
                    "--max-time",
                    "60",
                    "--output",
                    str(temporary),
                    url,
                ],
                capture_output=True,
                check=False,
                text=True,
                timeout=65,
            )
        except subprocess.TimeoutExpired as exc:
            temporary.unlink(missing_ok=True)
            raise DataError(f"Download timed out for {url}") from exc
        if result.returncode != 0:
            temporary.unlink(missing_ok=True)
            raise DataError(
                f"Could not download {url}: {result.stderr.strip() or result.returncode}"
            )
    else:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Capital-in-Code-CIC-003/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                temporary.write_bytes(response.read())
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise DataError(f"Could not download {url}: {exc}") from exc

    if not temporary.is_file() or temporary.stat().st_size == 0:
        temporary.unlink(missing_ok=True)
        raise DataError(f"The source returned an empty file: {url}")
    temporary.replace(destination)


def _read_rows(path: Path) -> tuple[list[dict[str, str]], str]:
    if not path.is_file():
        raise DataError(f"Source file is missing: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise DataError(f"Source file has no header: {path}")
        fields = {field.strip().lower(): field for field in reader.fieldnames}
        date_field = fields.get("observation_date") or fields.get("date")
        if date_field is None:
            raise DataError(f"Source file has no observation date column: {path}")
        value_fields = [field for field in reader.fieldnames if field != date_field]
        if len(value_fields) != 1:
            raise DataError(f"Expected one value column in {path}")
        return list(reader), value_fields[0]


def _parse_month(value: str) -> date:
    observed = date.fromisoformat(value)
    return date(observed.year, observed.month, 1)


def load_monthly_data(
    raw_dir: Path,
    *,
    refresh: bool = False,
) -> tuple[list[MonthlyObservation], dict[str, object]]:
    """Load a continuous common monthly sample from the two FRED series."""

    curve_path = raw_dir / "t10y3m.csv"
    recession_path = raw_dir / "usrec.csv"
    if refresh or not curve_path.is_file():
        _download(FRED_T10Y3M_URL, curve_path)
    if refresh or not recession_path.is_file():
        _download(FRED_USREC_URL, recession_path)

    curve_rows, curve_field = _read_rows(curve_path)
    recession_rows, recession_field = _read_rows(recession_path)

    daily_by_month: dict[date, list[float]] = defaultdict(list)
    seen_curve_dates: set[date] = set()
    valid_daily_dates: list[date] = []
    blank_daily_rows = 0
    for row in curve_rows:
        observed = date.fromisoformat(row["observation_date"].strip())
        if observed in seen_curve_dates:
            raise DataError(f"Duplicate T10Y3M date: {observed.isoformat()}")
        seen_curve_dates.add(observed)
        raw_value = (row[curve_field] or "").strip()
        if raw_value in {"", "."}:
            blank_daily_rows += 1
            continue
        value = float(raw_value)
        if not math.isfinite(value):
            raise DataError(f"Non-finite T10Y3M value on {observed.isoformat()}")
        daily_by_month[_parse_month(observed.isoformat())].append(value)
        valid_daily_dates.append(observed)

    recession_by_month: dict[date, int] = {}
    for row in recession_rows:
        month = _parse_month(row["observation_date"].strip())
        if month in recession_by_month:
            raise DataError(f"Duplicate USREC month: {month.isoformat()}")
        value = int(row[recession_field])
        if value not in {0, 1}:
            raise DataError(f"USREC must be 0 or 1 for {month.isoformat()}")
        recession_by_month[month] = value

    common_months = sorted(set(daily_by_month) & set(recession_by_month))
    if not common_months:
        raise DataError("The FRED sources have no common monthly observations")

    observations = [
        MonthlyObservation(
            month=month,
            spread_percent=sum(daily_by_month[month]) / len(daily_by_month[month]),
            recession=recession_by_month[month],
        )
        for month in common_months
    ]
    for previous, current in zip(observations, observations[1:], strict=False):
        expected_month = date(
            previous.month.year + (previous.month.month == 12),
            1 if previous.month.month == 12 else previous.month.month + 1,
            1,
        )
        if current.month != expected_month:
            raise DataError(
                "Common monthly data has a gap between "
                f"{previous.month:%Y-%m} and {current.month:%Y-%m}"
            )

    curve_mtime = datetime.fromtimestamp(
        curve_path.stat().st_mtime,
        tz=timezone.utc,
    ).isoformat(timespec="seconds")
    recession_mtime = datetime.fromtimestamp(
        recession_path.stat().st_mtime,
        tz=timezone.utc,
    ).isoformat(timespec="seconds")
    metadata: dict[str, object] = {
        "analysis_run_at_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "data_retrieved_at_utc": min(curve_mtime, recession_mtime),
        "source_file_modified_at_utc": {
            "T10Y3M": curve_mtime,
            "USREC": recession_mtime,
        },
        "curve_raw_first_date": min(valid_daily_dates).isoformat(),
        "curve_raw_last_date": max(valid_daily_dates).isoformat(),
        "curve_valid_daily_rows": len(valid_daily_dates),
        "curve_blank_source_rows": blank_daily_rows,
        "recession_raw_first_month": min(recession_by_month).strftime("%Y-%m"),
        "recession_raw_last_month": max(recession_by_month).strftime("%Y-%m"),
        "common_months": len(observations),
        "sample_start": observations[0].month.strftime("%Y-%m"),
        "sample_end": observations[-1].month.strftime("%Y-%m"),
        "data_sources": {
            "spread": "FRED T10Y3M daily series; monthly arithmetic mean",
            "recession": "FRED USREC monthly NBER-based indicator",
        },
    }
    return observations, metadata
