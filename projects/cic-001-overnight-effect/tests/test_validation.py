"""Tests for deterministic data validation and cleaning."""

from __future__ import annotations

import pandas as pd
import pytest

from src.validation import DataValidationError, validate_and_clean_prices


def test_unsorted_rows_are_sorted() -> None:
    prices = pd.DataFrame(
        {"Open": [102.0, 100.0], "Close": [103.0, 101.0]},
        index=pd.to_datetime(["2024-01-03", "2024-01-02"]),
    )

    cleaned, report = validate_and_clean_prices(prices)

    assert cleaned.index.is_monotonic_increasing
    assert not report.input_was_sorted


def test_missing_and_invalid_values_are_counted_and_removed() -> None:
    prices = pd.DataFrame(
        {
            "Open": [100.0, None, "bad", -5.0, 104.0, 105.0],
            "Close": [101.0, 102.0, 103.0, 104.0, 0.0, 106.0],
        },
        index=pd.date_range("2024-01-01", periods=6, freq="D"),
    )

    cleaned, report = validate_and_clean_prices(prices)

    assert len(cleaned) == 2
    assert report.missing_open_rows == 1
    assert report.non_numeric_open_rows == 1
    assert report.non_positive_open_rows == 1
    assert report.non_positive_close_rows == 1
    assert report.invalid_rows_removed == 4
    assert report.returns_removed_due_to_invalid_previous_row == 1


def test_duplicate_trading_dates_raise() -> None:
    prices = pd.DataFrame(
        {"Open": [100.0, 101.0, 102.0], "Close": [101.0, 102.0, 103.0]},
        index=pd.to_datetime(["2024-01-02", "2024-01-02", "2024-01-03"]),
    )

    with pytest.raises(DataValidationError, match="duplicate trading"):
        validate_and_clean_prices(prices)


def test_return_after_invalid_row_is_marked_unaligned() -> None:
    prices = pd.DataFrame(
        {
            "Open": [100.0, None, 102.0, 103.0],
            "Close": [101.0, None, 103.0, 104.0],
        },
        index=pd.bdate_range("2024-01-02", periods=4),
    )

    cleaned, report = validate_and_clean_prices(prices)

    assert cleaned["previous_observation_valid"].tolist() == [True, False, True]
    assert report.returns_removed_due_to_invalid_previous_row == 1


def test_timezone_is_removed_without_changing_calendar_date() -> None:
    prices = pd.DataFrame(
        {"Open": [100.0, 101.0], "Close": [101.0, 102.0]},
        index=pd.DatetimeIndex(
            ["2024-01-02 00:00", "2024-01-03 00:00"],
            tz="America/New_York",
        ),
    )

    cleaned, report = validate_and_clean_prices(prices)

    assert cleaned.index.tz is None
    assert cleaned.index[0].date().isoformat() == "2024-01-02"
    assert report.timezone_removed


@pytest.mark.parametrize(
    "prices, message",
    [
        (pd.DataFrame(), "empty"),
        (
            pd.DataFrame(
                {"Open": [100.0, 101.0]},
                index=pd.date_range("2024-01-01", periods=2),
            ),
            "missing required",
        ),
        (
            pd.DataFrame(
                {"Open": [0.0, -1.0], "Close": [1.0, 2.0]},
                index=pd.date_range("2024-01-01", periods=2),
            ),
            "not enough valid",
        ),
    ],
)
def test_unusable_data_raises(prices: pd.DataFrame, message: str) -> None:
    with pytest.raises(DataValidationError, match=message):
        validate_and_clean_prices(prices)
