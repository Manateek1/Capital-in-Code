from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

import cyclequant.cli as cli
from cyclequant.models import Action, OrderStatus


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
        latest_paper_account_snapshot=lambda: snapshot,
    )

    result = cli._health(settings, database, max_age_minutes=120, require_today=True)

    output = json.loads(capsys.readouterr().out)
    assert result == 0
    assert output["ok"] is True
    assert output["checks"]["position_reconciled"] is False
    assert output["position_reconciliation_pending"] is True
