"""Phase-1 offensive production stack conservation guards."""

from __future__ import annotations

from data_platform_nfl.offensive_production_stack import (
    LEAGUE_PASS_YARDS_POOL,
    LEAGUE_RUSH_YARDS_POOL,
    apply_offensive_production_stack,
    rookie_season_share_factor,
    smoke_offensive_stack,
)


def _flat_board() -> list[dict]:
    teams = [
        "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
        "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
        "LA", "LAC", "LV", "MIA", "MIN", "NE", "NO", "NYG",
        "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS",
    ]
    # Locked-ish pass board with ARI/BAL/SEA in zone.
    pass_y = {t: 3900.0 for t in teams}
    pass_y["ARI"] = 4080.0
    pass_y["BAL"] = 3340.0
    pass_y["SEA"] = 3970.0
    pass_y["CIN"] = 4800.0
    pass_y["WAS"] = 3000.0
    # Renorm to 126k.
    scale = LEAGUE_PASS_YARDS_POOL / sum(pass_y.values())
    pass_y = {t: v * scale for t, v in pass_y.items()}

    rows = []
    for team in teams:
        rows.append(
            {
                "player_key": f"{team}-QB1",
                "player_name": f"{team} QB1",
                "team": team,
                "position": "QB",
                "pass_yards_total": pass_y[team] * 0.97,
                "pass_tds_total": 20.0,
                "rush_yards_total": 200.0,
                "rush_tds_total": 2.0,
                "receiving_yards_total": 0.0,
                "rec_tds_total": 0.0,
                "receptions_total": 0.0,
                "is_rookie": False,
            }
        )
        rows.append(
            {
                "player_key": f"{team}-QB2",
                "player_name": f"{team} QB2",
                "team": team,
                "position": "QB",
                "pass_yards_total": pass_y[team] * 0.03,
                "pass_tds_total": 2.0,
                "rush_yards_total": 20.0,
                "rush_tds_total": 0.2,
                "receiving_yards_total": 0.0,
                "rec_tds_total": 0.0,
                "receptions_total": 0.0,
                "is_rookie": False,
            }
        )
        for i, pos in enumerate(("WR", "WR", "WR", "TE", "RB", "RB"), start=1):
            rows.append(
                {
                    "player_key": f"{team}-{pos}{i}",
                    "player_name": f"{team} {pos}{i}",
                    "team": team,
                    "position": pos,
                    "pass_yards_total": 0.0,
                    "pass_tds_total": 0.0,
                    "rush_yards_total": 600.0 if pos == "RB" else 0.0,
                    "rush_tds_total": 4.0 if pos == "RB" else 0.0,
                    "receiving_yards_total": 500.0 if pos != "RB" else 200.0,
                    "rec_tds_total": 3.0,
                    "receptions_total": 40.0,
                    "is_rookie": i == 1 and pos == "WR" and team == "ARI",
                    "draft_round": 1 if i == 1 and pos == "WR" and team == "ARI" else None,
                }
            )
    return rows


def test_rookie_ramp_first_round_wr() -> None:
    # 55/80/100 over 4/4/9 weeks → ~0.847
    f = rookie_season_share_factor("WR", 1)
    assert 0.80 <= f <= 0.90


def test_stack_conserves_and_hits_td_bands() -> None:
    rows, audit = apply_offensive_production_stack(_flat_board())
    assert audit["applied"] is True
    smoke = audit["smoke"]
    assert smoke["all_pass"] is True, smoke
    assert abs(smoke["league"]["pass_yards"] - LEAGUE_PASS_YARDS_POOL) < 50
    assert 58_000 <= smoke["league"]["rush_yards"] <= 62_000
    assert 1_050 <= smoke["league"]["pass_tds"] <= 1_150
    assert 450 <= smoke["league"]["rush_tds"] <= 520
    # Direct smoke re-check
    assert smoke_offensive_stack(rows)["all_pass"] is True


def test_pass_yards_stay_locked_for_median_team() -> None:
    board = _flat_board()
    before = {
        t: sum(
            float(r["pass_yards_total"])
            for r in board
            if r["team"] == t
        )
        for t in {r["team"] for r in board}
    }
    rows, _ = apply_offensive_production_stack(board)
    after = {
        t: sum(float(r["pass_yards_total"]) for r in rows if r["team"] == t)
        for t in before
    }
    # Locked within microscopic renorm.
    for t in before:
        assert abs(after[t] - before[t]) / max(before[t], 1.0) < 0.02
