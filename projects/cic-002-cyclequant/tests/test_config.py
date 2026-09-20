from cyclequant.config import Settings
from cyclequant.constants import ALPACA_PAPER_BASE_URL


def test_settings_are_safe_by_default() -> None:
    settings = Settings(_env_file=None)
    assert settings.trading_enabled is False
    assert settings.broker_mode == "simulated"
    assert settings.alpaca_base_url == ALPACA_PAPER_BASE_URL
    assert sum(settings.signal_weights.values()) == 1.0
