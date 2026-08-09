"""Phase-1 offensive production stack conservation guards."""

from __future__ import annotations

from data_platform_nfl.offensive_production_stack import (
    LEAGUE_PASS_YARDS_POOL,
    LEAGUE_RUSH_YARDS_POOL,
    LEAGUE_RUSH_YARDS_POOL_LIFTED,
    apply_alpha_usage_reanchor,
    apply_offensive_production_stack,
    apply_offensive_variance_lift,
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
    assert 58_000 <= smoke["league"]["rush_yards"] <= 66_000
    assert 1_050 <= smoke["league"]["pass_tds"] <= 1_150
    assert 450 <= smoke["league"]["rush_tds"] <= 520
    # Direct smoke re-check
    assert smoke_offensive_stack(rows)["all_pass"] is True


def test_offensive_variance_lift_keeps_pass_locked() -> None:
    board = _flat_board()
    # Seed rush variance so the asymmetric stretch has a residual to widen.
    teams = sorted({r["team"] for r in board})
    for i, team in enumerate(teams):
        for r in board:
            if r["team"] != team or r["position"] != "RB":
                continue
            r["rush_yards_total"] = 900.0 + i * 55.0
            r["rush_tds_total"] = 6.0 + i * 0.15
    before_pass = {
        t: sum(float(r["pass_yards_total"]) for r in board if r["team"] == t)
        for t in teams
    }
    rows, rush, audit = apply_offensive_variance_lift(board)
    assert audit["applied"] is True
    assert abs(sum(rush.values()) - LEAGUE_RUSH_YARDS_POOL_LIFTED) < 1.0
    after_pass = {
        t: sum(float(r["pass_yards_total"]) for r in rows if r["team"] == t)
        for t in before_pass
    }
    for t in ("ARI", "BAL", "SEA"):
        assert abs(after_pass[t] - before_pass[t]) < 0.05
    assert abs(sum(after_pass.values()) - sum(before_pass.values())) < 0.5
    assert max(rush.values()) * 0.60 >= 1_450.0
    assert max(rush.values()) - min(rush.values()) > 800.0
    smoke = smoke_offensive_stack(rows)
    assert smoke["checks"]["pass_pool_locked"] is True
    assert smoke["checks"]["ari_bal_sea_pass_zones"] is True
    assert smoke["checks"]["rush_pool_band"] is True


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


def test_alpha_usage_reanchor_lifts_jsn_and_conserves() -> None:
    board = _flat_board()
    # Inject named 2025 alphas onto high-volume teams; seed WR=TE logjam.
    for r in board:
        if r["team"] == "SEA" and r["player_key"] == "SEA-WR1":
            r["player_name"] = "Jaxon Smith-Njigba"
            r["receiving_yards_total"] = 900.0
        if r["team"] == "SEA" and r["player_key"] == "SEA-TE4":
            r["player_name"] = "AJ Barner"
            r["receiving_yards_total"] = 900.0
        if r["team"] == "CIN" and r["player_key"] == "CIN-WR1":
            r["player_name"] = "Ja'Marr Chase"
        if r["team"] == "LA" and r["player_key"] == "LA-WR1":
            r["player_name"] = "Puka Nacua"
        if r["team"] == "BUF" and r["player_key"] == "BUF-RB5":
            r["player_name"] = "James Cook"
            r["rush_yards_total"] = 1600.0
        if r["team"] == "BUF" and r["player_key"] == "BUF-RB6":
            r["rush_yards_total"] = 900.0
        if r["team"] == "SEA":
            if r["position"] == "RB" and r["player_key"].endswith("RB5"):
                r["rush_yards_total"] = 1500.0
            if r["position"] == "RB" and r["player_key"].endswith("RB6"):
                r["rush_yards_total"] = 900.0

    before_pass = {
        t: sum(float(r["pass_yards_total"]) for r in board if r["team"] == t)
        for t in {r["team"] for r in board}
    }
    before_rush = {
        t: sum(float(r["rush_yards_total"]) for r in board if r["team"] == t)
        for t in before_pass
    }
    rows, audit = apply_alpha_usage_reanchor(board)
    assert audit["applied"] is True
    smoke = audit["smoke"]
    assert smoke["checks"]["pass_rec_yards_within_1_5pct"] is True
    assert smoke["checks"]["pass_pool_locked"] is True

    after_pass = {
        t: sum(float(r["pass_yards_total"]) for r in rows if r["team"] == t)
        for t in before_pass
    }
    after_rush = {
        t: sum(float(r["rush_yards_total"]) for r in rows if r["team"] == t)
        for t in before_rush
    }
    for t in ("ARI", "BAL", "SEA"):
        assert abs(after_pass[t] - before_pass[t]) < 0.05
    for t in before_rush:
        assert abs(after_rush[t] - before_rush[t]) < 0.5

    by_name = {r["player_name"]: r for r in rows}
    jsn = float(by_name["Jaxon Smith-Njigba"]["receiving_yards_total"])
    barner = float(by_name["AJ Barner"]["receiving_yards_total"])
    chase = float(by_name["Ja'Marr Chase"]["receiving_yards_total"])
    nacua = float(by_name["Puka Nacua"]["receiving_yards_total"])
    cook = float(by_name["James Cook"]["rush_yards_total"])
    assert jsn > barner
    assert jsn >= 1400.0
    assert chase >= 1400.0
    assert nacua >= 1400.0
    assert cook >= 1400.0

    wrs = sorted(
        (float(r["receiving_yards_total"]) for r in rows if r["position"] == "WR"),
        reverse=True,
    )
    assert wrs[0] >= 1550.0
    assert sum(1 for y in wrs if y >= 1400.0) >= 2
