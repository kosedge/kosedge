from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import text


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fetch_latest_matchup_feature_pack(
    session: Any,
    *,
    game_id: str,
    season_year: Optional[int],
    home_team: str,
    away_team: str,
) -> Optional[Dict[str, Any]]:
    season = int(season_year) if season_year is not None else None
    row = session.execute(
        text(
            """
            WITH candidates AS (
              SELECT
                0 AS priority,
                season, week, game_id, home_team, away_team,
                home_off_epa_5g, away_off_epa_5g,
                home_def_epa_allowed_5g, away_def_epa_allowed_5g,
                home_pressure_allowed_5g, away_pressure_allowed_5g,
                home_pressure_generated_5g, away_pressure_generated_5g,
                home_pass_rate_5g, away_pass_rate_5g,
                home_early_down_pass_rate_5g, away_early_down_pass_rate_5g,
                home_red_zone_td_rate_5g, away_red_zone_td_rate_5g,
                home_success_offense_5g, away_success_offense_5g,
                home_success_defense_allowed_5g, away_success_defense_allowed_5g,
                diff_off_epa_5g, diff_def_epa_allowed_5g,
                diff_pressure_generated_5g, diff_pressure_allowed_5g,
                diff_red_zone_td_rate_5g,
                home_kav_offense_5g, away_kav_offense_5g,
                home_kav_defense_5g, away_kav_defense_5g,
                home_kav_net_5g, away_kav_net_5g,
                home_kav_offense_ytd, away_kav_offense_ytd,
                home_kav_defense_ytd, away_kav_defense_ytd,
                home_kav_net_ytd, away_kav_net_ytd,
                diff_kav_offense_5g, diff_kav_defense_5g, diff_kav_net_5g,
                kav_as_of_week,
                home_st_kav_net_5g, away_st_kav_net_5g, diff_st_kav_net_5g,
                home_personnel_edge_5g, away_personnel_edge_5g, diff_personnel_edge_5g,
                home_sub_elasticity_5g, away_sub_elasticity_5g,
                home_coach_aggression_5g, away_coach_aggression_5g, diff_coach_aggression_5g,
                home_coach_pace_5g, away_coach_pace_5g,
                second_order_as_of_week
              FROM nfl_dp_matchup_features_weekly
              WHERE game_id = :game_id
              UNION ALL
              SELECT
                1 AS priority,
                season, week, game_id, home_team, away_team,
                home_off_epa_5g, away_off_epa_5g,
                home_def_epa_allowed_5g, away_def_epa_allowed_5g,
                home_pressure_allowed_5g, away_pressure_allowed_5g,
                home_pressure_generated_5g, away_pressure_generated_5g,
                home_pass_rate_5g, away_pass_rate_5g,
                home_early_down_pass_rate_5g, away_early_down_pass_rate_5g,
                home_red_zone_td_rate_5g, away_red_zone_td_rate_5g,
                home_success_offense_5g, away_success_offense_5g,
                home_success_defense_allowed_5g, away_success_defense_allowed_5g,
                diff_off_epa_5g, diff_def_epa_allowed_5g,
                diff_pressure_generated_5g, diff_pressure_allowed_5g,
                diff_red_zone_td_rate_5g,
                home_kav_offense_5g, away_kav_offense_5g,
                home_kav_defense_5g, away_kav_defense_5g,
                home_kav_net_5g, away_kav_net_5g,
                home_kav_offense_ytd, away_kav_offense_ytd,
                home_kav_defense_ytd, away_kav_defense_ytd,
                home_kav_net_ytd, away_kav_net_ytd,
                diff_kav_offense_5g, diff_kav_defense_5g, diff_kav_net_5g,
                kav_as_of_week,
                home_st_kav_net_5g, away_st_kav_net_5g, diff_st_kav_net_5g,
                home_personnel_edge_5g, away_personnel_edge_5g, diff_personnel_edge_5g,
                home_sub_elasticity_5g, away_sub_elasticity_5g,
                home_coach_aggression_5g, away_coach_aggression_5g, diff_coach_aggression_5g,
                home_coach_pace_5g, away_coach_pace_5g,
                second_order_as_of_week
              FROM nfl_dp_matchup_features_weekly
              WHERE :season IS NOT NULL
                AND season = :season
                AND home_team = :home_team
                AND away_team = :away_team
            )
            SELECT
              season, week, game_id, home_team, away_team,
              home_off_epa_5g, away_off_epa_5g,
              home_def_epa_allowed_5g, away_def_epa_allowed_5g,
              home_pressure_allowed_5g, away_pressure_allowed_5g,
              home_pressure_generated_5g, away_pressure_generated_5g,
              home_pass_rate_5g, away_pass_rate_5g,
              home_early_down_pass_rate_5g, away_early_down_pass_rate_5g,
              home_red_zone_td_rate_5g, away_red_zone_td_rate_5g,
              home_success_offense_5g, away_success_offense_5g,
              home_success_defense_allowed_5g, away_success_defense_allowed_5g,
              diff_off_epa_5g, diff_def_epa_allowed_5g,
              diff_pressure_generated_5g, diff_pressure_allowed_5g,
              diff_red_zone_td_rate_5g,
              home_kav_offense_5g, away_kav_offense_5g,
              home_kav_defense_5g, away_kav_defense_5g,
              home_kav_net_5g, away_kav_net_5g,
              home_kav_offense_ytd, away_kav_offense_ytd,
              home_kav_defense_ytd, away_kav_defense_ytd,
              home_kav_net_ytd, away_kav_net_ytd,
              diff_kav_offense_5g, diff_kav_defense_5g, diff_kav_net_5g,
              kav_as_of_week,
              home_st_kav_net_5g, away_st_kav_net_5g, diff_st_kav_net_5g,
              home_personnel_edge_5g, away_personnel_edge_5g, diff_personnel_edge_5g,
              home_sub_elasticity_5g, away_sub_elasticity_5g,
              home_coach_aggression_5g, away_coach_aggression_5g, diff_coach_aggression_5g,
              home_coach_pace_5g, away_coach_pace_5g,
              second_order_as_of_week
            FROM candidates
            ORDER BY priority, season DESC, week DESC
            LIMIT 1
            """
        ),
        {
            "game_id": game_id,
            "season": season,
            "home_team": home_team,
            "away_team": away_team,
        },
    ).fetchone()
    if row is None:
        return None
    return dict(row._mapping)


def matchup_pack_to_sim_input_kwargs(
    matchup_pack: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if not matchup_pack:
        return {}

    home_success_off = _to_float(matchup_pack.get("home_success_offense_5g"))
    away_success_off = _to_float(matchup_pack.get("away_success_offense_5g"))
    home_success_def = _to_float(matchup_pack.get("home_success_defense_allowed_5g"))
    away_success_def = _to_float(matchup_pack.get("away_success_defense_allowed_5g"))

    success_terms = []
    if home_success_off is not None and away_success_off is not None:
        success_terms.append(home_success_off - away_success_off)
    if away_success_def is not None and home_success_def is not None:
        success_terms.append(away_success_def - home_success_def)
    diff_success_rate = (sum(success_terms) / len(success_terms)) if success_terms else None

    matchup_week_raw = matchup_pack.get("week")
    try:
        matchup_week = int(round(float(matchup_week_raw))) if matchup_week_raw is not None else None
    except (TypeError, ValueError):
        matchup_week = None
    matchup_season_raw = matchup_pack.get("season")
    try:
        matchup_season = int(round(float(matchup_season_raw))) if matchup_season_raw is not None else None
    except (TypeError, ValueError):
        matchup_season = None

    return {
        "matchup_season": matchup_season,
        "matchup_week": matchup_week,
        "matchup_game_id": matchup_pack.get("game_id"),
        "matchup_home_team": matchup_pack.get("home_team"),
        "matchup_away_team": matchup_pack.get("away_team"),
        "home_off_epa_5g": _to_float(matchup_pack.get("home_off_epa_5g")),
        "away_off_epa_5g": _to_float(matchup_pack.get("away_off_epa_5g")),
        "home_def_epa_allowed_5g": _to_float(matchup_pack.get("home_def_epa_allowed_5g")),
        "away_def_epa_allowed_5g": _to_float(matchup_pack.get("away_def_epa_allowed_5g")),
        "home_pass_rate_5g": _to_float(matchup_pack.get("home_pass_rate_5g")),
        "away_pass_rate_5g": _to_float(matchup_pack.get("away_pass_rate_5g")),
        "home_success_offense_5g": home_success_off,
        "away_success_offense_5g": away_success_off,
        "home_success_defense_allowed_5g": home_success_def,
        "away_success_defense_allowed_5g": away_success_def,
        "matchup_diff_off_epa_5g": _to_float(matchup_pack.get("diff_off_epa_5g")),
        "matchup_diff_def_epa_allowed_5g": _to_float(matchup_pack.get("diff_def_epa_allowed_5g")),
        "matchup_diff_pressure_generated_5g": _to_float(matchup_pack.get("diff_pressure_generated_5g")),
        "matchup_diff_pressure_allowed_5g": _to_float(matchup_pack.get("diff_pressure_allowed_5g")),
        "matchup_diff_red_zone_td_rate_5g": _to_float(matchup_pack.get("diff_red_zone_td_rate_5g")),
        "matchup_diff_success_rate_5g": diff_success_rate,
        "home_kav_offense_5g": _to_float(matchup_pack.get("home_kav_offense_5g")),
        "away_kav_offense_5g": _to_float(matchup_pack.get("away_kav_offense_5g")),
        "home_kav_defense_5g": _to_float(matchup_pack.get("home_kav_defense_5g")),
        "away_kav_defense_5g": _to_float(matchup_pack.get("away_kav_defense_5g")),
        "home_kav_net_5g": _to_float(matchup_pack.get("home_kav_net_5g")),
        "away_kav_net_5g": _to_float(matchup_pack.get("away_kav_net_5g")),
        "kav_as_of_week": (
            int(matchup_pack["kav_as_of_week"])
            if matchup_pack.get("kav_as_of_week") is not None
            else None
        ),
        # ST-KAV columns exist on matchup packs for supervised analysis only.
        # NflGameInputs does not accept them (failed v4 holdout; not wired).
        "home_personnel_edge_5g": _to_float(matchup_pack.get("home_personnel_edge_5g")),
        "away_personnel_edge_5g": _to_float(matchup_pack.get("away_personnel_edge_5g")),
        "home_sub_elasticity_5g": _to_float(matchup_pack.get("home_sub_elasticity_5g")),
        "away_sub_elasticity_5g": _to_float(matchup_pack.get("away_sub_elasticity_5g")),
        "home_coach_aggression_5g": _to_float(matchup_pack.get("home_coach_aggression_5g")),
        "away_coach_aggression_5g": _to_float(matchup_pack.get("away_coach_aggression_5g")),
        "home_coach_pace_5g": _to_float(matchup_pack.get("home_coach_pace_5g")),
        "away_coach_pace_5g": _to_float(matchup_pack.get("away_coach_pace_5g")),
        "second_order_as_of_week": (
            int(matchup_pack["second_order_as_of_week"])
            if matchup_pack.get("second_order_as_of_week") is not None
            else None
        ),
        "feature_pack_version": "nfl-v1.3-matchup-pack-second-order",
    }
