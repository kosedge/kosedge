"""NCAAM Lab fair engine — fail-closed joins + KenPom leakage as-of checks."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import polars as pl
import pytest

WEB_ROOT = Path(__file__).resolve().parent.parent
SRC = WEB_ROOT / "src"
for p in (str(WEB_ROOT), str(SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

from ncaam_lab.fair_b2 import compute_fair_b2
from ncaam_lab.kenpom_asof import (
    assert_no_kenpom_leakage,
    attach_kenpom_asof,
    load_kenpom_snapshot_archive,
)
from ncaam_lab.protocol import ContinuityState, classify_tip
from ncaam_lab.schedule_sot_d import build_lab_game_set, open_snapshot_honest_dates


def _mini_odds() -> pl.DataFrame:
    """Book-grain odds rows for two events (Train-A tip window)."""
    rows = []
    # Resolvable: Purdue vs Duke
    for book in ("draftkings", "fanduel"):
        rows.append(
            {
                "event_id": "evt_ok_1",
                "home_team": "Purdue Boilermakers",
                "away_team": "Duke Blue Devils",
                "commence_time": "2022-12-10T00:00:00Z",
                "book": book,
                "open_spread_home": -2.5,
                "close_spread_home": -3.0,
                "open_total": 140.0,
                "close_total": 141.5,
            }
        )
    # Fail-closed: bare Miami (omit) vs Purdue
    rows.append(
        {
            "event_id": "evt_omit_miami",
            "home_team": "Miami",
            "away_team": "Purdue Boilermakers",
            "commence_time": "2022-12-11T00:00:00Z",
            "book": "draftkings",
            "open_spread_home": 1.0,
            "close_spread_home": 1.5,
            "open_total": 145.0,
            "close_total": 146.0,
        }
    )
    # Outside Train-A cut (still in universe) — should drop for cut=train_a
    rows.append(
        {
            "event_id": "evt_outside_train",
            "home_team": "Purdue Boilermakers",
            "away_team": "Duke Blue Devils",
            "commence_time": "2023-11-10T00:00:00Z",
            "book": "draftkings",
            "open_spread_home": -4.0,
            "close_spread_home": -4.5,
            "open_total": 150.0,
            "close_total": 151.0,
        }
    )
    # Miami FL vs Miami OH — must not collapse; both resolve
    rows.append(
        {
            "event_id": "evt_miami_split",
            "home_team": "Miami Hurricanes",
            "away_team": "Miami (OH) RedHawks",
            "commence_time": "2023-01-15T00:00:00Z",
            "book": "draftkings",
            "open_spread_home": -10.0,
            "close_spread_home": -11.0,
            "open_total": 148.0,
            "close_total": 149.0,
        }
    )
    return pl.DataFrame(rows)


def test_classify_tip_locked_windows() -> None:
    assert classify_tip(date(2022, 11, 7)) == "train_a"
    assert classify_tip(date(2023, 3, 12)) == "train_a"
    assert classify_tip(date(2023, 11, 6)) == "test_a"
    assert classify_tip(date(2024, 1, 28)) == "test_a"
    assert classify_tip(date(2022, 11, 1)) == "universe_path_a"
    assert classify_tip(date(2025, 11, 15)) is None  # 2025 pocket OUT


def test_fail_closed_b7_omit_and_miami_split(tmp_path: Path) -> None:
    open_dir = tmp_path / "open"
    open_dir.mkdir()
    # Honest open snapshot for tip day
    (open_dir / "2022-12-10.json").write_text(
        json.dumps({"timestamp": "2022-12-10T12:00:00Z", "data": []}),
        encoding="utf-8",
    )
    (open_dir / "2023-01-15.json").write_text(
        json.dumps({"timestamp": "2023-01-15T12:00:00Z", "data": []}),
        encoding="utf-8",
    )

    games = build_lab_game_set(_mini_odds(), cut="train_a", open_dir=open_dir)
    ids = set(games["event_id"].to_list())
    assert "evt_ok_1" in ids
    assert "evt_miami_split" in ids
    assert "evt_omit_miami" not in ids  # bare Miami omit
    assert "evt_outside_train" not in ids

    miami = games.filter(pl.col("event_id") == "evt_miami_split").row(0, named=True)
    assert miami["home_team_id"] == "miami fl"
    assert miami["away_team_id"] == "miami oh"
    assert miami["espn_game_id"] is None
    assert miami["schedule_sot"] == "D"
    assert miami["b1_consensus_close_spread"] == pytest.approx(-11.0)


def test_open_timestamp_honesty_filter(tmp_path: Path) -> None:
    open_dir = tmp_path / "open"
    open_dir.mkdir()
    (open_dir / "2022-12-10.json").write_text(
        json.dumps({"timestamp": "2022-12-10T12:00:00Z", "data": []}),
        encoding="utf-8",
    )
    # >7d drift — dishonest
    (open_dir / "2022-12-11.json").write_text(
        json.dumps({"timestamp": "2022-04-05T03:45:00Z", "data": []}),
        encoding="utf-8",
    )
    honest = open_snapshot_honest_dates(open_dir)
    assert "2022-12-10" in honest
    assert "2022-12-11" not in honest


def test_kenpom_asof_no_leakage(tmp_path: Path) -> None:
    snap = tmp_path / "kenpom_snapshots"
    snap.mkdir()
    # Snapshot AFTER tip must never join for tip=2022-12-10
    pl.DataFrame(
        {
            "team_norm": ["purdue", "duke"],
            "adjem": [25.0, 20.0],
            "adjoe": [118.0, 115.0],
            "adjde": [93.0, 95.0],
            "adjtempo": [68.0, 70.0],
            "snapshot_date": ["2022-12-18", "2022-12-18"],
        }
    ).write_parquet(snap / "kenpom_2022-12-18.parquet")
    # Valid prior snapshot
    pl.DataFrame(
        {
            "team_norm": ["purdue", "duke"],
            "adjem": [24.0, 19.0],
            "adjoe": [117.0, 114.0],
            "adjde": [93.5, 95.5],
            "adjtempo": [68.5, 69.5],
            "snapshot_date": ["2022-12-04", "2022-12-04"],
        }
    ).write_parquet(snap / "kenpom_2022-12-04.parquet")

    archive = load_kenpom_snapshot_archive(snap)
    assert archive is not None

    games = pl.DataFrame(
        {
            "event_id": ["e1"],
            "tip_date": [date(2022, 12, 10)],
            "home_ratings_norm": ["purdue"],
            "away_ratings_norm": ["duke"],
        }
    )
    joined = attach_kenpom_asof(games, archive)
    ok, n_viol = assert_no_kenpom_leakage(joined)
    assert ok and n_viol == 0
    row = joined.row(0, named=True)
    assert row["kenpom_as_of_home"] == date(2022, 12, 4)
    assert row["kenpom_as_of_away"] == date(2022, 12, 4)
    assert row["adjem_home"] == pytest.approx(24.0)

    # Inject leakage and ensure detector fires
    leaked = joined.with_columns(pl.lit(date(2022, 12, 18)).alias("kenpom_as_of_home"))
    ok2, n2 = assert_no_kenpom_leakage(leaked)
    assert not ok2 and n2 >= 1


def test_fair_b2_continuity_and_no_silent_ml() -> None:
    games = pl.DataFrame(
        {
            "event_id": ["e1", "e2"],
            "tip_date": [date(2022, 12, 10), date(2022, 12, 10)],
            "adjem_home": [24.0, None],
            "adjem_away": [19.0, 10.0],
            "adjoe_home": [117.0, None],
            "adjde_home": [93.0, None],
            "adjt_home": [68.0, None],
            "adjoe_away": [114.0, None],
            "adjde_away": [95.0, None],
            "adjt_away": [70.0, None],
            "kenpom_as_of_home": [date(2022, 12, 4), None],
            "kenpom_as_of_away": [date(2022, 12, 4), date(2022, 12, 4)],
        }
    )
    out = compute_fair_b2(games, hca=2.8696)
    r0 = out.filter(pl.col("event_id") == "e1").row(0, named=True)
    r1 = out.filter(pl.col("event_id") == "e2").row(0, named=True)

    assert r0["continuity_state"] == ContinuityState.PRIOR.value
    assert r0["fair_spread_home"] == pytest.approx(24.0 - 19.0 + 2.8696)
    assert r0["fair_total"] is not None
    assert r0["fair_total_method"] == "kenpom_adj_oe_de_tempo_v1"
    assert r0["fair_ml_home"] is None
    assert "silent" in (r0["fair_ml_method"] or "")

    assert r1["continuity_state"] == ContinuityState.UNKNOWN.value
    assert r1["fair_spread_home"] is None
    assert ContinuityState.PRIOR.value in out["continuity_state"].to_list()
    assert "SETTLED" not in out["continuity_state"].to_list()


def test_materialize_refuses_product_side_effects(tmp_path: Path) -> None:
    """Smoke: materialize writes only under out_dir; product JSON names untouched."""
    from ncaam_lab.materialize import FORBIDDEN_PRODUCT_PATHS, materialize_lab_fair

    # Build tiny Path A + KenPom under tmp and run materialize
    processed = tmp_path / "processed"
    processed.mkdir()
    open_dir = tmp_path / "open"
    open_dir.mkdir()
    (open_dir / "2022-12-10.json").write_text(
        json.dumps({"timestamp": "2022-12-10T12:00:00Z", "data": []}),
        encoding="utf-8",
    )
    odds = _mini_odds()
    odds_path = processed / "ncaab_historical_odds_open_close.parquet"
    odds.write_parquet(odds_path)

    snap = processed / "kenpom_snapshots"
    snap.mkdir()
    pl.DataFrame(
        {
            "team_norm": ["purdue", "duke", "miami", "miami (oh)"],
            "adjem": [24.0, 19.0, 15.0, 5.0],
            "adjoe": [117.0, 114.0, 110.0, 105.0],
            "adjde": [93.0, 95.0, 95.0, 100.0],
            "adjtempo": [68.0, 70.0, 69.0, 67.0],
            "snapshot_date": ["2022-12-04"] * 4,
        }
    ).write_parquet(snap / "kenpom_2022-12-04.parquet")
    # Also need jan snapshot for miami game tip 2023-01-15
    pl.DataFrame(
        {
            "team_norm": ["purdue", "duke", "miami", "miami (oh)"],
            "adjem": [24.0, 19.0, 15.0, 5.0],
            "adjoe": [117.0, 114.0, 110.0, 105.0],
            "adjde": [93.0, 95.0, 95.0, 100.0],
            "adjtempo": [68.0, 70.0, 69.0, 67.0],
            "snapshot_date": ["2023-01-08"] * 4,
        }
    ).write_parquet(snap / "kenpom_2023-01-08.parquet")

    weights = processed / "ensemble_weights.json"
    weights.write_text(json.dumps({"home_court": 2.8696}), encoding="utf-8")

    out_dir = tmp_path / "lab_out"
    # Sentinels: product files that must remain untouched
    product_dir = tmp_path / "product"
    product_dir.mkdir()
    for name in FORBIDDEN_PRODUCT_PATHS:
        (product_dir / name).write_text("SENTINEL", encoding="utf-8")

    summary = materialize_lab_fair(
        cut="train_a",
        odds_path=odds_path,
        kenpom_snapshots_dir=snap,
        open_dir=open_dir,
        weights_path=weights,
        out_dir=out_dir,
    )
    assert summary["n_with_fair_spread"] >= 1
    assert summary["product_side_effects"] == "none"
    assert summary["kenpom_leakage_ok"] is True
    assert (out_dir / "ncaam-fair-lab-train_a-latest.parquet").exists()
    for name in FORBIDDEN_PRODUCT_PATHS:
        assert (product_dir / name).read_text(encoding="utf-8") == "SENTINEL"
