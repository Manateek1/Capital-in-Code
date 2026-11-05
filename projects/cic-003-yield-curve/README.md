# CIC-003 — The Yield Curve’s Warning Window

This project studies whether an inversion of the U.S. 10-year/3-month Treasury
spread appeared before NBER-based recession starts. It counts distinct,
confirmed inversion episodes and records both covered recessions and false
alarms. The historical signal is an educational research rule, not a live
forecast or a trading strategy.

For concise technical findings, see [analysis/summary.md](analysis/summary.md).
For the full paper, see [research-report.md](research-report.md).

## Project Code

`CIC-003`

## Status

Historical analysis complete for the common monthly sample from 1982-01 through
2026-10, retrieved on 2026-11-04. The committed website summary and charts
reflect that sample. The analysis script can refresh its FRED data cache.

## Research Question

When the monthly mean of the 10-year Treasury yield minus the 3-month Treasury
yield stays at or below zero for three consecutive months, how often does an
NBER-based recession start during the inversion or within twelve months after
the final inverted month?

## Pre-Analysis Hypothesis

Three-month-confirmed inversion episodes will precede or remain active for
most later recession starts, but the time between confirmation and recession
will vary and some inversion episodes will be false alarms.

## Main Result

The primary rule found six confirmed inversion episodes. Four covered one of
the four NBER-based recession starts in the sample; two completed their
warning windows without a recession start. The median interval from
confirmation to the covered recession start was 10 months.

| Measure | Result |
| --- | ---: |
| Common monthly observations | 538 |
| Sample | 1982-01 through 2026-10 |
| Recession starts | 4 |
| Confirmed zero-threshold episodes | 6 |
| Episodes covering a recession start | 4 |
| False-alarm episodes | 2 |
| Right-censored episodes | 0 |
| Recession starts covered | 4 of 4 |
| Median confirmation-to-start interval | 10 months |

The result is a small historical event count, not an estimated probability.
Episode and recession windows are serially related, so the counts are not
independent statistical trials.

## Research Rule

1. Average all available daily FRED `T10Y3M` observations in each calendar
   month. Do not fill blank dates or interpolate missing values.
2. Call a run of at least three consecutive monthly means at or below the
   threshold a confirmed inversion episode. The third month is the confirmation
   month.
3. Start the warning window in the month after confirmation. Keep it active
   through the final inverted month, then extend it by twelve months.
4. Count a hit if an NBER-based recession start occurs in that warning window.
   Count a false alarm only when the full window has elapsed without a start.
   An active or incomplete window is right-censored.
5. Repeat the analysis at −0.25 and +0.25 percentage points as fixed threshold
   sensitivity checks. The primary threshold remains 0.00.

This is an episode study, not a fixed twelve-month forecast measured from the
first inverted month. A long inversion keeps the warning active longer. The
full method and date convention are documented in
[research-report.md](research-report.md).

## Primary Episodes

| Inverted months | Confirmation | Recession start in window | Months from confirmation | Months after final inversion | Result |
| --- | --- | --- | ---: | ---: | --- |
| 1989-06–1989-08 | 1989-08 | 1990-08 | 12 | 12 | Hit |
| 2000-07–2001-01 | 2000-09 | 2001-04 | 7 | 3 | Hit |
| 2006-08–2007-05 | 2006-10 | 2008-01 | 15 | 8 | Hit |
| 2019-05–2019-09 | 2019-07 | 2020-03 | 8 | 6 | Hit |
| 2022-11–2024-11 | 2023-01 | None | — | — | False alarm |
| 2025-06–2025-08 | 2025-08 | None | — | — | False alarm |

Recession starts use the first month `USREC` changes from 0 to 1. Under the
NBER/FRED convention, that is the month after the NBER peak month.
The sample begins during the 1981–1982 recession, so that recession's onset
predates the available `T10Y3M` data and is not counted. The four events above
are complete onset transitions observed after the sample start.

## Threshold Sensitivity

| Threshold | Confirmed episodes | Hits | False alarms | Recession starts covered | Missed starts | Right-censored |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| −0.25 pp | 3 | 2 | 1 | 2 of 4 | 2 | 0 |
| 0.00 pp | 6 | 4 | 2 | 4 of 4 | 0 | 0 |
| +0.25 pp | 7 | 4 | 2 | 4 of 4 | 0 | 1 |

The more negative threshold missed two recession starts in this sample. The
more permissive threshold added one episode that was still right-censored at
the sample end. This check does not identify a best threshold.

## Data and Coverage

- **Yield spread:** FRED `T10Y3M`, daily percentage-point spread between the
  10-year and 3-month Treasury constant-maturity rates. The downloaded series
  contains 11,213 nonblank daily observations from 1982-01-04 through
  2026-11-04. FRED notes that the underlying source for the rate inputs changed
  to U.S. Treasury data on 2019-06-21.
- **Recession indicator:** FRED `USREC`, monthly NBER-based values of 0 or 1.
  The downloaded series extends from 1854-12 through 2026-10; the analysis uses
  the common window with `T10Y3M`.
- **Aligned analysis sample:** 538 consecutive months from 1982-01 through
  2026-10. November 2026 is excluded because the monthly recession indicator
  was not yet available for that month.
- **Sources:** See [References and data sources](research-report.md#references-and-data-sources).

The raw downloads are cached under `data/raw/` and ignored by Git. FRED marks
these series as requiring citation and asks users to review series-specific
copyright information before redistributing source data. The project links to
the source series and does not bundle the raw CSV files.

## Data Validation

The pipeline rejects duplicate source dates, non-finite spread values, invalid
recession codes, and gaps in the common monthly sample. Blank FRED daily rows
are skipped without interpolation; the remaining daily values are averaged by
calendar month. Every aligned month has both a spread and a recession label.

## Charts

- `spread-and-recessions.svg` shows the monthly mean spread, its zero line, and
  NBER-based recession months.
- `inversion-episode-timeline.svg` shows confirmed inversion runs, the
  follow-up window, and the recession starts covered by the primary rule.

The generated charts appear in `charts/` and are copied to the public site at
`site/public/images/cic-003/`.

## Limitations

- The primary sample contains only four recession starts and six confirmed
  inversion episodes. The counts cannot support a stable probability estimate.
- The 1981–1982 recession was already underway when `T10Y3M` begins in 1982-01;
  its onset is outside the spread sample and is not in the denominator.
- Inversion episodes and their outcome windows are time-dependent and may
  overlap. No p-values or confidence intervals are reported.
- `USREC` is a retrospective NBER-based classification. NBER dates are not
  known in real time and can be announced months after a peak, so this study
  does not measure a live forecasting system.
- The follow-up rule remains active during a long inversion and for twelve
  months after it ends. Its full window can be longer than one year from the
  first inverted month.
- The threshold and three-month confirmation rule are descriptive choices, not
  parameters selected or validated out of sample.
- FRED source values can be revised. A refresh can change the latest sample and
  generated outputs; the written findings below remain the fixed 2026-11-04
  snapshot until this report is revised.
- The study does not show that the yield curve causes recessions, measures
  equity-market returns, or establishes that any portfolio strategy works.

## Architecture

- `src/data.py` downloads and validates the two FRED CSV series and builds the
  common monthly sample.
- `src/analysis.py` identifies NBER-based recession starts, groups inversion
  runs, and computes the threshold sensitivity results.
- `src/charts.py` creates the accessible SVG charts without third-party
  plotting packages.
- `src/output.py` writes machine-readable CSV/JSON and updates the site's
  compact summary data.
- `src/main.py` runs the complete pipeline.

## Reproduce the Analysis

The project uses Python 3.11 or later and the standard library only. From this
directory, run:

```powershell
py -3 -m src.main
```

The first run downloads the FRED CSV files to `data/raw/`. Later runs use that
local cache. To retrieve current source data and rebuild the outputs:

```powershell
py -3 -m src.main --refresh
```

The pipeline writes `summary.json`, `monthly_observations.csv`,
`inversion_episodes.csv`, and `threshold_sensitivity.csv` under `results/`,
updates the two SVGs, and refreshes `site/src/cic003/summary.json`. The committed
report and homepage use the fixed 2026-11-04 results above; review and update
those written claims before publishing a later refreshed sample.

## Disclaimer

This project is for educational and informational purposes only. It is not
financial, investment, tax, or legal advice. It is not a forecast or a
recommendation to buy or sell any security.
