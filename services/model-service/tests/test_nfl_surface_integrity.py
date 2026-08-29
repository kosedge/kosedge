"""NFL surface integrity invariants (TD rates, pack IR, survivor=KEI, PLAY)."""

from __future__ import annotations

from src.services.nfl_player_projection_engine import (
    PlayerFeatureInputs,
    baseline_projection_from_features,
)
from src.services.nfl_prop_edge_policy import classify_prop_tag, evaluate_prop_edge
from src.services.nfl_snap_share_prior import is_out_row
from src.services.nfl_surface_integrity import (
    PASS_TD_YARDS_PER,
    REC_TD_YARDS_PER,
    apply_pack_injury_to_fantasy_rows,
    build_kei_win_prob_map_from_fair_lines,
    enforce_no_play_without_stake,
    overlay_survivor_kei_win_probs,
    pass_tds_from_yards,
    rec_tds_from_yards,
    recouple_player_tds_to_yards,
)


def test_pass_td_yards_rate_constant() -> None:
    assert PASS_TD_YARDS_PER == 115.0
    assert abs(pass_tds_from_yards(4252.0) - 4252.0 / 115.0) < 1e-9


def test_rec_td_yards_rate_constant() -> None:
    assert REC_TD_YARDS_PER == 100.0
    assert abs(rec_tds_from_yards(1791.0) - 17.91) < 1e-9


def test_invariant_1_qb_pass_td_peak_band() -> None:
    """max(QB pass_tds) season projection ∈ [32, 48] for elite starter yards."""
    starter_qb = PlayerFeatureInputs(
        position="QB",
        snap_proxy=0.85,
        route_proxy=0.0,
        target_proxy=0.05,
        rush_share=0.05,
        red_zone_share=0.05,
        qb_dropback_factor=1.0,
        qb_pressure_factor=1.0,
        team_pace_factor=1.0,
        team_pass_rate_factor=1.0,
        availability_confidence=0.95,
        role_confidence=0.80,
        team_snap_share=0.95,
    )
    projection = baseline_projection_from_features(starter_qb)
    season_pass_tds = projection["pass_tds_mean"] * 17
    season_pass_yds = projection["pass_yards_mean"] * 17
    assert 32.0 <= season_pass_tds <= 48.0
    # Yards and TDs share a rate.
    assert abs(season_pass_tds - season_pass_yds / PASS_TD_YARDS_PER) < 0.05


def test_invariant_2_wr_rec_td_peak_and_yards_rate() -> None:
    """max(WR rec_tds) ∈ [12, 20]; rec_tds / (rec_yds/20) not absurdly low."""
    elite_wr1 = PlayerFeatureInputs(
        position="WR",
        snap_proxy=0.6,
        route_proxy=0.46,
        target_proxy=0.27,
        rush_share=0.0,
        red_zone_share=0.20,
        qb_dropback_factor=1.0,
        qb_pressure_factor=1.0,
        team_pace_factor=1.0,
        team_pass_rate_factor=1.0,
        availability_confidence=0.95,
        role_confidence=0.75,
    )
    projection = baseline_projection_from_features(elite_wr1)
    season_rec_tds = projection["rec_tds_mean"] * 17
    season_rec_yds = projection["receiving_yards_mean"] * 17
    assert 12.0 <= season_rec_tds <= 20.0
    assert abs(season_rec_tds - season_rec_yds / REC_TD_YARDS_PER) < 0.05
    rate_per_20 = season_rec_tds / max(1e-9, season_rec_yds / 20.0)
    assert rate_per_20 >= 0.15  # not absurdly low vs yards


def test_invariant_3_pack_ir_zeros_games_and_volume() -> None:
    rows = [
        {
            "player_id": "00-0040130",
            "player_name": "Jayden Higgins",
            "team": "HOU",
            "position": "WR",
            "games_projected": 17,
            "receiving_yards_total": 491.0,
            "rec_tds_total": 0.0,
            "receptions_total": 40.0,
            "pass_yards_total": 0.0,
            "pass_tds_total": 0.0,
            "rush_yards_total": 0.0,
            "rush_tds_total": 0.0,
            "total_points": 80.0,
        },
        {
            "player_id": "00-0036322",
            "player_name": "Ja'Marr Chase",
            "team": "CIN",
            "position": "WR",
            "games_projected": 17,
            "receiving_yards_total": 1791.0,
            "rec_tds_total": 9.7,
            "receptions_total": 120.0,
            "pass_yards_total": 0.0,
            "pass_tds_total": 0.0,
            "rush_yards_total": 0.0,
            "rush_tds_total": 0.0,
            "total_points": 300.0,
        },
    ]
    pack = [
        {
            "team": "HOU",
            "position": "WR",
            "depth_order": 2,
            "player_id": "00-0040130",
            "player_name": "Jayden Higgins",
            "injury_status": "out",
        },
        {
            "team": "CIN",
            "position": "WR",
            "depth_order": 1,
            "player_id": "00-0036322",
            "player_name": "Ja'Marr Chase",
            "injury_status": "healthy",
        },
    ]
    assert is_out_row(pack[0])
    audit = apply_pack_injury_to_fantasy_rows(rows, pack, recouple_tds=True)
    higgins = rows[0]
    chase = rows[1]
    assert higgins["games_projected"] == 0
    assert higgins["receiving_yards_total"] == 0.0
    assert higgins["rec_tds_total"] == 0.0
    assert any(f.get("kind") == "availability" for f in higgins.get("risk_flags") or [])
    assert chase["games_projected"] == 17
    assert abs(chase["rec_tds_total"] - 1791.0 / REC_TD_YARDS_PER) < 1e-6
    assert audit["pack_injury_zeroed"] == 1


def test_invariant_4_survivor_matches_kei_win_prob() -> None:
    payload = {
        "ranked_picks": [
            {"team": "LAC", "win_prob": 0.54, "win_rate": 0.54, "opponent": "ARI"},
            {"team": "ARI", "win_prob": 0.46, "win_rate": 0.46, "opponent": "LAC"},
            {"team": "LAR", "win_prob": 0.66, "win_rate": 0.66, "opponent": "SF"},
            {"team": "SF", "win_prob": 0.34, "win_rate": 0.34, "opponent": "LAR"},
        ],
        "all_teams_week": [
            {"team": "LAC", "win_prob": 0.54, "win_rate": 0.54},
            {"team": "LAR", "win_prob": 0.66, "win_rate": 0.66},
        ],
    }
    lines = [
        {
            "week": 1,
            "home_abbr": "LAC",
            "away_abbr": "ARI",
            "home_win_prob": 0.7522,
            "away_win_prob": 0.2478,
        },
        {
            "week": 1,
            "home_abbr": "LAR",
            "away_abbr": "SF",
            "home_win_prob": 0.6058,
            "away_win_prob": 0.3942,
        },
    ]
    kei = build_kei_win_prob_map_from_fair_lines(lines, week=1)
    overlay_survivor_kei_win_probs(payload, kei)
    by_team = {r["team"]: r for r in payload["ranked_picks"]}
    assert abs(by_team["LAC"]["win_prob"] - 0.7522) < 0.005
    assert abs(by_team["ARI"]["win_prob"] - 0.2478) < 0.005
    assert abs(by_team["LAR"]["win_prob"] - 0.6058) < 0.005
    assert abs(by_team["SF"]["win_prob"] - 0.3942) < 0.005
    assert by_team["LAC"]["win_prob_source"] == "kei_fair_lines"


def test_invariant_5_no_play_when_stake_eligible_false() -> None:
    tag, eligible, reason = enforce_no_play_without_stake("PLAY", False)
    assert tag == "WATCH"
    assert eligible is False
    assert reason == "play_requires_stake_eligible"

    edge = evaluate_prop_edge(
        model_mean=53.0,
        model_std=18.0,
        line=84.5,
        market_over_price=-110,
        market_under_price=-110,
        market_key="rec_yds",
        position="WR",
        role_confidence=0.8,
        availability_confidence=0.9,
    )
    # Research highlight must not print PLAY while stake_eligible is false.
    assert edge["stake_eligible"] is False
    assert edge["tag"] != "PLAY"


def test_invariant_5_classify_prop_tag_watch_not_play() -> None:
    tag = classify_prop_tag(
        market_key="rec_yds",
        position="WR",
        z_over=0.97,
        edge_over=0.06,
        edge_under=-0.06,
        market_joined=True,
        model_mean=82.0,
        line=64.5,
        role_confidence=0.8,
        availability_confidence=0.9,
    )
    assert tag["tag"] == "WATCH"
    assert tag["stake_eligible"] is False


def test_invariant_7_higgins_recouple_illegal_zero_td_row() -> None:
    """One Higgins HOU row: after IR accept, not 491 yards / 0 TD."""
    row = {
        "player_name": "Jayden Higgins",
        "team": "HOU",
        "games_projected": 17,
        "receiving_yards_total": 491.0,
        "rec_tds_total": 0.0,
        "pass_yards_total": 0.0,
        "pass_tds_total": 0.0,
    }
    pack = [
        {
            "team": "HOU",
            "position": "WR",
            "player_name": "Jayden Higgins",
            "player_id": "00-0040130",
            "injury_status": "out",
            "depth_order": 2,
        }
    ]
    apply_pack_injury_to_fantasy_rows([row], pack, recouple_tds=True)
    assert row["games_projected"] == 0
    assert row["receiving_yards_total"] == 0.0
    assert row["rec_tds_total"] == 0.0


def test_recouple_preserves_shared_rate_on_stale_csv() -> None:
    row = {
        "pass_yards_total": 4456.7,
        "pass_tds_total": 16.559,  # stale season-engine undercount
        "receiving_yards_total": 1550.2,
        "rec_tds_total": 6.36,
    }
    recouple_player_tds_to_yards(row)
    assert abs(row["pass_tds_total"] - 4456.7 / 115.0) < 1e-3
    assert abs(row["rec_tds_total"] - 1550.2 / 100.0) < 1e-3
