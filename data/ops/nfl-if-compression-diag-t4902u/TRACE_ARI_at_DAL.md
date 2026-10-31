# TRACE 2026-W08-ARI@DAL

READ-ONLY replay of sealed IF (tip `6ca03716`). No math change.

## 1. Source ratings (through-W7 panel 340a06dd)

| side | team | record | games | rolling | off_idx | def_idx | off_epa_5g | def_epa_allowed_5g |
|---|---|---|---:|---:|---:|---:|---:|---:|
| home | DAL | 3-4 | 7 | 7 | 0.994286 | 1.005714 | 0.077152 | 0.110821 |
| away | ARI | 2-5 | 7 | 7 | 0.962857 | 0.977143 | -0.038534 | 0.156197 |

t5_source home/away = `team_strength_from_record` / `team_strength_from_record`. 2025 prior used: False / False.

## 2. Contract inputs (20 + context)

```json
{
  "context": {
    "game_id": "2026-W08-ARI@DAL",
    "home_team": "DAL",
    "away_team": "ARI",
    "matchup_season": 2026,
    "matchup_week": 8,
    "rest_days_home": 7.0,
    "rest_days_away": 7.0
  },
  "efficiency": {
    "offense_index_home": 0.9942857142857143,
    "offense_index_away": 0.9628571428571429,
    "defense_index_home": 1.0057142857142858,
    "defense_index_away": 0.9771428571428572,
    "home_off_epa_5g": 0.07715238478453973,
    "away_off_epa_5g": -0.03853422312029216,
    "home_def_epa_allowed_5g": 0.11082058387587826,
    "away_def_epa_allowed_5g": 0.15619696026779553,
    "home_pass_rate_5g": 0.641309605244585,
    "away_pass_rate_5g": 0.634531746031746,
    "home_success_offense_5g": 0.46911189706385537,
    "away_success_offense_5g": 0.4487698412698412,
    "home_success_defense_allowed_5g": 0.44830264148670224,
    "away_success_defense_allowed_5g": 0.4419733093417304,
    "matchup_diff_off_epa_5g": 0.11568660790483189,
    "matchup_diff_def_epa_allowed_5g": 0.04537637639191727,
    "matchup_diff_success_rate_5g": 0.007006361824521162,
    "matchup_diff_pressure_generated_5g": -0.03653595368965387,
    "matchup_diff_pressure_allowed_5g": 0.05611447039317881,
    "matchup_diff_red_zone_td_rate_5g": 0.08034798534798532
  }
}
```

Out-of-contract fields populated on NflGameInputs: none (all None).

## 3. Transforms

- off_def_home raw/clamped: 0.017544 / 0.017544
- off_def_away raw/clamped: -0.042614 / -0.042614
- efficiency from indices ×16: 0.9625
- spread_signal (EPA pack, cap ±4.25): 1.3609
- 0.35 × spread_signal: 0.4763
- base_efficiency raw → clamped (±6.5): 1.4389 → 1.4389
- HFA (once): 1.05
- rest margin: 0.0
- regression_luck margin: -0.2548
- matchup home/away point alloc (NOT added to μ): 1.3424 / -0.5158

## 4. Scoring means → margin / total / wp

- μ_home = 24.4164
- μ_away = 22.1823
- predicted_margin (decomp) = 2.2341
- predicted_total (decomp) = 46.5987
- IF margin_mu (MC, blend=0) = 2.378799
- IF spread_home = -2.38 (= −margin_mu)
- IF total_mu / total_mean = 46.949228 / 46.95
- IF home_win_prob = 0.569  fair ML -132/132
- sigma = 10.0068
- MC vs decomp margin Δ = 0.1447 (sampling, not a second model)

## 5. Signed IF − DraftKings gaps (independent recompute)

- DK spread_home = -7.0 (home favored = negative)
- Δspread = 4.62  (positive = IF closer to pick'em / less home-bullish)
- Δtotal = -7.55
- Δwp = -0.1531
- IF fair home ML -132 vs market de-vig fair -260

## 6. Factor margin inventory

- `base_efficiency`: 1.4389 pts  available=True
- `home_field_advantage`: 1.05 pts  available=True
- `rest_travel`: 0.0 pts  available=True
- `injuries_depth`: 0.0 pts  available=False
- `weather_environment`: 0.0 pts  available=False
- `travel_schedule`: 0.0 pts  available=False
- `situational_flags`: 0.0 pts  available=True
- `regression_luck`: -0.2548 pts  available=True
- `kav_efficiency`: 0.0 pts  available=False
- `external_dvoa`: 0.0 pts  available=False
- `personnel_efficiency`: 0.0 pts  available=True
- `coach_aggression`: 0.0 pts  available=True
- `info_velocity`: 0.0 pts  available=True
- `travel_weather_interaction`: 0.0 pts  available=False
- `error_regime`: 0.0 pts  available=True

Sealed RESULTS replay match: {'margin_mu': True, 'total_mu': True, 'spread_home': True, 'home_win_prob': True, 'sigma': True, 'market_blend': True}

≠edge ≠CLV ≠betting. NFL NO-GO CERT=0.
