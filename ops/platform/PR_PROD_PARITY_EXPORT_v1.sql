-- PR_PROD_PARITY_EXPORT_v1.sql
-- Ordered columns for the sealed prod CSV export (73815046).
-- v2 of this file is forthcoming; do not invent columns.
-- Reader: header required, empty field = null, unknown/missing column = NOT_RUN.

SELECT
  season,
  week,
  game_id,
  home_team,
  away_team,
  home_off_epa_5g,
  away_off_epa_5g,
  home_def_epa_allowed_5g,
  away_def_epa_allowed_5g,
  home_pass_rate_5g,
  away_pass_rate_5g,
  home_success_offense_5g,
  away_success_offense_5g,
  home_pressure_allowed_5g,
  away_pressure_allowed_5g,
  home_pressure_generated_5g,
  away_pressure_generated_5g,
  home_early_down_pass_rate_5g,
  away_early_down_pass_rate_5g,
  home_red_zone_td_rate_5g,
  away_red_zone_td_rate_5g,
  home_success_defense_allowed_5g,
  away_success_defense_allowed_5g,
  diff_off_epa_5g,
  home_rest_days,
  away_rest_days,
  roof_dome
FROM nfl_dp_matchup_features_weekly
WHERE season = 2026
  AND week BETWEEN 3 AND 7
ORDER BY week, game_id;
