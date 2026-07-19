# CIC-001 — The Overnight Effect

This project will compare SPY's historical overnight returns with its returns during regular market hours. The backtest has not been implemented yet.

## Project Code

`CIC-001`

## Research Question

Historically, have more of SPY's returns occurred overnight or during regular market hours?

## Why This Question Matters

A daily return can be split into two periods: the move from the previous close to the next open, and the move from that open to the close. Comparing them can show when returns have historically appeared and can challenge simple assumptions about what happens while the market is open.

## Hypothesis

Before running the test, the working hypothesis is that a larger share of SPY's cumulative return occurred overnight. This is only a hypothesis and will be evaluated against the data.

## Data Source

TODO: Choose and document a reliable source for historical daily SPY open and close prices. Record the date range, adjustment method, missing dates, and whether dividends and stock splits are reflected in the data.

## Method

The planned analysis will:

1. Load and validate daily SPY open and close prices.
2. Calculate each overnight return from the previous trading day's close to the current day's open.
3. Calculate each regular-hours return from the current day's open to its close.
4. Compare average, median, cumulative, and risk-adjusted results for the two periods.
5. Check the findings across different time periods and document important assumptions.

TODO: Decide how adjusted prices, dividends, transaction costs, and the first incomplete observation should be handled before implementing the calculations.

## Results

Not available yet. TODO: Run the backtest, verify the calculations, and report the results without overstating what they show.

## Charts

Planned charts include:

- Cumulative overnight return compared with cumulative regular-hours return
- Distribution of daily returns for both periods
- Results by year or another consistent time window

TODO: Build and label the charts only after the calculations have been validated.

## Limitations

The future analysis must consider data quality, price adjustments, dividends, trading costs, taxes, slippage, and the difference between a historical pattern and a tradable strategy. SPY's history also represents one asset and may not apply to other markets or future periods.

## What I Learned

TODO: Complete this section after the analysis. Include both a technical lesson and an investing or statistics lesson.

## How to Run the Code

The code does not exist yet. After implementation, the expected setup will be:

1. Create and activate a Python virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Run the documented script from `src/`.

TODO: Replace this outline with exact commands and expected outputs when the backtest is built.

## Implementation Checklist

- [ ] Select and document the data source.
- [ ] Define price-adjustment and dividend handling.
- [ ] Write the data download or import step.
- [ ] Validate dates, missing values, and price fields.
- [ ] Calculate overnight and regular-hours returns.
- [ ] Add checks for the return formulas.
- [ ] Create and review the planned charts.
- [ ] Write the results and final analysis summary.

## Disclaimer

This project is for educational and informational purposes only. It is not financial advice. Past performance does not guarantee future results.
