"""Hand-verified tests for aligned return calculations."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.returns import calculate_returns
from src.validation import validate_and_clean_prices


def test_return_formulas_and_previous_trading_close_alignment(
    synthetic_provider_prices: pd.DataFrame,
) -> None:
    prices, _ = validate_and_clean_prices(synthetic_provider_prices)

    result = calculate_returns(prices)
    daily = result.daily

    monday = daily.loc[pd.Timestamp("2024-01-08")]
    assert monday["previous_close"] == pytest.approx(100.0)
    assert monday["overnight_return"] == pytest.approx(0.10)
    assert monday["intraday_return"] == pytest.approx(105.0 / 110.0 - 1.0)
    assert monday["close_to_close_return"] == pytest.approx(0.05)

    tuesday = daily.loc[pd.Timestamp("2024-01-09")]
    assert tuesday["previous_close"] == pytest.approx(105.0)
    assert tuesday["overnight_return"] == pytest.approx(0.0)
    assert tuesday["intraday_return"] == pytest.approx(110.0 / 105.0 - 1.0)
    assert tuesday["close_to_close_return"] == pytest.approx(110.0 / 105.0 - 1.0)


def test_first_price_row_is_removed_from_returns(
    synthetic_provider_prices: pd.DataFrame,
) -> None:
    prices, _ = validate_and_clean_prices(synthetic_provider_prices)
    daily = calculate_returns(prices).daily

    assert len(daily) == len(prices) - 1
    assert daily.index.min() == pd.Timestamp("2024-01-08")


def test_reconstruction_and_log_identity(
    synthetic_provider_prices: pd.DataFrame,
) -> None:
    prices, _ = validate_and_clean_prices(synthetic_provider_prices)
    result = calculate_returns(prices)
    daily = result.daily

    assert result.maximum_reconstruction_error <= 1e-12
    np.testing.assert_allclose(
        daily["overnight_log_return"] + daily["intraday_log_return"],
        daily["close_to_close_log_return"],
        atol=1e-14,
    )


def test_compounded_cumulative_returns(
    synthetic_provider_prices: pd.DataFrame,
) -> None:
    prices, _ = validate_and_clean_prices(synthetic_provider_prices)
    daily = calculate_returns(prices).daily
    final = daily.iloc[-1]

    assert final["cumulative_overnight_return"] == pytest.approx(0.10)
    assert final["cumulative_intraday_return"] == pytest.approx(0.0, abs=1e-14)
    assert final["cumulative_buy_and_hold_return"] == pytest.approx(0.10)
    assert final["buy_and_hold_growth"] == pytest.approx(1.10)


def test_return_calculation_does_not_bridge_an_invalid_source_row() -> None:
    provider_prices = pd.DataFrame(
        {
            "Open": [100.0, None, 102.0, 103.0, 104.0],
            "Close": [101.0, None, 103.0, 104.0, 105.0],
        },
        index=pd.bdate_range("2024-01-02", periods=5),
    )
    prices, _ = validate_and_clean_prices(provider_prices)

    daily = calculate_returns(prices).daily

    assert pd.Timestamp("2024-01-04") not in daily.index
    assert daily.index.tolist() == [
        pd.Timestamp("2024-01-05"),
        pd.Timestamp("2024-01-08"),
    ]
    assert daily.iloc[0]["previous_close"] == pytest.approx(103.0)
