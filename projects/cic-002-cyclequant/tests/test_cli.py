from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

import cyclequant.cli as cli
from cyclequant.models import OrderStatus


class _ClientContext:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None


@pytest.mark.parametrize("position_reconciled, expected_exit", [(True, 0), (False, 1)])
async def test_sync_broker_exit_matches_reconciliation_state(
    monkeypatch, capsys, position_reconciled: bool, expected_exit: int
) -> None:
    settings = object()
    database = SimpleNamespace(list_decisions=lambda limit=1: [object()])
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
