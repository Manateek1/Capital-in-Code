# Prospective methodology

This document records the initial CycleQuant rules before a hosted paper
experiment begins. Material parameter changes should update the strategy
version and be justified prospectively rather than back-fit to results.

## Evaluation schedule

One run is evaluated per UTC date after daily market data is expected to be
available. A rerun for the same date returns the existing decision. The
strategy can make no more than one allocation adjustment per date.

## Features

- Trend: location versus SMA 20/50/100/200 and bounded RSI-14 contribution.
- Risk/structure: 30-day realized volatility and drawdown from ATH and local
  90-day high.
- Cycle/valuation: time since known halvings and an expanding-window log-log
  power-law regression. Only past data enters each estimate.
- On-chain/derivatives: MVRV and seven-day average funding when available.
- Macro/flows: changes in policy, broad dollar, Fed balance-sheet, and optional
  five-session ETF net flows.
- News: a bounded 25–75 score based on recent public headlines.

Rainbow-style concepts are represented only indirectly by long-horizon
valuation residuals and must remain a weak descriptive input. They are not an
authority or price target.

## Score and confidence

Default component weights are 25/25/15/15/10/10. Unavailable optional
components receive zero effective weight; remaining available weights are
renormalized. Confidence combines source coverage, required-source freshness,
and cross-component dispersion.

Base exposure bands are:

- `[0, 30)` → 0%
- `[30, 45)` → 25%
- `[45, 60)` → 50%
- `[60, 75)` → 75%
- `[75, 100]` → 100%

A proposed move must clear a five-point margin beyond the current band's
boundary. It normally needs two consecutive daily confirmations. A one-tier
move needs at least two independent directional components; a larger raw gap
needs at least four. Normal execution changes exposure by at most 25 percentage
points.

Low confidence always holds the existing allocation.

## Benchmark accounting

All benchmark paths normalize to `$1,000` on the paper inception date.
Buy-and-hold owns BTC throughout. Cash remains at `$1,000` with no assumed
interest. The optional SMA strategy applies today's return only when the prior
day's BTC close was above its then-known SMA-200, preventing look-ahead.

Reported Sharpe is approximate: mean daily return divided by daily standard
deviation, annualized with `sqrt(365)` and no assumed risk-free rate. Annualized
return is withheld for samples under 30 days. Win/loss is not emphasized
because allocation changes are not discrete closed trades.

## Research-integrity rules

- Preserve all daily outcomes, including holds, rejections, missing data, and
  underperformance.
- Do not rewrite history after parameter changes.
- Keep raw snapshots, derived indicators, news interpretation, strategy output,
  and execution status distinguishable.
- Never select a training/backtest endpoint because its result looks better.
- Report fees, slippage, revised data, survivorship, and sample-size limits.
