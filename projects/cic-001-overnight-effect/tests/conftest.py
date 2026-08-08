"""Shared synthetic fixtures for offline CIC-001 tests."""

from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def synthetic_provider_prices() -> pd.DataFrame:
    """Three trading dates spanning a weekend with hand-checkable prices."""

    return pd.DataFrame(
        {
            "Open": [100.0, 110.0, 105.0],
            "Close": [100.0, 105.0, 110.0],
        },
        index=pd.to_datetime(["2024-01-05", "2024-01-08", "2024-01-09"]),
    )
