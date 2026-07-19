from __future__ import annotations

from data_platform_nfl.tendency_profiles import (
    LEAGUE_TEAM_LABEL,
    compute_qb_situational_splits,
    compute_team_direction_tendencies,
    compute_team_situational_tendencies,
    down_distance_bucket,
    down_type_bucket,
    field_position_bucket,
    pressure_bucket,
    score_state_bucket,
)


# ---------------------------------------------------------------------------
# Bucket-assignment pure functions
# ---------------------------------------------------------------------------


def test_down_distance_bucket_early_down_thresholds() -> None:
    assert down_distance_bucket(1, 3) == "early_down_short"
    assert down_distance_bucket(2, 4) == "early_down_medium"
    assert down_distance_bucket(1, 7) == "early_down_medium"
    assert down_distance_bucket(2, 8) == "early_down_long"


def test_down_distance_bucket_money_down_thresholds() -> None:
    assert down_distance_bucket(3, 2) == "money_down_short"
    assert down_distance_bucket(4, 6) == "money_down_medium"
    assert down_distance_bucket(3, 7) == "money_down_long"


def test_down_distance_bucket_handles_missing_or_invalid() -> None:
    assert down_distance_bucket(None, 5) is None
    assert down_distance_bucket(1, None) is None
    assert down_distance_bucket(5, 3) is None  # not a real down


def test_down_type_bucket() -> None:
    assert down_type_bucket(1) == "early_down"
    assert down_type_bucket(2) == "early_down"
    assert down_type_bucket(3) == "money_down"
    assert down_type_bucket(4) == "money_down"
    assert down_type_bucket(None) is None


def test_score_state_bucket_one_possession_thresholds() -> None:
    assert score_state_bucket(-14) == "trailing_big"
    assert score_state_bucket(-9) == "trailing_big"
    assert score_state_bucket(-8) == "trailing_small"
    assert score_state_bucket(-1) == "trailing_small"
    assert score_state_bucket(0) == "tied"
    assert score_state_bucket(1) == "leading_small"
    assert score_state_bucket(8) == "leading_small"
    assert score_state_bucket(9) == "leading_big"


def test_field_position_bucket_thresholds() -> None:
    assert field_position_bucket(3) == "goal_to_go"
    assert field_position_bucket(5) == "goal_to_go"
    assert field_position_bucket(15) == "red_zone"
    assert field_position_bucket(40) == "midfield"
    assert field_position_bucket(75) == "own_territory"
    assert field_position_bucket(None) is None


def test_pressure_bucket() -> None:
    assert pressure_bucket(True, False) == "pressure"
    assert pressure_bucket(False, True) == "pressure"
    assert pressure_bucket(True, True) == "pressure"
    assert pressure_bucket(False, False) == "clean_pocket"
    assert pressure_bucket(None, None) == "clean_pocket"


# ---------------------------------------------------------------------------
# compute_team_situational_tendencies
# ---------------------------------------------------------------------------


def _base_play(**overrides):
    play = {
        "team": "BUF",
        "down": 1,
        "ydstogo": 10,
        "score_differential": 0,
        "yardline_100": 60,
        "play_type": "run",
        "qb_dropback": False,
        "xpass": 0.4,
        "shotgun": False,
        "no_huddle": False,
        "epa": 0.1,
        "success": True,
        "yards_gained": 4,
        "sack": False,
    }
    play.update(overrides)
    return play


def test_team_situational_tendencies_run_heavy_team_shows_low_pass_rate() -> None:
    plays = []
    # 8 runs, 2 passes on early-down-long (down=1, ydstogo=10) for BUF
    for _ in range(8):
        plays.append(_base_play(play_type="run", qb_dropback=False, xpass=0.45))
    for _ in range(2):
        plays.append(_base_play(play_type="pass", qb_dropback=True, xpass=0.45))

    rows = compute_team_situational_tendencies(plays)
    down_distance_rows = {r["situation_bucket"]: r for r in rows if r["situation_type"] == "down_distance"}
    row = down_distance_rows["early_down_long"]
    assert row["plays"] == 10
    assert row["pass_plays"] == 2
    assert row["rush_plays"] == 8
    assert row["pass_rate"] == 0.2
    assert row["dropback_rate"] == 0.2
    # This team passes far LESS than a neutral xpass model (0.45) would
    # expect in this situation -- a real, legitimate run-heavy tendency
    # signal.
    assert row["pass_rate_over_expected"] < -0.2


def test_team_situational_tendencies_score_state_uses_signed_differential() -> None:
    plays = [_base_play(score_differential=-14, play_type="pass", qb_dropback=True) for _ in range(9)]
    rows = compute_team_situational_tendencies(plays)
    score_rows = {r["situation_bucket"]: r for r in rows if r["situation_type"] == "score_state"}
    assert "trailing_big" in score_rows
    assert score_rows["trailing_big"]["pass_rate"] == 1.0


def test_team_situational_tendencies_one_play_contributes_to_every_dimension() -> None:
    plays = [_base_play() for _ in range(5)]
    rows = compute_team_situational_tendencies(plays)
    situation_types = {r["situation_type"] for r in rows}
    assert situation_types == {"down_distance", "score_state", "field_position"}


def test_team_situational_tendencies_explosive_and_sack_rate() -> None:
    plays = [
        _base_play(play_type="run", yards_gained=15),  # explosive run (>=10)
        _base_play(play_type="pass", qb_dropback=True, yards_gained=25),  # explosive pass (>=20)
        _base_play(play_type="pass", qb_dropback=True, sack=True, yards_gained=-5),
    ]
    rows = compute_team_situational_tendencies(plays)
    row = next(r for r in rows if r["situation_type"] == "down_distance" and r["situation_bucket"] == "early_down_long")
    assert row["explosive_play_rate"] == 2 / 3
    assert row["sack_rate"] == 1 / 2  # 1 sack out of 2 dropbacks


# ---------------------------------------------------------------------------
# compute_team_direction_tendencies
# ---------------------------------------------------------------------------


def test_team_direction_tendencies_pass_and_run_splits() -> None:
    plays = [
        {"team": "KC", "play_type": "pass", "pass_location": "left", "run_location": None, "run_gap": None},
        {"team": "KC", "play_type": "pass", "pass_location": "left", "run_location": None, "run_gap": None},
        {"team": "KC", "play_type": "pass", "pass_location": "right", "run_location": None, "run_gap": None},
        {"team": "KC", "play_type": "run", "pass_location": None, "run_location": "right", "run_gap": "guard"},
        {"team": "KC", "play_type": "run", "pass_location": None, "run_location": "middle", "run_gap": "end"},
    ]
    rows = compute_team_direction_tendencies(plays)
    kc_row = next(r for r in rows if r["team"] == "KC")
    assert kc_row["pass_plays_with_location"] == 3
    assert round(kc_row["pass_left_rate"], 4) == round(2 / 3, 4)
    assert kc_row["run_plays_with_location"] == 2
    assert kc_row["run_right_rate"] == 0.5
    assert kc_row["run_guard_rate"] == 0.5
    assert kc_row["run_end_rate"] == 0.5


def test_team_direction_tendencies_includes_league_row_by_default() -> None:
    plays = [
        {"team": "KC", "play_type": "pass", "pass_location": "left", "run_location": None, "run_gap": None},
        {"team": "BUF", "play_type": "pass", "pass_location": "right", "run_location": None, "run_gap": None},
    ]
    rows = compute_team_direction_tendencies(plays)
    league_row = next(r for r in rows if r["team"] == LEAGUE_TEAM_LABEL)
    assert league_row["pass_plays_with_location"] == 2
    assert league_row["pass_left_rate"] == 0.5
    assert league_row["pass_right_rate"] == 0.5


def test_team_direction_tendencies_can_exclude_league_row() -> None:
    plays = [{"team": "KC", "play_type": "pass", "pass_location": "left", "run_location": None, "run_gap": None}]
    rows = compute_team_direction_tendencies(plays, include_league=False)
    assert all(r["team"] != LEAGUE_TEAM_LABEL for r in rows)


# ---------------------------------------------------------------------------
# compute_qb_situational_splits
# ---------------------------------------------------------------------------


def _qb_play(**overrides):
    play = {
        "passer_player_id": "00-1111",
        "passer_player_name": "Test QB",
        "posteam": "BUF",
        "down": 1,
        "score_differential": 0,
        "yardline_100": 60,
        "sack": False,
        "qb_hit": False,
        "complete_pass": True,
        "passing_yards": 8,
        "epa": 0.2,
        "success": True,
        "cp": 0.65,
        "interception": False,
        "touchdown": False,
    }
    play.update(overrides)
    return play


def test_qb_situational_splits_pressure_vs_clean_pocket() -> None:
    plays = []
    for _ in range(5):
        plays.append(_qb_play(sack=False, qb_hit=False, complete_pass=True, cp=0.7))
    for _ in range(5):
        plays.append(_qb_play(sack=False, qb_hit=True, complete_pass=False, cp=0.7))

    rows = compute_qb_situational_splits(plays)
    pressure_rows = {r["situation_bucket"]: r for r in rows if r["situation_type"] == "pressure"}
    assert pressure_rows["clean_pocket"]["completion_rate"] == 1.0
    assert pressure_rows["pressure"]["completion_rate"] == 0.0


def test_qb_situational_splits_cpoe_positive_when_overperforming_cp() -> None:
    plays = [_qb_play(complete_pass=True, cp=0.5) for _ in range(10)]
    rows = compute_qb_situational_splits(plays)
    overall = next(r for r in rows if r["situation_type"] == "overall")
    assert overall["completion_rate"] == 1.0
    assert overall["avg_cp"] == 0.5
    assert round(overall["cpoe"], 2) == 50.0


def test_qb_situational_splits_sacks_counted_as_dropbacks_not_attempts() -> None:
    plays = [_qb_play(sack=False) for _ in range(8)] + [_qb_play(sack=True) for _ in range(2)]
    rows = compute_qb_situational_splits(plays)
    overall = next(r for r in rows if r["situation_type"] == "overall")
    assert overall["dropbacks"] == 10
    assert overall["pass_attempts"] == 8
    assert overall["sacks"] == 2
    assert overall["sack_rate"] == 0.2


def test_qb_situational_splits_ignores_plays_without_passer_id() -> None:
    plays = [_qb_play(passer_player_id=None)]
    rows = compute_qb_situational_splits(plays)
    assert rows == []


def test_qb_situational_splits_down_type_buckets_early_vs_money_down() -> None:
    plays = [_qb_play(down=1) for _ in range(5)] + [_qb_play(down=3) for _ in range(5)]
    rows = compute_qb_situational_splits(plays)
    down_type_rows = {r["situation_bucket"]: r for r in rows if r["situation_type"] == "down_type"}
    assert down_type_rows["early_down"]["dropbacks"] == 5
    assert down_type_rows["money_down"]["dropbacks"] == 5
