from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from cyclequant.config import Settings, load_settings
from cyclequant.database import Database, Repository
from cyclequant.reporting import build_dashboard_payload


def create_app(settings: Settings | None = None, database: Repository | None = None) -> FastAPI:
    runtime_settings = settings or load_settings()
    runtime_database = database or Database(runtime_settings.database_path)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        runtime_database.initialize()
        yield

    app = FastAPI(
        title="CycleQuant read-only API",
        version="0.1.0",
        description="Auditable paper-allocation research data. No order-entry endpoints.",
        lifespan=lifespan,
    )
    app.state.database = runtime_database
    app.add_middleware(
        CORSMiddleware,
        allow_origins=runtime_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Accept", "Content-Type"],
    )

    @app.get("/health")
    def health() -> dict[str, Any]:
        decisions = runtime_database.list_decisions(limit=1)
        return {
            "status": "ok",
            "service": "cyclequant-read-only-api",
            "latest_decision_at": decisions[0].timestamp if decisions else None,
        }

    @app.get("/api/v1/dashboard")
    def dashboard() -> dict[str, Any]:
        return build_dashboard_payload(runtime_database)

    @app.get("/api/v1/decisions")
    def decisions(limit: int = Query(default=100, ge=1, le=1000)) -> list[dict[str, Any]]:
        return [
            item.model_dump(mode="json") for item in runtime_database.list_decisions(limit=limit)
        ]

    @app.get("/api/v1/decisions/{decision_id}")
    def decision_detail(decision_id: str) -> dict[str, Any]:
        decision = runtime_database.get_decision(decision_id)
        if decision is None:
            raise HTTPException(status_code=404, detail="Decision not found")
        return {
            "decision": decision.model_dump(mode="json"),
            "order_events": [
                item.model_dump(mode="json")
                for item in runtime_database.list_order_events(decision_id)
            ],
            "market_snapshot": (
                snapshot.model_dump(mode="json")
                if (snapshot := runtime_database.get_market_snapshot(decision.market_snapshot_id))
                else None
            ),
        }

    return app


app = create_app()
