"""Publication-quality chart generation for CIC-001."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

OVERNIGHT_COLOR = "#0B3C5D"
INTRADAY_COLOR = "#D97A0D"
BUY_HOLD_COLOR = "#4D4D4D"
GRID_COLOR = "#D8D8D8"
SOURCE_NOTE = (
    "Source: Yahoo Finance via yfinance; split- and dividend-adjusted daily OHLC. "
    "Capital in Code calculations."
)


def _apply_style() -> None:
    plt.rcParams.update(
        {
            "figure.figsize": (11.0, 6.5),
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#222222",
            "axes.grid": True,
            "axes.grid.axis": "y",
            "grid.color": GRID_COLOR,
            "grid.linewidth": 0.7,
            "grid.alpha": 0.7,
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 16,
            "axes.titleweight": "bold",
            "axes.labelsize": 11,
            "legend.frameon": False,
            "savefig.dpi": 180,
        }
    )


def _finish_figure(
    figure: plt.Figure,
    path: Path,
    *,
    note: str = SOURCE_NOTE,
) -> None:
    figure.text(0.01, 0.01, note, ha="left", va="bottom", fontsize=8, color="#555555")
    figure.tight_layout(rect=(0.0, 0.045, 1.0, 1.0))
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)


def _format_date_axis(axis: plt.Axes) -> None:
    axis.xaxis.set_major_locator(mdates.YearLocator(base=5))
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))


def _drawdown(returns: pd.Series) -> pd.Series:
    wealth = np.exp(np.log1p(returns).cumsum())
    wealth = pd.concat(
        [pd.Series([1.0], index=[returns.index.min() - pd.Timedelta(days=1)]), wealth]
    )
    drawdown = wealth / wealth.cummax() - 1.0
    return drawdown.iloc[1:]


def _growth_chart(daily: pd.DataFrame, path: Path, ticker: str) -> None:
    figure, axis = plt.subplots()
    axis.plot(
        daily.index,
        daily["overnight_growth"],
        color=OVERNIGHT_COLOR,
        linewidth=1.6,
        label="Overnight",
    )
    axis.plot(
        daily.index,
        daily["intraday_growth"],
        color=INTRADAY_COLOR,
        linewidth=1.6,
        label="Regular hours",
    )
    axis.plot(
        daily.index,
        daily["buy_and_hold_growth"],
        color=BUY_HOLD_COLOR,
        linewidth=1.4,
        linestyle="--",
        label="Buy and hold",
    )
    axis.set_yscale("log")
    axis.set_title(f"{ticker}: Growth of $1 by Return Component")
    axis.set_ylabel("Value of $1 (log scale)")
    axis.set_xlabel("Trading date")
    axis.legend(loc="best", ncol=3)
    _format_date_axis(axis)
    _finish_figure(
        figure,
        path,
        note=SOURCE_NOTE + " Logarithmic y-axis preserves proportional changes.",
    )


def _distribution_chart(daily: pd.DataFrame, path: Path, ticker: str) -> None:
    overnight = daily["overnight_return"] * 100.0
    intraday = daily["intraday_return"] * 100.0
    combined = pd.concat([overnight, intraday], ignore_index=True)
    lower, upper = combined.quantile([0.005, 0.995])
    bins = np.linspace(float(lower), float(upper), 65)

    figure, axis = plt.subplots()
    axis.hist(
        overnight.clip(lower=lower, upper=upper),
        bins=bins.tolist(),
        density=True,
        alpha=0.55,
        color=OVERNIGHT_COLOR,
        label="Overnight",
    )
    axis.hist(
        intraday.clip(lower=lower, upper=upper),
        bins=bins.tolist(),
        density=True,
        alpha=0.5,
        color=INTRADAY_COLOR,
        label="Regular hours",
    )
    axis.axvline(0.0, color="#111111", linewidth=1.0)
    axis.set_title(f"{ticker}: Daily Return Distributions")
    axis.set_xlabel("Daily return (%)")
    axis.set_ylabel("Density")
    axis.legend(loc="upper right")
    _finish_figure(
        figure,
        path,
        note=(
            SOURCE_NOTE + " Values below the 0.5th or above the 99.5th percentile are "
            "clipped at the chart boundary for readability, not removed from analysis."
        ),
    )


def _yearly_chart(yearly: pd.DataFrame, path: Path, ticker: str) -> None:
    selected = yearly.loc[
        yearly["component"].isin(["overnight", "intraday"]),
        ["year", "component", "cumulative_return"],
    ]
    pivot = selected.pivot(
        index="year", columns="component", values="cumulative_return"
    )
    positions = np.arange(len(pivot))
    width = 0.4

    figure, axis = plt.subplots(figsize=(12.0, 6.8))
    axis.bar(
        positions - width / 2,
        pivot["overnight"] * 100.0,
        width=width,
        color=OVERNIGHT_COLOR,
        label="Overnight",
    )
    axis.bar(
        positions + width / 2,
        pivot["intraday"] * 100.0,
        width=width,
        color=INTRADAY_COLOR,
        label="Regular hours",
    )
    axis.axhline(0.0, color="#222222", linewidth=0.9)
    axis.set_title(f"{ticker}: Compounded Return by Calendar Year")
    axis.set_xlabel("Calendar year")
    axis.set_ylabel("Compounded return (%)")
    axis.set_xticks(positions)
    axis.set_xticklabels(pivot.index.astype(str), rotation=60, ha="right")
    axis.legend(loc="best")
    _finish_figure(figure, path)


def _rolling_average_chart(
    daily: pd.DataFrame,
    path: Path,
    ticker: str,
    rolling_window: int,
    trading_days_per_year: int,
) -> None:
    overnight = (
        daily["overnight_return"].rolling(rolling_window).mean()
        * trading_days_per_year
        * 100.0
    )
    intraday = (
        daily["intraday_return"].rolling(rolling_window).mean()
        * trading_days_per_year
        * 100.0
    )

    figure, axis = plt.subplots()
    axis.plot(
        daily.index,
        overnight,
        color=OVERNIGHT_COLOR,
        linewidth=1.2,
        label="Overnight",
    )
    axis.plot(
        daily.index,
        intraday,
        color=INTRADAY_COLOR,
        linewidth=1.2,
        label="Regular hours",
    )
    axis.axhline(0.0, color="#222222", linewidth=0.9)
    axis.set_title(
        f"{ticker}: {rolling_window}-Day Rolling Average Return (Annualized)"
    )
    axis.set_xlabel("Trading date")
    axis.set_ylabel("Arithmetic annualized return (%)")
    axis.legend(loc="best")
    _format_date_axis(axis)
    _finish_figure(
        figure,
        path,
        note=(
            SOURCE_NOTE + f" Rolling daily mean multiplied by {trading_days_per_year}; "
            "this is not a compounded forecast."
        ),
    )


def _drawdown_chart(daily: pd.DataFrame, path: Path, ticker: str) -> None:
    figure, axis = plt.subplots()
    axis.plot(
        daily.index,
        _drawdown(daily["overnight_return"]) * 100.0,
        color=OVERNIGHT_COLOR,
        linewidth=1.3,
        label="Overnight",
    )
    axis.plot(
        daily.index,
        _drawdown(daily["intraday_return"]) * 100.0,
        color=INTRADAY_COLOR,
        linewidth=1.3,
        label="Regular hours",
    )
    axis.plot(
        daily.index,
        _drawdown(daily["close_to_close_return"]) * 100.0,
        color=BUY_HOLD_COLOR,
        linewidth=1.1,
        linestyle="--",
        label="Buy and hold",
    )
    axis.set_title(f"{ticker}: Drawdown by Return Component")
    axis.set_xlabel("Trading date")
    axis.set_ylabel("Drawdown from prior peak (%)")
    axis.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=100.0))
    axis.legend(loc="upper center", ncol=3)
    _format_date_axis(axis)
    _finish_figure(figure, path)


def _cumulative_contribution_chart(
    daily: pd.DataFrame,
    path: Path,
    ticker: str,
) -> None:
    overnight = daily["overnight_log_return"].cumsum()
    intraday = daily["intraday_log_return"].cumsum()
    total = daily["close_to_close_log_return"].cumsum()

    figure, axis = plt.subplots()
    axis.plot(
        daily.index,
        overnight,
        color=OVERNIGHT_COLOR,
        linewidth=1.5,
        label="Cumulative overnight log return",
    )
    axis.plot(
        daily.index,
        intraday,
        color=INTRADAY_COLOR,
        linewidth=1.5,
        label="Cumulative regular-hours log return",
    )
    axis.plot(
        daily.index,
        total,
        color=BUY_HOLD_COLOR,
        linewidth=1.2,
        linestyle="--",
        label="Cumulative close-to-close log return",
    )
    axis.axhline(0.0, color="#222222", linewidth=0.9)
    axis.set_title(f"{ticker}: Cumulative Log-Return Contribution")
    axis.set_xlabel("Trading date")
    axis.set_ylabel("Cumulative log return")
    axis.legend(loc="best")
    _format_date_axis(axis)
    _finish_figure(
        figure,
        path,
        note=(
            SOURCE_NOTE
            + " Overnight plus regular-hours log return equals close-to-close "
            "log return on every aligned date."
        ),
    )


def generate_charts(
    daily: pd.DataFrame,
    yearly: pd.DataFrame,
    *,
    chart_dir: Path,
    ticker: str,
    rolling_window: int,
    trading_days_per_year: int,
) -> list[Path]:
    """Generate all documented charts and return their paths."""

    _apply_style()
    chart_dir.mkdir(parents=True, exist_ok=True)
    chart_paths = {
        "growth": chart_dir / "growth-of-one-dollar.png",
        "distribution": chart_dir / "return-distributions.png",
        "yearly": chart_dir / "yearly-return-comparison.png",
        "rolling": chart_dir / "rolling-average-returns.png",
        "drawdown": chart_dir / "drawdown-comparison.png",
        "contribution": chart_dir / "cumulative-log-return-contribution.png",
    }
    _growth_chart(daily, chart_paths["growth"], ticker)
    _distribution_chart(daily, chart_paths["distribution"], ticker)
    _yearly_chart(yearly, chart_paths["yearly"], ticker)
    _rolling_average_chart(
        daily,
        chart_paths["rolling"],
        ticker,
        rolling_window,
        trading_days_per_year,
    )
    _drawdown_chart(daily, chart_paths["drawdown"], ticker)
    _cumulative_contribution_chart(daily, chart_paths["contribution"], ticker)
    return list(chart_paths.values())
