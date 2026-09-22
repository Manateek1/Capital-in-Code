from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import uvicorn

from cyclequant.api import create_app
from cyclequant.broker import (
    AlpacaPaperBroker,
    SimulatedPaperBroker,
    capture_paper_account,
    reconcile_decision_order,
)
from cyclequant.config import Settings, load_settings
from cyclequant.data.aggregator import build_default_pipeline, build_http_client
from cyclequant.database import Database, Repository, SupabaseDatabase
from cyclequant.logging import configure_logging
from cyclequant.models import Action, OrderStatus
from cyclequant.news_analysis import GeminiNewsAnalyzer, HeuristicNewsAnalyzer, SafeNewsAnalyzer
from cyclequant.reporting import build_dashboard_payload
from cyclequant.strategy import DailyStrategyRunner


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cyclequant", description="CycleQuant research runner")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("init-db", help="Initialize the local SQLite schema")
    daily = subcommands.add_parser("daily", help="Run one idempotent UTC evaluation")
    daily.add_argument("--as-of", help="ISO-8601 evaluation timestamp (defaults to now)")
    daily.add_argument(
        "--dry-run",
        action="store_true",
        help="Force trading off while still creating a decision record",
    )
    subcommands.add_parser(
        "sync-broker",
        help="Publish a sanitized snapshot of the current paper broker state",
    )
    health = subcommands.add_parser(
        "health", help="Check that the paper system and public mirror are current"
    )
    health.add_argument("--max-age-minutes", type=int, default=120)
    health.add_argument("--require-today", action="store_true")
    serve = subcommands.add_parser("serve", help="Run the read-only API")
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)
    export = subcommands.add_parser("export-dashboard", help="Write static dashboard JSON")
    export.add_argument("--output", type=Path, required=True)
    return parser


def _parse_as_of(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _database(settings: Settings) -> Repository:
    if settings.database_backend == "supabase":
        if (
            not settings.supabase_url
            or not settings.supabase_publishable_key
            or not settings.supabase_write_token
        ):
            raise RuntimeError(
                "Supabase mode requires SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, "
                "and CYCLEQUANT_WRITE_TOKEN"
            )
        database: Repository = SupabaseDatabase(
            settings.supabase_url,
            settings.supabase_publishable_key,
            settings.supabase_write_token,
            timeout_seconds=settings.request_timeout_seconds,
        )
    else:
        database = Database(settings.database_path)
    database.initialize()
    return database


async def _daily(settings: Settings, database: Repository, as_of: datetime) -> int:
    async with build_http_client(settings) as client:
        pipeline = build_default_pipeline(settings, client)
        if settings.news_analyzer == "gemini" and settings.gemini_api_key:
            analyzer = SafeNewsAnalyzer(
                GeminiNewsAnalyzer(
                    client,
                    settings.gemini_api_key,
                    model=settings.gemini_model,
                    retries=settings.request_retries,
                )
            )
        else:
            analyzer = HeuristicNewsAnalyzer()
        broker = _broker(settings, client)
        result = await DailyStrategyRunner(
            settings=settings,
            database=database,
            pipeline=pipeline,
            news_analyzer=analyzer,
            broker=broker,
        ).run(as_of)
    print(
        json.dumps(
            {
                "created": result.created,
                "decision_id": result.decision.id,
                "decision_date": result.decision.decision_date.isoformat(),
                "action": result.decision.action.value,
                "target_exposure": result.decision.target_exposure,
                "score": result.decision.signals.total_score,
                "order_status": result.decision.order_status.value,
            },
            separators=(",", ":"),
        )
    )
    return 0


async def _sync_broker(settings: Settings, database: Repository) -> int:
    latest = database.list_decisions(limit=1)
    if not latest:
        raise RuntimeError("A decision must exist before the paper account can be mirrored")
    decision = latest[0]
    async with build_http_client(settings) as client:
        broker = _broker(settings, client)
        if hasattr(broker, "btc_price"):
            broker.btc_price = decision.btc_price
        decision = await reconcile_decision_order(database, broker, decision)
        snapshot = await capture_paper_account(
            settings=settings,
            database=database,
            broker=broker,
            decision=decision,
        )
    print(
        json.dumps(
            {
                "captured_at": snapshot.captured_at.isoformat(),
                "broker_mode": snapshot.broker_mode,
                "connected": snapshot.connected,
                "position_reconciled": snapshot.position_reconciled,
                "latest_order_status": snapshot.latest_order_status.value,
            },
            separators=(",", ":"),
        )
    )
    return 0


def _health(
    settings: Settings,
    database: Repository,
    *,
    max_age_minutes: int,
    require_today: bool,
) -> int:
    if max_age_minutes < 1:
        raise ValueError("max age must be positive")
    now = datetime.now(UTC)
    recent = database.list_decisions(limit=1)
    decision = recent[0] if recent else None
    snapshot = database.latest_paper_account_snapshot()
    checks = {
        "alpaca_paper_mode": settings.broker_mode == "alpaca-paper",
        "trading_switch_enabled": settings.trading_enabled,
        "decision_present": decision is not None,
        "daily_decision_current": not require_today
        or (decision is not None and decision.decision_date == now.date()),
        "broker_mirror_current": snapshot is not None
        and abs((now - snapshot.captured_at).total_seconds()) <= max_age_minutes * 60,
        "paper_account_connected": snapshot is not None
        and snapshot.broker_mode == "alpaca-paper"
        and snapshot.paper_only
        and snapshot.connected,
        "paper_account_healthy": snapshot is not None
        and snapshot.account_status.upper() == "ACTIVE"
        and not snapshot.trading_blocked
        and not snapshot.account_blocked
        and snapshot.crypto_trading_enabled
        and snapshot.trading_enabled,
        "position_reconciled": snapshot is not None and snapshot.position_reconciled,
        "order_healthy": decision is not None
        and snapshot is not None
        and (
            decision.action == Action.HOLD
            or snapshot.latest_order_status == OrderStatus.FILLED
            or (
                snapshot.latest_order_status
                in {OrderStatus.PENDING, OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FILLED}
                and (now - decision.timestamp).total_seconds() < 60 * 60
            )
        ),
    }
    print(
        json.dumps(
            {
                "ok": all(checks.values()),
                "checks": checks,
                "decision_date": decision.decision_date.isoformat() if decision else None,
                "mirror_captured_at": snapshot.captured_at.isoformat() if snapshot else None,
            },
            separators=(",", ":"),
        )
    )
    return 0 if all(checks.values()) else 1


def _broker(settings: Settings, client: httpx.AsyncClient):
    if settings.broker_mode == "simulated":
        return SimulatedPaperBroker()
    if not settings.alpaca_api_key_id or not settings.alpaca_api_secret_key:
        raise RuntimeError("Alpaca paper mode requires ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY")
    return AlpacaPaperBroker(
        client,
        api_key_id=settings.alpaca_api_key_id,
        api_secret_key=settings.alpaca_api_secret_key,
        base_url=settings.alpaca_base_url,
        retries=settings.request_retries,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    settings = load_settings()
    configure_logging(settings.log_level, json_output=settings.log_json)
    database = _database(settings)
    if args.command == "init-db":
        print(f"Initialized {database.description}")
        return 0
    if args.command == "daily":
        if args.dry_run:
            settings.trading_enabled = False
        return asyncio.run(_daily(settings, database, _parse_as_of(args.as_of)))
    if args.command == "sync-broker":
        return asyncio.run(_sync_broker(settings, database))
    if args.command == "health":
        return _health(
            settings,
            database,
            max_age_minutes=args.max_age_minutes,
            require_today=args.require_today,
        )
    if args.command == "serve":
        uvicorn.run(
            create_app(settings, database),
            host=args.host or settings.api_host,
            port=args.port or settings.api_port,
        )
        return 0
    if args.command == "export-dashboard":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(build_dashboard_payload(database), indent=2), encoding="utf-8"
        )
        print(f"Wrote {args.output}")
        return 0
    return 2
