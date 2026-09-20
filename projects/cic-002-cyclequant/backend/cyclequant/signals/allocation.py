from __future__ import annotations

from cyclequant.constants import ALLOWED_EXPOSURES
from cyclequant.models import (
    AllocationRecommendation,
    AllocationState,
    Confidence,
    SignalSnapshot,
)


def score_to_exposure(score: float) -> int:
    if not 0 <= score <= 100:
        raise ValueError("score must be between 0 and 100")
    if score < 30:
        return 0
    if score < 45:
        return 25
    if score < 60:
        return 50
    if score < 75:
        return 75
    return 100


LOWER_BOUND = {0: 0.0, 25: 30.0, 50: 45.0, 75: 60.0, 100: 75.0}
UPPER_BOUND = {0: 30.0, 25: 45.0, 50: 60.0, 75: 75.0, 100: 100.0}


class AllocationEngine:
    def __init__(
        self,
        *,
        hysteresis_points: float = 5.0,
        confirmation_days: int = 2,
        max_step: int = 25,
    ) -> None:
        if max_step not in {25, 50, 75, 100}:
            raise ValueError("max_step must be a 25-point allocation increment")
        self.hysteresis_points = hysteresis_points
        self.confirmation_days = confirmation_days
        self.max_step = max_step

    def recommend(
        self, signals: SignalSnapshot, state: AllocationState
    ) -> AllocationRecommendation:
        current = state.current_exposure
        raw = score_to_exposure(signals.total_score)

        if signals.confidence == Confidence.LOW:
            return AllocationRecommendation(
                raw_exposure=raw,
                target_exposure=current,
                candidate_exposure=None,
                changed=False,
                confirmations=0,
                reason="Low confidence blocks allocation changes.",
            )
        if raw == current:
            return AllocationRecommendation(
                raw_exposure=raw,
                target_exposure=current,
                candidate_exposure=None,
                changed=False,
                confirmations=0,
                reason="Composite score remains inside the current allocation band.",
            )

        moving_up = raw > current
        clears_hysteresis = (
            signals.total_score >= UPPER_BOUND[current] + self.hysteresis_points
            if moving_up
            else signals.total_score <= LOWER_BOUND[current] - self.hysteresis_points
        )
        if not clears_hysteresis:
            return AllocationRecommendation(
                raw_exposure=raw,
                target_exposure=current,
                candidate_exposure=None,
                changed=False,
                confirmations=0,
                reason="Score has not cleared the hysteresis margin around the current band.",
            )

        direction_scores = [
            component.score
            for component in signals.components.values()
            if component.available
            and ((moving_up and component.score >= 60) or (not moving_up and component.score <= 40))
        ]
        raw_gap = abs(raw - current)
        required_agreement = 4 if raw_gap > 25 else 2
        if len(direction_scores) < required_agreement:
            return AllocationRecommendation(
                raw_exposure=raw,
                target_exposure=current,
                candidate_exposure=None,
                changed=False,
                confirmations=0,
                reason=(
                    f"Only {len(direction_scores)} independent components support the move; "
                    f"{required_agreement} are required."
                ),
            )

        step = min(raw_gap, self.max_step)
        step -= step % 25
        candidate = current + step if moving_up else current - step
        candidate = min(ALLOWED_EXPOSURES, key=lambda exposure: abs(exposure - candidate))
        confirmations = (
            state.consecutive_confirmations + 1 if state.pending_exposure == candidate else 1
        )
        if confirmations < self.confirmation_days:
            return AllocationRecommendation(
                raw_exposure=raw,
                target_exposure=current,
                candidate_exposure=candidate,
                changed=False,
                confirmations=confirmations,
                reason=(
                    f"Candidate {candidate}% exposure has {confirmations} of "
                    f"{self.confirmation_days} required daily confirmations."
                ),
            )

        return AllocationRecommendation(
            raw_exposure=raw,
            target_exposure=candidate,
            candidate_exposure=candidate,
            changed=candidate != current,
            confirmations=confirmations,
            reason=(
                f"Score cleared hysteresis, {len(direction_scores)} independent components "
                f"agree, and {confirmations} daily confirmations were recorded."
            ),
        )
