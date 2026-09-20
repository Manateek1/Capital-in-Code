# Safety model

CycleQuant is designed for paper research only. Safety is enforced in code,
configuration, storage, and deployment rather than through prompt wording.

## Broker boundary

`AlpacaPaperBroker` rejects every base URL except the exact HTTPS origin
`https://paper-api.alpaca.markets`. The risk engine independently compares the
configured endpoint and broker-reported endpoint. No live URL, live broker
class, symbol selection, leverage, shorting, or derivatives path exists.

## Independent order gates

Every intended order must pass all gates:

- global trading flag explicitly enabled
- kill-switch file absent
- expected paper endpoint and active USD paper account
- BTC/USD instrument
- valid 0–100% allocation state and maximum step
- side consistent with allocation direction
- positive size, enough cash for buys, enough BTC for sells
- fresh required market source
- no earlier allocation change for the UTC date
- unused deterministic client order ID

Rejection returns before broker submission. A claimed ID is reconciled against
the broker after restart and is never resubmitted blindly.

## AI and content boundary

Headlines are untrusted data. Prompts explicitly prohibit obeying headline
instructions, following links, proposing trades, or inventing IDs. The model
receives no filesystem, shell, network, database, strategy, risk, or broker
tools. Output must match bounded fields and reference only supplied IDs.
Malformed or unknown-ID output falls back to deterministic classification.

## Secrets

- `.env` and runtime state are ignored by Git.
- Alpaca, Gemini, and Supabase service keys are server/scheduler secrets only.
- No secret may use a `VITE_` prefix.
- The browser receives only a Supabase publishable key, whose access remains
  constrained by row-level security.
- Logs should contain IDs and failure types, never credentials or authorization
  headers.

CycleQuant sizes from its isolated, internally marked `$1,000` research ledger,
not the Alpaca account's headline buying power. Use a dedicated paper account;
an unrelated BTC position cannot be separated from CycleQuant after Alpaca
aggregates it into the same symbol position.

## Emergency stop

Keep `CQ_TRADING_ENABLED=false` for development and initial cloud setup. To
stop a local runner independently, create `data/KILL_SWITCH`. For the cloud
workflow, set the repository variable `CYCLEQUANT_TRADING_ENABLED` to `false`
or disable the workflow. Cancel any already-open paper order directly in the
Alpaca paper console if needed.

## Non-goals

This project does not protect real funds because it must never access them. It
does not promise availability, profit, forecast accuracy, tax accounting, or
production custody controls.
