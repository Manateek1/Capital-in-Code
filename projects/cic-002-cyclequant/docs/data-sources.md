# Data-source notes

| Adapter | Required | Authentication | Freshness | Use |
| --- | --- | --- | --- | --- |
| Coinbase Exchange candles | Yes | None | 36 hours | BTC/USD daily OHLCV and spot close |
| FRED CSV | No | None | Series-dependent | Policy rate, dollar, liquidity changes |
| Coin Metrics community | No | None | 3 days | MVRV when exposed by community API |
| Binance funding history | No | None | 2 days | Seven-day average perpetual funding |
| Configured ETF JSON | No | Feed-specific | 2 days | Spot-Bitcoin ETF net flows |
| Google News RSS | No | None | 2 days | Recent public headline metadata |

Adapters return typed points with source, observed time, units, and metadata.
The aggregation layer isolates exceptions and records `fresh`, `stale`, or
`unavailable` status. A required source must exist and be fresh before risk can
approve an order.

Public APIs provide no uptime or schema guarantee. Rate limits and endpoint
terms must be reviewed before increasing frequency. CycleQuant runs only once
daily and uses bounded retries to keep demand modest.

ETF flows are disabled until a reliable, licensed JSON endpoint is explicitly
configured. Their absence lowers coverage instead of creating a fake zero-flow
observation.
