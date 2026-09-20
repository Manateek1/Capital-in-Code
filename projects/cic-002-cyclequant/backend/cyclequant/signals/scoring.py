from __future__ import annotations

import math
import statistics
from collections.abc import Callable
from itertools import pairwise
from typing import Any

from cyclequant.constants import DEFAULT_SIGNAL_WEIGHTS
from cyclequant.models import (
    Confidence,
    MarketDataBundle,
    SignalReading,
    SignalSnapshot,
)


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def interpolate(value: float, points: list[tuple[float, float]]) -> float:
    ordered = sorted(points)
    if value <= ordered[0][0]:
        return ordered[0][1]
    if value >= ordered[-1][0]:
        return ordered[-1][1]
    for (left_x, left_y), (right_x, right_y) in pairwise(ordered):
        if left_x <= value <= right_x:
            fraction = (value - left_x) / (right_x - left_x)
            return left_y + fraction * (right_y - left_y)
    return ordered[-1][1]


class SignalEngine:
    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = (weights or DEFAULT_SIGNAL_WEIGHTS).copy()
        if set(self.weights) != set(DEFAULT_SIGNAL_WEIGHTS):
            raise ValueError("signal weight names do not match the strategy components")
        if abs(sum(self.weights.values()) - 1.0) > 1e-9:
            raise ValueError("signal weights must sum to 1.0")

    def score(self, bundle: MarketDataBundle, news_score: float | None = None) -> SignalSnapshot:
        calculators: dict[str, Callable[[], tuple[float, bool, str, dict[str, Any]]]] = {
            "valuation": lambda: self._valuation(bundle),
            "trend": lambda: self._trend(bundle),
            "drawdown": lambda: self._drawdown(bundle),
            "onchain": lambda: self._onchain_derivatives(bundle),
            "macro": lambda: self._macro_flows(bundle),
            "news": lambda: self._news(news_score),
        }
        raw: dict[str, tuple[float, bool, str, dict[str, Any]]] = {
            name: calculator() for name, calculator in calculators.items()
        }
        available_weight = sum(
            self.weights[name] for name, (_, available, _, _) in raw.items() if available
        )
        if available_weight <= 0:
            raise ValueError("no signal components are available")

        components: dict[str, SignalReading] = {}
        for name, (score, available, rationale, inputs) in raw.items():
            effective_weight = self.weights[name] / available_weight if available else 0.0
            components[name] = SignalReading(
                name=name,
                score=round(clamp(score), 2),
                configured_weight=self.weights[name],
                effective_weight=effective_weight,
                available=available,
                rationale=rationale,
                inputs=inputs,
            )

        total_score = sum(
            component.score * component.effective_weight for component in components.values()
        )
        available_scores = [
            component.score for component in components.values() if component.available
        ]
        dispersion = statistics.pstdev(available_scores) if len(available_scores) > 1 else 0.0
        required_fresh = bundle.required_data_is_fresh()
        confidence = self._confidence(available_weight, dispersion, required_fresh)
        return SignalSnapshot(
            components=components,
            total_score=round(total_score, 2),
            confidence=confidence,
            coverage=round(available_weight, 4),
            dispersion=round(dispersion, 2),
        )

    def _valuation(self, bundle: MarketDataBundle) -> tuple[float, bool, str, dict[str, Any]]:
        indicators = bundle.indicators
        ratio = indicators.power_law_ratio
        if ratio is None:
            return 50.0, False, "Power-law valuation needs more history.", {}
        ratio_score = interpolate(
            ratio,
            [(0.45, 95), (0.7, 82), (1.0, 62), (1.5, 42), (2.25, 20), (4.0, 5)],
        )
        fraction = indicators.halving_cycle_fraction
        if fraction is None:
            cycle_score = 50.0
        else:
            cycle_score = interpolate(
                fraction,
                [(0.0, 58), (0.35, 72), (0.65, 58), (1.0, 32), (1.5, 22)],
            )
        score = 0.85 * ratio_score + 0.15 * cycle_score
        relation = "below" if ratio < 1 else "above"
        rationale = (
            f"Price is {relation} the expanding-window power-law estimate; "
            "cycle timing is a weak secondary feature."
        )
        return (
            score,
            True,
            rationale,
            {
                "power_law_ratio": ratio,
                "power_law_residual_zscore": indicators.power_law_residual_zscore,
                "halving_cycle_fraction": fraction,
            },
        )

    def _trend(self, bundle: MarketDataBundle) -> tuple[float, bool, str, dict[str, Any]]:
        indicators = bundle.indicators
        price = float(bundle.spot_price)
        averages = {
            "sma_20": indicators.sma_20,
            "sma_50": indicators.sma_50,
            "sma_100": indicators.sma_100,
            "sma_200": indicators.sma_200,
        }
        available = {name: value for name, value in averages.items() if value is not None}
        if len(available) < 2:
            return 50.0, False, "Insufficient moving-average history.", {}
        above_ratio = sum(price >= value for value in available.values()) / len(available)
        structure_score = 20.0 + 65.0 * above_ratio
        rsi = indicators.rsi_14
        if rsi is None:
            momentum_score = 50.0
        else:
            momentum_score = interpolate(
                rsi,
                [(0, 20), (30, 42), (50, 62), (65, 78), (75, 62), (100, 25)],
            )
        score = 0.75 * structure_score + 0.25 * momentum_score
        return (
            score,
            True,
            (
                f"Price is above {sum(price >= value for value in available.values())} of "
                f"{len(available)} tracked moving averages."
            ),
            {"price": price, "rsi_14": rsi, **available},
        )

    def _drawdown(self, bundle: MarketDataBundle) -> tuple[float, bool, str, dict[str, Any]]:
        ath = bundle.indicators.drawdown_from_ath
        local = bundle.indicators.drawdown_from_90d_high
        if ath is None or local is None:
            return 50.0, False, "Drawdown history is unavailable.", {}
        ath_score = interpolate(abs(ath), [(0.0, 32), (0.1, 45), (0.2, 62), (0.4, 82), (0.65, 94)])
        local_score = interpolate(
            abs(local), [(0.0, 48), (0.08, 60), (0.18, 76), (0.35, 88), (0.55, 94)]
        )
        score = 0.65 * ath_score + 0.35 * local_score
        return (
            score,
            True,
            (
                "Deeper drawdowns raise valuation opportunity but cannot override "
                "trend and risk gates."
            ),
            {"drawdown_from_ath": ath, "drawdown_from_90d_high": local},
        )

    def _onchain_derivatives(
        self, bundle: MarketDataBundle
    ) -> tuple[float, bool, str, dict[str, Any]]:
        sub_scores: list[float] = []
        inputs: dict[str, Any] = {}
        mvrv = bundle.onchain.get("mvrv")
        if mvrv:
            inputs["mvrv"] = mvrv.value
            sub_scores.append(
                interpolate(
                    mvrv.value,
                    [(0.7, 95), (1.0, 88), (1.5, 72), (2.5, 48), (3.5, 25), (6, 5)],
                )
            )
        funding = bundle.derivatives.get("funding_rate_7d_average")
        if funding:
            inputs["funding_rate_7d_average"] = funding.value
            sub_scores.append(
                interpolate(
                    funding.value,
                    [(-0.002, 85), (-0.0002, 70), (0.0, 58), (0.0003, 42), (0.0015, 12)],
                )
            )
        if not sub_scores:
            return 50.0, False, "On-chain and derivatives feeds are unavailable.", inputs
        return (
            statistics.fmean(sub_scores),
            True,
            ("Available MVRV and funding observations are combined with equal weight."),
            inputs,
        )

    def _macro_flows(self, bundle: MarketDataBundle) -> tuple[float, bool, str, dict[str, Any]]:
        contributions: list[float] = []
        inputs: dict[str, Any] = {}

        fed = bundle.macro.get("fed_funds_rate")
        if fed and "change" in fed.metadata:
            change = float(fed.metadata["change"])
            inputs["fed_funds_change"] = change
            contributions.append(interpolate(change, [(-0.5, 75), (0.0, 50), (0.5, 25)]))

        dollar = bundle.macro.get("broad_dollar_index")
        if dollar and "change" in dollar.metadata:
            change = float(dollar.metadata["change"])
            inputs["dollar_change"] = change
            contributions.append(interpolate(change, [(-2.0, 75), (0.0, 50), (2.0, 25)]))

        liquidity = bundle.macro.get("fed_balance_sheet")
        if liquidity and "change" in liquidity.metadata:
            change = float(liquidity.metadata["change"])
            inputs["fed_balance_sheet_change"] = change
            contributions.append(interpolate(change, [(-50000, 25), (0, 50), (50000, 75)]))

        etf = bundle.etf_flows.get("spot_btc_etf_net_flow_usd")
        if etf:
            flow = float(etf.metadata.get("five_session_sum", etf.value))
            inputs["etf_five_session_flow_usd"] = flow
            contributions.append(
                interpolate(
                    flow,
                    [(-1_500_000_000, 15), (0, 50), (1_500_000_000, 85)],
                )
            )

        if not contributions:
            return 50.0, False, "Macro and ETF-flow observations are unavailable.", inputs
        return (
            statistics.fmean(contributions),
            True,
            ("Macro and flow inputs are averaged only when their source observations are present."),
            inputs,
        )

    @staticmethod
    def _news(news_score: float | None) -> tuple[float, bool, str, dict[str, Any]]:
        if news_score is None or not math.isfinite(news_score):
            return 50.0, False, "No validated news classification is available.", {}
        score = clamp(news_score)
        return (
            score,
            True,
            ("News is a bounded qualitative feature and cannot directly authorize an order."),
            {"validated_news_score": score},
        )

    @staticmethod
    def _confidence(coverage: float, dispersion: float, required_fresh: bool) -> Confidence:
        if not required_fresh or coverage < 0.65:
            return Confidence.LOW
        if coverage >= 0.85 and dispersion <= 25:
            return Confidence.HIGH
        return Confidence.MEDIUM
