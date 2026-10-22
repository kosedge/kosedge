# t4149u — Deviation register (local nflverse path vs production)

The nflverse reconstruction is a **file-backed feature path**. It is **not**
a second NFL model. When `--base` is the `b1d857d3` worktree the sealed
runner imports `simulate_nfl_game` / `NflGameInputs` from that tree. Feature
construction is a **different code path** from warehouse ingest and must not
drift into a second rating book.

**Code reading only.** Builder / seal / W7 were not run. No values were
computed.

## SHAs read

| Ref                                        | Status on this clone                                                                                                                                                                                                         |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `20d51f220ce772545161ae5ce4ed22041110a150` | Present. Production files below are **byte-identical** to this commit (`git diff 20d51f22` empty on ingest / simulator / backbone / tasks / matchup / retrain / calibration).                                                |
| `b1d857d356d5afc422c86ffb1e9a25afdf2a4225` | **Not in this clone** (same unpublished-object fact as the IMV audits). Runner still **requires** BASE HEAD == this pin. Rows marked IDENTICAL assume that pin, citing `20d51f22` line numbers for the production functions. |

Local path cited: `scripts/nfl/imv/nfl_imv_v21.py`, `nfl_imv_v22.py`, `nfl_imv_v23.py`, `nfl-imv-sealed-v2.3.sh`.

## Model version and sim transform

| Item                             | Prod (`20d51f22`)                                                                               | Local                                                                                                                                | Status                                                                                                 |
| -------------------------------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| Model version string             | `DEFAULT_NFL_MODEL_VERSION = "nfl-v1.5-matchup-sim"` `nfl_simulator.py:14`                      | Runner `MODEL_VERSION="nfl-v1.5-matchup-sim"` `nfl-imv-sealed-v2.3.sh:47`; passed into `simulate_nfl_game(..., model_version=model)` | **IDENTICAL** function + string if BASE is `b1d857d3`                                                  |
| Sim entry                        | `simulate_nfl_game` `nfl_simulator.py:518`                                                      | `from src.services.nfl_simulator import NflGameInputs, simulate_nfl_game` `nfl-imv-sealed-v2.3.sh` (~669)                            | **IDENTICAL** import of BASE function                                                                  |
| Input dataclass                  | `NflGameInputs` `nfl_simulator.py:89-99` (defaults `offense_index_*=1.0`, `rest_days_*=7.0`)    | Same class. Local **refuses** those defaults: missing rest/index → no call (`try_sim` ~696–713)                                      | **IDENTICAL** type; **DEVIATES** on default policy (prod tasks.py:4882 / 5026 `or 7.0`; dataclass 1.0) |
| HFA                              | `HOME_FIELD_POINTS = 1.05` `calibration.py:42`; applied inside sim                              | `read_and_assert_hfa` imports that constant; mismatch BLOCKED                                                                        | **IDENTICAL** import of BASE constant                                                                  |
| Market blend                     | Prod may pass `market_spread_home` / `market_total` (documented 0.30)                           | `market_spread_home=None`, `market_total=None` (`try_sim` ~749–750). W8 MODEL-ONLY                                                   | **DEVIATES** — no close blend                                                                          |
| Call kwargs vs full FEATURE_KEYS | `tasks.py` passes matchup pack + KAV + injury nowcast + rest defaults into sim / supervised row | Local passes only rest + 4 EPA + 4 strength indices + injury **None**. Other `NflGameInputs` fields stay None                        | **DEVIATES** — same function, thinner kwargs                                                           |

## Strength-rating logic

| Step           | Prod                                                                                                                                              | Local                                                                                                                                                              | Status                                                             |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------ |
| Blend weight   | `prior_current_blend_weight` `efficiency_backbone.py:164` (`w_current = clamp(games/8,0,1)`)                                                      | `rebuild_strength_indices` calls the same function `nfl_imv_v22.py:378`                                                                                            | **IDENTICAL** function                                             |
| Package build  | `build_package_from_season_row` `efficiency_backbone.py:469` from warehouse rolling + ST-KAV + packaged priors                                    | Same function `nfl_imv_v22.py:346–377` from **local** weekly PBP rows                                                                                              | **IDENTICAL** function; **DEVIATES** inputs                        |
| Blend          | `blend_packages` `efficiency_backbone.py:659` + SOS / continuity / QB premium / packaged fill `tasks.py:1051–1200` (`_load_team_strength_priors`) | `blend_packages` only (`nfl_imv_v22.py:379`). No SOS, continuity, QB premium, ST-KAV, packaged-prior fill                                                          | **DEVIATES** — backbone call without warehouse overlays            |
| Indices        | `package_to_strength_indices` `efficiency_backbone.py:262` or `strength_payload_from_package`                                                     | `package_to_strength_indices` `nfl_imv_v22.py:380`                                                                                                                 | **IDENTICAL** function                                             |
| Prior season   | Warehouse 2025 rolling (`_fetch_rolling_feature_latest_rows`, CURRENT-ROW 5g) + packaged 2025 backbone                                            | 2025 REG weekly rates from pre-staged PBP, unweighted mean of weeks 1–18 (`_season_row_from_weekly` `nfl_imv_v22.py:249–283`). `prior_source=pbp_rolling_backbone` | **DEVIATES** — 2025-only PBP prior, not warehouse/packaged true-PR |
| Current season | Warehouse rolling week-capped (`week_cap_current = as_of_week`) still built with CURRENT ROW SQL                                                  | Current weeks `<= game_week-1` only                                                                                                                                | **DEVIATES** — lag-only current                                    |
| Miss           | Dataclass / `team_strength.py` default `offense_index=1.0`                                                                                        | Null + `FLAG_MISSING_TRUE_PR_PRIOR`; never emit 1.0 (`nfl_imv_v22.py:322–330`, `try_sim` ~711)                                                                     | **DEVIATES**                                                       |

## 41 FEATURE_KEYS

Schema list is the production contract: `nfl_supervised_retrain.py:30-72` (schema v3). Local names the same keys. **Construction is not the same path.**

Shared rolling deviations (apply to every `*_5g` rate unless a row says more):

1. Prod window: `ROWS BETWEEN 4 PRECEDING AND CURRENT ROW` `ingest.py:1310-1314` (includes game week).
2. Prod join: `h.season = s.season AND h.week = s.week` `ingest.py:1498-1501` (same-week leak).
3. Prod grain: weekly rates from `play_type IN ('pass','run')` `ingest.py:1059-1063`; 5g = SQL `AVG` of those **same-season** weekly rows (base CTE `WHERE season = :season` `ingest.py:1298`).
4. Local window: last 5 **played REG** team-weeks with `(season,week) < game` (`last_n_played_reg` / `attach_lagged_rolling_played` `nfl_imv_v22.py:151–246`). Current week excluded. Bye omitted. POST / `week>18` dropped. **2025 REG tail fills early 2026**.
5. Local weekly rates: `weekly_situational_from_pbp` `nfl_imv_v21.py:527–610` — **not** restricted to `play_type IN ('pass','run')`; uses `pass` / `sack` / `qb_hit` flags. Unweighted mean of weekly rates (`WEEKLY_AVG_RULE` in `nfl_imv_v23.py`).

| #   | Key                               | Status   | Notes                                                                                                                                                                                                                                                             |
| --- | --------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `week`                            | DEVIATES | Prod: warehouse `nfl_dp_schedules.week` / matchup pack (`tasks.py:5031`). Local: `games.csv` `week` via `_load_games_csv` `nfl_imv_v21.py:680`. Same nflverse column in spirit; different reader. Local parse is `W##` (`parse_product_week`), never `gid[8:10]`. |
| 2   | `home_off_epa_5g`                 | DEVIATES | Prod: CURRENT-ROW 5g + same-week join (`ingest.py:1320-1324`, `:1473`). Local: lag-only unweighted REG window + 2025 tail (`nfl_imv_v22.py:213-246`). Weekly EPA grain also differs (`ingest.py:1056` vs `nfl_imv_v21.py:574-576`).                               |
| 3   | `away_off_epa_5g`                 | DEVIATES | Same as #2, away side (`ingest.py:1474`).                                                                                                                                                                                                                         |
| 4   | `home_def_epa_allowed_5g`         | DEVIATES | Prod `ingest.py:1325-1334`, `:1475`. Local lag-only + grain (#2).                                                                                                                                                                                                 |
| 5   | `away_def_epa_allowed_5g`         | DEVIATES | Same as #4, away (`ingest.py:1476`).                                                                                                                                                                                                                              |
| 6   | `home_pressure_allowed_5g`        | DEVIATES | Prod dropback pressure `ingest.py:1114`, rolling `:1335-1344`, join `:1477`. Local: mean of `sack\|qb_hit` on `pass` flag (`nfl_imv_v21.py:571-588`).                                                                                                             |
| 7   | `away_pressure_allowed_5g`        | DEVIATES | Same as #6, away.                                                                                                                                                                                                                                                 |
| 8   | `home_pressure_generated_5g`      | DEVIATES | Prod `ingest.py:1115`, `:1479`. Local builds the 5g key (`SIDE_MAP`) but **does not pass it into** `simulate_nfl_game`.                                                                                                                                           |
| 9   | `away_pressure_generated_5g`      | DEVIATES | Same as #8.                                                                                                                                                                                                                                                       |
| 10  | `home_pass_rate_5g`               | DEVIATES | Prod: `pass_plays/offensive_plays` on `play_type='pass'` `ingest.py:1109`. Local: mean of `pass` flag (`nfl_imv_v21.py:567,580`) then lag window.                                                                                                                 |
| 11  | `away_pass_rate_5g`               | DEVIATES | Same as #10.                                                                                                                                                                                                                                                      |
| 12  | `home_early_down_pass_rate_5g`    | DEVIATES | Prod `ingest.py:1110`, `:1483`. Local `down∈{1,2}` + `pass` flag (`nfl_imv_v21.py:581-583`). Not passed to sim.                                                                                                                                                   |
| 13  | `away_early_down_pass_rate_5g`    | DEVIATES | Same as #12.                                                                                                                                                                                                                                                      |
| 14  | `home_red_zone_td_rate_5g`        | DEVIATES | Prod `yardline_100<=20` counts `ingest.py:1113`. Local same threshold (`nfl_imv_v21.py:584-586`) but different play filter + lag. Not passed to sim.                                                                                                              |
| 15  | `away_red_zone_td_rate_5g`        | DEVIATES | Same as #14.                                                                                                                                                                                                                                                      |
| 16  | `home_success_offense_5g`         | DEVIATES | Prod `ingest.py:1055`. Local success flag mean (`nfl_imv_v21.py:577-579`) + lag. Built; **not** in `try_sim` kwargs.                                                                                                                                              |
| 17  | `away_success_offense_5g`         | DEVIATES | Same as #16.                                                                                                                                                                                                                                                      |
| 18  | `home_success_defense_allowed_5g` | DEVIATES | Prod `ingest.py:1075`. Local builds 5g; not passed to sim.                                                                                                                                                                                                        |
| 19  | `away_success_defense_allowed_5g` | DEVIATES | Same as #18.                                                                                                                                                                                                                                                      |
| 20  | `diff_off_epa_5g`                 | DEVIATES | Prod: `h.off - a.off` `ingest.py:1491`. Local: `home - away` `nfl_imv_v22.py:539-548` on **lagged** sides. Same minus; different operands.                                                                                                                        |
| 21  | `diff_def_epa_allowed_5g`         | DEVIATES | Prod: **`away - home`** `ingest.py:1492`. Local: **`home - away`** `nfl_imv_v22.py:541`. Sign convention differs.                                                                                                                                                 |
| 22  | `diff_pressure_generated_5g`      | DEVIATES | Prod: `home - away` `ingest.py:1493`. Local: `home - away` on lagged generated. Built; not passed to sim.                                                                                                                                                         |
| 23  | `diff_pressure_allowed_5g`        | DEVIATES | Prod: **`away - home`** `ingest.py:1494`. Local: **`home - away`**. Sign convention differs.                                                                                                                                                                      |
| 24  | `diff_red_zone_td_rate_5g`        | DEVIATES | Prod `ingest.py:1495` home−away. Local home−away on lagged RZ. Not passed to sim.                                                                                                                                                                                 |
| 25  | `diff_success_rate_5g`            | DEVIATES | Prod: mean of `(home_off−away_off)` and `(away_def−home_def)` `nfl_matchup_features.py:153-158`. Local: `home_success_offense_5g - away_success_offense_5g` only (`nfl_imv_v22.py:545`).                                                                          |
| 26  | `home_kav_offense_5g`             | DEVIATES | Prod: warehouse KAV via matchup pack / `kav.build_weekly_lagged_features` `kav.py:172-184` (week−1). Local: `feat.setdefault(..., None)` `nfl_imv_v21.py:834-842`. **`kav.py` is never called.**                                                                  |
| 27  | `away_kav_offense_5g`             | DEVIATES | Same as #26.                                                                                                                                                                                                                                                      |
| 28  | `home_kav_defense_5g`             | DEVIATES | Same as #26.                                                                                                                                                                                                                                                      |
| 29  | `away_kav_defense_5g`             | DEVIATES | Same as #26.                                                                                                                                                                                                                                                      |
| 30  | `home_kav_net_5g`                 | DEVIATES | Same as #26.                                                                                                                                                                                                                                                      |
| 31  | `away_kav_net_5g`                 | DEVIATES | Same as #26.                                                                                                                                                                                                                                                      |
| 32  | `diff_kav_net_5g`                 | DEVIATES | Prod: home_net−away_net `tasks.py:5062-5068`. Local: always null (`nfl_imv_v21.py:830`).                                                                                                                                                                          |
| 33  | `home_injury_impact`              | DEVIATES | Prod supervised row: nowcast `or 0.0` `tasks.py:5028`. Sim path may pass nowcast (`tasks.py:4888`). Local: **null**, `FLAG_MISSING_KOSEDGE_INJURY_NOWCAST`; never `0.0`; raw `injuries_2026` refused (`injury_allowed_flagged` `nfl_imv_v21.py:405-438`).         |
| 34  | `away_injury_impact`              | DEVIATES | Same as #33.                                                                                                                                                                                                                                                      |
| 35  | `diff_injury_impact`              | DEVIATES | Prod: home−away of possibly-zeroed impacts `tasks.py:5088`. Local: null.                                                                                                                                                                                          |
| 36  | `home_rest_days`                  | DEVIATES | Prod: `rest_days_from_schedule` / date LAG, **`or 7.0`** `tasks.py:5026`. Local: nflverse `games.csv` `home_rest`; missing → BLOCKED, never 7.0 (`try_sim` ~696).                                                                                                 |
| 37  | `away_rest_days`                  | DEVIATES | Same as #36 (`away_rest` / `or 7.0`).                                                                                                                                                                                                                             |
| 38  | `diff_rest_days`                  | DEVIATES | Prod: home−away after 7.0 fill `tasks.py:5091`. Local: home−away only if both present (`nfl_imv_v22.py:503-507`).                                                                                                                                                 |
| 39  | `roof_dome`                       | DEVIATES | Prod: `1.0 if roof in {dome,closed} else 0.0` `tasks.py:5092` (missing roof → 0). Local: same `{dome,closed}` test (`nfl_imv_v22.py:508-512`) but **None** if roof missing. Reimplemented, not called.                                                            |
| 40  | `surface_turf`                    | DEVIATES | Prod: `"turf" in surface else 0.0` `tasks.py:5093`. Local: same substring (`nfl_imv_v22.py:513-517`) but None if surface missing.                                                                                                                                 |
| 41  | `is_divisional_game`              | DEVIATES | Prod: `NFL_TEAM_DIVISION` equality `tasks.py:5094`. Local: nflverse `div_game` numeric (`nfl_imv_v22.py:518`).                                                                                                                                                    |

**IDENTICAL feature-key constructions: none of 41.** Every key is a different reader, window, default, or omission. The **sim function** and **backbone helpers** remain IDENTICAL (table above) so this path does not become a second model.

## Parity coverage (14 vs remaining 27)

v2.2 `PARITY_KEYS` (`nfl_imv_v22.py:37-52`) — 14 names. v2.3 live compare is
**local week W vs prod week W-1, team-form only**
(`PARITY_TEAM_KEYS` `nfl_imv_v23.py:37-43`) and is
`NOT_RUN_NO_PROD_EXPORT` until a genuine sealed export exists. No builder
run; no values.

### Of the 14 — covered by the v2.3 join (10)

`home_off_epa_5g`, `away_off_epa_5g`, `home_def_epa_allowed_5g`,
`away_def_epa_allowed_5g`, `home_pass_rate_5g`, `away_pass_rate_5g`,
`home_success_offense_5g`, `away_success_offense_5g`,
`home_pressure_allowed_5g`, `away_pressure_allowed_5g`.

### Of the 14 — listed in v2.2, **not** in the v2.3 W−1 team join (4)

`home_rest_days`, `away_rest_days`, `diff_off_epa_5g`, `roof_dome`
(game-level; W vs W−1 team join does not apply).

### Remaining 27 FEATURE_KEYS — untested by any parity list

`week`,
`home_pressure_generated_5g`, `away_pressure_generated_5g`,
`home_early_down_pass_rate_5g`, `away_early_down_pass_rate_5g`,
`home_red_zone_td_rate_5g`, `away_red_zone_td_rate_5g`,
`home_success_defense_allowed_5g`, `away_success_defense_allowed_5g`,
`diff_def_epa_allowed_5g`, `diff_pressure_generated_5g`,
`diff_pressure_allowed_5g`, `diff_red_zone_td_rate_5g`, `diff_success_rate_5g`,
`home_kav_offense_5g`, `away_kav_offense_5g`, `home_kav_defense_5g`,
`away_kav_defense_5g`, `home_kav_net_5g`, `away_kav_net_5g`, `diff_kav_net_5g`,
`home_injury_impact`, `away_injury_impact`, `diff_injury_impact`,
`diff_rest_days`, `surface_turf`, `is_divisional_game`.

## What would make this a second model (forbidden)

- A local EPA→margin mapping that is not `simulate_nfl_game`
- A local `offense_index` formula that is not BASE `package_to_strength_indices`
- Shipping these lagged/unweighted/null-injury numbers as if they were warehouse true-PR
- Filling rest `7.0` / injury `0.0` / index `1.0` to “look like prod”

Plumbing-only Mac runs may call the **pinned** sim. They must keep the
deviation flags on every row.
