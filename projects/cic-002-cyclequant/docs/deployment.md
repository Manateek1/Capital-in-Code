# Cloud deployment and operations

CycleQuant is cloud-first so no personal computer needs to remain online. The
baseline is designed for free tiers. Database migrations and deployments can
be automated, but Alpaca credentials must be created by the account owner
inside an authenticated Alpaca session.

## 1. Select and migrate a Supabase project

Use a dedicated project when a free slot is available. If CycleQuant must share
an existing Supabase project, the committed migration keeps its objects under
the `cq_*` prefix and gives the scheduled writer a separate token enforced by
RLS. It never gives the workflow a service-role key.

Install/authenticate the Supabase CLI, then from this directory run:

```powershell
npx supabase link --project-ref <project-ref>
npx supabase db push
```

The committed migration enables RLS on every exposed table, creates
security-invoker public views, withholds full snapshots/private payloads from
ordinary anonymous requests, and keeps audit tables immutable. After applying
the migration, provision a random writer token by storing only its SHA-256 hash
in `cyclequant_private.cq_runtime_secrets`.

## 2. Add GitHub Actions secrets

In the GitHub repository, add:

- `CYCLEQUANT_SUPABASE_URL`
- `CYCLEQUANT_SUPABASE_PUBLISHABLE_KEY`
- `CYCLEQUANT_WRITE_TOKEN`
- `CYCLEQUANT_ALPACA_API_KEY_ID` (only for Alpaca paper mode)
- `CYCLEQUANT_ALPACA_API_SECRET_KEY` (only for Alpaca paper mode)
- `CYCLEQUANT_GEMINI_API_KEY` (optional)

Add repository variables:

- `CYCLEQUANT_BROKER_MODE=simulated` initially; later `alpaca-paper`
- `CYCLEQUANT_TRADING_ENABLED=false` initially
- `CYCLEQUANT_NEWS_ANALYZER=heuristic` initially; optional `gemini`

Production currently uses `alpaca-paper`, with paper execution enabled. The
workflow refreshes the broker mirror hourly, makes the primary decision at
06:37 UTC, and runs an idempotent recovery at 08:47 UTC. It can also be
dispatched manually. Missing required configuration or a failed health check
fails the run visibly. For a new installation, keep trading disabled through
migration, initial data collection, and audit review. Enabling it affects only
the configured Alpaca **paper** account.

## 3. Configure public Vercel reads

The site source includes the deployed Supabase URL and publishable browser key;
both are public identifiers protected by RLS. These optional Vercel variables
can override them later without changing source:

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_PUBLISHABLE_KEY`

Never add the CycleQuant writer token or a service-role key to Vercel or any
`VITE_*` variable. The production dashboard never silently uses the committed
demo fixture. If public data is unavailable, it shows an error or the last
verified snapshot with a freshness warning. The demo fixture is available
only in explicit local demo mode with `VITE_CYCLEQUANT_DEMO=true`.

The site's existing SPA rewrite already supports direct visits to
`/projects/cic-002-cyclequant` on `capitalincode.com`.

## 4. Verify before enabling paper submissions

1. Run the workflow manually with trading disabled.
2. Confirm one decision, snapshot, and performance row in Supabase.
3. Run `cyclequant sync-broker` and confirm a sanitized broker-snapshot row.
4. Confirm anonymous requests can read the public views and cannot
   read `private_payload`, market snapshots, or idempotency keys.
5. Confirm the writer token has authority only in CycleQuant RLS policies and
   does not bypass any unrelated table policy.
6. Confirm the Vercel dashboard reports real data and shows the correct broker
   connection state.
7. Review source freshness and the complete risk-check list.
8. Sign in to Alpaca, create paper-only credentials, and store them directly in
   GitHub Actions secrets. Never put them in chat, source control, or Vercel.
9. Switch broker mode to `alpaca-paper` while trading remains disabled.
10. Verify the exact paper endpoint, account health, managed position, and
    reconciliation result.
11. Only then, if desired, set `CYCLEQUANT_TRADING_ENABLED=true`.

## Ongoing health

Open GitHub Actions → **CycleQuant daily evaluation**. A normal hourly or daily
run finishes with `cyclequant health` and `"ok":true`. The `daily` mode also
requires a decision for the current UTC date. If a run fails, inspect its
error; do not submit a compensating order by hand. The site should show
`ALPACA PAPER · CONNECTED`, a recent snapshot, and a reconciled position.
An overdue sync is labeled `STALE` on the public page.

The monthly **CycleQuant schedule keepalive** workflow makes an empty commit
to keep GitHub's public-repository schedule from being disabled after 60 days
without repository activity. GitHub can still delay scheduled jobs, and this
workflow must itself be able to push to the repository's default branch.

## Optional Windows fallback

From PowerShell:

```powershell
.\scripts\register_windows_task.ps1 -DailyAt "06:45"
```

The task calls `scripts/run_daily.ps1` from this checkout. It is a fallback,
not required for cloud operation.
