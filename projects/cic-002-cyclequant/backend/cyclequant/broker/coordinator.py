from __future__ import annotations

import logging

from cyclequant.broker.base import PaperBroker
from cyclequant.database import Repository
from cyclequant.models import OrderResult, OrderStatus, TradeIntent
from cyclequant.risk import RiskEvaluation

logger = logging.getLogger(__name__)


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
