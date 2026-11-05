"""Create publication-quality, dependency-free SVG charts for CIC-003."""

from __future__ import annotations

from datetime import date
from html import escape
from pathlib import Path

from .analysis import add_months, months_between
from .data import MonthlyObservation

INK = "#101114"
NAVY = "#123675"
MUTED = "#595D64"
RULE = "#A8ABB1"
GRID = "#E5E7EB"
RECESSION = "#E9EDF3"
PALE_NAVY = "#EAF0F8"


def _month_x(month: date, start: date, end: date, left: float, width: float) -> float:
    span = max(1, months_between(start, end))
    return left + months_between(start, month) / span * width


def _svg_header(title: str, description: str, width: int, height: int) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(title)}</title>',
        f'<desc id="desc">{escape(description)}</desc>',
        f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#101114}'
        '.muted{fill:#595D64}.axis{stroke:#8E939B;stroke-width:1}'
        '.grid{stroke:#E5E7EB;stroke-width:1}.small{font-size:12px}'
        '.label{font-size:13px}.title{font-size:19px;font-weight:600}'
        '.subtitle{font-size:12px;fill:#595D64}</style>',
    ]


def _draw_spread_chart(
    observations: list[MonthlyObservation],
    path: Path,
) -> None:
    width, height = 1120, 570
    left, right, top, bottom = 86, 35, 84, 82
    plot_width = width - left - right
    plot_height = height - top - bottom
    start = observations[0].month
    end = observations[-1].month
    minimum = min(point.spread_percent for point in observations)
    maximum = max(point.spread_percent for point in observations)
    low = min(-2.0, float(int(minimum)) - 1.0)
    high = max(5.0, float(int(maximum + 1.0)))

    def y(value: float) -> float:
        return top + (high - value) / (high - low) * plot_height

    parts = _svg_header(
        "10-year minus 3-month Treasury spread and NBER recessions",
        "Monthly mean of the daily FRED T10Y3M spread in percentage points, "
        "with NBER-based recession months shaded and a zero-spread reference line.",
        width,
        height,
    )
    parts.extend(
        [
            '<text class="title" x="86" y="31">10-year minus 3-month Treasury spread</text>',
            f'<text class="subtitle" x="86" y="53">Monthly mean, percentage points · '
            f'{start:%b %Y}–{end:%b %Y}</text>',
        ]
    )

    recessions = [point for point in observations if point.recession == 1]
    if recessions:
        group_start = recessions[0].month
        group_end = group_start
        for point in recessions[1:]:
            if months_between(group_end, point.month) > 1:
                x0 = _month_x(group_start, start, end, left, plot_width)
                x1 = _month_x(add_months(group_end, 1), start, end, left, plot_width)
                parts.append(
                    f'<rect x="{x0:.2f}" y="{top}" width="{x1 - x0:.2f}" '
                    f'height="{plot_height}" fill="{RECESSION}"/>'
                )
                group_start = point.month
            group_end = point.month
        x0 = _month_x(group_start, start, end, left, plot_width)
        x1 = _month_x(add_months(group_end, 1), start, end, left, plot_width)
        parts.append(
            f'<rect x="{x0:.2f}" y="{top}" width="{max(1, x1 - x0):.2f}" '
            f'height="{plot_height}" fill="{RECESSION}"/>'
        )

    tick = int(low)
    while tick <= high:
        tick_y = y(float(tick))
        if tick != 0:
            parts.append(
                f'<line class="grid" x1="{left}" y1="{tick_y:.2f}" '
                f'x2="{left + plot_width}" y2="{tick_y:.2f}"/>'
            )
        parts.append(
            f'<text class="small muted" x="{left - 13}" y="{tick_y + 4:.2f}" '
            f'text-anchor="end">{tick}</text>'
        )
        tick += 1

    zero_y = y(0.0)
    parts.append(
        f'<line x1="{left}" y1="{zero_y:.2f}" x2="{left + plot_width}" '
        f'y2="{zero_y:.2f}" stroke="{INK}" stroke-width="1.6" '
        'stroke-dasharray="6 4"/>'
    )
    parts.append(
        f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" '
        f'y2="{top + plot_height}"/>'
    )
    parts.append(
        f'<line class="axis" x1="{left}" y1="{top + plot_height}" '
        f'x2="{left + plot_width}" y2="{top + plot_height}"/>'
    )

    points = []
    for observation in observations:
        x = _month_x(observation.month, start, end, left, plot_width)
        points.append(f"{x:.2f},{y(observation.spread_percent):.2f}")
    parts.append(
        f'<polyline points="{" ".join(points)}" fill="none" stroke="{NAVY}" '
        'stroke-width="2.1" stroke-linejoin="round" stroke-linecap="round"/>'
    )

    years = list(range(((start.year + 4) // 5) * 5, end.year + 1, 5))
    tick_months = [start, *[date(year, 1, 1) for year in years], end]
    seen_years: set[tuple[int, int]] = set()
    for month in tick_months:
        key = month.year, month.month
        if key in seen_years:
            continue
        seen_years.add(key)
        x = _month_x(month, start, end, left, plot_width)
        label = month.strftime("%b %Y") if month in {start, end} else str(month.year)
        parts.append(
            f'<line class="axis" x1="{x:.2f}" y1="{top + plot_height}" '
            f'x2="{x:.2f}" y2="{top + plot_height + 5}"/>'
        )
        parts.append(
            f'<text class="small muted" x="{x:.2f}" y="{top + plot_height + 23}" '
            f'text-anchor="middle">{label}</text>'
        )

    parts.extend(
        [
            f'<text class="label" x="21" y="{top + plot_height / 2:.2f}" '
            f'text-anchor="middle" transform="rotate(-90 21 '
            f'{top + plot_height / 2:.2f})">10Y − 3M spread (%)</text>',
            f'<text class="label" x="{left + plot_width / 2:.2f}" '
            f'y="{height - 17}" text-anchor="middle">Calendar month</text>',
            f'<line x1="{left + 13}" y1="{height - 50}" x2="{left + 47}" '
            f'y2="{height - 50}" stroke="{NAVY}" stroke-width="2.1"/>',
            f'<text class="small muted" x="{left + 55}" y="{height - 46}">Monthly mean</text>',
            f'<rect x="{left + 187}" y="{height - 58}" width="17" height="15" '
            f'fill="{RECESSION}" stroke="{RULE}" stroke-width=".5"/>',
            f'<text class="small muted" x="{left + 211}" y="{height - 46}">'
            'NBER-based recession</text>',
            f'<line x1="{left + 382}" y1="{height - 50}" x2="{left + 416}" '
            f'y2="{height - 50}" stroke="{INK}" stroke-width="1.5" '
            'stroke-dasharray="6 4"/>',
            f'<text class="small muted" x="{left + 424}" y="{height - 46}">Zero spread</text>',
            "</svg>",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts), encoding="utf-8")


def _draw_episode_chart(
    observations: list[MonthlyObservation],
    episodes: list[dict[str, object]],
    path: Path,
) -> None:
    width = 1120
    row_height = 44
    height = max(235, 144 + len(episodes) * row_height)
    left, right, top, bottom = 208, 38, 74, 68
    plot_width = width - left - right
    start = observations[0].month
    end = observations[-1].month
    plot_height = max(1, height - top - bottom)
    parts = _svg_header(
        "Confirmed yield-curve inversion episodes and NBER recession starts",
        "Each row shows a run of three or more months with a monthly mean 10-year "
        "minus 3-month spread at or below zero. Solid navy marks the inversion; "
        "the dashed gray segment is the 12-month follow-up after the last inverted "
        "month; a navy circle marks a covered recession start.",
        width,
        height,
    )
    parts.extend(
        [
            '<text class="title" x="208" y="31">Inversion episodes and recession starts</text>',
            f'<text class="subtitle" x="208" y="53">Primary rule: 3 consecutive monthly means ≤ 0.00 percentage points; '
            'follow-up extends 12 months after the last inverted month.</text>',
        ]
    )

    years = list(range(((start.year + 4) // 5) * 5, end.year + 1, 5))
    for year in years:
        month = date(year, 1, 1)
        x = _month_x(month, start, end, left, plot_width)
        parts.append(
            f'<line class="grid" x1="{x:.2f}" y1="{top}" x2="{x:.2f}" '
            f'y2="{top + plot_height}"/>'
        )
        parts.append(
            f'<text class="small muted" x="{x:.2f}" y="{height - 28}" '
            f'text-anchor="middle">{year}</text>'
        )

    for index, episode in enumerate(episodes):
        y = top + index * row_height + row_height / 2
        first = date.fromisoformat(str(episode["confirmation_month"]))
        last = date.fromisoformat(str(episode["inversion_end"]))
        theoretical_end = date.fromisoformat(str(episode["evaluation_end"]))
        visible_end = min(theoretical_end, end)
        x0 = _month_x(first, start, end, left, plot_width)
        x1 = _month_x(last, start, end, left, plot_width)
        x2 = _month_x(visible_end, start, end, left, plot_width)
        label = (
            f"Episode {index + 1} · {episode['inversion_start']}–{episode['inversion_end']}"
        )
        parts.append(
            f'<text class="small muted" x="{left - 12}" y="{y + 4:.2f}" '
            f'text-anchor="end">{escape(label)}</text>'
        )
        parts.append(
            f'<line x1="{x0:.2f}" y1="{y:.2f}" x2="{max(x0 + 4, x1):.2f}" '
            f'y2="{y:.2f}" stroke="{NAVY}" stroke-width="8" '
            'stroke-linecap="round"/>'
        )
        if visible_end > last:
            parts.append(
                f'<line x1="{x1:.2f}" y1="{y:.2f}" x2="{x2:.2f}" '
                f'y2="{y:.2f}" stroke="{RULE}" stroke-width="2" '
                'stroke-dasharray="4 4"/>'
            )
        onsets = episode["recession_onsets_in_window"]
        if onsets:
            onset = date.fromisoformat(str(onsets[0]))
            x_event = _month_x(onset, start, end, left, plot_width)
            parts.append(
                f'<circle cx="{x_event:.2f}" cy="{y:.2f}" r="6" '
                f'fill="#FFFFFF" stroke="{INK}" stroke-width="2"/>'
            )
            parts.append(
                f'<text class="small muted" x="{x_event + 9:.2f}" '
                f'y="{y - 9:.2f}">{escape(onset.strftime("%Y-%m"))}</text>'
            )

    parts.extend(
        [
            f'<line class="axis" x1="{left}" y1="{top + plot_height}" '
            f'x2="{left + plot_width}" y2="{top + plot_height}"/>',
            f'<line x1="{left + 14}" y1="{height - 51}" x2="{left + 43}" '
            f'y2="{height - 51}" stroke="{NAVY}" stroke-width="8" '
            'stroke-linecap="round"/>',
            f'<text class="small muted" x="{left + 52}" y="{height - 47}">'
            'Confirmed inversion</text>',
            f'<line x1="{left + 216}" y1="{height - 51}" x2="{left + 247}" '
            f'y2="{height - 51}" stroke="{RULE}" stroke-width="2" '
            'stroke-dasharray="4 4"/>',
            f'<text class="small muted" x="{left + 256}" y="{height - 47}">'
            '12-month follow-up</text>',
            f'<circle cx="{left + 447}" cy="{height - 51}" r="5" fill="#FFFFFF" '
            f'stroke="{INK}" stroke-width="2"/>',
            f'<text class="small muted" x="{left + 459}" y="{height - 47}">'
            'NBER recession start</text>',
            f'<text class="label" x="{left + plot_width / 2:.2f}" '
            f'y="{height - 10}" text-anchor="middle">Calendar month</text>',
            "</svg>",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts), encoding="utf-8")


def generate_charts(
    observations: list[MonthlyObservation],
    primary_result: dict[str, object],
    charts_dir: Path,
    site_image_dir: Path,
) -> list[Path]:
    """Write local SVG outputs and their public-site copies."""

    spread_name = "spread-and-recessions.svg"
    episodes_name = "inversion-episode-timeline.svg"
    local_paths = [charts_dir / spread_name, charts_dir / episodes_name]
    public_paths = [site_image_dir / spread_name, site_image_dir / episodes_name]
    _draw_spread_chart(observations, local_paths[0])
    _draw_spread_chart(observations, public_paths[0])
    episode_rows = primary_result["episodes"]
    _draw_episode_chart(observations, episode_rows, local_paths[1])
    _draw_episode_chart(observations, episode_rows, public_paths[1])
    return public_paths
