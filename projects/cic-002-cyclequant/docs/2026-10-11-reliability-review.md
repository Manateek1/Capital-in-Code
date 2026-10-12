# CycleQuant reliability review — 2026-10-11

## Result

The public record contains **one buy and no sells**. A roughly 1% paper loss
was real and reconciled with the recorded BTC holding and posted fee. The
review also reproduced a software error: valid completed daily candles became
falsely stale after noon UTC, suppressing allocation changes. This branch
corrects that error as strategy version `2026.3`. Dillon authorized release
through [PR #13](https://github.com/Manateek1/Capital-in-Code/pull/13) on October 11.
The PR and GitHub Actions records track the release and production verification.
The initial review's broker-only checks did not submit a new paper order.

The reviewed `main` was `a70ba0fe3be2e9c507b4146eae6fdd8761adc0f1`. Verification
started October 9 and was refreshed October 11. Published views were read with
the same public access used by the dashboard. No broker credentials, account
identifiers, private snapshots, or unrelated account balances are included here.

## Account evidence

There were 22 daily decisions from September 20 through October 11, one BUY
decision resolved to FILLED by its append-only order events, 21 HOLDs, and no
SELLs. The original decision is still PENDING in its immutable row; the
dashboard correctly overlays the later FILLED event. Historical decisions and
the two existing order events remained intact during verification.

| Published paper snapshot (UTC) | Managed cash | Net BTC value | Managed equity | Return from $1,000 |
| --- | ---: | ---: | ---: | ---: |
| 2026-10-10 01:01 | $754.90 | $235.81 | $990.71 | -0.929% |
| 2026-10-11 15:49 | $754.90 | $238.25 | $993.15 | -0.685% |
| 2026-10-11 18:13 | $754.90 | $239.54 | $994.44 | -0.556% |

The net position was `0.002858280 BTC`, after the posted `0.000007165 BTC`
buy fee. These snapshots were paper-only, connected, active, unblocked, and
position-reconciled. These dated marks explain the reported loss and are not
claims about the balance at a later time. [Alpaca's fee documentation](https://docs.alpaca.markets/us/docs/crypto-fees)
describes fees in the asset received and the CFEE/FEE activity records.

The comparison with buy-and-hold remains part of the experiment. A short sample
and functioning execution do not establish outperformance. No return history
was overwritten, and no counterfactual profit claim was calculated.

## Reproduced error and correction

[Coinbase's candle specification](https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles)
defines its timestamp as the bucket start. CycleQuant excludes incomplete daily
candles, but previously used that opening timestamp to age the closing price.

For the October 9 evaluation at **13:41:05 UTC**, live Coinbase data reproduced:

- Latest completed candle opened October 8 at 00:00 UTC.
- Its closing observation became available October 9 at 00:00 UTC.
- Old age: **37.68 hours**, incorrectly exceeding the 36-hour freshness limit.
- Correct age: **13.68 hours**, correctly fresh.
- The read-only replay returned 499 completed bars and zero incomplete bars;
  its core-only confidence was Medium after correction.

All 16 Low-confidence decisions in the first 20 published rows had 100% signal
coverage, dispersion below 25, and evaluation times after noon UTC. That pattern
matches the reproduced required-source failure. This is evidence of an input
timestamp error, not justification to lower confidence standards.

Changes:

- `backend/cyclequant/data/market.py`: use candle end for source and spot-close
  observation time. Retain opening timestamps on OHLCV bars, and record both
  boundaries in snapshot metadata.
- `backend/cyclequant/constants.py`: version future decisions as `2026.3`.
- `tests/test_data_pipeline.py`: cover early, noon, and late UTC evaluations,
  incomplete-candle exclusion, missing latest data, and downstream confidence.
- `tests/test_strategy_and_api.py`: exercise two-confirmation buy and sell,
  holding through a price loss, selling only held BTC, preserving the resulting
  $950 ledger, isolation from a $100,000 broker headline balance, and retry
  idempotency. This test uses a simulated broker and synthetic signals.
- Data-source notes, methodology, project report, and root `PROJECT_CONTEXT.md`:
  document the error, prospective version, evidence, and limits.

Signal weights, score thresholds, the 36-hour freshness limit, confirmations,
one-tier daily steps, and paper risk controls retain their existing values.
Truly old data still blocks allocation changes. Existing same-date decisions
are returned on retry; the correction applies to future evaluations.

## Verification

| Check | Result |
| --- | --- |
| Reproduce on original timestamp behavior | Five parameterized regression cases failed before the fix |
| `python -m pytest` | 50 passed; one dependency deprecation warning |
| `python -m ruff check backend tests scripts` | Passed |
| `npm ci` and `npm run build` in `site/` | Installation and production build passed |
| Live Coinbase replay of the delayed October 9 evaluation | Fresh completed close, no incomplete candles |
| Existing production broker-only refresh | [Run 38020390475](https://github.com/Manateek1/Capital-in-Code/actions/runs/38020390475) succeeded; health `ok=true`, connected and reconciled |
| Refreshed October 11 production check | [Run 38162863195](https://github.com/Manateek1/Capital-in-Code/actions/runs/38162863195) succeeded; all health checks passed; no decision or order-event changes |
| Public accounting and history | Fill-event overlay, net fee-adjusted BTC, cash, and dated equity matched; historical decisions and order events preserved |

Python checks ran locally on Python 3.14.6; the production workflow uses Python
3.12. The initial review preceded production execution of the patch. The observed
Starlette warning concerns its test client's deprecated httpx integration;
the tests passed. npm reported an existing high-severity `source-map-js`
[advisory](https://github.com/advisories/GHSA-68fv-2mgg-jv7q) in the unchanged site
lockfile; dependency remediation is outside this timestamp correction.

### Rendered dashboard QA

The flow checked was the production CycleQuant route → September 22 paper
trade → decision drawer showing the actual fill → close drawer. Playwright CLI
was used because the Browser plugin was not available. No frontend files were
changed by this patch.

| Rendered check | Result |
| --- | --- |
| Environment | `https://capitalincode.com/projects/cic-002-cyclequant`; desktop 1440×1000 and mobile 390×844 |
| Page identity and meaningful content | Correct URL and Capital in Code title; account, portfolio, and journal rendered |
| Framework overlay | None observed |
| Console health | Zero errors and zero warnings |
| Screenshot evidence | Desktop account and decision drawer plus mobile screenshots inspected; connected status and dated equity matched the public snapshot |
| Interaction proof | Drawer showed FILLED and $245.10 actual paper value; closing it removed the dialog |
| Mobile width | Content width 390 px at a 390 px viewport; no horizontal overflow |

Screenshot artifacts remain outside the repository. Other browsers, real-money
execution, and future market states were not exercised.

## Rollout and research limits

After review and merge, inspect the first new daily snapshot for the candle
closing timestamp and required-source freshness, then confirm the public
decision, order lifecycle, and reconciliation. A correctly evaluated signal may
still HOLD under the existing agreement and confirmation rules.

GitHub Actions schedules continue to be best-effort. The dashboard's overdue
mirror warning was observed and accurately reflected delayed hourly updates;
a broker-only refresh recovered the mirror. This patch fixes candle-age
accounting and does not guarantee schedule timing or profitable trades.
