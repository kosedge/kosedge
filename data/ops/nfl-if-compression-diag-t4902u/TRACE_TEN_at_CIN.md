# TRACE 2026-W08-TEN@CIN

READ-ONLY replay of sealed IF (tip `6ca03716`). No math change.

## 1. Source ratings (through-W7 panel 340a06dd)

| side | team | record | games | rolling | off_idx | def_idx | off_epa_5g | def_epa_allowed_5g |
|---|---|---|---:|---:|---:|---:|---:|---:|
| home | CIN | 4-2 | 6 | 7 | 1.046667 | 1.053333 | 0.141630 | 0.003853 |
| away | TEN | 1-6 | 7 | 7 | 0.931429 | 0.948571 | -0.175716 | 0.044915 |

t5_source home/away = `team_strength_from_record` / `team_strength_from_record`. 2025 prior used: False / False.

## 2. Contract inputs (20 + context)

```json
{
  "context": {
    "game_id": "2026-W08-TEN@CIN",
    "home_team": "CIN",
    "away_team": "TEN",
    "matchup_season": 2026,
    "matchup_week": 8,
    "rest_days_home": 7.0,
    "rest_days_away": 7.0
  },
  "efficiency": {
    "offense_index_home": 1.0466666666666666,
    "offense_index_away": 0.9314285714285715,
    "defense_index_home": 1.0533333333333335,
    "defense_index_away": 0.9485714285714286,
    "home_off_epa_5g": 0.1416298707673455,
    "away_off_epa_5g": -0.17571582338495736,
    "home_def_epa_allowed_5g": 0.003852867335598237,
    "away_def_epa_allowed_5g": 0.04491469915341546,
    "home_pass_rate_5g": 0.6440853558598736,
    "away_pass_rate_5g": 0.5793370371877168,
    "home_success_offense_5g": 0.4909418977425443,
    "away_success_offense_5g": 0.38905798310097267,
    "home_success_defense_allowed_5g": 0.42583742101989375,
    "away_success_defense_allowed_5g": 0.4523699496030991,
    "matchup_diff_off_epa_5g": 0.31734569415230285,
    "matchup_diff_def_epa_allowed_5g": 0.041061831817817224,
    "matchup_diff_success_rate_5g": 0.06420822161238851,
    "matchup_diff_pressure_generated_5g": 0.0232005862503728,
    "matchup_diff_pressure_allowed_5g": -0.0680086825078336,
    "matchup_diff_red_zone_td_rate_5g": 0.2180495356037152
  }
}
```

Out-of-contract fields populated on NflGameInputs: none (all None).

## 3. Transforms

- off_def_home raw/clamped: 0.103414 / 0.103414
- off_def_away raw/clamped: -0.115732 / -0.115732
- efficiency from indices ×16: 3.5063
- spread_signal (EPA pack, cap ±4.25): 2.8150
- 0.35 × spread_signal: 0.9852
- base_efficiency raw → clamped (±6.5): 4.4916 → 4.4916
- HFA (once): 1.05
- rest margin: 0.0
- regression_luck margin: -1.264
- matchup home/away point alloc (NOT added to μ): 2.1704 / -1.5244

## 4. Scoring means → margin / total / wp

- μ_home = 24.9120
- μ_away = 20.6344
- predicted_margin (decomp) = 4.2776
- predicted_total (decomp) = 45.5464
- IF margin_mu (MC, blend=0) = 4.440978
- IF spread_home = -4.44 (= −margin_mu)
- IF total_mu / total_mean = 45.712953 / 45.71
- IF home_win_prob = 0.6218  fair ML -164/164
- sigma = 10.0068
- MC vs decomp margin Δ = 0.1634 (sampling, not a second model)

## 5. Signed IF − DraftKings gaps (independent recompute)

- DK spread_home = -12.5 (home favored = negative)
- Δspread = 8.06  (positive = IF closer to pick'em / less home-bullish)
- Δtotal = -0.79
- Δwp = -0.2153
- IF fair home ML -164 vs market de-vig fair -514

## 6. Factor margin inventory

- `base_efficiency`: 4.4916 pts  available=True
- `home_field_advantage`: 1.05 pts  available=True
- `rest_travel`: 0.0 pts  available=True
- `injuries_depth`: 0.0 pts  available=False
- `weather_environment`: 0.0 pts  available=False
- `travel_schedule`: 0.0 pts  available=False
- `situational_flags`: 0.0 pts  available=True
- `regression_luck`: -1.264 pts  available=True
- `kav_efficiency`: 0.0 pts  available=False
- `external_dvoa`: 0.0 pts  available=False
- `personnel_efficiency`: 0.0 pts  available=True
- `coach_aggression`: 0.0 pts  available=True
- `info_velocity`: 0.0 pts  available=True
- `travel_weather_interaction`: 0.0 pts  available=False
- `error_regime`: 0.0 pts  available=True

Sealed RESULTS replay match: {'margin_mu': True, 'total_mu': True, 'spread_home': True, 'home_win_prob': True, 'sigma': True, 'market_blend': True}

≠edge ≠CLV ≠betting. NFL NO-GO CERT=0.
