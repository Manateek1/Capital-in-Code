from __future__ import annotations

import argparse
import math
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from cyclequant.constants import DEFAULT_SIGNAL_WEIGHTS
from cyclequant.database import Database
from cyclequant.indicators import IndicatorEngine
from cyclequant.models import (
    Action,
    AllocationRecommendation,
    Confidence,
    DecisionRecord,
    MarketDataBundle,
    NewsItem,
    OHLCVBar,
    OrderStatus,
    SignalReading,
    SignalSnapshot,
    SourceHealth,
    SourceState,
)

SIGNAL_NAMES = ["valuation", "trend", "drawdown", "onchain", "macro", "news"]


def _bars(end: date, count: int = 460) -> list[OHLCVBar]:
    start = end - timedelta(days=count - 1)
    raw = [42000 + index * 38 + math.sin(index / 13) * 2600 for index in range(count)]
    scale = 61240 / raw[-1]
    bars = []
    for index, unscaled in enumerate(raw):
        close = Decimal(str(round(unscaled * scale, 2)))
        bars.append(
            OHLCVBar(
                timestamp=datetime.combine(start + timedelta(days=index), datetime.min.time(), UTC),
                open=close * Decimal("0.997"),
                high=close * Decimal("1.018"),
                low=close * Decimal("0.982"),
                close=close,
                volume=Decimal("18000") + Decimal(index * 17),
            )
        )
    return bars


def _signals(index: int, latest: bool = False) -> SignalSnapshot:
    scores = [88, 72, 82, 74, 57, 51] if latest else [
        58 + 14 * math.sin(index / 7 + offset) for offset in range(6)
    ]
    components = {
        name: SignalReading(
            name=name,
            score=round(max(0, min(100, score)), 2),
            configured_weight=DEFAULT_SIGNAL_WEIGHTS[name],
            effective_weight=DEFAULT_SIGNAL_WEIGHTS[name],
            rationale=f"Demo {name} reading from the documented deterministic methodology.",
            inputs={"demo": True},
        )
        for name, score in zip(SIGNAL_NAMES, scores, strict=True)
    }
    total = sum(item.score * item.effective_weight for item in components.values())
    return SignalSnapshot(
        components=components,
        total_score=round(total, 2),
        confidence=Confidence.HIGH,
        coverage=1,
        dispersion=12.4,
    )


def seed(path: Path, end: date) -> Database:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing demo database: {path}")
    database = Database(path)
    database.initialize()
    bars = _bars(end)
    indicator_engine = IndicatorEngine()
    decision_start = end - timedelta(days=29)
    exposures = [25] * 7 + [50] * 10 + [25] * 5 + [50] * 7 + [75]
    previous_exposure = exposures[0]

    for index in range(30):
        day = decision_start + timedelta(days=index)
        day_bars = [bar for bar in bars if bar.timestamp.date() <= day]
        price = day_bars[-1].close
        bundle = MarketDataBundle(
            as_of=datetime.combine(day, datetime.max.time(), UTC),
            spot_price=price,
            bars=day_bars,
            sources=[
                SourceHealth(
                    name=name,
                    state=SourceState.FRESH,
                    required=name == "coinbase_exchange",
                    observed_at=day_bars[-1].timestamp,
                )
                for name in (
                    "coinbase_exchange",
                    "fred_macro",
                    "coinmetrics_community",
                    "binance_funding",
                    "google_news_rss",
                )
            ],
            indicators=indicator_engine.compute(day_bars, as_of=day_bars[-1].timestamp),
        )
        snapshot_id = database.save_market_snapshot(bundle)
        target = exposures[index]
        changed = target != previous_exposure or index == 29
        current = previous_exposure if index else target
        action = Action.HOLD
        if changed:
            action = Action.BUY if target > current else Action.SELL
        signals = _signals(index, latest=index == 29)
        news = NewsItem(
            id=f"demo-news-{index}",
            title="Institutional Bitcoin flows remain constructive while macro signals are mixed",
            source="Demo research feed",
            url="https://example.com/cyclequant-demo",
            published_at=datetime.combine(day, datetime.min.time(), UTC),
            relevance=0.9,
            sentiment="mixed",
        )
        decision = DecisionRecord(
            id=f"demo-{day.isoformat()}",
            decision_date=day,
            timestamp=datetime.combine(day, datetime.max.time(), UTC),
            market_snapshot_id=snapshot_id,
            btc_price=price,
            portfolio_value=Decimal(str(round(1000 + index * (82.4 / 29), 2))),
            current_exposure=current,
            target_exposure=target,
            signals=signals,
            allocation_recommendation=AllocationRecommendation(
                raw_exposure=target,
                target_exposure=target,
                candidate_exposure=target if changed else None,
                changed=changed,
                confirmations=2 if changed else 0,
                reason=(
                    "Score cleared hysteresis with broad component agreement."
                    if changed
                    else "Composite score remains inside the current allocation band."
                ),
            ),
            important_news=[news],
            ai_news_summary=(
                "News tone is balanced: institutional participation is constructive, "
                "while macro uncertainty limits conviction."
            ),
            action=action,
            trade_value=Decimal("250") if changed else Decimal("0"),
            trade_quantity=(Decimal("250") / price if changed else Decimal("0")),
            reasoning=(
                "Long-term valuation and drawdown conditions remain constructive. Trend and "
                "on-chain readings confirm the move, while mixed macro and news inputs keep "
                "the allocation below 100%."
            ),
            broker_order_id=f"demo-paper-{index}" if changed else None,
            order_status=OrderStatus.FILLED if changed else OrderStatus.NOT_SUBMITTED,
            fill_price=price if changed else None,
            risk_checks=[
                {"name": "paper_endpoint", "passed": True, "reason": "Demo paper account."},
                {"name": "no_margin", "passed": True, "reason": "Cash-funded allocation."},
            ],
        )
        database.create_decision(decision)
        previous_exposure = target

    start_price = bars[-90].close
    for index, bar in enumerate(bars[-90:]):
        progress = index / 89
        cycle_value = Decimal(
            str(round(1000 + 82.4 * progress + math.sin(progress * math.tau) * 13, 2))
        )
        btc_value = (Decimal("1000") * bar.close / start_price).quantize(Decimal("0.01"))
        ma_value = Decimal(str(round(1000 + 61 * progress + math.sin(index / 8) * 8, 2)))
        exposure = 50 if index < 82 else (75 if index == 89 else 50)
        database.upsert_performance(
            as_of=bar.timestamp.date(),
            cyclequant_value=cycle_value,
            btc_buy_hold_value=btc_value,
            cash_value=Decimal("1000"),
            ma200_value=ma_value,
            btc_price=bar.close,
            btc_exposure=exposure,
        )
    return database


def main() -> None:
    parser = argparse.ArgumentParser(description="Create deterministic CycleQuant demo data")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--end-date", type=date.fromisoformat, default=date(2026, 9, 20))
    args = parser.parse_args()
    database = seed(args.database, args.end_date)
    print(f"Seeded {database.description}")


if __name__ == "__main__":
    main()
