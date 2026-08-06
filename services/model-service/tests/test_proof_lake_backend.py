"""Tests for proof lake backend resolution and JSONL roundtrip."""

from __future__ import annotations

import json
import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.services.proof_layer.core import ProjectionLog, log_projection, record_close
from src.services.proof_layer.proof_lake import (
    JsonlLakeBackend,
    ProofLakeError,
    resolve_backend_name,
    reset_lake_cache,
)


@pytest.fixture(autouse=True)
def _reset_cache(monkeypatch):
    reset_lake_cache()
    monkeypatch.setenv("PROOF_LAKE_BACKEND", "jsonl")
    monkeypatch.delenv("PROJECTION_LOG_BACKEND", raising=False)
    yield
    reset_lake_cache()


def test_resolve_backend_auto_without_db(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("PROOF_LAKE_BACKEND", "auto")
    assert resolve_backend_name() == "jsonl"


def test_resolve_backend_auto_with_db(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:y@localhost/db")
    monkeypatch.setenv("PROOF_LAKE_BACKEND", "auto")
    assert resolve_backend_name() == "postgres"


def test_resolve_backend_legacy_projection_log_backend(monkeypatch):
    monkeypatch.delenv("PROOF_LAKE_BACKEND", raising=False)
    monkeypatch.setenv("PROJECTION_LOG_BACKEND", "postgres")
    assert resolve_backend_name() == "postgres"


def test_jsonl_roundtrip_upsert_get_list(tmp_path):
    lake = JsonlLakeBackend(tmp_path / "lake")
    record = ProjectionLog(
        id="11111111-1111-1111-1111-111111111111",
        sport="nfl",
        market_type="game",
        game_key="2026-W01-BUF@KC",
        season=2026,
        week=1,
        home_team="KC",
        away_team="BUF",
        engine_version="test-v1",
        projected_at="2026-08-06T12:00:00Z",
        model_spread_home=-3.0,
        model_total=48.0,
    )
    saved = lake.upsert(record)
    assert saved.storage == "jsonl"

    loaded = lake.get(record.id)
    assert loaded is not None
    assert loaded.sport == "nfl"
    assert loaded.model_spread_home == -3.0

    updated = ProjectionLog.from_dict({**record.to_dict(), "model_total": 49.0})
    lake.upsert(updated)
    assert lake.count() == 1
    reloaded = lake.get(record.id)
    assert reloaded is not None
    assert reloaded.model_total == 49.0

    listed = lake.list_records(sport="nfl", limit=10)
    assert len(listed) == 1


def test_jsonl_persists_to_disk(tmp_path):
    lake_dir = tmp_path / "persist"
    rec = log_projection(
        {
            "sport": "cfb",
            "home_team": "ALA",
            "away_team": "UGA",
            "season": 2026,
            "week": 1,
            "spread_home": -2.5,
            "expected_total": 52.0,
        },
        sport="cfb",
        lake_dir=lake_dir,
    )
    path = lake_dir / "projections.jsonl"
    assert path.exists()
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["id"] == rec.id

    closed = record_close(rec.id, close_spread_home=-3.0, lake_dir=lake_dir)
    assert closed is not None
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["close_spread_home"] == -3.0


def test_projection_log_serialize_roundtrip():
    raw = {
        "id": "22222222-2222-2222-2222-222222222222",
        "sport": "nfl",
        "market_type": "game",
        "game_key": "2026-W02-SF@DAL",
        "season": 2026,
        "week": 2,
        "home_team": "DAL",
        "away_team": "SF",
        "engine_version": "nfl-v1",
        "projected_at": "2026-08-06T14:00:00Z",
        "model_spread_home": 1.5,
        "model_total": 44.0,
        "drivers": {"summary": "test"},
        "projection": {"game_id": "g99", "source": "test"},
        "storage": "postgres",
    }
    rec = ProjectionLog.from_dict(raw)
    out = rec.to_dict()
    assert out["sport"] == "nfl"
    assert out["drivers"]["summary"] == "test"
    again = ProjectionLog.from_dict(out)
    assert again.id == rec.id
    assert again.projection["game_id"] == "g99"


def test_postgres_backend_requires_database_url(monkeypatch):
    monkeypatch.setenv("PROOF_LAKE_BACKEND", "postgres")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    reset_lake_cache()
    from src.services.proof_layer.proof_lake import PostgresLakeBackend

    backend = PostgresLakeBackend()
    record = ProjectionLog(
        id="33333333-3333-3333-3333-333333333333",
        sport="nfl",
        market_type="game",
        game_key="k",
        season=2026,
        week=1,
        home_team="A",
        away_team="B",
        engine_version="v",
        projected_at="2026-08-06T12:00:00Z",
    )
    with pytest.raises(ProofLakeError):
        backend.upsert(record)
