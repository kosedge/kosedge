# TRACE 2026-W08-IND@JAX

READ-ONLY replay of sealed IF (tip `6ca03716`). No math change.

## 1. Source ratings (through-W7 panel 340a06dd)

| side | team | record | games | rolling | off_idx | def_idx | off_epa_5g | def_epa_allowed_5g |
|---|---|---|---:|---:|---:|---:|---:|---:|
| home | JAX | 4-2 | 6 | 6 | 1.046667 | 1.053333 | 0.122700 | -0.012123 |
| away | IND | 2-5 | 7 | 7 | 0.962857 | 0.977143 | -0.082550 | -0.065378 |

t5_source home/away = `team_strength_from_record` / `team_strength_from_record`. 2025 prior used: False / False.

## 2. Contract inputs (20 + context)

```json
{
  "context": {
    "game_id": "2026-W08-IND@JAX",
    "home_team": "JAX",
    "away_team": "IND",
    "matchup_season": 2026,
    "matchup_week": 8,
    "rest_days_home": 7.0,
    "rest_days_away": 7.0
  },
  "efficiency": {
    "offense_index_home": 1.0466666666666666,
    "offense_index_away": 0.9628571428571429,
    "defense_index_home": 1.0533333333333335,
    "defense_index_away": 0.9771428571428572,
    "home_off_epa_5g": 0.12270003442291666,
    "away_off_epa_5g": -0.08254972582438688,
    "home_def_epa_allowed_5g": -0.012122877362661068,
    "away_def_epa_allowed_5g": -0.06537807130831466,
    "home_pass_rate_5g": 0.5596690298271362,
    "away_pass_rate_5g": 0.5658243542449849,
    "home_success_offense_5g": 0.45670829553274583,
    "away_success_offense_5g": 0.41557848674750997,
    "home_success_defense_allowed_5g": 0.4220416851390831,
    "away_success_defense_allowed_5g": 0.37789898590284315,
    "matchup_diff_off_epa_5g": 0.20524976024730354,
    "matchup_diff_def_epa_allowed_5g": -0.05325519394565359,
    "matchup_diff_success_rate_5g": -0.0015064452255020289,
    "matchup_diff_pressure_generated_5g": -0.025702729923931356,
    "matchup_diff_pressure_allowed_5g": 0.006033546539722184,
    "matchup_diff_red_zone_td_rate_5g": 0.012450980392156863
  }
}
```

Out-of-contract fields populated on NflGameInputs: none (all None).

## 3. Transforms

- off_def_home raw/clamped: 0.071150 / 0.071150
- off_def_away raw/clamped: -0.085895 / -0.085895
- efficiency from indices ×16: 2.5127
- spread_signal (EPA pack, cap ±4.25): 0.7525
- 0.35 × spread_signal: 0.2634
- base_efficiency raw → clamped (±6.5): 2.7761 → 2.7761
- HFA (once): 1.05
- rest margin: 0.0
- regression_luck margin: -0.038
- matchup home/away point alloc (NOT added to μ): 0.5637 / -0.4200

## 4. Scoring means → margin / total / wp

- μ_home = 24.2718
- μ_away = 20.4837
- predicted_margin (decomp) = 3.7881
- predicted_total (decomp) = 44.7556
- IF margin_mu (MC, blend=0) = 3.637151
- IF spread_home = -3.64 (= −margin_mu)
- IF total_mu / total_mean = 44.774149 / 44.77
- IF home_win_prob = 0.6085  fair ML -155/155
- sigma = 10.0068
- MC vs decomp margin Δ = -0.1509 (sampling, not a second model)

## 5. Signed IF − DraftKings gaps (independent recompute)

- DK spread_home = -10.0 (home favored = negative)
- Δspread = 6.36  (positive = IF closer to pick'em / less home-bullish)
- Δtotal = -1.73
- Δwp = -0.1915
- IF fair home ML -155 vs market de-vig fair -400

## 6. Factor margin inventory

- `base_efficiency`: 2.7761 pts  available=True
- `home_field_advantage`: 1.05 pts  available=True
- `rest_travel`: 0.0 pts  available=True
- `injuries_depth`: 0.0 pts  available=False
- `weather_environment`: 0.0 pts  available=False
- `travel_schedule`: 0.0 pts  available=False
- `situational_flags`: 0.0 pts  available=True
- `regression_luck`: -0.038 pts  available=True
- `kav_efficiency`: 0.0 pts  available=False
- `external_dvoa`: 0.0 pts  available=False
- `personnel_efficiency`: 0.0 pts  available=True
- `coach_aggression`: 0.0 pts  available=True
- `info_velocity`: 0.0 pts  available=True
- `travel_weather_interaction`: 0.0 pts  available=False
- `error_regime`: 0.0 pts  available=True

Sealed RESULTS replay match: {'margin_mu': True, 'total_mu': True, 'spread_home': True, 'home_win_prob': True, 'sigma': True, 'market_blend': True}

≠edge ≠CLV ≠betting. NFL NO-GO CERT=0.
