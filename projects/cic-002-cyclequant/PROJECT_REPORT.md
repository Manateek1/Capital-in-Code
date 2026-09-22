# CIC-002 — CycleQuant project report

**Status as of 2026-09-22:** Alpaca paper trading is enabled. The first BTC/USD paper order filled, and the project publishes a read-only account mirror at [capitalincode.com/projects/cic-002-cyclequant](https://capitalincode.com/projects/cic-002-cyclequant). This is an educational experiment, not an investment recommendation or evidence of a profitable strategy.

## In plain English

CycleQuant is a small, automated **practice-money** Bitcoin portfolio. Once per UTC day it checks market data, scores six groups of signals, and chooses a target Bitcoin share from 0%, 25%, 50%, 75%, or 100%. Separate safety rules decide whether an Alpaca **paper** order may be sent. The website shows the decision, the paper fill, the managed position, and whether the published position matches the broker. It does not trade real money, predict tomorrow's price, or let an AI model place trades.

## What has happened

| UTC date | Recorded result |
| --- | --- |
| 2026-09-20 | HOLD at 0% BTC; low confidence blocked an allocation change. |
| 2026-09-21 | HOLD at 0% BTC; first of two required confirmations for 25%. |
| 2026-09-22 | BUY to a 25% BTC target. Alpaca paper filled **0.002865445 BTC** at **$85,535.837013237/BTC**, about **$245.10** executed against a $250 target. |

The difference between a $250 target and a ~$245.10 paper fill is real execution variance. Alpaca also [charges crypto trading fees in the asset received on a buy](https://docs.alpaca.markets/us/docs/crypto-fees), so the BTC held can be lower than the gross order fill. The public portfolio calculates cash, **net BTC after posted broker fees**, marked value, and actual BTC percentage from recorded fills and Alpaca fee activities—not from the planned target. The bot compares that managed quantity with Alpaca's paper position before another order is permitted. A mismatch is shown publicly and stops a new order until resolved; it does not guess an unposted fee.

There is not enough operating history to claim outperformance. The benchmark and statistics on the site are descriptive. CycleQuant includes posted Alpaca paper fees, but paper fills still differ from real execution and omit other real-world costs.

## How the live system works

1. A scheduled GitHub Actions job runs the daily decision at **06:37 UTC**, with an idempotent recovery attempt at **08:47 UTC**. Re-running a day does not create another daily decision or duplicate the order.
2. A separate hourly run refreshes the Alpaca paper account mirror. Every run checks connection, paper-only status, account health, snapshot age, order state, and position reconciliation. Failures make the workflow fail visibly.
3. Decision and order history are stored in append-only records in Supabase. Public read-only views publish sanitized data; credentials, account identifiers, and Alpaca's unrelated headline balance do not appear on the site.
4. The Capital in Code website reads those public views, refreshes automatically, and marks an overdue snapshot **stale** rather than treating it as live. It does not silently substitute sample results in production.
5. A monthly repository keepalive protects the GitHub Actions schedule from GitHub's inactivity shutdown for public repositories. Scheduled runs can still be delayed by GitHub, so the page's freshness warning remains important.

A separate daily Codex health watch checks for missed decisions and stale or mismatched public data after the recovery window. It can retry the existing idempotent GitHub workflow once and alerts the owner only when recovery fails or action is needed. It is a secondary check, not a guarantee that external services will always be available.

The production website is on the existing Capital in Code Vercel deployment and domain. The trading process is cloud-hosted by GitHub Actions; the user's Windows computer does not need to remain on. The project uses the existing Supabase free project and Alpaca paper account. No paid OpenAI API key is required: the news input currently uses a deterministic local heuristic.

## Safety boundaries

- The broker adapter accepts only Alpaca's exact `https://paper-api.alpaca.markets` origin; a live-money endpoint is rejected.
- BTC/USD only, long-only, cash-backed, no leverage, and at most one 25-percentage-point allocation step per UTC day.
- The managed sleeve begins at **$1,000**. Unrelated paper-account equity cannot increase order size.
- Required inputs must be fresh and the paper account healthy. An unmanaged or mismatched BTC position stops new orders.
- Deterministic client order IDs and reconciliation protect against duplicate submissions after retries or restarts.
- A kill-switch file and the repository's trading-enabled setting can disable orders. The public website has no order-entry capability.
- The optional AI news classifier cannot set the allocation, access the broker, or override safety checks; production currently uses the no-key heuristic.

## Operations and checks

The two workflows are [daily evaluation and hourly mirror](../../.github/workflows/cyclequant-daily.yml) and [schedule keepalive](../../.github/workflows/cyclequant-keepalive.yml). In GitHub, open **Actions → CycleQuant daily evaluation** to inspect the latest run or manually run `daily` / `sync-broker`. A healthy run ends with JSON containing `"ok":true` from `cyclequant health`. A failure should be investigated rather than hidden or compensated with a manual trade.

To check the public side, open the [CycleQuant page](https://capitalincode.com/projects/cic-002-cyclequant). Look for **ALPACA PAPER · CONNECTED**, a recent update time, and **Reconciled**. If it says **STALE** or **Review required**, do not assume the displayed value is current. The homepage preview uses the same public data.

Local verification commands (from this project directory):

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check backend tests scripts
```

The website is built from `site/` with `npm run build`. The implementation and method are described in [README.md](README.md), [methodology](docs/methodology.md), and [safety](docs/safety.md).

## Limits and costs

The normal operating baseline is **$0 additional fixed cost** on the existing domain/Vercel setup, GitHub Actions for this public repository, Supabase's free project, public market-data feeds, the no-key news heuristic, and Alpaca paper trading. Free-service limits and policies can change; verify them before scaling. GitHub's schedule is not a guaranteed clock and external data feeds may fail. Paper fills can differ materially from live execution. BTC can lose substantial value. This experiment makes no promise of returns.
