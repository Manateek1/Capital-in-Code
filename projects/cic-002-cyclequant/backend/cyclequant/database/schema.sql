PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO schema_metadata(key, value) VALUES ('schema_version', '1');

CREATE TABLE IF NOT EXISTS market_snapshots (
    id TEXT PRIMARY KEY,
    as_of TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    symbol TEXT NOT NULL,
    spot_price TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    integrity_hash TEXT NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_market_snapshots_as_of
    ON market_snapshots(as_of DESC);

CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    decision_date TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    strategy_version TEXT NOT NULL,
    market_snapshot_id TEXT NOT NULL REFERENCES market_snapshots(id),
    current_exposure INTEGER NOT NULL CHECK(current_exposure IN (0, 25, 50, 75, 100)),
    target_exposure INTEGER NOT NULL CHECK(target_exposure IN (0, 25, 50, 75, 100)),
    action TEXT NOT NULL CHECK(action IN ('BUY', 'SELL', 'HOLD')),
    total_score REAL NOT NULL CHECK(total_score BETWEEN 0 AND 100),
    confidence TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    integrity_hash TEXT NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_decisions_created_at
    ON decisions(created_at DESC);

CREATE TABLE IF NOT EXISTS decision_signals (
    decision_id TEXT NOT NULL REFERENCES decisions(id),
    signal_name TEXT NOT NULL,
    score REAL NOT NULL CHECK(score BETWEEN 0 AND 100),
    configured_weight REAL NOT NULL,
    effective_weight REAL NOT NULL,
    available INTEGER NOT NULL CHECK(available IN (0, 1)),
    rationale TEXT NOT NULL,
    inputs_json TEXT NOT NULL,
    PRIMARY KEY(decision_id, signal_name)
);

CREATE TABLE IF NOT EXISTS order_events (
    id TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL REFERENCES decisions(id),
    order_id TEXT,
    event_type TEXT NOT NULL,
    status TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    integrity_hash TEXT NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_order_events_decision
    ON order_events(decision_id, occurred_at);

CREATE INDEX IF NOT EXISTS idx_order_events_order
    ON order_events(order_id, occurred_at);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    key TEXT PRIMARY KEY,
    decision_date TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS performance_daily (
    as_of TEXT PRIMARY KEY,
    cyclequant_value TEXT NOT NULL,
    btc_buy_hold_value TEXT NOT NULL,
    cash_value TEXT NOT NULL,
    ma200_value TEXT,
    btc_price TEXT NOT NULL,
    btc_exposure INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS market_snapshots_no_update
BEFORE UPDATE ON market_snapshots
BEGIN SELECT RAISE(ABORT, 'market snapshots are immutable'); END;

CREATE TRIGGER IF NOT EXISTS market_snapshots_no_delete
BEFORE DELETE ON market_snapshots
BEGIN SELECT RAISE(ABORT, 'market snapshots are immutable'); END;

CREATE TRIGGER IF NOT EXISTS decisions_no_update
BEFORE UPDATE ON decisions
BEGIN SELECT RAISE(ABORT, 'decision records are immutable'); END;

CREATE TRIGGER IF NOT EXISTS decisions_no_delete
BEFORE DELETE ON decisions
BEGIN SELECT RAISE(ABORT, 'decision records are immutable'); END;

CREATE TRIGGER IF NOT EXISTS decision_signals_no_update
BEFORE UPDATE ON decision_signals
BEGIN SELECT RAISE(ABORT, 'decision signals are immutable'); END;

CREATE TRIGGER IF NOT EXISTS decision_signals_no_delete
BEFORE DELETE ON decision_signals
BEGIN SELECT RAISE(ABORT, 'decision signals are immutable'); END;

CREATE TRIGGER IF NOT EXISTS order_events_no_update
BEFORE UPDATE ON order_events
BEGIN SELECT RAISE(ABORT, 'order events are immutable'); END;

CREATE TRIGGER IF NOT EXISTS order_events_no_delete
BEFORE DELETE ON order_events
BEGIN SELECT RAISE(ABORT, 'order events are immutable'); END;
