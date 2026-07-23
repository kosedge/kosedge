"""Wire situational tendency profiles into live game + prop pricing.

Season-level PROE / direction / pressure splits already live in
`nfl_dp_team_situational_tendencies` and `nfl_dp_team_direction_tendencies`
for the Team Intel UI. This module turns those into bounded multiplicative
adjustments for:

- Game sim: pass-rate / total / margin tilt from PROE differentials
- Player props: team_pass_rate_factor for WR/TE/RB/QB

All effects are intentionally mild (± few %) so tendency never overrides
EPA matchup packs or market blend — it sharpens, it does not rewrite.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping

from sqlalchemy import text


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _safe(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def fetch_team_proe_map(
    session: Any,
    *,
    season: int,
    situation: str = "all",
) -> Dict[str, float]:
    """{team: pass_rate_over_expected} play-weighted across down/distance buckets.

    `situation` is accepted for API compatibility; the owned table keys on
    (situation_type, situation_bucket). We aggregate offense-perspective
    down_distance rows so callers get one season-level PROE per team.
    """
    _ = situation  # reserved for future bucket filters
    rows = session.execute(
        text(
            """
            SELECT
              team,
              SUM(COALESCE(pass_rate_over_expected, 0) * GREATEST(plays, 1))
                / NULLIF(SUM(GREATEST(plays, 1)), 0) AS pass_rate_over_expected
            FROM nfl_dp_team_situational_tendencies
            WHERE season = :season
              AND perspective = 'offense'
              AND situation_type = 'down_distance'
              AND team <> 'LEAGUE'
            GROUP BY team
            """
        ),
        {"season": int(season)},
    ).fetchall()
    return {str(r.team): _safe(r.pass_rate_over_expected) for r in rows}


def fetch_team_direction_rates(
    session: Any,
    *,
    season: int,
) -> Dict[str, Dict[str, float]]:
    rows = session.execute(
        text(
            """
            SELECT
              team,
              pass_left_rate, pass_middle_rate, pass_right_rate,
              run_left_rate, run_middle_rate, run_right_rate,
              run_end_rate, run_guard_rate, run_tackle_rate
            FROM nfl_dp_team_direction_tendencies
            WHERE season = :season
              AND perspective = 'offense'
              AND team <> 'LEAGUE'
            """
        ),
        {"season": int(season)},
    ).fetchall()
    out: Dict[str, Dict[str, float]] = {}
    for r in rows:
        out[str(r.team)] = {
            "pass_left_rate": _safe(r.pass_left_rate),
            "pass_middle_rate": _safe(r.pass_middle_rate),
            "pass_right_rate": _safe(r.pass_right_rate),
            "run_left_rate": _safe(r.run_left_rate),
            "run_middle_rate": _safe(r.run_middle_rate),
            "run_right_rate": _safe(r.run_right_rate),
            "run_end_rate": _safe(r.run_end_rate),
            "run_guard_rate": _safe(r.run_guard_rate),
            "run_tackle_rate": _safe(r.run_tackle_rate),
        }
    return out


def tendency_pass_rate_factor(team_proe: float, *, opponent_proe: float = 0.0) -> float:
    """Map PROE (pass_rate − xpass) → multiplicative pass-volume factor.

    League PROE is ~0; +0.05 means a team passes ~5pp more than expected.
    Cap effect at ±6% so scheme tilt cannot mint fake pass leaders alone.
    """
    signal = _clamp(team_proe - (0.35 * opponent_proe), -0.08, 0.08)
    return _clamp(1.0 + (0.75 * signal), 0.94, 1.06)


def tendency_game_signals(
    home_proe: float,
    away_proe: float,
) -> Dict[str, float]:
    """Point-space signals for sides/totals from PROE differential."""
    home_pass_tilt = _clamp(home_proe, -0.08, 0.08)
    away_pass_tilt = _clamp(away_proe, -0.08, 0.08)
    total_signal = _clamp(6.0 * (home_pass_tilt + away_pass_tilt), -1.2, 1.2)
    spread_signal = _clamp(4.0 * (home_pass_tilt - away_pass_tilt), -0.6, 0.6)
    return {
        "total_signal": total_signal,
        "spread_signal": spread_signal,
        "home_pass_rate_factor": tendency_pass_rate_factor(home_proe, opponent_proe=away_proe),
        "away_pass_rate_factor": tendency_pass_rate_factor(away_proe, opponent_proe=home_proe),
    }


def apply_tendency_to_player_pass_rate(
    base_pass_rate_factor: float,
    *,
    team: str,
    opponent: str,
    proe_by_team: Mapping[str, float] | None,
) -> float:
    if not proe_by_team:
        return float(base_pass_rate_factor)
    team_proe = float(proe_by_team.get(str(team), 0.0) or 0.0)
    opp_proe = float(proe_by_team.get(str(opponent), 0.0) or 0.0)
    return _clamp(
        float(base_pass_rate_factor) * tendency_pass_rate_factor(team_proe, opponent_proe=opp_proe),
        0.70,
        1.35,
    )
