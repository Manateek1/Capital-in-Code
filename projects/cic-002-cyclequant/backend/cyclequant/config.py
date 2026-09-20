from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from cyclequant.constants import ALPACA_PAPER_BASE_URL, DEFAULT_SIGNAL_WEIGHTS


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(
        env_prefix="CQ_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    database_backend: Literal["sqlite", "supabase"] = "sqlite"
    database_path: Path = Path("data/cyclequant.db")
    kill_switch_path: Path = Path("data/KILL_SWITCH")
    log_level: str = "INFO"
    log_json: bool = True

    trading_enabled: bool = False
    broker_mode: Literal["simulated", "alpaca-paper"] = "simulated"
    alpaca_base_url: str = ALPACA_PAPER_BASE_URL
    alpaca_data_url: str = "https://data.alpaca.markets"
    alpaca_api_key_id: str | None = Field(default=None, validation_alias="ALPACA_API_KEY_ID")
    alpaca_api_secret_key: str | None = Field(
        default=None, validation_alias="ALPACA_API_SECRET_KEY"
    )

    data_max_age_hours: int = Field(default=36, ge=1, le=168)
    history_days: int = Field(default=4000, ge=250, le=7000)
    request_timeout_seconds: float = Field(default=20.0, ge=1.0, le=120.0)
    request_retries: int = Field(default=3, ge=0, le=6)

    fred_csv_base_url: str = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    etf_flows_url: str | None = None

    news_analyzer: Literal["heuristic", "gemini"] = "heuristic"
    gemini_model: str = "gemini-3.8-flash"
    gemini_api_key: str | None = Field(default=None, validation_alias="GEMINI_API_KEY")

    confirmation_days: int = Field(default=2, ge=1, le=7)
    hysteresis_points: float = Field(default=5.0, ge=0.0, le=20.0)
    max_allocation_step: int = Field(default=25)
    initial_exposure: int = Field(default=0)
    signal_weights: dict[str, float] = Field(default_factory=lambda: DEFAULT_SIGNAL_WEIGHTS.copy())

    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://127.0.0.1:5173", "http://localhost:5173"]
    )

    supabase_url: str | None = Field(default=None, validation_alias="SUPABASE_URL")
    supabase_service_role_key: str | None = Field(
        default=None, validation_alias="SUPABASE_SERVICE_ROLE_KEY"
    )

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        return value.upper()

    @field_validator("alpaca_base_url")
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("max_allocation_step")
    @classmethod
    def validate_allocation_step(cls, value: int) -> int:
        if value not in {25, 50, 75, 100}:
            raise ValueError("max_allocation_step must use a positive 25-point increment")
        return value

    @field_validator("initial_exposure")
    @classmethod
    def validate_initial_exposure(cls, value: int) -> int:
        if value not in {0, 25, 50, 75, 100}:
            raise ValueError("initial_exposure must use a 25-point increment")
        return value

    @field_validator("signal_weights")
    @classmethod
    def validate_signal_weights(cls, value: dict[str, float]) -> dict[str, float]:
        expected = set(DEFAULT_SIGNAL_WEIGHTS)
        if set(value) != expected:
            raise ValueError(f"signal_weights must contain exactly: {sorted(expected)}")
        if any(weight < 0 for weight in value.values()):
            raise ValueError("signal weights cannot be negative")
        total = sum(value.values())
        if abs(total - 1.0) > 1e-9:
            raise ValueError("signal weights must sum to 1.0")
        return value

    def resolve_path(self, path: Path, project_root: Path | None = None) -> Path:
        if path.is_absolute():
            return path
        return (project_root or Path.cwd()) / path


def load_settings() -> Settings:
    return Settings()
