# CIC-003 Analysis Summary

This is the concise technical findings summary. For reproduction instructions,
see the [project README](../README.md). For the full research paper, see
[research-report.md](../research-report.md).

## Research Question and Hypothesis

When the monthly mean 10-year/3-month Treasury spread is at or below zero for
three consecutive months, does an NBER-based recession start during the
inversion or within twelve months after the final inverted month?

The pre-analysis hypothesis was that confirmed inversion episodes would
precede or remain active for most later recession starts, with variable lead
times and some false alarms.

## Data and Approach

The study uses daily FRED `T10Y3M` observations, averaged by calendar month, and
the monthly FRED `USREC` NBER-based recession indicator. The common sample has
538 monthly observations from 1982-01 through 2026-10. The source data were
retrieved on 2026-11-04. Blank daily observations are skipped, not filled.

An inversion episode is a run of three or more consecutive monthly means at or
below 0.00 percentage points. It is confirmed at the end of month three. The
warning window begins the next month, remains active through the final
inverted month, and runs for twelve more months. A recession start is the first
month `USREC` changes from 0 to 1, which follows the NBER peak month under the
FRED/NBER convention.

## Primary Results

| Measure | Result |
| --- | ---: |
| Recession starts in sample | 4 |
| Confirmed inversion episodes | 6 |
| Episodes covering a start | 4 |
| False alarms | 2 |
| Recession starts covered | 4 of 4 |
| Median confirmation-to-start interval | 10 months |

| Recession start | Inversion episode | Confirmation | Months to start | Months after last inversion |
| --- | --- | --- | ---: | ---: |
| 1990-08 | 1989-06–1989-08 | 1989-08 | 12 | 12 |
| 2001-04 | 2000-07–2001-01 | 2000-09 | 7 | 3 |
| 2008-01 | 2006-08–2007-05 | 2006-10 | 15 | 8 |
| 2020-03 | 2019-05–2019-09 | 2019-07 | 8 | 6 |

The 1981–1982 recession was already in progress at the beginning of the
`T10Y3M` sample, so its onset predates the common sample and is excluded.

## Threshold Sensitivity

| Threshold | Episodes | Hits | False alarms | Starts covered | Missed | Right-censored |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| −0.25 pp | 3 | 2 | 1 | 2 of 4 | 2 | 0 |
| 0.00 pp | 6 | 4 | 2 | 4 of 4 | 0 | 0 |
| +0.25 pp | 7 | 4 | 2 | 4 of 4 | 0 | 1 |

The more negative threshold missed two starts. The more permissive threshold
left one additional episode right-censored at the sample end. These are
descriptive sensitivity results, not a parameter search.

## Interpretation and Limits

The 0.00 pp rule covered all four recession starts in this sample and also
produced two false-alarm episodes. Four events are too few for a reliable
probability estimate, and inversion episodes are not independent trials. The
NBER-based outcome labels are retrospective, so these results do not measure a
real-time warning service or establish causation.

The rule's warning period stays active while a spread remains inverted and for
twelve months after the last inverted month. That window can extend more than
twelve months beyond the initial confirmation. Full definitions, data-source
notes, citations, and limitations are in the research report.
