# Cloud deployment

CycleQuant is cloud-first so no personal computer needs to remain online. The
baseline is designed for free tiers and does not provision anything
automatically.

## 1. Create and migrate a Supabase project

Create a free Supabase project, install/authenticate the Supabase CLI, then from
this directory run:

```powershell
npx supabase link --project-ref <project-ref>
npx supabase db push
```

The committed migration enables RLS on every exposed table, creates
security-invoker public views, withholds full snapshots/private payloads from
anonymous roles, and keeps audit tables immutable.

## 2. Add GitHub Actions secrets

In the GitHub repository, add:

- `CYCLEQUANT_SUPABASE_URL`
- `CYCLEQUANT_SUPABASE_SERVICE_ROLE_KEY`
- `CYCLEQUANT_ALPACA_API_KEY_ID` (only for Alpaca paper mode)
- `CYCLEQUANT_ALPACA_API_SECRET_KEY` (only for Alpaca paper mode)
- `CYCLEQUANT_GEMINI_API_KEY` (optional)

Add repository variables:

- `CYCLEQUANT_BROKER_MODE=simulated` initially; later `alpaca-paper`
- `CYCLEQUANT_TRADING_ENABLED=false` initially
- `CYCLEQUANT_NEWS_ANALYZER=heuristic` initially; optional `gemini`

The scheduled workflow runs at 06:30 UTC and can also be dispatched manually.
It exits successfully without running when the two required Supabase secrets
are absent, so merging the code does not create a failing unconfigured schedule.
Keep trading disabled through migration, first data collection, and audit
review. Enabling it affects only the configured Alpaca **paper** account.

## 3. Configure public Vercel reads

Add these variables to the existing Capital in Code Vercel project:

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_PUBLISHABLE_KEY`

Never add the service-role key to Vercel or any `VITE_*` variable. Without
these variables the dashboard intentionally displays the labeled committed
demo fixture.

The site's existing SPA rewrite already supports direct visits to
`/projects/cic-002-cyclequant` on `capitalincode.com`.

## 4. Verify before enabling paper submissions

1. Run the workflow manually with trading disabled.
2. Confirm one decision, snapshot, and performance row in Supabase.
3. Confirm anonymous requests can read the three `cq_public_*` views and cannot
   read `private_payload`, market snapshots, or idempotency keys.
4. Confirm the Vercel dashboard reports real data and no longer says `DEMO`.
5. Review source freshness and the complete risk-check list.
6. Switch broker mode to `alpaca-paper` while trading remains disabled.
7. Verify the exact paper account state and endpoint.
8. Only then, if desired, set `CYCLEQUANT_TRADING_ENABLED=true`.

## Optional Windows fallback

From PowerShell:

```powershell
.\scripts\register_windows_task.ps1 -DailyAt "06:45"
```

The task calls `scripts/run_daily.ps1` from this checkout. It is a fallback,
not required for cloud operation.
