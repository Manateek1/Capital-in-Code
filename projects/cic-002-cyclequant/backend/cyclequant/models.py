from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from cyclequant.constants import ALLOWED_EXPOSURES, BTC_USD, STRATEGY_VERSION


class SourceState(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


class Action(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class Confidence(StrEnum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class OrderStatus(StrEnum):
    NOT_SUBMITTED = "NOT_SUBMITTED"
    REJECTED = "REJECTED"
    ACCEPTED = "ACCEPTED"
    PENDING = "PENDING"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    FAILED = "FAILED"


class OHLCVBar(BaseModel):
    timestamp: datetime
    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    close: Decimal = Field(gt=0)
    volume: Decimal = Field(ge=0)

    @field_validator("timestamp")
    @classmethod
    def ensure_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_range(self) -> OHLCVBar:
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must be greater than or equal to OHLC values")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must be less than or equal to OHLC values")
        return self


class MetricPoint(BaseModel):
    value: float
    observed_at: datetime
    source: str
    unit: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("observed_at")
    @classmethod
    def ensure_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class NewsItem(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    title: str
    source: str
    url: str
    published_at: datetime
    summary: str | None = None
    sentiment: str | None = None
    relevance: float | None = Field(default=None, ge=0, le=1)

    @field_validator("published_at")
    @classmethod
    def normalize_published_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class NewsSentiment(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class NewsAssessment(BaseModel):
    headline_id: str = Field(min_length=1, max_length=128)
    relevance: float = Field(ge=0, le=1)
    sentiment: NewsSentiment
    sentiment_score: float = Field(ge=-1, le=1)
    uncertainty: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1, max_length=280)


class NewsAnalysis(BaseModel):
    provider: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    score: float = Field(ge=0, le=100)
    uncertainty: float = Field(ge=0, le=1)
    summary: str = Field(min_length=1, max_length=1000)
    assessments: list[NewsAssessment] = Field(default_factory=list, max_length=20)
    considered_headline_ids: list[str] = Field(default_factory=list, max_length=20)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("generated_at")
    @classmethod
    def normalize_generated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def assessments_match_considered_ids(self) -> NewsAnalysis:
        assessment_ids = [item.headline_id for item in self.assessments]
        if len(assessment_ids) != len(set(assessment_ids)):
            raise ValueError("news assessment headline IDs must be unique")
        if len(self.considered_headline_ids) != len(set(self.considered_headline_ids)):
            raise ValueError("considered headline IDs must be unique")
        if not set(assessment_ids).issubset(self.considered_headline_ids):
            raise ValueError("every news assessment must reference a considered headline ID")
        return self


class SourceHealth(BaseModel):
    name: str
    state: SourceState
    required: bool
    observed_at: datetime | None = None
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IndicatorSnapshot(BaseModel):
    as_of: datetime
    sma_20: float | None = None
    sma_50: float | None = None
    sma_100: float | None = None
    sma_200: float | None = None
    distance_from_sma_200: float | None = None
    rsi_14: float | None = None
    realized_volatility_30d: float | None = None
    drawdown_from_ath: float | None = None
    drawdown_from_90d_high: float | None = None
    days_since_halving: int | None = None
    halving_cycle_fraction: float | None = None
    power_law_fair_value: float | None = None
    power_law_ratio: float | None = None
    power_law_residual_zscore: float | None = None


class MarketDataBundle(BaseModel):
    as_of: datetime
    symbol: str = BTC_USD
    spot_price: Decimal = Field(gt=0)
    bars: list[OHLCVBar]
    macro: dict[str, MetricPoint] = Field(default_factory=dict)
    derivatives: dict[str, MetricPoint] = Field(default_factory=dict)
    onchain: dict[str, MetricPoint] = Field(default_factory=dict)
    etf_flows: dict[str, MetricPoint] = Field(default_factory=dict)
    news: list[NewsItem] = Field(default_factory=list)
    sources: list[SourceHealth]
    indicators: IndicatorSnapshot

    def required_data_is_fresh(self) -> bool:
        required = [source for source in self.sources if source.required]
        return bool(required) and all(source.state == SourceState.FRESH for source in required)


class SignalReading(BaseModel):
    name: str
    score: float = Field(ge=0, le=100)
    configured_weight: float = Field(ge=0, le=1)
    effective_weight: float = Field(ge=0, le=1)
    available: bool = True
    rationale: str
    inputs: dict[str, Any] = Field(default_factory=dict)


class SignalSnapshot(BaseModel):
    components: dict[str, SignalReading]
    total_score: float = Field(ge=0, le=100)
    confidence: Confidence
    coverage: float = Field(ge=0, le=1)
    dispersion: float = Field(ge=0)


class AllocationRecommendation(BaseModel):
    raw_exposure: int
    target_exposure: int
    candidate_exposure: int | None = None
    changed: bool
    confirmations: int = Field(ge=0)
    reason: str

    @field_validator("raw_exposure", "target_exposure", "candidate_exposure")
    @classmethod
    def valid_exposure(cls, value: int | None) -> int | None:
        if value is not None and value not in ALLOWED_EXPOSURES:
            raise ValueError(f"exposure must be one of {ALLOWED_EXPOSURES}")
        return value


class AllocationState(BaseModel):
    current_exposure: int
    pending_exposure: int | None = None
    consecutive_confirmations: int = Field(default=0, ge=0)

    @field_validator("current_exposure", "pending_exposure")
    @classmethod
    def state_exposure_is_valid(cls, value: int | None) -> int | None:
        if value is not None and value not in ALLOWED_EXPOSURES:
            raise ValueError(f"exposure must be one of {ALLOWED_EXPOSURES}")
        return value


class TradeIntent(BaseModel):
    decision_date: date
    symbol: str = BTC_USD
    action: Action
    current_exposure: int
    target_exposure: int
    notional: Decimal = Field(ge=0)
    quantity: Decimal | None = Field(default=None, ge=0)
    client_order_id: str


class BrokerAccountSnapshot(BaseModel):
    account_id: str
    status: str
    currency: str
    portfolio_value: Decimal = Field(gt=0)
    cash: Decimal = Field(ge=0)
    buying_power: Decimal = Field(ge=0)
    trading_blocked: bool = False
    account_blocked: bool = False
    crypto_trading_enabled: bool = True
    endpoint: str


class OrderResult(BaseModel):
    order_id: str | None = None
    client_order_id: str
    status: OrderStatus
    action: Action
    symbol: str
    requested_notional: Decimal = Decimal("0")
    filled_quantity: Decimal = Decimal("0")
    filled_average_price: Decimal | None = None
    submitted_at: datetime | None = None
    raw: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class OrderEvent(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    decision_id: str
    order_id: str | None = None
    event_type: str
    status: OrderStatus
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    filled_quantity: Decimal = Decimal("0")
    filled_average_price: Decimal | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class DecisionRecord(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    decision_date: date
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    strategy_version: str = STRATEGY_VERSION
    market_snapshot_id: str
    btc_price: Decimal
    portfolio_value: Decimal
    current_exposure: int
    target_exposure: int
    signals: SignalSnapshot
    allocation_recommendation: AllocationRecommendation | None = None
    important_news: list[NewsItem] = Field(default_factory=list)
    ai_news_summary: str
    action: Action
    trade_value: Decimal = Decimal("0")
    trade_quantity: Decimal = Decimal("0")
    reasoning: str
    broker_order_id: str | None = None
    order_status: OrderStatus = OrderStatus.NOT_SUBMITTED
    fill_price: Decimal | None = None
    risk_checks: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("current_exposure", "target_exposure")
    @classmethod
    def decision_exposure_is_valid(cls, value: int) -> int:
        if value not in ALLOWED_EXPOSURES:
            raise ValueError(f"exposure must be one of {ALLOWED_EXPOSURES}")
        return value
