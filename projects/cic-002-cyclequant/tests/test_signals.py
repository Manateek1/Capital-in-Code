from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest

from cyclequant.indicators import IndicatorEngine
from cyclequant.models import (
    AllocationState,
    Confidence,
    MarketDataBundle,
    MetricPoint,
    SignalReading,
    SignalSnapshot,
    SourceHealth,
    SourceState,
)
from cyclequant.signals import AllocationEngine, SignalEngine, score_to_exposure


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0, 0),
        (29.99, 0),
        (30, 25),
        (44.99, 25),
        (45, 50),
        (59.99, 50),
        (60, 75),
        (74.99, 75),
        (75, 100),
        (100, 100),
    ],
)
def test_score_mapping_boundaries(score: float, expected: int) -> None:
    assert score_to_exposure(score) == expected


def make_signal_snapshot(
    total: float, *, confidence: Confidence = Confidence.HIGH, supporting: int = 6
) -> SignalSnapshot:
    components = {}
    for index, name in enumerate(["valuation", "trend", "drawdown", "onchain", "macro", "news"]):
        component_score = 80 if index < supporting else 50
        components[name] = SignalReading(
            name=name,
            score=component_score,
            configured_weight=1 / 6,
            effective_weight=1 / 6,
            rationale="fixture",
        )
    return SignalSnapshot(
        components=components,
        total_score=total,
        confidence=confidence,
        coverage=1,
        dispersion=10,
    )


def test_hysteresis_and_confirmation_delay_a_change() -> None:
    engine = AllocationEngine(hysteresis_points=5, confirmation_days=2, max_step=25)
    signals = make_signal_snapshot(66)

    first = engine.recommend(signals, AllocationState(current_exposure=50))
    assert first.target_exposure == 50
    assert first.candidate_exposure == 75
    assert first.confirmations == 1

    second = engine.recommend(
        signals,
        AllocationState(
            current_exposure=50,
            pending_exposure=75,
            consecutive_confirmations=first.confirmations,
        ),
    )
    assert second.changed
    assert second.target_exposure == 75


def test_score_inside_hysteresis_margin_holds() -> None:
    recommendation = AllocationEngine().recommend(
        make_signal_snapshot(64), AllocationState(current_exposure=50)
    )
    assert recommendation.target_exposure == 50
    assert "hysteresis" in recommendation.reason


def test_low_confidence_forces_hold() -> None:
    recommendation = AllocationEngine(confirmation_days=1).recommend(
        make_signal_snapshot(90, confidence=Confidence.LOW),
        AllocationState(current_exposure=25),
    )
    assert recommendation.target_exposure == 25
    assert not recommendation.changed


def test_large_raw_move_is_step_limited_and_requires_breadth() -> None:
    engine = AllocationEngine(confirmation_days=1, max_step=25)
    blocked = engine.recommend(
        make_signal_snapshot(85, supporting=3), AllocationState(current_exposure=25)
    )
    assert blocked.target_exposure == 25
    assert "4 are required" in blocked.reason

    allowed = engine.recommend(
        make_signal_snapshot(85, supporting=4), AllocationState(current_exposure=25)
    )
    assert allowed.target_exposure == 50


def test_missing_optional_signals_are_reweighted_not_scored_neutral(daily_bars) -> None:
    as_of = daily_bars[-1].timestamp + timedelta(hours=1)
    bundle = MarketDataBundle(
        as_of=as_of,
        spot_price=daily_bars[-1].close,
        bars=daily_bars,
        sources=[
            SourceHealth(
                name="market",
                state=SourceState.FRESH,
                required=True,
                observed_at=daily_bars[-1].timestamp,
            )
        ],
        indicators=IndicatorEngine().compute(daily_bars, as_of=as_of),
    )
    snapshot = SignalEngine().score(bundle)
    assert snapshot.coverage == pytest.approx(0.65)
    assert snapshot.components["news"].available is False
    assert snapshot.components["news"].effective_weight == 0
    assert sum(item.effective_weight for item in snapshot.components.values()) == pytest.approx(1)
    assert snapshot.confidence == Confidence.MEDIUM


def test_optional_data_contributes_when_present(daily_bars) -> None:
    as_of = daily_bars[-1].timestamp + timedelta(hours=1)
    bundle = MarketDataBundle(
        as_of=as_of,
        spot_price=daily_bars[-1].close,
        bars=daily_bars,
        onchain={
            "mvrv": MetricPoint(value=1.25, observed_at=as_of, source="fixture", unit="ratio")
        },
        derivatives={
            "funding_rate_7d_average": MetricPoint(value=0.0, observed_at=as_of, source="fixture")
        },
        macro={
            "fed_funds_rate": MetricPoint(
                value=4.0,
                observed_at=as_of,
                source="fixture",
                metadata={"change": -0.25},
            )
        },
        etf_flows={
            "spot_btc_etf_net_flow_usd": MetricPoint(
                value=250_000_000,
                observed_at=as_of,
                source="fixture",
                metadata={"five_session_sum": 800_000_000},
            )
        },
        sources=[
            SourceHealth(
                name="market",
                state=SourceState.FRESH,
                required=True,
                observed_at=daily_bars[-1].timestamp,
            )
        ],
        indicators=IndicatorEngine().compute(daily_bars, as_of=as_of),
    )
    snapshot = SignalEngine().score(bundle, news_score=60)
    assert snapshot.coverage == 1
    assert all(component.available for component in snapshot.components.values())
    assert Decimal("0") <= Decimal(str(snapshot.total_score)) <= Decimal("100")
