from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

import cyclequant.cli as cli
from cyclequant.models import (
    Action,
    Confidence,
    DecisionRecord,
    OrderEvent,
    OrderStatus,
    SignalSnapshot,
)


class _ClientContext:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None


@pytest.mark.parametrize(
    "position_reconciled, pending_fee, expected_exit",
    [(True, False, 0), (False, True, 0), (False, False, 1)],
)
async def test_sync_broker_exit_matches_reconciliation_state(
    monkeypatch,
    capsys,
    position_reconciled: bool,
    pending_fee: bool,
    expected_exit: int,
) -> None:
    settings = object()
    decision = SimpleNamespace(
        action=Action.BUY if pending_fee else Action.HOLD,
        order_status=OrderStatus.FILLED if pending_fee else OrderStatus.NOT_SUBMITTED,
        trade_quantity=Decimal("0.01") if pending_fee else Decimal("0"),
        timestamp=datetime.now(UTC),
    )
    database = SimpleNamespace(list_decisions=lambda limit=1: [decision])
    snapshot = SimpleNamespace(
        captured_at=datetime(2026, 10, 13, 14, 32, tzinfo=UTC),
        broker_mode="alpaca-paper",
        connected=True,
        position_reconciled=position_reconciled,
        btc_fee_quantity=Decimal("0"),
        usd_fees_paid=Decimal("0"),
        latest_order_status=OrderStatus.FILLED,
    )

    monkeypatch.setattr(cli, "build_http_client", lambda _: _ClientContext())
    monkeypatch.setattr(cli, "_broker", lambda settings, client: object())

    async def reconcile(database, broker, decision):
        return decision

    monkeypatch.setattr(cli, "reconcile_decision_order", reconcile)

    async def capture(*, settings, database, broker, decision):
        return snapshot

    monkeypatch.setattr(cli, "capture_paper_account", capture)

    result = await cli._sync_broker(settings, database)

    output = json.loads(capsys.readouterr().out)
    assert output["position_reconciled"] is position_reconciled
    assert result == expected_exit


def test_health_accepts_same_day_buy_while_fee_posting_is_pending(capsys) -> None:
    now = datetime.now(UTC)
    decision = SimpleNamespace(
        id="decision",
        action=Action.BUY,
        decision_date=now.date(),
        order_status=OrderStatus.FILLED,
        trade_quantity=Decimal("0.01"),
        timestamp=now,
    )
    snapshot = SimpleNamespace(
        captured_at=now,
        broker_mode="alpaca-paper",
        paper_only=True,
        connected=True,
        account_status="ACTIVE",
        trading_enabled=True,
        trading_blocked=False,
        account_blocked=False,
        crypto_trading_enabled=True,
        position_reconciled=False,
        latest_order_status=OrderStatus.FILLED,
    )
    settings = SimpleNamespace(broker_mode="alpaca-paper", trading_enabled=True)
    database = SimpleNamespace(
        list_decisions=lambda limit=1: [decision],
        list_order_events=lambda decision_id: [],
        latest_paper_account_snapshot=lambda: snapshot,
    )

    result = cli._health(settings, database, max_age_minutes=120, require_today=True)

    output = json.loads(capsys.readouterr().out)
    assert result == 0
    assert output["ok"] is True
    assert output["checks"]["position_reconciled"] is False
    assert output["position_reconciliation_pending"] is True


@pytest.mark.parametrize("command", ["health", "sync-broker"])
@pytest.mark.parametrize(
    "buy_age, prior_action, prior_status, expected_exit",
    [
        (timedelta(hours=20), Action.BUY, OrderStatus.FILLED, 0),
        (timedelta(hours=20), Action.BUY, OrderStatus.PENDING, 0),
        (timedelta(hours=36), Action.BUY, OrderStatus.FILLED, 0),
        (timedelta(hours=36, seconds=1), Action.BUY, OrderStatus.FILLED, 1),
        (timedelta(seconds=-1), Action.BUY, OrderStatus.FILLED, 1),
        (timedelta(hours=20), Action.SELL, OrderStatus.FILLED, 1),
        (timedelta(hours=20), Action.BUY, OrderStatus.REJECTED, 1),
    ],
)
async def test_pending_buy_fee_after_a_new_hold(
    monkeypatch, capsys, command, buy_age, prior_action, prior_status, expected_exit
) -> None:
    now = datetime(2026, 10, 16, 8, tzinfo=UTC)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return now

    monkeypatch.setattr(cli, "datetime", FixedDatetime)
    hold = SimpleNamespace(
        id="hold",
        action=Action.HOLD,
        decision_date=now.date(),
        order_status=OrderStatus.NOT_SUBMITTED,
        trade_quantity=Decimal("0"),
        timestamp=now,
    )
    buy = DecisionRecord(
        id="buy",
        action=prior_action,
        decision_date=(now - buy_age).date(),
        order_status=prior_status,
        trade_quantity=Decimal("0.01"),
        timestamp=now - buy_age,
        market_snapshot_id="snapshot",
        btc_price=Decimal("80000"),
        portfolio_value=Decimal("1000"),
        current_exposure=25,
        target_exposure=50,
        signals=SignalSnapshot(
            components={}, total_score=70, confidence=Confidence.HIGH, coverage=1, dispersion=0
        ),
        ai_news_summary="fixture",
        reasoning="fixture",
    )
    history = [hold, buy]
    if buy_age >= timedelta(hours=32):
        history.insert(
            1,
            SimpleNamespace(
                **{
                    **vars(hold),
                    "id": "prior-hold",
                    "decision_date": (now - timedelta(days=1)).date(),
                    "timestamp": now - timedelta(days=1),
                }
            ),
        )
    events = (
        [
            OrderEvent(
                decision_id=buy.id,
                event_type="broker_reconciliation",
                status=OrderStatus.FILLED,
                filled_quantity=Decimal("0.01"),
                filled_average_price=Decimal("80000"),
            )
        ]
        if prior_status == OrderStatus.PENDING
        else []
    )
    snapshot = SimpleNamespace(
        captured_at=now,
        broker_mode="alpaca-paper",
        paper_only=True,
        connected=True,
        account_status="ACTIVE",
        trading_enabled=True,
        trading_blocked=False,
        account_blocked=False,
        crypto_trading_enabled=True,
        position_reconciled=False,
        btc_fee_quantity=Decimal("0"),
        usd_fees_paid=Decimal("0"),
        latest_order_status=OrderStatus.NOT_SUBMITTED,
    )
    settings = SimpleNamespace(broker_mode="alpaca-paper", trading_enabled=True)
    database = SimpleNamespace(
        list_decisions=lambda limit=1: history[:limit],
        list_order_events=lambda decision_id: events if decision_id == buy.id else [],
        latest_paper_account_snapshot=lambda: snapshot,
    )
    monkeypatch.setattr(cli, "build_http_client", lambda _: _ClientContext())
    monkeypatch.setattr(cli, "_broker", lambda settings, client: object())

    async def reconcile(database, broker, decision):
        return decision

    async def capture(**kwargs):
        return snapshot

    monkeypatch.setattr(cli, "reconcile_decision_order", reconcile)
    monkeypatch.setattr(cli, "capture_paper_account", capture)
    if command == "health":
        result = cli._health(settings, database, max_age_minutes=120, require_today=True)
    else:
        result = await cli._sync_broker(settings, database)

    output = json.loads(capsys.readouterr().out)
    assert result == expected_exit
    if command == "health":
        assert output["ok"] is (expected_exit == 0)
        assert output["checks"]["position_reconciled"] is False
        assert output["position_reconciliation_pending"] is (expected_exit == 0)
    else:
        assert output["position_reconciled"] is False
