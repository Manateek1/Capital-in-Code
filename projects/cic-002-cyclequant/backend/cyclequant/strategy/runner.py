from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel

from cyclequant.broker.base import PaperBroker
from cyclequant.broker.coordinator import OrderCoordinator
from cyclequant.broker.mirror import capture_paper_account
from cyclequant.config import Settings
from cyclequant.constants import ALLOWED_EXPOSURES, STARTING_CAPITAL, STRATEGY_VERSION
from cyclequant.data.aggregator import MarketDataPipeline
from cyclequant.database import Repository
from cyclequant.models import (
    Action,
    AllocationState,
    DecisionRecord,
    NewsAnalysis,
    OrderEvent,
    OrderResult,
    OrderStatus,
    TradeIntent,
)
from cyclequant.news_analysis.analyzers import NewsAnalyzer
from cyclequant.news_analysis.explanations import build_decision_explanation
from cyclequant.risk import RiskContext, RiskEngine
from cyclequant.signals import AllocationEngine, SignalEngine

logger = logging.getLogger(__name__)


class DailyEvaluationResult(BaseModel):
    created: bool
    decision: DecisionRecord
    news_analysis: NewsAnalysis | None = None


class DailyStrategyRunner:
    """Executes one idempotent UTC evaluation from data collection through audit storage."""

    def __init__(
        self,
        *,
        settings: Settings,
        database: Repository,
        pipeline: MarketDataPipeline,
        news_analyzer: NewsAnalyzer,
        broker: PaperBroker,
        signal_engine: SignalEngine | None = None,
        allocation_engine: AllocationEngine | None = None,
        risk_engine: RiskEngine | None = None,
    ) -> None:
        self.settings = settings
        self.database = database
        self.pipeline = pipeline
        self.news_analyzer = news_analyzer
        self.broker = broker
        self.signal_engine = signal_engine or SignalEngine(settings.signal_weights)
        self.allocation_engine = allocation_engine or AllocationEngine(
            hysteresis_points=settings.hysteresis_points,
            confirmation_days=settings.confirmation_days,
            max_step=settings.max_allocation_step,
        )
        self.risk_engine = risk_engine or RiskEngine()

    async def run(self, as_of: datetime | None = None) -> DailyEvaluationResult:
        evaluated_at = (as_of or datetime.now(UTC)).astimezone(UTC)
        decision_date = evaluated_at.date()
        existing = self.database.get_decision_for_date(decision_date)
        if existing:
            logger.info("daily evaluation already exists", extra={"decision_id": existing.id})
            self._mark_simulated_price(existing.btc_price)
            await capture_paper_account(
                settings=self.settings,
                database=self.database,
                broker=self.broker,
                decision=existing,
            )
            return DailyEvaluationResult(created=False, decision=existing)

        market = await self.pipeline.run(evaluated_at, self.settings.history_days)
        snapshot_id = self.database.save_market_snapshot(market)
        news = await self.news_analyzer.analyze(market.news, evaluated_at)
        signals = self.signal_engine.score(market, news_score=news.score)
        prior = self.database.list_decisions(limit=1)
        allocation_state = self._allocation_state(prior[0] if prior else None, decision_date)
        recommendation = self.allocation_engine.recommend(signals, allocation_state)

        self._mark_simulated_price(market.spot_price)
        account = await self.broker.get_account()
        position_quantity = await self.broker.get_btc_position_quantity()
        strategy_portfolio_value = self._managed_portfolio_value(market.spot_price)
        action = self._action(
            recommendation.changed, allocation_state, recommendation.target_exposure
        )
        order_result: OrderResult | None = None
        risk_checks: list[dict] = []
        requested_notional = Decimal("0")

        if action != Action.HOLD:
            # Size only the isolated CycleQuant sleeve. Broker headline equity or
            # unrelated paper positions can never increase an order's notional.
            position_delta = (
                strategy_portfolio_value
                * Decimal(recommendation.target_exposure - allocation_state.current_exposure)
                / Decimal("100")
            )
            direction_matches_position = (action == Action.BUY and position_delta > 0) or (
                action == Action.SELL and position_delta < 0
            )
            requested_notional = (
                abs(position_delta).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                if direction_matches_position
                else Decimal("0")
            )
            quantity = (
                (requested_notional / market.spot_price).quantize(Decimal("0.00000001"))
                if action == Action.SELL
                else None
            )
            intent = TradeIntent(
                decision_date=decision_date,
                action=action,
                current_exposure=allocation_state.current_exposure,
                target_exposure=recommendation.target_exposure,
                notional=requested_notional,
                quantity=min(quantity, position_quantity) if quantity is not None else None,
                client_order_id=self._client_order_id(
                    decision_date.isoformat(), recommendation.target_exposure
                ),
            )
            risk = self.risk_engine.evaluate(
                RiskContext(
                    settings=self.settings,
                    database=self.database,
                    intent=intent,
                    account=account,
                    market=market,
                    kill_switch_path=self.settings.resolve_path(self.settings.kill_switch_path),
                    position_quantity=position_quantity,
                    strategy_portfolio_value=strategy_portfolio_value,
                )
            )
            risk_checks = [check.model_dump(mode="json") for check in risk.checks]
            order_result = await OrderCoordinator(self.database, self.broker).submit(intent, risk)

        important_news = self._important_news(market.news, news)
        reasoning = build_decision_explanation(signals, recommendation, news)
        executed_value = self._executed_value(order_result)
        decision = DecisionRecord(
            decision_date=decision_date,
            timestamp=evaluated_at,
            market_snapshot_id=snapshot_id,
            btc_price=market.spot_price,
            portfolio_value=strategy_portfolio_value,
            current_exposure=allocation_state.current_exposure,
            target_exposure=recommendation.target_exposure,
            signals=signals,
            allocation_recommendation=recommendation,
            important_news=important_news,
            ai_news_summary=news.summary,
            action=action,
            trade_value=executed_value,
            trade_quantity=order_result.filled_quantity if order_result else Decimal("0"),
            reasoning=reasoning,
            broker_order_id=order_result.order_id if order_result else None,
            order_status=order_result.status if order_result else OrderStatus.NOT_SUBMITTED,
            fill_price=order_result.filled_average_price if order_result else None,
            risk_checks=risk_checks,
        )
        self.database.create_decision(decision)
        if order_result:
            self.database.append_order_event(
                OrderEvent(
                    decision_id=decision.id,
                    order_id=order_result.order_id,
                    event_type="submission_result",
                    status=order_result.status,
                    filled_quantity=order_result.filled_quantity,
                    filled_average_price=order_result.filled_average_price,
                    payload={
                        "client_order_id": order_result.client_order_id,
                        "requested_notional": str(requested_notional),
                        "error": order_result.error,
                    },
                )
            )
        await self._record_performance(decision, market.bars)
        await capture_paper_account(
            settings=self.settings,
            database=self.database,
            broker=self.broker,
            decision=decision,
        )
        return DailyEvaluationResult(created=True, decision=decision, news_analysis=news)

    def _allocation_state(
        self, previous: DecisionRecord | None, decision_date
    ) -> AllocationState:
        if previous is None:
            return AllocationState(current_exposure=self.settings.initial_exposure)
        order_executed = previous.order_status == OrderStatus.FILLED
        current = previous.target_exposure if order_executed else previous.current_exposure
        recommendation = previous.allocation_recommendation
        is_consecutive = previous.decision_date == decision_date - timedelta(days=1)
        if (
            is_consecutive
            and recommendation
            and not recommendation.changed
            and recommendation.candidate_exposure is not None
            and recommendation.confirmations > 0
        ):
            return AllocationState(
                current_exposure=current,
                pending_exposure=recommendation.candidate_exposure,
                consecutive_confirmations=recommendation.confirmations,
            )
        return AllocationState(current_exposure=current)

    @staticmethod
    def _action(changed: bool, state: AllocationState, target: int) -> Action:
        if not changed or target == state.current_exposure:
            return Action.HOLD
        return Action.BUY if target > state.current_exposure else Action.SELL

    @staticmethod
    def _important_news(items, analysis: NewsAnalysis):
        relevance = {item.headline_id: item.relevance for item in analysis.assessments}
        return sorted(items, key=lambda item: relevance.get(item.id, 0), reverse=True)[:5]

    @staticmethod
    def _executed_value(result: OrderResult | None) -> Decimal:
        if not result or result.status in {OrderStatus.REJECTED, OrderStatus.FAILED}:
            return Decimal("0")
        if result.filled_average_price is not None and result.filled_quantity:
            return (result.filled_average_price * result.filled_quantity).quantize(Decimal("0.01"))
        return result.requested_notional

    @staticmethod
    def _client_order_id(decision_date: str, target: int) -> str:
        version = STRATEGY_VERSION.replace(".", "-")
        return f"cq-{decision_date.replace('-', '')}-{version}-{target}"

    def _mark_simulated_price(self, price: Decimal) -> None:
        if hasattr(self.broker, "btc_price"):
            self.broker.btc_price = price

    def _managed_portfolio_value(self, current_price: Decimal) -> Decimal:
        """Mark the isolated $1,000 research portfolio without using broker account size."""

        rows = self.database.list_performance()
        if not rows:
            return STARTING_CAPITAL
        previous = rows[-1]
        previous_value = Decimal(str(previous["cyclequant_value"]))
        previous_price = Decimal(str(previous["btc_price"]))
        previous_exposure = Decimal(str(previous["btc_exposure"])) / Decimal("100")
        btc_return = current_price / previous_price - Decimal("1")
        return (previous_value * (Decimal("1") + previous_exposure * btc_return)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    async def _record_performance(self, decision: DecisionRecord, bars) -> None:
        rows = self.database.list_performance()
        if not rows:
            cyclequant = STARTING_CAPITAL
            buy_hold = STARTING_CAPITAL
            ma200 = STARTING_CAPITAL
        else:
            previous = rows[-1]
            previous_price = Decimal(str(previous["btc_price"]))
            current_price = decision.btc_price
            buy_hold = (
                STARTING_CAPITAL * current_price / Decimal(str(rows[0]["btc_price"]))
            )
            cyclequant = Decimal(str(decision.portfolio_value))
            previous_ma = Decimal(str(previous["ma200_value"] or previous["cash_value"]))
            prior_closes = [
                bar.close for bar in bars if bar.timestamp.date() < decision.decision_date
            ]
            invested = (
                len(prior_closes) >= 200
                and prior_closes[-1] > sum(prior_closes[-200:]) / 200
            )
            ma200 = previous_ma * current_price / previous_price if invested else previous_ma
        resulting_exposure = (
            decision.target_exposure
            if decision.order_status == OrderStatus.FILLED
            else decision.current_exposure
        )
        self.database.upsert_performance(
            as_of=decision.decision_date,
            cyclequant_value=cyclequant.quantize(Decimal("0.01")),
            btc_buy_hold_value=buy_hold.quantize(Decimal("0.01")),
            cash_value=STARTING_CAPITAL,
            ma200_value=ma200.quantize(Decimal("0.01")),
            btc_price=decision.btc_price,
            btc_exposure=min(ALLOWED_EXPOSURES, key=lambda item: abs(item - resulting_exposure)),
        )
