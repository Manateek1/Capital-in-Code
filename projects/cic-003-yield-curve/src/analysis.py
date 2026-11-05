"""Episode-based analysis of the 10-year/3-month Treasury spread."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from statistics import median

from .config import CONFIRMATION_MONTHS, POST_EPISODE_MONTHS
from .data import MonthlyObservation


@dataclass(frozen=True)
class InversionEpisode:
    """One run of below-threshold monthly spreads and its outcome window."""

    episode: int
    threshold_percent: float
    inversion_start: date
    confirmation_month: date
    inversion_end: date
    duration_months: int
    evaluation_end: date
    status: str
    recession_onsets_in_window: tuple[date, ...]
    months_from_confirmation_to_first_onset: int | None
    months_from_inversion_end_to_first_onset: int | None


def add_months(month: date, count: int) -> date:
    """Return a first-of-month date offset by a calendar-month count."""

    absolute_month = month.year * 12 + month.month - 1 + count
    return date(absolute_month // 12, absolute_month % 12 + 1, 1)


def months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + end.month - start.month


def find_recession_onsets(observations: list[MonthlyObservation]) -> list[date]:
    """Find 0-to-1 transitions in FRED's monthly NBER-based indicator."""

    return [
        current.month
        for previous, current in zip(observations, observations[1:])
        if previous.recession == 0 and current.recession == 1
    ]


def build_episodes(
    observations: list[MonthlyObservation],
    recession_onsets: list[date],
    *,
    threshold_percent: float,
    confirmation_months: int = CONFIRMATION_MONTHS,
    post_episode_months: int = POST_EPISODE_MONTHS,
) -> list[InversionEpisode]:
    """Group consecutive inversions and test each confirmed warning window."""

    episodes: list[InversionEpisode] = []
    index = 0
    while index < len(observations):
        if observations[index].spread_percent > threshold_percent:
            index += 1
            continue

        run_start = index
        while (
            index + 1 < len(observations)
            and observations[index + 1].spread_percent <= threshold_percent
        ):
            index += 1
        run_end = index
        run_length = run_end - run_start + 1
        if run_length >= confirmation_months:
            confirmation_month = observations[
                run_start + confirmation_months - 1
            ].month
            inversion_end = observations[run_end].month
            evaluation_end = add_months(inversion_end, post_episode_months)
            onsets_in_window = tuple(
                onset
                for onset in recession_onsets
                if confirmation_month < onset <= evaluation_end
            )
            is_open = run_end == len(observations) - 1
            has_complete_horizon = evaluation_end <= observations[-1].month
            if onsets_in_window:
                status = "hit"
            elif is_open or not has_complete_horizon:
                status = "right-censored"
            else:
                status = "false-alarm"

            first_onset = onsets_in_window[0] if onsets_in_window else None
            episodes.append(
                InversionEpisode(
                    episode=len(episodes) + 1,
                    threshold_percent=threshold_percent,
                    inversion_start=observations[run_start].month,
                    confirmation_month=confirmation_month,
                    inversion_end=inversion_end,
                    duration_months=run_length,
                    evaluation_end=evaluation_end,
                    status=status,
                    recession_onsets_in_window=onsets_in_window,
                    months_from_confirmation_to_first_onset=(
                        months_between(confirmation_month, first_onset)
                        if first_onset
                        else None
                    ),
                    months_from_inversion_end_to_first_onset=(
                        months_between(inversion_end, first_onset)
                        if first_onset
                        else None
                    ),
                )
            )
        index += 1
    return episodes


def analyze_threshold(
    observations: list[MonthlyObservation],
    recession_onsets: list[date],
    threshold_percent: float,
) -> dict[str, object]:
    """Summarize episode outcomes and onset coverage for one threshold."""

    episodes = build_episodes(
        observations,
        recession_onsets,
        threshold_percent=threshold_percent,
    )
    covered_onsets = {
        onset
        for episode in episodes
        for onset in episode.recession_onsets_in_window
    }
    evaluated = [episode for episode in episodes if episode.status != "right-censored"]
    hit_episodes = [episode for episode in evaluated if episode.status == "hit"]
    false_alarms = [
        episode for episode in evaluated if episode.status == "false-alarm"
    ]
    leads = [
        episode.months_from_confirmation_to_first_onset
        for episode in hit_episodes
        if episode.months_from_confirmation_to_first_onset is not None
    ]
    recession_matches: list[dict[str, object]] = []
    for onset in recession_onsets:
        candidates = [
            episode
            for episode in episodes
            if episode.confirmation_month < onset <= episode.evaluation_end
        ]
        latest_episode = max(
            candidates,
            key=lambda episode: episode.confirmation_month,
            default=None,
        )
        recession_matches.append(
            {
                "recession_start": onset.strftime("%Y-%m"),
                "status": "covered" if latest_episode else "missed",
                "latest_covering_episode": (
                    latest_episode.episode if latest_episode else None
                ),
            }
        )

    return {
        "threshold_percent": threshold_percent,
        "confirmation_months": CONFIRMATION_MONTHS,
        "post_episode_months": POST_EPISODE_MONTHS,
        "confirmed_episodes": len(episodes),
        "evaluated_episodes": len(evaluated),
        "hit_episodes": len(hit_episodes),
        "false_alarm_episodes": len(false_alarms),
        "right_censored_episodes": len(episodes) - len(evaluated),
        "recession_onsets": len(recession_onsets),
        "covered_recession_onsets": len(covered_onsets),
        "missed_recession_onsets": len(recession_onsets) - len(covered_onsets),
        "median_confirmation_lead_months": median(leads) if leads else None,
        "episodes": [asdict(episode) for episode in episodes],
        "recession_matches": recession_matches,
    }


def analyze(
    observations: list[MonthlyObservation],
    thresholds_percent: tuple[float, ...],
) -> dict[str, object]:
    """Run the fixed primary rule and its predeclared threshold sensitivities."""

    recession_onsets = find_recession_onsets(observations)
    threshold_results = [
        analyze_threshold(observations, recession_onsets, threshold)
        for threshold in thresholds_percent
    ]
    primary = next(
        result for result in threshold_results if result["threshold_percent"] == 0.0
    )
    return {
        "sample_start": observations[0].month.strftime("%Y-%m"),
        "sample_end": observations[-1].month.strftime("%Y-%m"),
        "monthly_observations": len(observations),
        "recession_onsets": [month.strftime("%Y-%m") for month in recession_onsets],
        "primary": primary,
        "threshold_sensitivity": [
            {
                key: value
                for key, value in result.items()
                if key not in {"episodes", "recession_matches"}
            }
            for result in threshold_results
        ],
        "threshold_details": threshold_results,
    }
