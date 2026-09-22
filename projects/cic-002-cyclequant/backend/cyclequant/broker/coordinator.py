from __future__ import annotations

import logging
from decimal import Decimal

from cyclequant.broker.base import PaperBroker
from cyclequant.database import Repository
from cyclequant.models import (
    Action,
    DecisionRecord,
    OrderEvent,
    OrderResult,
    OrderStatus,
    TradeIntent,
)
from cyclequant.risk import RiskEvaluation

logger = logging.getLogger(__name__)

TERMINAL_ORDER_STATUSES = {
    OrderStatus.FILLED,
    OrderStatus.CANCELED,
    OrderStatus.REJECTED,
    OrderStatus.FAILED,
}


def resolve_decision_order_state(
    decision: DecisionRecord, events: list[OrderEvent]
) -> DecisionRecord:
    """Overlay the latest append-only broker event on an immutable decision."""

    if not events:
        return decision
    latest = events[-1]
    filled_quantity = latest.filled_quantity or decision.trade_quantity
    fill_price = latest.filled_average_price or decision.fill_price
    trade_value = decision.trade_value
    if filled_quantity and fill_price is not None:
        trade_value = (filled_quantity * fill_price).quantize(Decimal("0.01"))
    return decision.model_copy(
        update={
            "order_status": latest.status,
            "trade_quantity": filled_quantity,
            "fill_price": fill_price,
            "trade_value": trade_value,
        }
    )


async def reconcile_decision_order(
    database: Repository,
    broker: PaperBroker,
    decision: DecisionRecord,
) -> DecisionRecord:
    """Append a broker lifecycle event and return the effective decision state."""

    events = database.list_order_events(decision.id)
    effective = resolve_decision_order_state(decision, events)
    if effective.action == Action.HOLD or effective.order_status in TERMINAL_ORDER_STATUSES:
        return effective

    client_order_id = next(
        (
            str(event.payload["client_order_id"])
            for event in reversed(events)
            if event.payload.get("client_order_id")
        ),
        None,
    )
    if client_order_id is None:
        return effective

    result = await broker.get_order_by_client_id(client_order_id)
    if result is None:
        return effective

    latest = events[-1] if events else None
    unchanged = bool(
        latest
        and latest.status == result.status
        and latest.filled_quantity == result.filled_quantity
        and latest.filled_average_price == result.filled_average_price
    )
    if unchanged:
        return effective

    reconciled = OrderEvent(
        decision_id=decision.id,
        order_id=result.order_id,
        event_type="broker_reconciliation",
        status=result.status,
        filled_quantity=result.filled_quantity,
        filled_average_price=result.filled_average_price,
        payload={
            "client_order_id": result.client_order_id,
            "requested_notional": str(result.requested_notional),
            "error": result.error,
        },
    )
    database.append_order_event(reconciled)
    return resolve_decision_order_state(decision, [*events, reconciled])


class OrderCoordinator:
    """Restart-safe order submission using deterministic client order IDs."""

    def __init__(self, database: Repository, broker: PaperBroker) -> None:
        self.database = database
        self.broker = broker

    async def submit(self, intent: TradeIntent, risk: RiskEvaluation) -> OrderResult:
        # A prior process may have submitted successfully and crashed before it
        # persisted the decision. Reconcile that exact client ID before applying
        # the duplicate-id risk rejection; never send a second order.
        if self.database.idempotency_key_exists(intent.client_order_id):
            existing = await self.broker.get_order_by_client_id(intent.client_order_id)
            if existing:
                return existing
            return OrderResult(
                client_order_id=intent.client_order_id,
                status=OrderStatus.REJECTED,
                action=intent.action,
                symbol=intent.symbol,
                requested_notional=intent.notional,
                error=(
                    "Idempotency key already exists but no broker order was found; "
                    "manual reconciliation is required and no retry was submitted."
                ),
            )

        if not risk.approved:
            failures = "; ".join(check.reason for check in risk.failures)
            logger.warning(
                "paper order rejected by risk engine",
                extra={"client_order_id": intent.client_order_id, "failures": failures},
            )
            return OrderResult(
                client_order_id=intent.client_order_id,
                status=OrderStatus.REJECTED,
                action=intent.action,
                symbol=intent.symbol,
                requested_notional=intent.notional,
                error=failures,
            )

        claimed = self.database.claim_idempotency_key(intent.client_order_id, intent.decision_date)
        if not claimed:
            return OrderResult(
                client_order_id=intent.client_order_id,
                status=OrderStatus.REJECTED,
                action=intent.action,
                symbol=intent.symbol,
                requested_notional=intent.notional,
                error=(
                    "Idempotency key already exists but no broker order was found; "
                    "manual reconciliation is required and no retry was submitted."
                ),
            )

        try:
            return await self.broker.submit_market_order(intent)
        except Exception as exc:
            logger.exception(
                "paper broker submission failed",
                extra={"client_order_id": intent.client_order_id},
            )
            return OrderResult(
                client_order_id=intent.client_order_id,
                status=OrderStatus.FAILED,
                action=intent.action,
                symbol=intent.symbol,
                requested_notional=intent.notional,
                error=str(exc),
            )
