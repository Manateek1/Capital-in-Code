from __future__ import annotations

import json

import httpx
import pytest

from cyclequant.database import SupabaseDatabase
from cyclequant.indicators import IndicatorEngine
from cyclequant.models import MarketDataBundle, SourceHealth, SourceState


def test_supabase_writer_uses_scoped_headers_and_validates_integrity(daily_bars) -> None:
    stored_snapshots: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["apikey"] == "publishable-test"
        assert request.headers["authorization"] == "Bearer publishable-test"
        assert request.headers["x-cyclequant-write-token"] == "writer-test"
        assert "writer-test" not in str(request.url)
        table = request.url.path.rsplit("/", 1)[-1]
        if table == "cq_decisions":
            return httpx.Response(200, json=[])
        if table == "cq_market_snapshots" and request.method == "POST":
            stored_snapshots.append(json.loads(request.content))
            return httpx.Response(201)
        if table == "cq_market_snapshots":
            snapshot_id = request.url.params.get("id")
            digest = request.url.params.get("integrity_hash")
            if snapshot_id and stored_snapshots:
                row = stored_snapshots[0]
                return httpx.Response(
                    200,
                    json=[
                        {
                            "private_payload": row["private_payload"],
                            "integrity_hash": row["integrity_hash"],
                        }
                    ],
                )
            if digest and stored_snapshots:
                return httpx.Response(200, json=[{"id": stored_snapshots[0]["id"]}])
            return httpx.Response(200, json=[])
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    bundle = MarketDataBundle(
        as_of=daily_bars[-1].timestamp,
        spot_price=daily_bars[-1].close,
        bars=daily_bars,
        sources=[
            SourceHealth(
                name="fixture",
                state=SourceState.FRESH,
                required=True,
                observed_at=daily_bars[-1].timestamp,
            )
        ],
        indicators=IndicatorEngine().compute(daily_bars),
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        database = SupabaseDatabase(
            "https://project.supabase.co",
            "publishable-test",
            "writer-test",
            client=client,
        )
        database.initialize()
        snapshot_id = database.save_market_snapshot(bundle)
        restored = database.get_market_snapshot(snapshot_id)
        duplicate_id = database.save_market_snapshot(bundle)

    assert restored == bundle
    assert duplicate_id == snapshot_id
    assert len(stored_snapshots) == 1


def test_supabase_writer_rejects_non_https_url() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        SupabaseDatabase("http://project.supabase.co", "publishable-test", "writer-test")
