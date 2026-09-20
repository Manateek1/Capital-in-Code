# Architecture

CycleQuant separates measurement, strategy, risk, execution, persistence, and
presentation so no language-model or UI change can silently acquire trading
authority.

## Runtime boundaries

1. Source adapters fetch independently and return typed payloads with observed
   timestamps. A failed optional source is isolated; failed required BTC market
   data stops the run.
2. The indicator engine derives only from bars available at `as_of`.
3. News analysis returns a bounded feature. Its text is untrusted and its
   output is schema-validated.
4. The signal engine combines available components with configured weights.
5. The allocation state machine applies bands, hysteresis, breadth,
   confirmations, confidence, and maximum step size.
6. The risk engine independently validates configuration, endpoint, account,
   instrument, cash/position size, freshness, daily limit, kill switch, and
   idempotency.
7. The coordinator claims a deterministic client order ID before any broker
   submission and reconciles an already-claimed ID after a restart.
8. The repository writes the immutable decision and order event, then updates
   the replaceable daily benchmark projection.
9. FastAPI and the web client are read-only consumers.

## Storage

SQLite uses WAL mode and immutable triggers for reproducible local development.
The cloud schedule selects `SupabaseDatabase`, which writes through the
service-role REST interface. Supabase row-level security grants anonymous users
only selected columns from published decisions/events and published performance
rows. Full snapshots, private payloads, and idempotency keys have no anonymous
grant.

The service-role key belongs only in GitHub Actions. The browser uses a
publishable key and security-invoker views.

## Failure semantics

- Network calls use bounded exponential retry only for timeouts, network
  errors, rate limits, and transient server responses.
- Required market failure aborts without a decision or order.
- Optional failure is recorded and reduces signal coverage/confidence.
- Model failure produces a deterministic fallback analysis.
- Risk rejection produces an auditable rejected decision and no broker call.
- A broker error becomes a failed order result; it is never retried blindly.
- An ambiguous idempotency state requires manual reconciliation.

## Public deployment

The React dashboard is code-split from the lighter portfolio routes. It reads
RLS-protected Supabase views when public configuration is present and otherwise
shows the committed `DEMO DATA` fixture. No FastAPI service is required for the
public Vercel deployment; FastAPI exists for local research and inspection.
