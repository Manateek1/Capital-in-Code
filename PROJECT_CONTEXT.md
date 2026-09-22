# Capital in Code — Project Context

> This is the living memory for the Capital in Code project. It was initialized
> from the user-provided `Capital_in_Code_Context.md` on 2026-07-29 and should
> evolve as durable decisions and milestones emerge. It is working context, not
> a substitute for the user's latest explicit instructions.

## High-Level Goal

Capital in Code is a software-focused project centered on finance, investing,
and programming. The goal is to build substantial work that demonstrates
technical ability while providing real value.

The current repository direction describes Capital in Code more specifically as
Dillon Nagar's public portfolio of coding and investing experiments. Each
project should explore a clear market or investing question using code,
financial data, models, charts, and a concise written analysis.

## Desired Characteristics

- Useful to real people.
- Portfolio-quality code.
- Strong enough to discuss in college applications and interviews.
- An opportunity to learn modern software engineering practices.
- Focused, reproducible research explained in plain language.

## Core Themes

- Finance and investing
- Software engineering
- Data analysis and statistics
- APIs and automation
- Financial modeling
- AI-assisted development

## Project Identity and Boundaries

- Capital in Code is a portfolio, not currently a startup, fund, nonprofit, or
  formal academic journal.
- It is separate from RentMax AI.
- It is separate from Voices United.
- It is focused on coding, finance, and long-term technical growth.
- Public work must include an educational/informational disclaimer and must not
  present itself as financial, investment, tax, or legal advice.

## Project Structure

- Projects receive permanent sequential identifiers: `CIC-001`, `CIC-002`, and
  so on.
- Each project should include a focused question, testable hypothesis, source
  code, data/method notes, charts, a written analysis, limitations, and
  reproducibility instructions.
- The public website should remain simple, fast, readable, and consistent with
  the repository's branding direction.

## Current Status

### Current completion status — 2026-08-08

- `CIC-001`, **The Overnight Effect**, is complete on `main`, including its
  tested Python research pipeline, verified results, formal research report,
  concise technical summary, charts, and reproducibility instructions.
- The public Capital in Code site is a React/Vite application in `site/` with
  Home, CIC-001, Methods, and About routes. It is connected to GitHub for
  deployments from `main`; its Vercel project uses `site` as the root directory
  and `dist` as the build output. Its public production address is
  `https://capitalincode.vercel.app`.
- The site identifies Dillon Nagar as its creator, links to the public GitHub
  repository and the CIC-001 research materials, and includes a site-wide
  educational disclaimer. It is intended as a public admissions-oriented
  research portfolio, not investment advice.

### Dated branding decision — 2026-08-08

- The public site now uses a primary, text-free mark: a navy circular orbit
  with an ascending signal path. It is used alongside the Capital in Code
  wordmark in the header and footer, and as the website favicon.
- The mark supports the existing minimalist, geometric, circle-based identity
  and is explicitly not a promise of financial performance.

### Public-report access - 2026-08-08

- The CIC-001 project page includes a direct, downloadable PDF report at
  `/reports/cic-001-the-overnight-effect.pdf`, so readers can inspect the
  completed findings without using GitHub. The committed source builder is
  `scripts/generate_cic001_report.py`; it presents the verified fixed-sample
  results, charts, robustness checks, reproducibility notes, and research
caveats in a public-facing format.

### Canonical domain — 2026-09-20

- Dillon already owns and pays for `capitalincode.com`.
- Treat `https://capitalincode.com` as the canonical public address for the
  Capital in Code portfolio. Do not include a new domain purchase in project
  cost estimates.
- Vercel may remain the deployment provider, but its generated
  `capitalincode.vercel.app` address is a deployment URL rather than the
  portfolio's canonical domain.

### CIC-002 cloud deployment decision — 2026-09-20

- CycleQuant (`CIC-002`) is cloud-first: its public, read-only dashboard will
  live with the existing Capital in Code Vercel deployment at
  `capitalincode.com`.
- A scheduled GitHub Actions workflow will run the once-daily evaluator, so a
  personal Windows computer does not need to stay powered on.
- Supabase PostgreSQL is the intended hosted audit/data store. SQLite remains
  the local-development and reproducible-demo store, and Windows Task
  Scheduler is an optional fallback rather than the primary deployment.
- The target baseline operating cost is $0 using appropriate free tiers and
  public/free data sources. Do not add a paid service or paid API dependency
  without Dillon's explicit approval.
- AI-assisted news analysis is optional and must always have a deterministic
  fallback; the core signal, risk, and allocation logic may not depend on a
  paid model call.

### CIC-002 implementation status — 2026-09-20

- CycleQuant is implemented under `projects/cic-002-cyclequant` with modular
  data adapters, indicators, deterministic scoring/allocation, independent
  paper-only risk controls, Alpaca paper and simulated brokers, immutable audit
  storage, constrained news analysis, benchmarks, a read-only API, tests, and
  reproducible documentation.
- The public React dashboard is integrated at
  `/projects/cic-002-cyclequant`. It uses a clearly labeled deterministic demo
  fixture until the RLS-protected Supabase public views are configured.
- The versioned Supabase migrations and scheduled GitHub Actions workflow are
  deployed. GitHub stores only the public Supabase connection values and a
  CycleQuant-specific writer token; no Alpaca credential is configured.
- Trading remains disabled by default. The validated live-data smoke run made
  no broker submission; optional Binance funding was unavailable in the local
  region and was isolated as designed.

### CIC-002 cloud publication status — 2026-09-20

- GitHub pull request #3 is merged into `main`, and Vercel successfully
  deployed CycleQuant to the canonical production domain at
  `https://capitalincode.com/projects/cic-002-cyclequant`.
- Supabase quoted $0/month for another free project but rejected creation
  because the account-level two-active-free-project limit was already reached.
  CycleQuant therefore uses only prefixed `cq_*` objects in the existing free
  database, with RLS and a separate 256-bit writer token. The workflow has no
  service-role credential and cannot bypass unrelated table policies.
- The first GitHub Actions cloud evaluation completed successfully and wrote
  one market snapshot, one published decision, and one performance row. Its
  2026-09-20 decision was HOLD with a 72.68 score, zero BTC exposure, and order
  status `NOT_SUBMITTED`.
- The public view exposes the published decision while an ordinary browser key
  cannot see market snapshots. The daily schedule runs at 06:30 UTC without a
  personal computer.
- Trading remains disabled, broker mode remains simulated, and the operating
  baseline remains $0/month within the selected free-tier limits.

### CIC-002 Alpaca paper mirror — 2026-09-20

- Dillon clarified that CycleQuant's core product is an Alpaca paper-trading
  account mirrored publicly under `CIC-002`, with transparent position data,
  paper-order activity, and decision insights that make the research process
  legible and credible.
- Strategy version `2026.2` adds a sanitized broker snapshot to SQLite and
  Supabase. The public dashboard shows only CycleQuant's isolated `$1,000`
  managed sleeve, BTC position, paper-order state, freshness, reconciliation,
  research notes, and hard guardrails. It must never expose credentials,
  account IDs, unrelated funds, or Alpaca headline account equity.
- The broker-snapshot migration is applied to the production Supabase project.
  The redesigned desktop and mobile dashboard has been checked for responsive
  overflow, browser errors, drawer behavior, and automated accessibility.
- No Alpaca credential is currently installed. Production must truthfully show
  `CONNECTION PENDING`; broker mode remains `simulated` and trading remains
  disabled until Dillon signs in to Alpaca, creates paper credentials, stores
  them securely in GitHub Actions, and a disabled-trading connection test
  succeeds. Do not claim that Alpaca is connected before that verification.
- Paper-order sizing is always based on the isolated managed sleeve rather than
  the broker account's total balance. Connecting an account must not broaden
  CycleQuant's capital scope.
- GitHub pull request #4 is merged into `main` at commit `34e7c6e`, and Vercel
  deployed that commit successfully to the canonical CycleQuant page. A
  production browser check confirmed the account strip, responsive layout,
  decision journal, and `CONNECTION PENDING` truth state with no browser or
  Vercel runtime errors.
- The first production broker-mirror snapshot was published successfully from
  GitHub Actions. It records a simulated, paper-only, reconciled `$1,000`
  managed sleeve with `$1,000` cash and 0% BTC exposure; the public payload
  does not contain the raw broker position. The 2026-09-21 daily evaluation
  remains HOLD at 0% exposure while the 25% candidate has one of two required
  confirmations.

### CIC-002 Alpaca activation and first paper fill — 2026-09-21

- Dillon explicitly approved regenerating the Alpaca paper API credentials,
  installing them in GitHub Actions, testing with trading disabled, and then
  enabling paper execution. The previous Alpaca key was invalidated. The new
  values exist only as encrypted repository secrets named
  `CYCLEQUANT_ALPACA_API_KEY_ID` and `CYCLEQUANT_ALPACA_API_SECRET_KEY`; never
  record or expose either value in project files, logs, or the public site.
- Production variables are now `CYCLEQUANT_BROKER_MODE=alpaca-paper`,
  `CYCLEQUANT_TRADING_ENABLED=true`, and
  `CYCLEQUANT_NEWS_ANALYZER=heuristic`. GitHub Actions run `35686312994`
  completed the disabled-trading connection test successfully before trading
  was enabled: the paper account was active, connected, unblocked, and
  position-reconciled.
- The first enabled production evaluation, run `35686412629`, created the UTC
  2026-09-22 decision: BUY, 25% target exposure, 70.78 composite score, and a
  `$250` target inside the isolated `$1,000` sleeve. Alpaca filled the paper
  order for `0.002865445 BTC` at an average `$85,535.837013237`, or about
  `$245.10` executed value. No real-money endpoint or broker headline equity
  is permitted to affect CycleQuant sizing.
- Pull requests #6, #7, and #8 are merged. They added a reusable broker-only
  workflow mode, made BTC position reads robust to Alpaca crypto symbology,
  and reconciled pending submissions through append-only order events so
  future allocations and the public dashboard use the actual fill state. The
  resulting production code is on `main` at commit `5434bb5` before this
  context update.
- Final production reconciliation run `35687504482` reported
  `alpaca-paper`, connected, `FILLED`, and `position_reconciled=true`. The
  sanitized public mirror shows only the `$1,000` managed sleeve: `$750`
  strategy cash, 25% BTC exposure, and `$250` managed BTC value.
- A production browser verification at
  `https://capitalincode.com/projects/cic-002-cyclequant` confirmed
  `ALPACA PAPER · CONNECTED`, paper execution enabled, the filled order and
  exact fill details in the audit drawer, successful reads from all four
  public Supabase views, and no browser console or rendering errors.

### CIC-002 reliability, truth-in-reporting, and site design — 2026-09-22

- Dillon's priority is a continuously operating Alpaca **paper** bot whose
  public CIC-002 page stays consistent with the account, plus a durable
  GitHub project report and a visual design matching Capital in Code/CIC-001:
  spacious white, navy, restrained financial presentation rather than a dark
  crypto-trading terminal. Explain the bot in plain language.
- Managed cash, BTC quantity, marked equity, return, and actual BTC exposure
  must derive from the immutable Alpaca fill ledger. The first `$250` target
  executed for about `$245.10`; the public site must not present that target
  as the actual fill. A broker-position mismatch is a stop condition for new
  orders and a visible public warning; reconciliation tolerance is one cent of
  BTC market value. Never use unrelated Alpaca paper-account
  equity to scale CycleQuant's isolated `$1,000` sleeve.
- The cloud operating design is daily evaluation at 06:37 UTC, idempotent
  recovery at 08:47 UTC, hourly broker-mirror refresh, health checks that fail
  visibly, and a monthly GitHub Actions keepalive to prevent the public-repo
  inactivity shutdown. The site auto-refreshes and labels overdue data stale;
  it does not silently substitute a demo result in production. GitHub
  schedules remain best-effort, not a guarantee of uninterrupted execution.
- `projects/cic-002-cyclequant/PROJECT_REPORT.md` is the public plain-language
  record of status, first paper fill, architecture, safeguards, operating
  checks, costs, and limitations. The site links to it. Very short samples
  should not show annualized volatility or Sharpe estimates as meaningful.
- A quiet daily Codex heartbeat named `CycleQuant health watch` checks the
  GitHub workflow and public mirror after the recovery window. It may retry
  the existing idempotent workflow once when safe and alerts Dillon only on
  actionable failure or mismatch. GitHub Actions remains the primary runner;
  this secondary check does not guarantee uptime.
- Tight one-cent reconciliation revealed that Alpaca's BTC/USD paper fill
  quantity is gross while its crypto buy fee is deducted from the BTC received.
  The managed ledger must subtract posted `CFEE` BTC activity (and any BTC/USD
  USD-denominated `FEE` activity) before comparing with the net Alpaca paper
  position. If fee activities have not posted, keep the mismatch visible and
  trading blocked rather than assuming a fixed fee percentage.

### Historical repository snapshot — 2026-07-29

- GitHub repository: `Manateek1/Capital-in-Code`.
- The repository foundation is present on `main`.
- The local working branch was `codex/repository-foundation` and was
  synchronized with its remote tracking branch.
- `CIC-001`, **The Overnight Effect**, is the selected first research project.
- A substantial implementation and verified analysis existed on the downloaded
  remote branch `origin/codex/cic-001-overnight-effect`; it had not yet been
  merged into `main` as of this snapshot.
- The public website was still a future placeholder; no website framework had
  yet been added as of this snapshot.

## Direction History

The initial conversation context described the project as early-stage and in
planning/discovery, with no finalized product direction. It identified the
immediate priority as choosing a clear MVP instead of brainstorming
indefinitely. The repository foundation subsequently narrowed the direction to
a public portfolio of reproducible coding-and-investing experiments and selected
The Overnight Effect as `CIC-001`.

## Possible Future Areas

- Investment research tools
- Portfolio analytics
- Financial dashboards
- Market-data integrations
- Quantitative analysis
- Educational finance software
- Developer-focused finance tools

These are possibilities, not committed roadmap items.

## Current Near-Term Priority

Operate and verify `CIC-002`, CycleQuant, as a cloud-run, transparent Alpaca
paper-allocation experiment; keep its public mirror current and reconciled
while preserving `CIC-001` and the portfolio's research-integrity standards.

## Context Maintenance

Add only durable, project-level information here. Date meaningful status
snapshots and record major decisions or reversals so future work has both the
current direction and the relevant history.
