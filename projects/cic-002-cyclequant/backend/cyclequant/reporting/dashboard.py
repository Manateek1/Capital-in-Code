from __future__ import annotations

import math
import statistics
from datetime import UTC, datetime
from decimal import Decimal
from itertools import pairwise
from typing import Any

from cyclequant.broker import resolve_decision_order_state
from cyclequant.constants import STARTING_CAPITAL
from cyclequant.database import Repository
from cyclequant.models import DecisionRecord, OrderStatus


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _returns(values: list[float]) -> list[float]:
    return [right / left - 1 for left, right in pairwise(values) if left]


def _max_drawdown(values: list[float]) -> float:
    if not values:
        return 0.0
    peak = values[0]
    drawdown = 0.0
    for value in values:
        peak = max(peak, value)
        drawdown = min(drawdown, value / peak - 1)
    return drawdown


def _metrics(values: list[float], elapsed_days: int) -> dict[str, float | int | None]:
    if not values:
        return {
            "total_return": 0.0,
            "annualized_return": None,
            "max_drawdown": 0.0,
            "annualized_volatility": None,
            "approximate_sharpe": None,
        }
    daily = _returns(values)
    total = values[-1] / values[0] - 1 if values[0] else 0.0
    annualized = (
        (values[-1] / values[0]) ** (365 / elapsed_days) - 1
        if elapsed_days >= 30 and values[0] > 0 and values[-1] > 0
        else None
    )
    volatility = statistics.pstdev(daily) * math.sqrt(365) if len(daily) >= 2 else None
    sharpe = (
        statistics.fmean(daily) / statistics.pstdev(daily) * math.sqrt(365)
        if len(daily) >= 2 and statistics.pstdev(daily) > 0
        else None
    )
    return {
        "total_return": total,
        "annualized_return": annualized,
        "max_drawdown": _max_drawdown(values),
        "annualized_volatility": volatility,
        "approximate_sharpe": sharpe,
    }


def _resulting_exposure(decision: DecisionRecord) -> int:
    if decision.order_status == OrderStatus.FILLED:
        return decision.target_exposure
    return decision.current_exposure


def build_dashboard_payload(database: Repository) -> dict[str, Any]:
    decisions = [
        resolve_decision_order_state(decision, database.list_order_events(decision.id))
        if decision.action.value != "HOLD"
        else decision
        for decision in database.list_decisions(limit=1000)
    ]
    performance = database.list_performance()
    latest = decisions[0] if decisions else None
    oldest_date = datetime.fromisoformat(performance[0]["as_of"]).date() if performance else None
    newest_date = datetime.fromisoformat(performance[-1]["as_of"]).date() if performance else None
    elapsed_days = max((newest_date - oldest_date).days, 1) if oldest_date and newest_date else 1

    cycle_values = [float(_decimal(row["cyclequant_value"])) for row in performance]
    btc_values = [float(_decimal(row["btc_buy_hold_value"])) for row in performance]
    cash_values = [float(_decimal(row["cash_value"])) for row in performance]
    ma_values = [float(_decimal(row["ma200_value"])) for row in performance if row["ma200_value"]]
    trades = [decision for decision in decisions if decision.action.value != "HOLD"]
    paper_account = database.latest_paper_account_snapshot()

    source_health: list[dict[str, Any]] = []
    if latest:
        snapshot = database.get_market_snapshot(latest.market_snapshot_id)
        if snapshot:
            source_health = [item.model_dump(mode="json") for item in snapshot.sources]

    portfolio_value = cycle_values[-1] if cycle_values else float(STARTING_CAPITAL)
    managed_cash = (
        float(paper_account.strategy_cash)
        if paper_account
        else portfolio_value * (1 - (_resulting_exposure(latest) if latest else 0) / 100)
    )
    return {
        "schema_version": 2,
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": "paper-research",
        "disclaimer": (
            "Educational research only. Not investment advice and not a recommendation "
            "to buy or sell Bitcoin."
        ),
        "summary": {
            "portfolio_value": portfolio_value,
            "managed_cash": managed_cash,
            "total_return": portfolio_value / float(STARTING_CAPITAL) - 1,
            "current_exposure": _resulting_exposure(latest) if latest else 0,
            "btc_price": float(latest.btc_price) if latest else None,
            "signal_score": latest.signals.total_score if latest else None,
            "confidence": latest.signals.confidence.value if latest else None,
            "latest_action": latest.action.value if latest else "HOLD",
            "last_evaluated_at": latest.timestamp.isoformat() if latest else None,
        },
        "performance": [
            {
                "date": row["as_of"],
                "cyclequant": float(_decimal(row["cyclequant_value"])),
                "btc_buy_hold": float(_decimal(row["btc_buy_hold_value"])),
                "cash": float(_decimal(row["cash_value"])),
                "ma200": float(_decimal(row["ma200_value"])) if row["ma200_value"] else None,
                "btc_price": float(_decimal(row["btc_price"])),
                "exposure": int(row["btc_exposure"]),
            }
            for row in performance
        ],
        "metrics": {
            "cyclequant": _metrics(cycle_values, elapsed_days),
            "btc_buy_hold": _metrics(btc_values, elapsed_days),
            "cash": _metrics(cash_values, elapsed_days),
            "ma200": _metrics(ma_values, elapsed_days),
            "trade_count": len(trades),
            "filled_trade_count": sum(item.order_status == OrderStatus.FILLED for item in trades),
        },
        "latest_decision": latest.model_dump(mode="json") if latest else None,
        "paper_account": paper_account.model_dump(mode="json") if paper_account else None,
        "trade_history": [item.model_dump(mode="json") for item in trades],
        "decision_journal": [item.model_dump(mode="json") for item in decisions],
        "source_health": source_health,
    }
