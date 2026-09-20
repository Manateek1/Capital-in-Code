# Cloud deployment

CycleQuant is cloud-first so no personal computer needs to remain online. The
baseline is designed for free tiers and does not provision anything
automatically.

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

The scheduled workflow runs at 06:30 UTC and can also be dispatched manually.
It exits successfully without running when the three required Supabase values
are absent, so merging the code does not create a failing unconfigured schedule.
Keep trading disabled through migration, first data collection, and audit
review. Enabling it affects only the configured Alpaca **paper** account.

## 3. Configure public Vercel reads

The site source includes the deployed Supabase URL and publishable browser key;
both are public identifiers protected by RLS. These optional Vercel variables
can override them later without changing source:

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_PUBLISHABLE_KEY`

Never add the CycleQuant writer token or a service-role key to Vercel or any
`VITE_*` variable. The dashboard displays the labeled committed demo fixture
until the database contains its first published decision.

The site's existing SPA rewrite already supports direct visits to
`/projects/cic-002-cyclequant` on `capitalincode.com`.

## 4. Verify before enabling paper submissions

1. Run the workflow manually with trading disabled.
2. Confirm one decision, snapshot, and performance row in Supabase.
3. Confirm anonymous requests can read the three `cq_public_*` views and cannot
   read `private_payload`, market snapshots, or idempotency keys.
4. Confirm the writer token has authority only in CycleQuant RLS policies and
   does not bypass any unrelated table policy.
5. Confirm the Vercel dashboard reports real data and no longer says `DEMO`.
6. Review source freshness and the complete risk-check list.
7. Switch broker mode to `alpaca-paper` while trading remains disabled.
8. Verify the exact paper account state and endpoint.
9. Only then, if desired, set `CYCLEQUANT_TRADING_ENABLED=true`.

## Optional Windows fallback

From PowerShell:

```powershell
.\scripts\register_windows_task.ps1 -DailyAt "06:45"
```

The task calls `scripts/run_daily.ps1` from this checkout. It is a fallback,
not required for cloud operation.
