"""Role-aware production shape — no 1,380 RB magnet, dual-threat QB, WR alpha pin."""

from __future__ import annotations

from data_platform_nfl.role_aware_production import apply_role_aware_player_shape


def _rb(team: str, depth: int, name: str, rush: float, rec: float = 200.0, rush_td: float = 6.0) -> dict:
    return {
        "player_key": f"{team}-RB{depth}-{name.replace(' ', '')}",
        "player_name": name,
        "team": team,
        "position": "RB",
        "rush_yards_total": rush,
        "rush_tds_total": rush_td,
        "receiving_yards_total": rec,
        "receptions_total": rec / 8.2,
        "rec_tds_total": 3.0,
        "pass_yards_total": 0.0,
        "pass_tds_total": 0.0,
    }


def _qb(team: str, name: str, pass_y: float, rush: float, pass_td: float = 28.0, rush_td: float = 2.0) -> dict:
    return {
        "player_key": f"{team}-QB1-{name.replace(' ', '')}",
        "player_name": name,
        "team": team,
        "position": "QB",
        "pass_yards_total": pass_y,
        "pass_tds_total": pass_td,
        "rush_yards_total": rush,
        "rush_tds_total": rush_td,
        "receiving_yards_total": 0.0,
        "receptions_total": 0.0,
        "rec_tds_total": 0.0,
    }


def _wr(team: str, depth: int, name: str, rec: float) -> dict:
    return {
        "player_key": f"{team}-WR{depth}-{name.replace(' ', '')}",
        "player_name": name,
        "team": team,
        "position": "WR",
        "rush_yards_total": 0.0,
        "rush_tds_total": 0.0,
        "receiving_yards_total": rec,
        "receptions_total": rec / 11.8,
        "rec_tds_total": 8.0,
        "pass_yards_total": 0.0,
        "pass_tds_total": 0.0,
    }


def test_non_alpha_rb1_not_pinned_to_1380_blob() -> None:
    rows = [
        _qb("SEA", "Sam Darnold", 3500, 200),
        _rb("SEA", 1, "Zach Charbonnet", 1425, 340, 10.6),
        _rb("SEA", 2, "Jadarian Price", 722, 218, 5.1),
        _rb("SEA", 3, "George Holani", 208, 60, 1.5),
        _wr("SEA", 1, "Jaxon Smith-Njigba", 1276),
        _wr("SEA", 2, "Cooper Kupp", 700),
        _wr("SEA", 3, "Tyler Lockett", 400),
    ]
    team_rush = sum(r["rush_yards_total"] for r in rows)
    out, audit = apply_role_aware_player_shape(rows)
    by = {r["player_name"]: r for r in out}
    charb = by["Zach Charbonnet"]
    assert charb["rush_yards_total"] < 1300, charb["rush_yards_total"]
    assert abs(sum(r["rush_yards_total"] for r in out) - team_rush) < 1.0
    assert audit["applied"] is True


def test_gibbs_rb1_gets_majority_and_three_down_targets() -> None:
    rows = [
        _qb("DET", "Jared Goff", 4200, 147, 34.0, 1.2),
        _rb("DET", 1, "Jahmyr Gibbs", 956, 317, 6.8),
        _rb("DET", 2, "Isiah Pacheco", 274, 184, 2.0),
        _rb("DET", 3, "Sione Vaki", 114, 74, 0.8),
        _wr("DET", 1, "Amon-Ra St. Brown", 1400),
        _wr("DET", 2, "Jameson Williams", 800),
        _wr("DET", 3, "Kalif Raymond", 400),
    ]
    out, _ = apply_role_aware_player_shape(rows)
    by = {r["player_name"]: r for r in out}
    gibbs = by["Jahmyr Gibbs"]
    pacheco = by["Isiah Pacheco"]
    assert gibbs["rush_yards_total"] > pacheco["rush_yards_total"] + 200
    assert gibbs["receiving_yards_total"] >= 450
    assert gibbs["rush_tds_total"] > pacheco["rush_tds_total"] * 2


def test_allen_dual_threat_rush_tds_material() -> None:
    rows = [
        _qb("BUF", "Josh Allen", 3407, 289, 29.0, 2.3),
        _rb("BUF", 1, "James Cook III", 1505, 316, 11.4),
        _rb("BUF", 2, "Ray Davis", 400, 80, 2.0),
        _rb("BUF", 3, "Ty Johnson", 150, 40, 0.5),
        _wr("BUF", 1, "Khalil Shakir", 900),
        _wr("BUF", 2, "Keon Coleman", 700),
        _wr("BUF", 3, "Joshua Palmer", 400),
    ]
    team_rush = sum(r["rush_yards_total"] for r in rows)
    out, _ = apply_role_aware_player_shape(rows)
    by = {r["player_name"]: r for r in out}
    allen = by["Josh Allen"]
    cook = by["James Cook III"]
    assert allen["rush_yards_total"] >= 250
    assert allen["rush_tds_total"] >= 4.0
    assert cook["rush_yards_total"] > allen["rush_yards_total"]
    assert abs(sum(r["rush_yards_total"] for r in out) - team_rush) < 1.5


def test_puka_alpha_not_stuck_at_wr8_volume() -> None:
    rows = [
        _qb("LAR", "Matthew Stafford", 4450, 179, 39.0, 1.4),
        _rb("LAR", 1, "Kyren Williams", 1200, 300, 10.0),
        _rb("LAR", 2, "Blake Corum", 400, 80, 2.0),
        _wr("LAR", 1, "Puka Nacua", 1010),
        _wr("LAR", 2, "Davante Adams", 900),
        _wr("LAR", 3, "Tutu Atwell", 500),
    ]
    out, _ = apply_role_aware_player_shape(rows)
    by = {r["player_name"]: r for r in out}
    puka = by["Puka Nacua"]
    assert puka["receiving_yards_total"] >= 1400
