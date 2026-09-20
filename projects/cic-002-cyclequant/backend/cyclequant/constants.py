from decimal import Decimal

BTC_USD = "BTC/USD"
ALPACA_PAPER_BASE_URL = "https://paper-api.alpaca.markets"
ALLOWED_EXPOSURES = (0, 25, 50, 75, 100)
STARTING_CAPITAL = Decimal("1000.00")
STRATEGY_VERSION = "2026.1"

DEFAULT_SIGNAL_WEIGHTS = {
    "valuation": 0.25,
    "trend": 0.25,
    "drawdown": 0.15,
    "onchain": 0.15,
    "macro": 0.10,
    "news": 0.10,
}
