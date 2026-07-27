# CIC-001 — The Overnight Effect

This project asks a simple question with an important detail: **when did SPY
historically earn its return?**

A trading day can be separated into two periods:

1. **Overnight:** the previous trading day's close to the current trading day's
   open.
2. **Regular hours:** the current trading day's open to its close.

The analysis uses correctly aligned trading dates, adjusted daily prices, a
tested Python pipeline, statistical comparisons, focused robustness checks, and
publication-quality charts. It is a historical research project, not a trading
recommendation.

## Project Code

`CIC-001`

## Status

Complete. The implementation and offline tests were verified on July 27, 2026.
The reported results come from a successful live SPY download and analysis run.

## Research Question

From January 1994 through December 2025, did SPY produce more of its return
overnight or during regular market hours?

## Pre-Analysis Hypothesis

Before the backtest was implemented, the recorded hypothesis was that a larger
share of SPY's cumulative return occurred overnight.

## Main Result

The full-sample evidence supports the hypothesis.

One dollar exposed only to each gross return component on every aligned trading
date would have ended at:

- **$20.17 overnight** — a cumulative return of **1,917.13%**
- **$1.29 during regular hours** — a cumulative return of **28.63%**
- **$25.95 in close-to-close buy and hold** — a cumulative return of
  **2,494.64%**

The two component returns multiply rather than add. The ending buy-and-hold
growth is therefore approximately `20.17 × 1.286 = 25.95`.

### Verified Full-Sample Statistics

| Metric | Overnight | Regular hours | Buy and hold |
| --- | ---: | ---: | ---: |
| Aligned observations | 8,053 | 8,053 | 8,053 |
| Arithmetic mean per day | 0.03962% | 0.00785% | 0.04748% |
| Median per day | 0.06070% | 0.04775% | 0.07081% |
| Positive observations | 56.33% | 52.61% | 54.28% |
| Cumulative return | 1,917.13% | 28.63% | 2,494.64% |
| Annualized return | 9.86% | 0.79% | 10.73% |
| Annualized volatility | 10.75% | 15.43% | 18.84% |
| Sharpe ratio | 0.929 | 0.128 | 0.635 |
| Maximum drawdown | -32.79% | -68.49% | -55.19% |

Annualization uses 252 trading days per year. The default annual risk-free rate
is 0%, so the Sharpe ratios are return divided by volatility on an annualized
basis.

## What the Statistical Tests Say

The average overnight return exceeded the average regular-hours return by
**0.03177 percentage points, or 3.18 basis points, per trading day**.

- A paired t-test produced `p = 0.0160`.
- A Wilcoxon signed-rank test produced `p = 0.000163`.
- A 10,000-sample paired bootstrap estimated a 95% confidence interval of
  **0.55 to 5.74 basis points per day** for the difference in means.

These tests compare returns from the same dates, which is preferable to treating
the two samples as unrelated. Their assumptions are still imperfect: returns
can be serially dependent, the Wilcoxon test assumes roughly symmetric paired
differences, and the simple bootstrap treats dates as exchangeable. The
p-values are evidence of a historical difference, not proof of a profitable
strategy or a permanent market law.

## Data

### Source and Coverage

- **Provider:** Yahoo Finance, downloaded through `yfinance`
- **Ticker:** SPY
- **Requested dates:** 1994-01-01 through 2025-12-31, inclusive
- **Available price dates:** 1994-01-03 through 2025-12-31
- **Aligned return dates:** 1994-01-04 through 2025-12-31
- **Clean price rows:** 8,054
- **Return rows:** 8,053

The requested start and end dates are fixed defaults so the published analysis
does not silently move each day.

### Price-Adjustment Method

The download uses `auto_adjust=True`. Yahoo's split- and dividend-adjustment
factor is therefore applied consistently to **both Open and Close**. Raw and
adjusted fields are never mixed.

This creates a total-return-style decomposition:

- stock splits do not appear as artificial jumps;
- distribution adjustments can enter the overnight interval when the
  adjustment factor changes across an ex-dividend boundary; and
- the adjusted overnight and adjusted regular-hours components reconstruct the
  adjusted close-to-close return.

This choice is appropriate for studying the return received by a holder across
the close-to-open boundary, but it is not identical to a backtest based only on
unadjusted quoted prices.

### Validation

Before returns are calculated, the pipeline:

- parses and normalizes trading dates;
- removes time-zone information without shifting the local calendar date;
- rejects duplicate trading dates rather than guessing which row to keep;
- sorts rows chronologically;
- confirms that Open and Close exist and are numeric;
- counts missing, non-numeric, and non-positive prices;
- removes invalid price rows and records every removal reason;
- suppresses the next return after an invalid row so it cannot bridge across a
  missing trading observation;
- requires enough clean observations to calculate a return; and
- removes the first clean row because it has no previous trading-day close.

The verified SPY run removed **zero invalid rows**. Its maximum difference
between reconstructed and observed close-to-close return was
`2.22 × 10^-16`, well below the `1 × 10^-12` tolerance.

Non-trading calendar days are not filled or treated as zero-return days. Friday
is followed by the next observed trading date, whether that is Monday or a
later date after a holiday.

## Return Definitions

For trading date `t`:

```python
previous_close = close[t - 1 trading observation]
overnight_return = open[t] / previous_close - 1
intraday_return = close[t] / open[t] - 1
close_to_close_return = close[t] / previous_close - 1
```

The core identity is checked on every row:

```python
(1 + overnight_return) * (1 + intraday_return) - 1
    == close_to_close_return
```

Log returns are also calculated:

```python
overnight_log_return = log(open[t] / previous_close)
intraday_log_return = log(close[t] / open[t])
```

Log returns add exactly across the two periods, while simple returns compound.
The pipeline uses cumulative log sums and exponentiation for numerically stable
long-run growth calculations.

## Statistical Methods

For overnight, regular-hours, and close-to-close returns, the pipeline reports:

- observation count;
- arithmetic and geometric daily means;
- median, minimum, maximum, and selected percentiles;
- daily standard deviation and annualized volatility;
- percentages of positive, negative, and zero observations;
- skewness and excess kurtosis;
- cumulative and annualized return;
- annualized Sharpe ratio; and
- maximum drawdown.

It also reports the overnight-minus-intraday differences in mean, median,
cumulative return, volatility, and Sharpe ratio.

The default annual risk-free rate is 0%. If a different rate is supplied, it is
converted to a compounded daily rate and subtracted from both component return
series. Applying one daily risk-free rate to holding periods of different
lengths is a simplifying convention and should be interpreted cautiously.

## Robustness Checks

The implementation favors a smaller set of interpretable checks:

### Start-Date Sensitivity

| Sample start | Overnight annualized return | Regular-hours annualized return |
| --- | ---: | ---: |
| Full sample (1994) | 9.86% | 0.79% |
| 2000 | 6.96% | 1.01% |
| 2010 | 8.62% | 4.89% |
| 2020 | 8.71% | 5.66% |

The overnight advantage was smaller in recent subsamples but remained positive
through the fixed 2025 end date.

### Extreme Observations

The paired trim retains a date only when both component returns fall between
their own 1st and 99th full-sample percentiles. It removed 284 of 8,053 dates.
After trimming, overnight compounded to **3,746.17%** versus **11.76%** during
regular hours. The full-sample result was therefore not created by only a few
extreme dates.

This is a sensitivity check, not a claim that real investors could avoid bad
tail events.

### Time Periods

Results are produced by calendar year, decade, later start date, and five
descriptive market periods. The pattern was not uniform. For example, during
the defined COVID shock from 2020-02-19 through 2020-03-23, overnight return was
**-28.12%** and regular-hours return was **-7.34%**. A strong full-sample pattern
can still fail badly during a particular crisis.

The market-period labels are descriptive windows, not causal tests.

### Simple Versus Log Returns

The robustness output compares daily means and medians in simple and log space
and independently reconstructs compounded growth from both. This guards against
mistaking an arithmetic average for an investable compounded result.

### Hypothetical Transaction Costs

The default sensitivity model charges **1 basis point on entry and 1 basis
point on exit every trading day**. Under that simplified assumption:

| Component | Gross annualized return | Net annualized return | Net cumulative return |
| --- | ---: | ---: | ---: |
| Overnight | 9.86% | 4.46% | 302.96% |
| Regular hours | 0.79% | -4.16% | -74.30% |

The model assumes fills exactly around the official close and open apart from
the stated proportional cost. It omits variable spreads, slippage, market
impact, taxes, financing, failed executions, capacity, and account constraints.
It also requires far more trading than passive buy and hold.

The simplified overnight result remained positive, but it underperformed the
verified **10.73%** annualized buy-and-hold return. This analysis does **not**
establish that the effect was practically superior or realistically tradable.

## Architecture

The code is separated by responsibility:

```text
src/
├── config.py       # dataclass configuration and CLI validation
├── data.py         # yfinance download, provider-shape handling, and cache
├── validation.py   # date and price validation with removal counts
├── returns.py      # aligned simple/log returns and identity checks
├── stats.py        # descriptive, inferential, yearly, and risk statistics
├── robustness.py   # period, start-date, tails, log, and cost checks
├── charts.py       # six consistent publication-quality figures
├── output.py       # atomic CSV/JSON output and run metadata
└── main.py         # end-to-end orchestration and structured logging
```

The implementation uses type hints, docstrings, explicit exceptions, stable
file names, key-value-friendly logs, and deterministic bootstrap sampling.

## Installation

Python 3.11 or newer is required. The verified environment used Python 3.14.3.

From the repository root:

```powershell
cd projects/cic-001-overnight-effect
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On macOS or Linux, activate with:

```bash
source .venv/bin/activate
```

## Run the Analysis

Run the verified configuration from this project directory:

```powershell
python -m src.main `
  --ticker SPY `
  --start-date 1994-01-01 `
  --end-date 2025-12-31
```

The same command in a POSIX shell is:

```bash
python -m src.main \
  --ticker SPY \
  --start-date 1994-01-01 \
  --end-date 2025-12-31
```

All published settings are defaults, so this is equivalent:

```bash
python -m src.main
```

Useful options include:

| Option | Default | Purpose |
| --- | --- | --- |
| `--ticker` | `SPY` | Yahoo Finance ticker |
| `--start-date` | `1994-01-01` | Inclusive requested start |
| `--end-date` | `2025-12-31` | Inclusive requested end |
| `--output-dir` | `results` | CSV and JSON destination |
| `--chart-dir` | `charts` | PNG chart destination |
| `--cache-dir` | `data/raw` | Ignored raw-data cache |
| `--cache-mode` | `use` | `use`, `refresh`, or `off` |
| `--risk-free-rate` | `0.0` | Annual decimal rate |
| `--trading-days-per-year` | `252` | Annualization convention |
| `--rolling-window` | `63` | Rolling chart window |
| `--bootstrap-samples` | `10000` | Paired bootstrap draws |
| `--random-seed` | `42` | Reproducible random seed |
| `--transaction-cost-bps` | `1.0` | Cost for each trade leg |

Use `--cache-mode refresh` to force a new download. Use `off` to download
without writing a cache file. A provider failure, invalid ticker, empty
response, malformed response, or unusable dataset exits with a clear error
instead of fabricating results.

## Run the Quality Checks

All tests are offline and use synthetic data:

```bash
python -m pytest
python -m ruff format --check src tests
python -m ruff check src tests
python -m mypy src
```

The synthetic test suite includes manually checkable examples with a Friday
close, Monday open, and Tuesday session. This catches a likely bug where a
calendar shift could be confused with a previous trading observation.

## Generated Output Files

The pipeline writes:

| File | Contents |
| --- | --- |
| `results/daily_returns.csv` | Clean aligned prices, simple/log returns, identity error, growth, and cumulative returns |
| `results/summary_statistics.csv` | Overall component statistics |
| `results/component_comparison.csv` | Overnight-minus-intraday differences |
| `results/inferential_tests.csv` | Paired t-test, Wilcoxon test, and bootstrap interval |
| `results/yearly_statistics.csv` | Tidy calendar-year component results |
| `results/robustness_checks.json` | Decades, market periods, start dates, tails, log returns, and costs |
| `results/data_validation_report.json` | Row counts and every validation decision |
| `results/run_metadata.json` | Parameters, actual dates, formulas, package versions, platform, and UTC timestamp |

Downloaded raw data and generated result files are ignored by Git, following
the repository's reproducibility and size conventions. Re-run the command to
create them locally.

## Charts

The run creates six PNG files in `charts/`:

1. `growth-of-one-dollar.png` — overnight, regular-hours, and buy-and-hold
   wealth on a clearly labeled logarithmic axis.
2. `return-distributions.png` — overlapping daily return histograms. Values
   outside the central 99% are clipped only at the visual boundary and remain
   in all calculations.
3. `yearly-return-comparison.png` — compounded overnight and regular-hours
   return for every calendar year.
4. `rolling-average-returns.png` — 63-trading-day arithmetic rolling means,
   annualized for scale.
5. `drawdown-comparison.png` — each component's decline from its own prior
   wealth peak.
6. `cumulative-log-return-contribution.png` — the additive log-return
   decomposition through time.

Each chart includes a title, units, legend, source note, consistent colors, and
an explanation when an axis or visual treatment could otherwise be
misunderstood. Generated charts are ignored by Git under the existing
repository convention.

## Interpretation

### What the Data Shows

For adjusted SPY data in this fixed sample, the overnight component had a
higher mean, higher median, much higher compounded return, lower annualized
volatility, better Sharpe ratio, and shallower maximum drawdown than the
regular-hours component.

### What the Analysis Suggests

SPY's historical close-to-close growth was disproportionately associated with
the close-to-next-open interval. The finding was not limited to one extreme
observation or one starting year, although its size changed over time.

### What the Analysis Cannot Establish

This project cannot show why the pattern existed, whether it will continue,
whether another data vendor would produce identical values, or whether a real
investor could capture the official adjusted close-to-open calculation after
costs and taxes. Statistical significance does not prove economic
profitability.

### Was the Hypothesis Supported?

**Yes.** The full-sample historical data supports the pre-analysis hypothesis
that more of SPY's cumulative return occurred overnight.

### Was It Practically Tradable?

**Not established.** The simplified cost model leaves a positive overnight
return at 1 basis point per leg, but the result is much weaker, assumes
idealized execution, omits major frictions, and underperforms passive buy and
hold. A credible trading claim would require timestamp-level executable prices,
historical spread and fee data, tax assumptions, and a more realistic execution
model.

## Limitations

- Yahoo Finance can revise historical adjusted data, and `yfinance` is an
  unofficial interface to that provider.
- Daily OHLC data does not show which prices were realistically executable or
  available in size.
- Adjusted OHLC assigns corporate-action effects consistently, but a different
  adjustment convention can change the component attribution.
- Results cover one U.S. ETF and do not automatically generalize to other
  assets, countries, or periods.
- The fixed start date can still create selection effects; later starts reduce
  but do not eliminate that concern.
- Returns have fat tails, changing volatility, and possible serial dependence.
  The reported classical tests simplify those features.
- The cost model is hypothetical and does not include taxes, financing,
  variable spreads, slippage, market impact, or operational failures.
- This is an historical decomposition, not a causal model or forward forecast.

## Reproducibility Notes

- Dates are sorted and aligned by observed trading row, never by a one-calendar-
  day shift.
- The end date passed to `yfinance` is moved forward by one calendar day because
  the provider treats its `end` parameter as exclusive.
- The cache filename includes ticker, requested dates, and the adjusted-price
  convention.
- The bootstrap uses a fixed random seed.
- CSV and JSON files use stable names; JSON metadata records package versions
  and the run timestamp.
- The verified environment used NumPy 2.5.1, pandas 3.0.5, SciPy 1.18.0,
  matplotlib 3.11.1, and yfinance 1.5.2.
- Exact future values can drift if Yahoo revises history or a later provider
  version changes its adjustment logic. Refreshing the cache is therefore a new
  data snapshot, not a byte-for-byte replay.

## What I Learned

The main technical lesson is that date alignment matters as much as the return
formula. An overnight return must use the current open and the **previous
observed trading close**, not yesterday's calendar date and not the current
close.

The investing lesson is that a striking historical decomposition can still be
a weak trading strategy. Compounding, drawdowns, execution, costs, taxes, and
the passive alternative all matter before a statistical pattern becomes an
economic opportunity.

## Disclaimer

Capital in Code is for educational and informational purposes only. Nothing in
this project is financial, investment, tax, or legal advice. Historical results
do not guarantee future performance. Data and calculations may contain errors.
Always do your own research before making financial decisions.
