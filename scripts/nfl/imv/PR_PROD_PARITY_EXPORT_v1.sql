-- PR_PROD_PARITY_EXPORT_v1.sql
-- Historical 27-col SELECT. Live reader binds to v3
-- (ops/platform/PR_PROD_PARITY_EXPORT_v3.sql pin b10d6cfd…).
-- Do not invent v3 bytes here. Reader: missing/mismatch v3 = NOT_RUN.

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
