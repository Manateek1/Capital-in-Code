from __future__ import annotations

from datetime import UTC, date, datetime

HALVING_DATES = (
    date(2012, 11, 28),
    date(2016, 7, 9),
    date(2020, 5, 11),
    date(2024, 4, 20),
)
EXPECTED_CYCLE_DAYS = 1460.0


def halving_cycle_position(as_of: date | datetime) -> tuple[int | None, float | None]:
    current_date = as_of.astimezone(UTC).date() if isinstance(as_of, datetime) else as_of
    prior = [halving for halving in HALVING_DATES if halving <= current_date]
    if not prior:
        return None, None
    days_since = (current_date - prior[-1]).days
    return days_since, max(0.0, min(days_since / EXPECTED_CYCLE_DAYS, 2.0))
