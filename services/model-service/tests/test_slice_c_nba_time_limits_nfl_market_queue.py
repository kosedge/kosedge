"""#5 R1 Slice C-fix: NBA time limits + NFL market-history queue isolation."""

from __future__ import annotations

import ast
import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from src.celery_app import QUEUE_MODELS, QUEUE_NFL_MARKET, celery_app, celery_healthcheck
from src.celerybeat_schedule import beat_schedule

_TASKS_PY = Path(__file__).resolve().parents[1] / "src" / "tasks.py"


def _task_decorator_kwargs(fn_name: str) -> dict:
    tree = ast.parse(_TASKS_PY.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name != fn_name:
            continue
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call):
                return {
                    kw.arg: ast.literal_eval(kw.value)
                    for kw in dec.keywords
                    if kw.arg is not None
                }
    raise AssertionError(f"task decorator not found for {fn_name}")


def test_nba_context_matches_wnba_context_time_limits() -> None:
    # pull_wnba_context_snapshot: soft_time_limit=120, time_limit=180
    kwargs = _task_decorator_kwargs("pull_nba_context_snapshot")
    assert kwargs["soft_time_limit"] == 120
    assert kwargs["time_limit"] == 180


def test_nba_daily_cycle_matches_wnba_season_ingest_time_limits() -> None:
    # pull_wnba_season_ingest / run_wnba_phase2_calibrate: soft=1800, hard=2100
    kwargs = _task_decorator_kwargs("run_nba_daily_cycle")
    assert kwargs["soft_time_limit"] == 1800
    assert kwargs["time_limit"] == 2100


def test_materialize_nfl_market_history_routes_to_nfl_market_queue() -> None:
    routes = celery_app.conf.task_routes
    route = routes["src.tasks.materialize_nfl_market_history"]
    assert route["queue"] == QUEUE_NFL_MARKET
    assert route["routing_key"] == QUEUE_NFL_MARKET
    assert QUEUE_NFL_MARKET == "nfl_market"
    assert QUEUE_NFL_MARKET != QUEUE_MODELS


def test_beat_materialize_entries_use_nfl_market_queue() -> None:
    for name in (
        "materialize-nfl-market-history-3am-refresh",
        "materialize-nfl-market-history-hourly",
    ):
        entry = beat_schedule[name]
        assert entry["options"]["queue"] == QUEUE_NFL_MARKET, name


def test_celery_healthcheck_exposes_nfl_market_queue() -> None:
    payload = celery_healthcheck()
    assert payload["queues"]["nfl_market"] == QUEUE_NFL_MARKET
    names = {q.name for q in celery_app.conf.task_queues}
    assert QUEUE_NFL_MARKET in names


def test_worker_dockerfile_default_queues_include_nfl_market() -> None:
    dockerfile = Path(__file__).resolve().parents[1] / "Dockerfile"
    text = dockerfile.read_text(encoding="utf-8")
    assert "default,odds,models,nfl_market" in text
