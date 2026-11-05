# CIC-003: The Yield Curve’s Warning Window

## Abstract

This study asks whether a confirmed inversion in the U.S. 10-year/3-month
Treasury spread preceded or remained active for later NBER-based recession
starts. Daily FRED `T10Y3M` observations were averaged by calendar month and
aligned with the monthly FRED `USREC` indicator. The common sample contains 538
months from 1982-01 through 2026-10.

The primary rule defines a confirmed inversion as three consecutive monthly
means at or below 0.00 percentage points. Its warning window begins the month
after confirmation, remains active through the last inverted month, and extends
twelve months beyond that month. Six episodes met the rule. Four covered one of
the four recession starts in the sample; two completed their warning windows
without a recession start. The median confirmation-to-start interval among the
four covered starts was 10 months.

The observed coverage is historically complete but based on only four recession
starts. The episodes and their warning windows are not independent trials, and
the NBER-based labels are retrospective. The result is not a real-time forecast,
a causal claim, or investment advice.

## Research Question

When the monthly mean of the 10-year Treasury yield minus the 3-month Treasury
yield stays at or below zero for three consecutive months, how often does an
NBER-based recession start during the inversion or within twelve months after
the final inverted month?

## Background and Motivation

The yield curve compares interest rates at different maturities. A negative
10-year/3-month spread means the shorter-term constant-maturity rate is above
the longer-term rate. This simple comparison is frequently discussed as a
recession warning, but a warning can arrive early, stay active for a long time,
or fail to be followed by a recession within a chosen horizon.

This project makes those choices explicit. It counts unique runs of inversion,
records how long they lasted, and reports which recession starts were inside a
predefined warning window. It does not tune a model or turn the historical
association into an investment recommendation.

## Pre-Analysis Hypothesis

Three-month-confirmed inversion episodes will precede or remain active for
most later recession starts, but the time from confirmation to recession will
vary and some inversion episodes will be false alarms.

## Data

### Sources and Coverage

- **Yield spread:** FRED series `T10Y3M`, daily, in percentage points, not
  seasonally adjusted. The series is defined as the 10-year constant-maturity
  Treasury rate minus the 3-month constant-maturity Treasury rate. The
  downloaded file contained 11,213 nonblank daily observations from 1982-01-04
  through 2026-11-04.
- **Recession indicator:** FRED series `USREC`, monthly values of 0 or 1 based
  on NBER business-cycle dates. The downloaded file covered 1854-12 through
  2026-10.
- **Aligned analysis sample:** 538 consecutive calendar months from 1982-01
  through 2026-10. November 2026 is excluded because `USREC` had no monthly
  observation for it when the data were retrieved on 2026-11-04.

FRED's notes for `T10Y3M` state that the source for the underlying Treasury
rates changed to direct U.S. Treasury data beginning 2019-06-21. FRED labels
the series as requiring citation and asks readers to review its series-specific
copyright information before redistributing source data. The raw CSV downloads
are cached locally under `data/raw/` and are not included in Git.

### Recession-Date Convention

The `USREC` series is an interpretation of the NBER chronology, not a live
monthly announcement feed. Under the FRED trough method, a recession indicator
begins in the month after the NBER peak and stays on through the trough month.
The NBER itself defines the peak month as the last month of expansion and the
trough month as the last month of recession. This study identifies a recession
start as a 0-to-1 transition in `USREC`; it therefore uses the first recession
month after the peak month.

## Methodology

1. Download the FRED CSV files for `T10Y3M` and `USREC`, or use the existing
   local cache.
2. Parse daily spread observations, reject duplicate dates and non-finite
   values, and skip blank source rows without filling or interpolation.
3. Compute an arithmetic mean of the observed daily spread values in each
   calendar month.
4. Join the monthly means to the same-month `USREC` values. Reject duplicate
   months, invalid recession codes, and gaps in the common monthly series.
5. Find recession starts as months where `USREC` changes from 0 to 1.
6. For each threshold, group consecutive monthly means at or below the
   threshold. Retain a run only when it lasts at least three months, and set
   the confirmation month to the third consecutive month.
7. Begin its warning window in the following month. Keep the warning active
   through the last inverted month, then include the next twelve calendar
   months. This period can be longer than twelve months from the initial
   inversion or confirmation when an episode is long.
8. Count an episode as a **hit** if at least one recession start falls inside
   its warning window. Count it as a **false alarm** only when the full window
   elapsed with no recession start. An open episode or an incomplete
   follow-up window without an event is **right-censored**.
9. Use 0.00 percentage points as the primary threshold. Report −0.25 and
   +0.25 percentage points as fixed sensitivity checks; do not select a
   threshold from the outcomes.

### Outcome and Lead-Time Definitions

The primary episode table reports the first recession start in each episode's
warning window. The confirmation lead is the calendar-month difference between
the third consecutive inverted month and that start. The post-inversion lag is
the difference between the final inverted month and that start. Positive
post-inversion values mean the recession began after the spread returned above
the threshold. These are date differences, not trading-day durations.

The project separately counts how many unique recession starts are covered by
at least one warning window. A recession start can lie inside more than one
episode's window when windows overlap; such overlap does not create additional
recession events. Episode counts are descriptive and are not treated as
independent statistical observations.

## Statistical Methods

The project reports counts, calendar-month date differences, and the median
confirmation lead across covered recession starts. It does not report a
p-value, confidence interval, regression, or estimated recession probability.
There are only four recession starts in the common sample, while monthly
spread observations and warning windows are serially related. A formal test
would imply more independent evidence than this design provides.

## Results

### Primary Threshold: 0.00 Percentage Points

| Measure | Result |
| --- | ---: |
| Monthly observations | 538 |
| Sample | 1982-01 through 2026-10 |
| NBER-based recession starts | 4 |
| Confirmed inversion episodes | 6 |
| Hit episodes | 4 |
| False-alarm episodes | 2 |
| Right-censored episodes | 0 |
| Recession starts covered | 4 of 4 |
| Median confirmation lead | 10 months |

| NBER-based recession start | Corresponding NBER peak month | Inversion episode | Confirmation | Months from confirmation | Months after final inversion |
| --- | --- | --- | --- | ---: | ---: |
| 1990-08 | 1990-07 | 1989-06–1989-08 | 1989-08 | 12 | 12 |
| 2001-04 | 2001-03 | 2000-07–2001-01 | 2000-09 | 7 | 3 |
| 2008-01 | 2007-12 | 2006-08–2007-05 | 2006-10 | 15 | 8 |
| 2020-03 | 2020-02 | 2019-05–2019-09 | 2019-07 | 8 | 6 |

The four recession starts follow their corresponding NBER peak months by one
month under the series convention. The 2006–2007 inversion ended eight months
before the January 2008 recession start; the warning window still covered it.
The 1981–1982 recession was already underway at the first common month,
1982-01. Its onset predates the spread sample and is excluded; the four events
above are all complete 0-to-1 transitions observed in the common sample.

| Inversion episode | Confirmation | End of inverted run | Recession start in warning window | Result |
| --- | --- | --- | --- | --- |
| 1989-06–1989-08 | 1989-08 | 1989-08 | 1990-08 | Hit |
| 2000-07–2001-01 | 2000-09 | 2001-01 | 2001-04 | Hit |
| 2006-08–2007-05 | 2006-10 | 2007-05 | 2008-01 | Hit |
| 2019-05–2019-09 | 2019-07 | 2019-09 | 2020-03 | Hit |
| 2022-11–2024-11 | 2023-01 | 2024-11 | None through 2025-11 | False alarm |
| 2025-06–2025-08 | 2025-08 | 2025-08 | None through 2026-08 | False alarm |

The 2022–2024 episode remained inverted for 25 months. Its active signal and
12-month follow-up ended in November 2025 without an NBER-based recession
start. The 2025 episode's complete follow-up also ended without a start.

### Threshold Sensitivity

| Threshold | Confirmed episodes | Hits | False alarms | Starts covered | Missed starts | Right-censored |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| −0.25 pp | 3 | 2 | 1 | 2 of 4 | 2 | 0 |
| 0.00 pp | 6 | 4 | 2 | 4 of 4 | 0 | 0 |
| +0.25 pp | 7 | 4 | 2 | 4 of 4 | 0 | 1 |

The more negative threshold missed two recession starts. The more permissive
threshold added an episode whose warning window was still right-censored at
the end of the sample. This is a small, fixed sensitivity check, not an
optimization exercise.

## Interpretation

The primary rule covered each recession start in the common sample, but it
also issued two warnings that were not followed by a start within the defined
window. Confirmation-to-start intervals ranged from 7 to 15 months. The
2022–2024 inversion is a prominent example of why a negative spread is not a
precise calendar prediction.

These findings support the pre-analysis hypothesis for this historical
sample, but the support is descriptive and limited to four recession events.
They do not show that the spread caused a recession or that an investor could
profit from the signal.

## Limitations

- **Small event count:** Four recession starts are not enough to estimate a
  stable probability or compare thresholds with high confidence.
- **Left-censored first recession:** The spread series begins during the
  1981–1982 recession. That recession's onset predates the common sample and
  is not included in the four-event count.
- **Retrospective labels:** NBER peak and trough dates are determined after
  reviewing economic data. The NBER says there is no fixed announcement delay;
  its published examples range from four to twenty-one months. A live system
  would not know the final label at the turning point.
- **Long and overlapping warning windows:** The signal remains active during
  inversion and for twelve months afterward. Long episodes create long
  windows, and nearby episodes can overlap. Episodes are not independent.
- **Threshold choice:** The primary 0.00 pp cutoff and three-month confirmation
  rule were not trained or validated on a later holdout sample.
- **Data revisions and source changes:** FRED can revise source observations;
  its `T10Y3M` source methodology changed in 2019. A new download can change
  the latest sample and derived outputs.
- **No market-return test:** The project studies recession chronology, not
  Treasury, equity, or portfolio returns. It does not quantify the cost of
  acting on a warning.
- **No causal claim:** Monetary policy, growth expectations, inflation, and
  other conditions may affect both the spread and recession timing. This
  design only compares historical dates.

## Conclusion

Between 1982-01 and 2026-10, a three-month-confirmed 0.00 pp inversion rule
covered all four NBER-based recession starts and produced two false-alarm
episodes. The result is an inspectable account of this small historical
sample. It does not establish a reliable real-time forecast or an investment
strategy.

## Reproducibility

The pipeline uses Python 3.11 or later and the standard library. From the
project directory, run `py -3 -m src.main`. The script downloads source files
when the local cache is absent; pass `--refresh` to retrieve current data.
Outputs include the monthly aligned data, episode and sensitivity CSVs, a JSON
summary, two SVG charts, and the website summary JSON. The source snapshot
used for this paper was retrieved on 2026-11-04.

## References and Data Sources

1. Federal Reserve Bank of St. Louis, FRED, [10-Year Treasury Constant
   Maturity Minus 3-Month Treasury Constant Maturity (`T10Y3M`)](https://fred.stlouisfed.org/series/T10Y3M).
2. Federal Reserve Bank of St. Louis, FRED, [NBER-based Recession Indicators
   for the United States (`USREC`)](https://fred.stlouisfed.org/series/USREC).
3. National Bureau of Economic Research, [U.S. Business Cycle Expansions and
   Contractions](https://www.nber.org/research/data/us-business-cycle-expansions-and-contractions).
4. National Bureau of Economic Research, [Business Cycle Dating Procedure:
   Frequently Asked Questions](https://www.nber.org/research/business-cycle-dating/business-cycle-dating-procedure-frequently-asked-questions).

## Disclaimer

This report is for educational and informational purposes only. It is not
financial, investment, tax, or legal advice, and it is not a recommendation to
buy or sell any security.
