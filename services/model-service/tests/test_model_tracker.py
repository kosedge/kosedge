"""Unit tests for model pick ledger grading + unit math."""

from __future__ import annotations

import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ["MODEL_TRACKER_BACKEND"] = "jsonl"

from src.services.model_tracker.core import (
    close_pick,
    grade_pick,
    log_pick,
    summary,
)
from src.services.model_tracker.grading import (
    american_odds_profit,
    compute_clv,
    grade_market,
    grade_to_units,
    units_for_tag,
)


def test_units_for_tag_play_lean() -> None:
    assert units_for_tag("PLAY") == 1.0
    assert units_for_tag("LEAN") == 0.0
    assert units_for_tag("PLAY", explicit_units=2.0) == 2.0
    assert units_for_tag("LEAN", explicit_units=2.0) == 0.0


def test_american_odds_profit_minus_110() -> None:
    assert american_odds_profit(1.0, -110) == round(100 / 110, 6)


def test_grade_to_units_play_win_loss_push_void() -> None:
    win = grade_to_units(tag="PLAY", grade="win", odds_american=-110)
    assert win["units_risked"] == 1.0
    assert win["units_pnl"] == american_odds_profit(1.0, -110)
    assert win["units_won"] > 0

    loss = grade_to_units(tag="PLAY", grade="loss")
    assert loss["units_pnl"] == -1.0
    assert loss["units_lost"] == 1.0

    push = grade_to_units(tag="PLAY", grade="push")
    assert push["units_pnl"] == 0.0

    void = grade_to_units(tag="PLAY", grade="void")
    assert void["units_risked"] == 0.0
    assert void["units_pnl"] == 0.0


def test_lean_never_moves_units() -> None:
    for g in ("win", "loss", "push", "void"):
        u = grade_to_units(tag="LEAN", grade=g)
        assert u["units_pnl"] == 0.0
        assert u["units_won"] == 0.0
        assert u["units_lost"] == 0.0


def test_grade_spread_home_and_away() -> None:
    # Home -3.5, home wins 31-24 (margin +7) → home covers
    g, _ = grade_market(
        market_type="spread",
        side="home",
        line=-3.5,
        home_score=31,
        away_score=24,
    )
    assert g == "win"

    g2, _ = grade_market(
        market_type="spread",
        side="away",
        line=-3.5,
        home_score=31,
        away_score=24,
    )
    assert g2 == "loss"


def test_grade_total_and_moneyline() -> None:
    g, _ = grade_market(
        market_type="total",
        side="over",
        line=50.5,
        home_score=31,
        away_score=24,
    )
    assert g == "win"

    g2, _ = grade_market(
        market_type="moneyline",
        side="away",
        line=None,
        home_score=20,
        away_score=24,
    )
    assert g2 == "win"


def test_compute_clv_spread_and_total() -> None:
    # Bet home -3, close -7 → beat close by 4
    assert compute_clv(
        market_type="spread",
        side="home",
        line_at_publish=-3.0,
        line_at_close=-7.0,
    ) == 4.0
    assert compute_clv(
        market_type="total",
        side="over",
        line_at_publish=50.0,
        line_at_close=47.0,
    ) == -3.0


def test_log_close_grade_summary_play_and_lean(tmp_path) -> None:
    lake = tmp_path / "tracker"

    play = log_pick(
        {
            "sport": "cfb",
            "season": 2026,
            "week": 0,
            "home_team": "TCU",
            "away_team": "UNC",
            "market_type": "spread",
            "side": "home",
            "line_at_publish": -3.5,
            "tag": "PLAY",
            "engine_version": "cfb-season-engine-v0.9-inseason",
            "edge_pts": 4.2,
            "created_by": "desk",
            "source": "manual",
        },
        lake_dir=lake,
    )
    assert play["units"] == 1.0
    assert play["grade"] == "pending"

    lean = log_pick(
        {
            "sport": "cfb",
            "season": 2026,
            "week": 0,
            "home_team": "USC",
            "away_team": "SJSU",
            "market_type": "spread",
            "side": "home",
            "line_at_publish": -21.5,
            "tag": "LEAN",
            "engine_version": "cfb-season-engine-v0.9-inseason",
        },
        lake_dir=lake,
    )
    assert lean["units"] == 0.0

    closed = close_pick(play["id"], line_at_close=-6.5, lake_dir=lake)
    assert closed is not None
    assert closed["clv"] == 3.0

    graded_play = grade_pick(
        play["id"], home_score=31, away_score=24, lake_dir=lake
    )
    assert graded_play is not None
    assert graded_play["grade"] == "win"
    assert graded_play["units_pnl"] > 0

    graded_lean = grade_pick(
        lean["id"], home_score=42, away_score=10, lake_dir=lake
    )
    assert graded_lean is not None
    assert graded_lean["grade"] == "win"
    assert graded_lean["units_pnl"] == 0.0

    s = summary(sport="cfb", season=2026, lake_dir=lake)
    assert s["ok"] is True
    assert s["plays"]["wins"] == 1
    assert s["leans"]["wins"] == 1
    assert abs(s["units"]["units_net"] - float(graded_play["units_pnl"])) < 1e-3
    assert abs(
        s["unit_curve"][-1]["cumulative_units"] - float(graded_play["units_pnl"])
    ) < 1e-3
    assert s["by_engine"]["cfb-season-engine-v0.9-inseason"]["n"] == 2


def test_push_and_void_units(tmp_path) -> None:
    lake = tmp_path / "tracker2"
    play = log_pick(
        {
            "sport": "nfl",
            "season": 2026,
            "week": 1,
            "home_team": "KC",
            "away_team": "BUF",
            "market_type": "spread",
            "side": "home",
            "line_at_publish": -3.0,
            "tag": "PLAY",
        },
        lake_dir=lake,
    )
    # Exact cover → push
    graded = grade_pick(play["id"], home_score=24, away_score=21, lake_dir=lake)
    assert graded["grade"] == "push"
    assert graded["units_pnl"] == 0.0

    voided = log_pick(
        {
            "sport": "nfl",
            "season": 2026,
            "week": 1,
            "home_team": "DAL",
            "away_team": "NYG",
            "market_type": "spread",
            "side": "home",
            "line_at_publish": -3.5,
            "tag": "PLAY",
        },
        lake_dir=lake,
    )
    g2 = grade_pick(voided["id"], grade="void", lake_dir=lake)
    assert g2["grade"] == "void"
    assert g2["units_pnl"] == 0.0


def test_route_handlers_status_log_grade(tmp_path, monkeypatch) -> None:
    """Exercise route callables without booting full model-service app."""
    os.environ["MODEL_TRACKER_BACKEND"] = "jsonl"
    monkeypatch.setenv("MODEL_TRACKER_BACKEND", "jsonl")
    monkeypatch.setenv("MODEL_TRACKER_LOG_DIR", str(tmp_path / "http_tracker"))

    # Import module file directly to avoid routes package pulling mlb/db.
    import importlib.util
    from pathlib import Path
    from types import SimpleNamespace

    route_path = (
        Path(__file__).resolve().parents[1] / "src" / "routes" / "model_tracker.py"
    )
    spec = importlib.util.spec_from_file_location(
        "model_tracker_routes_under_test", route_path
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    st = mod.tracker_status()
    assert st["ok"] is True
    assert st["unit_rules"]["PLAY"] == 1.0

    sports = mod.tracker_sports()
    assert "cfb" in sports["sports"]

    body = SimpleNamespace(
        model_dump=lambda exclude_none=True: {
            "sport": "cfb",
            "season": 2026,
            "week": 0,
            "home_team": "ALA",
            "away_team": "UGA",
            "market_type": "spread",
            "side": "away",
            "line_at_publish": -7.5,
            "tag": "PLAY",
            "engine_version": "test-engine",
            "created_by": "desk",
            "source": "manual",
            "odds_american": -110,
        }
    )
    created = mod.tracker_log_pick(body)
    assert created["ok"] is True
    pid = created["pick"]["id"]

    closed = mod.tracker_close_pick(
        pid, SimpleNamespace(line_at_close=-3.5, source="manual")
    )
    assert closed["ok"] is True
    assert closed["pick"]["clv"] is not None

    graded = mod.tracker_grade_pick(
        pid,
        SimpleNamespace(
            home_score=20, away_score=24, grade=None, source="manual"
        ),
    )
    assert graded["ok"] is True
    assert graded["pick"]["grade"] in {"win", "loss", "push"}

    summ = mod.tracker_summary(
        sport="cfb", season=None, week=None, engine_version=None, limit=1000
    )
    assert summ["ok"] is True

    dry = mod.tracker_cfb_import_kei(
        SimpleNamespace(weeks=[0], tags=["PLAY", "LEAN"], dry_run=True)
    )
    assert dry["ok"] is True
