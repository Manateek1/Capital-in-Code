# CIC-001: The Overnight Effect in SPY

## Abstract

This study decomposes the historical return of the SPDR S&P 500 ETF Trust (SPY) into two non-overlapping holding intervals: the previous trading close to the next trading open (overnight) and the current open to current close (regular hours). Using adjusted daily OHLC data obtained from Yahoo Finance through yfinance, the fixed sample contains 8,053 aligned trading-day returns from 1994-01-04 through 2025-12-31.

Over the full sample, the overnight component compounded to 1,917.13% (9.86% annualized), while the regular-hours component compounded to 28.63% (0.79% annualized). Close-to-close buy and hold compounded to 2,494.64% (10.73% annualized). The average overnight-minus-regular-hours daily return difference was 3.18 basis points. A paired t-test returned p = 0.0160, the Wilcoxon signed-rank test returned p = 0.000163, and a 10,000-sample paired bootstrap placed the 95% interval for the mean daily difference between 0.55 and 5.74 basis points.

The pattern is historically striking but neither uniform nor sufficient to establish practical tradability. It persisted in selected later-start samples and after paired tail trimming, yet the defined COVID shock was a sharp counterexample: overnight return was -28.12% versus -7.34% during regular hours. A simplified 1-basis-point-per-leg daily cost model left the overnight series positive, but reduced its annualized return to 4.46%, below the 10.73% historical buy-and-hold return. These results are a historical return decomposition, not a causal explanation, forecast, or investment recommendation.

## Research Question

From January 1994 through December 2025, did SPY historically earn more of its adjusted close-to-close return in the close-to-next-open interval than in the open-to-close interval?

## Background and Motivation

Daily equity returns are commonly presented as close-to-close changes. That convention is useful for a continuous holder, but it combines time when the exchange is closed with time when regular trading is open. Separating those intervals clarifies where historical growth occurred without assuming why it occurred.

The distinction also matters for interpretation. A large difference between components may be statistically detectable without being available to an investor after spreads, slippage, taxes, and the mechanics of trading at the official open and close. This study treats return attribution and strategy feasibility as separate questions.

## Pre-Analysis Hypothesis

Before implementation, the recorded hypothesis was that the overnight component would account for a larger share of SPY's cumulative return than the regular-hours component.

## Data

The analysis uses daily SPY Open and Close data downloaded from Yahoo Finance through yfinance with auto_adjust=True. The requested window was 1994-01-01 through 2025-12-31. Available price observations began on 1994-01-03; after excluding the first price row, which has no prior observed close, the aligned return sample begins on 1994-01-04 and ends on 2025-12-31.

The verified run contained 8,054 clean price rows and 8,053 aligned return rows. It found no invalid prices, duplicate dates, or removals beyond the first unaligned observation. Trading dates are ordered observed trading rows: weekends and holidays are not filled with zero returns. An overnight return following a Friday close is consequently measured to the next observed trading open.

### Adjusted-Price Convention

auto_adjust=True applies Yahoo Finance's split- and dividend-adjustment factor consistently to both Open and Close. Raw and adjusted fields are never mixed. This prevents stock splits from appearing as artificial price jumps and allows the adjusted overnight and regular-hours components to reconstruct the adjusted close-to-close return.

The convention matters because corporate-action adjustments can be attributed across an ex-dividend boundary, including in the close-to-open interval. The result is a total-return-style adjusted decomposition, not the same as a simulation that trades only unadjusted quoted prices. It is a coherent historical accounting convention, not proof that the reported adjusted Open or Close was executable.

## Methodology

Prices are validated before returns are calculated. The pipeline normalizes dates without shifting their local calendar date, rejects duplicate trading dates, sorts chronologically, requires numeric positive Open and Close values, and records removals. If an invalid row occurs, the subsequent return is also suppressed rather than bridged across a missing trading observation.

For each observed trading date t, the prior close is the Close on the previous trading observation, not the prior calendar day:

    overnight return = current Open / previous Close - 1
    regular-hours return = current Close / current Open - 1
    close-to-close return = current Close / previous Close - 1

The pipeline verifies on each row that:

    (1 + overnight return) * (1 + regular-hours return) - 1
        = close-to-close return

The largest verified reconstruction discrepancy was 2.22 × 10^-16, well below the configured tolerance of 1 × 10^-12.

## Return Definitions

### Why the Components Compound Rather Than Add

Simple returns must compound because each return is earned on a changing capital base. On a single day, the close-to-close gross return is the product of the overnight and regular-hours gross returns, not their arithmetic sum. Over multiple days, each component's wealth is the product of its daily gross returns.

This is why the reported dollar-growth values reconcile multiplicatively: $1 invested in the overnight component grew to $20.17 and $1 invested during regular hours grew to $1.29; their product is approximately the $25.95 ending value of the adjusted close-to-close series. Adding simple returns is at most a small-return approximation, not exact multi-period wealth accounting.

For numerical stability, the pipeline also calculates log returns. Overnight and regular-hours log returns add exactly to the close-to-close log return on each date, and cumulative log returns are exponentiated to recover compounded growth. The simple-return and log-return implementations produced the same compounded results in the verified output.

## Statistical Methods

For each component, the analysis reports daily location and dispersion statistics, tail percentiles, skewness, excess kurtosis, frequency of positive returns, cumulative and annualized return, annualized volatility, Sharpe ratio, and maximum drawdown. Annualization uses 252 trading days and the reported Sharpe ratios use a 0% annual risk-free rate.

The primary inferential comparison uses matched return pairs from the same trading dates. A paired design is appropriate because overnight and regular-hours observations are two components of the same day rather than unrelated samples. It avoids treating shared day-specific market conditions as though the samples were independent.

- The paired t-test assesses whether the mean paired difference differs from zero, assuming independent paired differences over time and an approximately normal sampling mean.
- The Wilcoxon signed-rank test is a nonparametric paired test based on signed ranks of nonzero differences; it still assumes independent, approximately symmetric paired differences.
- The paired bootstrap resamples same-date return pairs 10,000 times with a fixed random seed and estimates an interval for the mean difference. It treats dates as exchangeable and does not model serial dependence.

These procedures do not establish a causal mechanism, a stable market law, or economically executable profit. Statistical significance concerns compatibility with a test's null model; economic significance additionally requires attention to magnitude, risk, costs, capacity, and investability.

## Results

The full-sample return decomposition favors the overnight component on compounded return, annualized return, volatility, Sharpe ratio, and maximum drawdown.

| Metric | Overnight | Regular hours | Buy and hold |
| --- | ---: | ---: | ---: |
| Observations | 8,053 | 8,053 | 8,053 |
| Arithmetic mean per day | 0.03962% | 0.00785% | 0.04748% |
| Median per day | 0.06070% | 0.04775% | 0.07081% |
| Positive observations | 56.33% | 52.61% | 54.28% |
| Cumulative return | 1,917.13% | 28.63% | 2,494.64% |
| Annualized return | 9.86% | 0.79% | 10.73% |
| Annualized volatility | 10.75% | 15.43% | 18.84% |
| Sharpe ratio | 0.929 | 0.128 | 0.635 |
| Maximum drawdown | -32.79% | -68.49% | -55.19% |

The mean daily overnight-minus-regular-hours difference was 0.03177 percentage points, or 3.18 basis points. The paired t-test yielded a statistic of 2.409 and p = 0.0160. The Wilcoxon signed-rank statistic was 15,416,259 with p = 0.000163. The paired bootstrap's 95% interval was 0.55 to 5.74 basis points per day. Together, these results provide historical evidence of a positive paired difference under their stated assumptions. They do not say that the difference is constant, causal, or tradable.

![Growth of one dollar by return component](charts/growth-of-one-dollar.png)

*Figure 1. Compounded adjusted growth of $1 by component. The logarithmic axis preserves proportional changes. Generated locally by the project pipeline.*

![Cumulative log-return contribution](charts/cumulative-log-return-contribution.png)

*Figure 2. Cumulative log-return contribution. The two component series add to the close-to-close log return on each aligned date.*

## Robustness Checks

The project uses focused sensitivity analyses rather than treating one full-sample estimate as a universal constant.

### Later Starting Periods

Holding the end date fixed at 2025-12-31, the overnight annualized return exceeded the regular-hours annualized return in each tested later-start sample. The size of the gap narrowed materially in recent windows.

| Sample start | Overnight annualized return | Regular-hours annualized return |
| --- | ---: | ---: |
| Full sample (1994) | 9.86% | 0.79% |
| 2000 | 6.96% | 1.01% |
| 2010 | 8.62% | 4.89% |
| 2020 | 8.71% | 5.66% |

These results show the full-sample conclusion is not confined to the 1994 start date. They do not show stability: the smaller recent gap is direct evidence that the magnitude is period-dependent.

### Extreme Observations

The paired trim retains a date only when both component returns lie between their respective full-sample 1st and 99th percentiles. It removed 284 of 8,053 dates, leaving 7,769. In the retained sample, overnight compounded to 3,746.17% and regular hours to 11.76%. This indicates that the original full-sample ordering was not produced only by a handful of dates. It is a sensitivity check, not a claim that an investor could avoid adverse tails.

### Market-Period Evidence and the COVID Counterexample

The period results are descriptive, not causal tests, and they show that the effect was not uniform. During the defined COVID shock window from 2020-02-19 through 2020-03-23, overnight compounded return was -28.12%, compared with -7.34% during regular hours. A full-sample tendency therefore coexisted with a short crisis interval in which overnight exposure was especially damaging.

![Compounded return by calendar year](charts/yearly-return-comparison.png)

*Figure 3. Calendar-year compounded return for the two components. The annual dispersion illustrates why an aggregate result should not be read as uniform year-to-year performance.*

![Drawdown by return component](charts/drawdown-comparison.png)

*Figure 4. Drawdown from each component's prior peak. Drawdowns are evaluated on component wealth paths, not on a simulated executable strategy.*

## Transaction-Cost / Practical-Tradability Analysis

The transaction-cost exercise is explicitly hypothetical. It applies a 1-basis-point cost on entry and a 1-basis-point cost on exit on every observed trading day, assumes fills at price multiplied by (1 + cost) on entry and price multiplied by (1 - cost) on exit, and compounds the result daily.

| Component | Gross annualized return | Net annualized return | Net cumulative return |
| --- | ---: | ---: | ---: |
| Overnight | 9.86% | 4.46% | 302.96% |
| Regular hours | 0.79% | -4.16% | -74.30% |

The overnight figure remains positive under that mechanical sensitivity, but it does not establish a realistically tradable strategy. It assumes execution at prices tied to the official open and close apart from a fixed proportional cost; it omits changing bid-ask spreads, slippage, market impact, failed or partial executions, financing and account constraints, capacity, and taxes. It also requires daily turnover and underperformed the full-sample 10.73% annualized close-to-close buy-and-hold result. A trading conclusion would need timestamp-level executable price data, historical fees and spreads, tax assumptions, and an execution model appropriate to the intended scale.

## Interpretation

Within this fixed adjusted SPY sample, a disproportionate share of historical close-to-close growth is associated with the close-to-next-open interval. The full-sample evidence also shows lower annualized volatility and a shallower maximum drawdown for the overnight component than for regular-hours returns.

That attribution should not be mistaken for a causal account. The analysis does not identify whether information arrival, risk compensation, market microstructure, institutional trading patterns, corporate-action treatment, or another mechanism produced the pattern. Nor does it imply that the pattern should continue. The reduced gap in later-start samples and the COVID-period losses are reasons to avoid presenting the result as invariant.

## Limitations

- Yahoo Finance may revise historical adjusted data, and yfinance is an unofficial interface to that provider.
- Adjusted daily OHLC data is an accounting input, not evidence that its Open and Close values were executable at the desired size and time.
- The adjusted-price convention can affect how dividend and other corporate-action effects are attributed between the components.
- Daily data omits bid-ask spreads, intraday path, opening and closing auction mechanics, slippage, market impact, latency, and failed execution.
- Taxes, financing, borrowing or account constraints, and implementation capacity are absent from the return decomposition and cost sensitivity.
- Daily return differences can exhibit serial dependence, fat tails, and changing volatility. The paired t-test, Wilcoxon test, and simple bootstrap do not fully model those features.
- SPY is a single U.S. ETF and the fixed historical sample is not a cross-asset or out-of-sample study. Later-start checks reduce, but cannot eliminate, selection and sample-period concerns.
- The work documents historical association only. It does not establish causality, forecast future returns, or recommend an investment action.

## Conclusion

The pre-analysis hypothesis was supported in the verified adjusted-price sample: from 1994-01-04 through 2025-12-31, SPY's overnight component had far higher compounded and annualized return than its regular-hours component. The paired inferential tests and bootstrap provide evidence that the average daily difference was positive under their assumptions, while the start-date and tail checks show the full-sample ordering was not isolated to one initial year or a few extreme observations.

The result nevertheless falls short of a tradable-strategy claim. The effect varied across periods, performed poorly during the defined COVID shock, and was substantially weakened by even a deliberately simple daily cost model. This report is historical evidence about a return decomposition, not a prediction or investment recommendation.

## Reproducibility

The repository's [README](README.md) is the project landing page and contains installation, command-line, testing, and generated-output instructions. The concise technical findings are maintained in [analysis/summary.md](analysis/summary.md).

From this project directory, reproduce the documented configuration with:

    python -m src.main --ticker SPY --start-date 1994-01-01 --end-date 2025-12-31

The pipeline writes machine-readable statistics and robustness output to results/ and generates the figures referenced above in charts/. Raw data, results, and charts are intentionally ignored by Git; rerunning the pipeline produces them locally. The fixed bootstrap seed is 42, with 10,000 resamples. Future refreshes may differ if Yahoo Finance revises historical data or the provider's adjustment logic changes.

Run the offline validation suite with:

    python -m pytest
    python -m ruff format --check src tests
    python -m ruff check src tests
    python -m mypy src

## References / Data Sources

1. Yahoo Finance. Daily SPY historical OHLC data, retrieved through the yfinance Python package with auto_adjust=True for the verified run.
2. CIC-001 generated artifacts: results/summary_statistics.csv, results/component_comparison.csv, results/inferential_tests.csv, results/robustness_checks.json, results/data_validation_report.json, and results/run_metadata.json.
3. CIC-001 research pipeline: src/data.py, src/validation.py, src/returns.py, src/stats.py, src/robustness.py, and src/charts.py.

