from __future__ import annotations

import os
from datetime import date
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

import src.services.mlb_lineup_sp_snapshots as snaps
import src.services.mlb_park_orientation as park
import src.services.mlb_pitch_matchup as pitch
import src.services.mlb_simulator as mlb_sim
from src.services.mlb_simulator import MlbGameInputs, simulate_mlb_game


def test_lineup_sp_snapshot_late_info_and_persist(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(snaps, "LAKE_DIR", tmp_path)
    snap = snaps.build_snapshot(
        game_id="g1",
        hours_to_first_pitch=2.5,
        known_home=9,
        known_away=9,
        sp_home="A",
        sp_away="B",
        lineup_confirmed=True,
    )
    path = snaps.persist_snapshot(snap)
    assert path.exists()
    loaded = snaps.load_snapshots("g1")
    assert len(loaded) == 1
    assert snaps.is_late_info_snapshot(loaded[0], max_hours=3.0)
    assert not snaps.is_late_info_snapshot(loaded[0], max_hours=1.0)

    early = snaps.reconstruct_densify_snapshot(
        game_id="g2",
        hours_to_first_pitch=12.0,
        known_home=9,
        known_away=9,
        sp_home="A",
        sp_away="B",
        lineup_confirmed=False,
        persist=True,
    )
    assert early.known_home <= 3
    assert not snaps.is_late_info_snapshot(early, max_hours=3.0)


def test_pitch_matchup_flag_moves_win_prob() -> None:
    prior = pitch.get_pitch_matchup_enabled()
    arsenal_soft = {
        "pitches": 400.0,
        "hard_pct": 0.50,
        "break_pct": 0.40,
        "soft_pct": 0.10,
        "break_whiff_pct": 0.22,
        "hard_barrel_pct": 0.05,
    }
    arsenal_meat = {
        "pitches": 400.0,
        "hard_pct": 0.60,
        "break_pct": 0.25,
        "soft_pct": 0.15,
        "break_whiff_pct": 0.10,
        "hard_barrel_pct": 0.14,
    }
    weak = MlbGameInputs(
        game_id="pm-weak",
        home_team="A",
        away_team="B",
        offense_split_home=0.96,
        recent_form_index_home=0.95,
        pitcher_arsenal_away=arsenal_soft,
        starter_firmness_away=0.95,
    )
    power = MlbGameInputs(
        game_id="pm-power",
        home_team="A",
        away_team="B",
        offense_split_home=1.08,
        recent_form_index_home=1.06,
        pitcher_arsenal_away=arsenal_meat,
        starter_firmness_away=0.95,
    )
    try:
        pitch.apply_pitch_matchup_flag(False)
        off_w = simulate_mlb_game(weak, simulations=1800, seed=7)["markets"]["fg_home_win_prob"]
        off_p = simulate_mlb_game(power, simulations=1800, seed=7)["markets"]["fg_home_win_prob"]
        pitch.apply_pitch_matchup_flag(True)
        on_w = simulate_mlb_game(weak, simulations=1800, seed=7)["markets"]["fg_home_win_prob"]
        on_p = simulate_mlb_game(power, simulations=1800, seed=7)["markets"]["fg_home_win_prob"]
        # Flag on should separate weak-vs-whiff-break from power-vs-barrels more than off.
        assert abs(on_p - on_w) >= abs(off_p - off_w) - 1e-9
        assert on_w != off_w or on_p != off_p
    finally:
        pitch.apply_pitch_matchup_flag(prior)


def test_arsenal_from_stuff_shape_asof_safe() -> None:
    shaped = pitch.arsenal_from_stuff_shape(
        {
            "pitches": 500.0,
            "whiff_pct": 0.14,
            "barrel_pct": 0.09,
            "chase_pct": 0.31,
        }
    )
    assert shaped["pitches"] == 500.0
    assert 0.2 <= shaped["break_pct"] <= 0.5
    pitch.set_arsenal_metrics_override(
        season=2026,
        pitcher_id=1,
        as_of=date(2026, 6, 1),
        metrics={**shaped, "source": "test"},
    )
    got = pitch.get_pitcher_arsenal_as_of(1, as_of=date(2026, 6, 1), fetch_if_missing=False)
    assert got is not None
    assert float(got["pitches"]) == 500.0


def test_park_rel_wind_totals_only_leaves_ml() -> None:
    prior_flags = mlb_sim.get_stack_ablation_flags()
    prior_wind = park.get_totals_park_rel_wind_enabled()
    inputs = MlbGameInputs(
        game_id="wind-totals",
        home_team="Cubs",
        away_team="Cards",
        home_abbr="CHC",
        weather_wind_dir_deg=210.0,  # from SSW → to NNE; CHC CF ~30°
        weather_wind_mph=18.0,
        weather_temp_f=78.0,
        park_factor_runs=1.0,
        weather_reliability=1.0,
    )
    try:
        park.apply_totals_park_rel_wind_flag(False)
        off = simulate_mlb_game(inputs, simulations=2000, seed=11)
        park.apply_totals_park_rel_wind_flag(True)
        on = simulate_mlb_game(inputs, simulations=2000, seed=11)
        # ML / spreads identical (totals-only post-sim).
        assert off["markets"]["fg_home_win_prob"] == on["markets"]["fg_home_win_prob"]
        assert off["markets"]["fair_fg_spread_home"] == on["markets"]["fair_fg_spread_home"]
        # Totals move when park-rel aligns out/in.
        assert off["markets"]["fg_total_mean"] != on["markets"]["fg_total_mean"]
        assert on["diagnostics"]["totals_park_rel_wind_mul"] != 1.0
    finally:
        park.apply_totals_park_rel_wind_flag(prior_wind)
        mlb_sim.apply_stack_ablation_flags(
            matchup_mul_enabled=prior_flags["matchup_mul_enabled"],
            weather_wind_dir_mul_enabled=prior_flags["weather_wind_dir_mul_enabled"],
        )


def test_wind_to_and_cf_relative() -> None:
    assert abs(park.wind_to_deg(0.0) - 180.0) < 1e-9
    # Wind from south (180) → to north (0); CF bearing 0 ⇒ out to CF.
    rel = park.relative_to_cf_deg(wind_from_deg=180.0, cf_bearing_deg=0.0)
    assert rel < 1.0
    # Wind from north (0) → to south (180); CF 0 ⇒ in from CF.
    rel_in = park.relative_to_cf_deg(wind_from_deg=0.0, cf_bearing_deg=0.0)
    assert rel_in > 179.0
