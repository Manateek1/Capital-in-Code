from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import uvicorn

from cyclequant.api import create_app
from cyclequant.broker import AlpacaPaperBroker, SimulatedPaperBroker
from cyclequant.config import Settings, load_settings
from cyclequant.data.aggregator import build_default_pipeline, build_http_client
from cyclequant.database import Database, Repository, SupabaseDatabase
from cyclequant.logging import configure_logging
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
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise RuntimeError(
                "Supabase mode requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY"
            )
        database: Repository = SupabaseDatabase(
            settings.supabase_url,
            settings.supabase_service_role_key,
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
