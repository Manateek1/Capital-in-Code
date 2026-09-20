from __future__ import annotations

from cyclequant.models import AllocationRecommendation, NewsAnalysis, SignalSnapshot


def build_decision_explanation(
    signals: SignalSnapshot,
    recommendation: AllocationRecommendation,
    news: NewsAnalysis,
) -> str:
    """Explain an already-computed deterministic recommendation."""

    ranked = sorted(
        (component for component in signals.components.values() if component.available),
        key=lambda component: component.effective_weight,
        reverse=True,
    )
    drivers = ", ".join(
        f"{component.name} {component.score:.0f}/100" for component in ranked[:3]
    )
    movement = (
        f"move to {recommendation.target_exposure}% exposure"
        if recommendation.changed
        else f"hold {recommendation.target_exposure}% exposure"
    )
    return (
        f"The deterministic signal scored {signals.total_score:.1f}/100 with "
        f"{signals.confidence.value.lower()} confidence, led by {drivers}. The allocation "
        f"rules {movement}: {recommendation.reason} News contributed a bounded "
        f"{news.score:.1f}/100 feature and did not select or authorize the allocation."
    )
