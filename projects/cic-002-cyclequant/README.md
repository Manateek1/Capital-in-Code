# CycleQuant

**An AI-assisted quantitative Bitcoin allocation and risk-management system.**

CycleQuant is `CIC-002`, a public Capital in Code research project. It asks:

> Can a transparent, multi-factor allocation system use quantitative market
> data and AI-assisted qualitative analysis to manage Bitcoin exposure better
> than simple passive strategies?

The system evaluates Bitcoin once per UTC day and recommends one of five
exposure states: **0%, 25%, 50%, 75%, or 100%**. It can submit only BTC/USD
paper orders, and only after a separate risk engine approves them. It is a
swing/cycle allocator—not a day trader or a next-day price predictor.

The production dashboard reads the experiment's published Supabase records and
mirrors its sanitized paper-account state. It shows only CycleQuant's isolated
`$1,000` sleeve, managed BTC position, recent paper orders, data freshness,
reconciliation state, and deterministic research notes. It never publishes an
Alpaca account identifier, credential, or headline account balance. The
committed deterministic fixture is for explicit local demo mode only; it is
**not a claimed investment result**. Production does not silently substitute it
if public data is unavailable. See the [project report](PROJECT_REPORT.md) for
the current paper-account status and operating checks.

## Hypothesis

A prospectively defined, multi-factor allocation process may reduce drawdowns
or improve risk-adjusted performance relative to continuously holding Bitcoin.
The experiment does not assume that it will outperform. Underperformance and
failed hypotheses remain part of the permanent record.

## System at a glance

```text
Public/free data adapters
          │
          ▼
Validated daily snapshot ──► deterministic indicators and six signal scores
          │                                      │
          │                                      ▼
          │                          hysteresis + confirmations
          │                                      │
          ▼                                      ▼
bounded news classification              target exposure
          │                                      │
          └────────► explanation ◄───────────────┘
                                                 │
                                                 ▼
                                  independent paper-only risk engine
                                                 │
                           ┌─────────────────────┴─────────────────────┐
                           ▼                                           ▼
                  Alpaca paper order                         immutable audit row
                                                                      │
                                                                      ▼
                                                      read-only public dashboard
```

The language model has no broker tools, cannot choose the allocation, and
cannot bypass a risk rule. With no model key, the complete system uses its
deterministic news fallback.

## Safety invariants

- Alpaca's exact `https://paper-api.alpaca.markets` origin is the only remote
  broker endpoint accepted.
- Trading defaults to `CQ_TRADING_ENABLED=false`.
- A local `data/KILL_SWITCH` file blocks orders independently of strategy state.
- BTC/USD only; no leverage, margin, shorting, options, or derivatives.
- One allocation adjustment at most per UTC date.
- Required market data must be fresh and the paper account must be healthy.
- Order IDs are deterministic and claimed before submission for restart-safe
  duplicate prevention.
- Market snapshots, decisions, and order events are append-only and protected
  by integrity hashes.
- Order sizing uses CycleQuant's isolated `$1,000` research ledger rather than
  the paper account's total buying power; use a dedicated paper account.
- The ledger uses recorded fill quantities, prices, and posted Alpaca crypto
  fees. A broker-position mismatch blocks the next order until resolved.
- The public broker mirror is sanitized: it publishes the managed sleeve and
  reconciliation result, never credentials, account IDs, or unrelated funds.
- The API and public dashboard expose no order-entry endpoint.

See [docs/safety.md](docs/safety.md) for the threat boundaries and failure
behavior.

## Strategy

| Component | Default weight | Examples |
| --- | ---: | --- |
| Long-term valuation / cycle | 25% | Expanding-window power law, halving position |
| Trend / momentum | 25% | SMA 20/50/100/200, RSI-14 |
| Drawdown / structure | 15% | ATH and 90-day-high drawdown |
| On-chain / derivatives | 15% | MVRV, seven-day funding rate |
| Macro / ETF flows | 10% | Policy, dollar, liquidity, optional ETF feed |
| News | 10% | Bounded relevance and tone classification |

The score-to-allocation map is stabilized by a five-point hysteresis margin,
two consecutive daily confirmations, independent-component agreement, and a
normal maximum step of 25 percentage points. Missing optional data is removed
and remaining weights are renormalized; it is never silently scored neutral.

The full prospective method is in [docs/methodology.md](docs/methodology.md).

## Data sources

Each source is isolated behind an adapter and can be replaced independently.

- Coinbase Exchange daily BTC/USD candles (required)
- Federal Reserve Economic Data CSV series
- Coin Metrics community API for MVRV when available
- Binance public funding-rate history when reachable
- Optional configured spot-Bitcoin ETF-flow JSON feed
- Google News RSS headlines

Source timestamps, freshness, failures, and coverage are saved with each daily
snapshot. See [docs/data-sources.md](docs/data-sources.md).

## AI's limited role

The default `heuristic` analyzer is local, deterministic, and free. An optional
Gemini free-tier classifier can be selected with `CQ_NEWS_ANALYZER=gemini` and
`GEMINI_API_KEY`. Headlines are supplied as untrusted JSON data, provider output
must match a strict schema, unknown headline IDs are rejected, and every error
falls back to the deterministic analyzer. Only public headlines are sent.

Google states that free-tier Gemini inputs may be used to improve its products;
do not send private data. No paid model is required.

## Benchmarks

All series start at `$1,000` and are updated without future observations:

1. CycleQuant paper portfolio
2. BTC buy-and-hold
3. Cash
4. Optional prior-day 200-day moving-average strategy

The dashboard reports total and annualized return, maximum drawdown,
annualized volatility, an explicitly approximate Sharpe ratio, trade count,
and exposure history. The managed CycleQuant series includes posted Alpaca
paper crypto fees; benchmark series omit fees. All series omit taxes, real
execution slippage, and risk-free-rate adjustments unless stated otherwise.

## Local setup

Python 3.11+ and Node.js are required.

```powershell
cd projects/cic-002-cyclequant
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
cyclequant init-db
cyclequant daily --dry-run
cyclequant serve
```

In another terminal:

```powershell
cd site
npm install
npm run dev
```

Open `http://127.0.0.1:5173/projects/cic-002-cyclequant`.

Useful commands:

```powershell
python -m pytest
ruff check backend tests scripts
cyclequant sync-broker
cyclequant health --require-today
cyclequant export-dashboard --output ..\..\site\public\data\cyclequant-dashboard.json
python scripts\seed_demo.py --database data\cyclequant.db
```

The seed command refuses to overwrite an existing database.

## Cloud operation at $0 baseline

The intended small personal-research deployment uses existing/free services:

- Capital in Code dashboard: existing Vercel project and `capitalincode.com`
- Daily evaluator: GitHub Actions schedule
- Audit database: Supabase PostgreSQL free tier
- Market/macro/news feeds: public endpoints
- AI: no-key heuristic by default; optional Gemini free tier
- Broker: Alpaca paper account only

Your Windows computer does not need to stay on. The local Windows task scripts
remain an optional fallback. Alpaca **paper** mode is active in production;
its credentials are encrypted GitHub Actions secrets and must never be pasted
into chat, source files, logs, or Vercel variables. GitHub Actions makes one
daily decision, retries it once later, and refreshes the public broker mirror
hourly. Each run includes a health check that fails visibly if the account or
mirror is unhealthy. The site labels snapshots older than two hours as stale.

Follow [docs/deployment.md](docs/deployment.md) to connect the free hosted
services without granting the scheduled writer a Supabase service-role key.

## Repository layout

```text
backend/cyclequant/
  api/             # read-only FastAPI endpoints
  broker/          # simulated and exact-origin Alpaca paper adapters
  data/            # isolated source adapters and aggregation
  database/        # SQLite and Supabase repositories
  indicators/      # technical, cycle, and valuation features
  news_analysis/   # deterministic + optional structured model analysis
  reporting/       # dashboard projection and benchmark metrics
  risk/            # independent hard constraints
  signals/         # component scoring and allocation state machine
  strategy/        # once-daily orchestration
docs/              # architecture, method, deployment, and safety notes
scripts/           # demo seed and optional Windows scheduling
supabase/           # versioned RLS-enabled hosted schema
tests/              # critical strategy, storage, AI, API, and risk tests
```

The public React dashboard lives in the repository's existing `site/` app so it
deploys under the canonical Capital in Code domain.

## Limitations

- Public free endpoints can change, rate-limit, revise history, or become
  unavailable; optional-source loss reduces confidence.
- Power-law, halving, rainbow-style, and on-chain models are descriptive
  heuristics, not laws of value.
- Paper fills differ from real execution and omit several real-world costs.
- A short sample cannot establish statistical superiority.
- The weights and thresholds are hypotheses recorded before results, not tuned
  to manufacture an attractive backtest.
- Cryptocurrency can lose most or all of its value.

## Disclaimer

CycleQuant is educational research and software experimentation. It is not
financial, investment, tax, or legal advice; it is not an investment adviser;
and it is not a recommendation to buy or sell Bitcoin or any other asset. Past
or simulated performance does not predict future results.
