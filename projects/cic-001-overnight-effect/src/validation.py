"""Validation and cleaning for daily adjusted market prices."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd


class DataValidationError(ValueError):
    """Raised when market data is malformed or unusable."""


@dataclass(frozen=True)
class ValidationReport:
    """Counts describing every deterministic cleaning decision."""

    input_rows: int
    input_was_sorted: bool
    timezone_removed: bool
    duplicate_date_rows: int
    missing_open_rows: int
    missing_close_rows: int
    non_numeric_open_rows: int
    non_numeric_close_rows: int
    non_positive_open_rows: int
    non_positive_close_rows: int
    invalid_rows_removed: int
    returns_removed_due_to_invalid_previous_row: int
    final_price_rows: int

    def as_dict(self, final_return_rows: int | None = None) -> dict[str, object]:
        """Return the report with optional alignment counts."""

        report = asdict(self)
        if final_return_rows is not None:
            report["first_unaligned_observation_removed"] = int(
                self.final_price_rows > 0
            )
            report["total_return_rows_removed_for_alignment"] = (
                self.final_price_rows - final_return_rows
            )
            report["final_return_rows"] = final_return_rows
        return report


def validate_and_clean_prices(
    prices: pd.DataFrame,
    *,
    minimum_observations: int = 2,
) -> tuple[pd.DataFrame, ValidationReport]:
    """Validate adjusted daily Open and Close data and remove invalid price rows.

    Duplicate trading dates are rejected because choosing one duplicate could
    silently alter previous-close alignment. Rows with missing, non-numeric, or
    non-positive prices are removed and counted. At least two clean price rows
    are required so one aligned return can be calculated.
    """

    if not isinstance(prices, pd.DataFrame) or prices.empty:
        raise DataValidationError("price data is empty")
    missing_columns = {"Open", "Close"} - set(prices.columns)
    if missing_columns:
        raise DataValidationError(
            f"price data is missing required columns: {sorted(missing_columns)}"
        )

    working = prices.loc[:, ["Open", "Close"]].copy()
    parsed_index = pd.DatetimeIndex(pd.to_datetime(working.index, errors="coerce"))
    invalid_date_mask = np.asarray(pd.isna(parsed_index), dtype=bool)
    if invalid_date_mask.any():
        raise DataValidationError(
            f"price data contains {int(invalid_date_mask.sum())} invalid dates"
        )
    dates = pd.DatetimeIndex(parsed_index)
    timezone_removed = dates.tz is not None
    if dates.tz is not None:
        dates = dates.tz_localize(None)
    dates = dates.normalize()
    working.index = pd.DatetimeIndex(dates, name="date")

    duplicate_rows = int(working.index.duplicated(keep=False).sum())
    if duplicate_rows:
        duplicated_dates = (
            working.index[working.index.duplicated(keep=False)]
            .unique()
            .strftime("%Y-%m-%d")
            .tolist()
        )
        raise DataValidationError(
            f"price data contains {duplicate_rows} rows on duplicate trading "
            f"dates: {duplicated_dates[:5]}"
        )

    input_was_sorted = working.index.is_monotonic_increasing
    working.sort_index(inplace=True)

    original_open = working["Open"]
    original_close = working["Close"]
    numeric_open = pd.to_numeric(original_open, errors="coerce")
    numeric_close = pd.to_numeric(original_close, errors="coerce")

    missing_open = original_open.isna()
    missing_close = original_close.isna()
    non_numeric_open = numeric_open.isna() & original_open.notna()
    non_numeric_close = numeric_close.isna() & original_close.notna()
    non_positive_open = numeric_open.le(0.0).fillna(False)
    non_positive_close = numeric_close.le(0.0).fillna(False)

    invalid_rows = (
        numeric_open.isna()
        | numeric_close.isna()
        | non_positive_open
        | non_positive_close
    )
    valid_rows = ~invalid_rows
    cleaned = pd.DataFrame(
        {"open": numeric_open, "close": numeric_close},
        index=working.index,
    ).loc[valid_rows]
    cleaned = cleaned.astype(float)

    previous_source_row_valid = valid_rows.shift(1, fill_value=False)
    alignment_valid = previous_source_row_valid.loc[valid_rows].astype(bool)
    if not alignment_valid.empty:
        # The first clean price row is removed later because its shifted close is
        # missing, regardless of what preceded it in the unclean source data.
        alignment_valid.iloc[0] = True
    cleaned["previous_observation_valid"] = alignment_valid
    invalid_predecessor_returns = int((~alignment_valid.iloc[1:]).sum())

    report = ValidationReport(
        input_rows=len(working),
        input_was_sorted=input_was_sorted,
        timezone_removed=timezone_removed,
        duplicate_date_rows=duplicate_rows,
        missing_open_rows=int(missing_open.sum()),
        missing_close_rows=int(missing_close.sum()),
        non_numeric_open_rows=int(non_numeric_open.sum()),
        non_numeric_close_rows=int(non_numeric_close.sum()),
        non_positive_open_rows=int(non_positive_open.sum()),
        non_positive_close_rows=int(non_positive_close.sum()),
        invalid_rows_removed=int(invalid_rows.sum()),
        returns_removed_due_to_invalid_previous_row=invalid_predecessor_returns,
        final_price_rows=len(cleaned),
    )

    if len(cleaned) < minimum_observations:
        raise DataValidationError(
            "not enough valid price observations after cleaning: "
            f"required={minimum_observations}, available={len(cleaned)}, "
            f"removed={report.invalid_rows_removed}"
        )
    return cleaned, report
