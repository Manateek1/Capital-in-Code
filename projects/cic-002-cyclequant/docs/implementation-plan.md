# CycleQuant implementation plan

CycleQuant is `CIC-002`: a transparent Bitcoin allocation experiment with a
$1,000 paper portfolio. It is a daily swing/cycle allocator, not a price
prediction product or a high-frequency trader.

## Non-negotiable boundaries

- BTC/USD only; exposure states are exactly 0%, 25%, 50%, 75%, and 100%.
- No leverage, shorting, derivatives, margin, or live brokerage endpoint.
- At most one allocation adjustment per UTC day.
- `CQ_TRADING_ENABLED=false` is the default and a kill-switch file can stop
  execution independently of strategy state.
- Missing/stale required market data or an unexpected broker account state is
  a hard rejection.
- The language model may classify news and draft explanations. It cannot
  select an exposure or place an order.
- Daily decisions and broker lifecycle events are append-only audit records.
- Backtests and benchmarks use only information available at each evaluation
  timestamp; no future observations are permitted.

## Stage 1 — foundation, data, storage, indicators

Deliverables:

- Installable Python package and environment-driven configuration.
- Isolated adapters for Coinbase daily BTC OHLCV, FRED macro series, Coin
  Metrics on-chain metrics, Binance futures funding, optional ETF-flow JSON,
  and RSS news.
- Bounded exponential retries, explicit rate-limit handling, source health,
  and staleness metadata.
- SQLite in WAL mode with append-only decisions/order events and durable market
  snapshots.
- SMA 20/50/100/200, RSI-14, 30-day realized volatility, ATH/local drawdown,
  halving-cycle position, and expanding-window power-law valuation.

Gate: unit tests cover indicator boundaries, stale-source behavior, database
round trips, and immutable audit rows.

## Stage 2 — deterministic signal and allocation engine

Deliverables:

- Six normalized components: valuation/cycle, trend/momentum, drawdown/market
  structure, on-chain/derivatives, macro/ETF flows, and news.
- Configurable weights defaulting to 25/25/15/15/10/10.
- Confidence derived from source coverage, freshness, and component agreement.
- Base score bands plus a five-point hysteresis margin, two daily
  confirmations, and a one-tier (25 percentage point) maximum normal step.
- Component-agreement requirements prevent one headline or one factor from
  causing a large allocation move.

Gate: table-driven tests cover every score boundary, hysteresis transition,
confirmation sequence, and missing optional component.

## Stage 3 — paper broker and independent risk engine

Deliverables:

- Alpaca adapter with a hard allow-list for
  `https://paper-api.alpaca.markets` and account-state verification.
- Local simulated paper broker for deterministic development and demos.
- Decimal-based position sizing, deterministic client order IDs, database
  idempotency keys, and restart-safe reconciliation.
- Independent risk validation for symbol, side, notional, exposure, account,
  source freshness, kill switch, daily order count, and configuration.

Gate: tests prove live URLs, leverage, shorting, duplicate orders, stale data,
disabled trading, and unsafe account states are rejected before broker I/O.

## Stage 4 — constrained AI and news reasoning

Deliverables:

- RSS ingestion, deduplication, source/time metadata, and deterministic
  heuristic fallback.
- Optional Gemini free-tier structured output for relevance, sentiment,
  uncertainty, summary, and cited headline IDs. The deterministic heuristic is
  the default when no key is configured or the provider is unavailable.
- Strict schema validation and prompt-injection-resistant treatment of article
  text as untrusted data.
- Quantitative engine consumes only a bounded 0–100 news feature; explanations
  are generated after the deterministic target is fixed.

Gate: malicious/instructional headlines cannot alter policies, execute code, or
create trade intents; malformed model output falls back safely.

## Stage 5 — dashboard and benchmarking

Deliverables:

- React + TypeScript + Vite dashboard implementing the approved design system.
- Performance series normalized to $1,000 for CycleQuant, BTC buy-and-hold,
  cash, and an optional 200-day moving-average strategy.
- Return, annualized return, maximum drawdown, volatility, approximate Sharpe,
  trade count, and exposure history.
- Responsive signal decomposition, current thesis, allocation table, decision
  journal, and complete audit drawer.
- Read-only FastAPI endpoints; the dashboard exposes no order-entry endpoint.

Gate: TypeScript build, browser interaction checks, desktop/mobile visual
comparison against the approved concepts, and decision-drawer accessibility.

## Stage 6 — continuous operation and handoff

Deliverables:

- One-command daily CLI and a GitHub Actions scheduled workflow so operation
  does not depend on a personal computer.
- Supabase PostgreSQL schema with row-level security: anonymous readers can
  select only explicitly published dashboard views; the scheduled writer's
  secret never reaches the browser.
- Optional Windows Task Scheduler registration script for local fallback.
- Structured JSON logging, run summaries, safe failure behavior, and health
  endpoint.
- Complete README, architecture/data/method/safety documentation, `.env.example`,
  and reproducible demo seed.
- Capital in Code project index and public-site project entry.

Gate: lint, backend tests, frontend tests/build, demo seed, API smoke test, and a
dry-run daily evaluation all pass from a clean checkout.

## Deployment and cost boundary

The public dashboard is deployed under the existing `capitalincode.com`
Vercel project. The daily evaluator runs in GitHub Actions and persists public
dashboard data to Supabase. All three are designed to fit their free tiers for
this once-daily personal research workload. No paid infrastructure or model is
required, and none should be enabled without explicit approval.

## Research integrity

Parameter changes are versioned and justified prospectively. Results are never
rewritten to improve the story. The project reports underperformance, missing
data, and limitations plainly. Data snapshots, derived features, AI output, and
assumptions remain distinguishable in every decision record.

## Verification snapshot — 2026-09-20

- Stages 1–6 are implemented locally.
- Backend lint passes and 38 tests pass across indicators, data isolation,
  allocation boundaries, risk gates, idempotency, SQLite/Supabase repositories,
  news injection handling, daily orchestration, and the read-only API.
- The Vite production build passes with the CycleQuant route code-split from the
  main portfolio bundle.
- A trading-disabled live-data smoke run completed with a 63.97 signal and a
  HOLD decision. Required Coinbase data was fresh; region-blocked Binance
  funding and unconfigured ETF flows were isolated as optional failures.
- Desktop, mobile, menu, chart, journal, and audit-drawer browser checks pass
  with no console error in a fresh tab.
- External Supabase/Vercel/GitHub/Alpaca credentials remain unconfigured, and
  trading remains disabled; those are deployment steps, not implicit setup.
