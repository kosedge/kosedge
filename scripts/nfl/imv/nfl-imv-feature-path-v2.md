# IMV local feature path v2 — file-backed, nflverse-only, feeds `b1d857d3`

**Ticket:** e0bdcc1a follow-on (W7 BLOCKED: `model_execution=NOT_RUN_NO_DB`).
**Do not run W7.** Targets: W4–W6 **RETROSPECTIVE** numbers, then W8 **PROSPECTIVE-RESEARCH** sealed before first W8 kickoff `2026-10-30T00:15:00Z` (`2026-W08-CAR@GB`).
**Pin:** `b1d857d356d5afc422c86ffb1e9a25afdf2a4225` (`nfl-v1.5-matchup-sim`, 41 `FEATURE_KEYS`, schema v3).
**Rule:** never default silently. Null model output ⇒ **BLOCKED**, but the snapshot still seals.
**Not this step:** prod DB, Railway, Odds key, `~/kosedge` checkout, W7 mode.

This is a design. No builder or runner was executed.

---

## 0. Feature-coverage table (41 v3 keys + sim extras)

Status is **sourced** only if a pre-staged, sha-pinned nflverse file can produce the value through BASE builders with **strict lag**. Unavailable keys are **flagged and left null** — never filled with `7.0` / `0.0` / `1.0`.

| Feature                                                   | Status                            | nflverse source                      | If missing / unused                                                                                   |
| --------------------------------------------------------- | --------------------------------- | ------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| `week`                                                    | sourced                           | `games.csv` `week`                   | `FLAG_MISSING_WEEK` → BLOCKED                                                                         |
| `home_off_epa_5g`                                         | sourced                           | PBP 2025+2026 → rolling 5g           | `FLAG_MISSING_EPA` → BLOCKED                                                                          |
| `away_off_epa_5g`                                         | sourced                           | PBP 2025+2026 → rolling 5g           | `FLAG_MISSING_EPA` → BLOCKED                                                                          |
| `home_def_epa_allowed_5g`                                 | sourced                           | PBP 2025+2026 → rolling 5g           | `FLAG_MISSING_EPA` → BLOCKED                                                                          |
| `away_def_epa_allowed_5g`                                 | sourced                           | PBP 2025+2026 → rolling 5g           | `FLAG_MISSING_EPA` → BLOCKED                                                                          |
| `home_pressure_allowed_5g`                                | sourced                           | PBP `sack`/`qb_hit` rolling          | `FLAG_MISSING_PRESSURE`                                                                               |
| `away_pressure_allowed_5g`                                | sourced                           | PBP `sack`/`qb_hit` rolling          | `FLAG_MISSING_PRESSURE`                                                                               |
| `home_pressure_generated_5g`                              | sourced                           | PBP `sack`/`qb_hit` rolling          | `FLAG_MISSING_PRESSURE`                                                                               |
| `away_pressure_generated_5g`                              | sourced                           | PBP `sack`/`qb_hit` rolling          | `FLAG_MISSING_PRESSURE`                                                                               |
| `home_pass_rate_5g`                                       | sourced                           | PBP pass/run rolling                 | `FLAG_MISSING_PASS_RATE`                                                                              |
| `away_pass_rate_5g`                                       | sourced                           | PBP pass/run rolling                 | `FLAG_MISSING_PASS_RATE`                                                                              |
| `home_early_down_pass_rate_5g`                            | sourced                           | PBP `down`∈{1,2}                     | `FLAG_MISSING_EARLY_DOWN`                                                                             |
| `away_early_down_pass_rate_5g`                            | sourced                           | PBP `down`∈{1,2}                     | `FLAG_MISSING_EARLY_DOWN`                                                                             |
| `home_red_zone_td_rate_5g`                                | sourced                           | PBP `yardline_100`+TD                | `FLAG_MISSING_RZ`                                                                                     |
| `away_red_zone_td_rate_5g`                                | sourced                           | PBP `yardline_100`+TD                | `FLAG_MISSING_RZ`                                                                                     |
| `home_success_offense_5g`                                 | sourced                           | PBP `success`                        | `FLAG_MISSING_SUCCESS`                                                                                |
| `away_success_offense_5g`                                 | sourced                           | PBP `success`                        | `FLAG_MISSING_SUCCESS`                                                                                |
| `home_success_defense_allowed_5g`                         | sourced                           | PBP `success`                        | `FLAG_MISSING_SUCCESS`                                                                                |
| `away_success_defense_allowed_5g`                         | sourced                           | PBP `success`                        | `FLAG_MISSING_SUCCESS`                                                                                |
| `diff_off_epa_5g`                                         | sourced                           | both EPA sides                       | `FLAG_MISSING_DIFF` (never 0)                                                                         |
| `diff_def_epa_allowed_5g`                                 | sourced                           | both EPA sides                       | `FLAG_MISSING_DIFF` (never 0)                                                                         |
| `diff_pressure_generated_5g`                              | sourced                           | both pressure sides                  | `FLAG_MISSING_DIFF` (never 0)                                                                         |
| `diff_pressure_allowed_5g`                                | sourced                           | both pressure sides                  | `FLAG_MISSING_DIFF` (never 0)                                                                         |
| `diff_red_zone_td_rate_5g`                                | sourced                           | both RZ sides                        | `FLAG_MISSING_DIFF` (never 0)                                                                         |
| `diff_success_rate_5g`                                    | sourced                           | both success sides                   | `FLAG_MISSING_DIFF` (never 0)                                                                         |
| `home_kav_offense_5g`                                     | sourced                           | PBP via `kav.py`, week−1             | `FLAG_KAV_LAGGED_NULL` (never 0)                                                                      |
| `away_kav_offense_5g`                                     | sourced                           | PBP via `kav.py`, week−1             | `FLAG_KAV_LAGGED_NULL` (never 0)                                                                      |
| `home_kav_defense_5g`                                     | sourced                           | PBP via `kav.py`, week−1             | `FLAG_KAV_LAGGED_NULL` (never 0)                                                                      |
| `away_kav_defense_5g`                                     | sourced                           | PBP via `kav.py`, week−1             | `FLAG_KAV_LAGGED_NULL` (never 0)                                                                      |
| `home_kav_net_5g`                                         | sourced                           | PBP via `kav.py`, week−1             | `FLAG_KAV_LAGGED_NULL` (never 0)                                                                      |
| `away_kav_net_5g`                                         | sourced                           | PBP via `kav.py`, week−1             | `FLAG_KAV_LAGGED_NULL` (never 0)                                                                      |
| `diff_kav_net_5g`                                         | sourced                           | both KAV nets, week−1                | `FLAG_KAV_LAGGED_NULL` (never 0)                                                                      |
| `home_rest_days`                                          | sourced                           | `games.csv` `home_rest`              | `FLAG_MISSING_REST` — never `7.0`                                                                     |
| `away_rest_days`                                          | sourced                           | `games.csv` `away_rest`              | `FLAG_MISSING_REST` — never `7.0`                                                                     |
| `diff_rest_days`                                          | sourced                           | both rest sides                      | `FLAG_MISSING_REST` — never `0`                                                                       |
| `roof_dome`                                               | sourced                           | `games.csv` `roof` ∈ {dome,closed}   | `FLAG_MISSING_ROOF` (do not assume outdoor)                                                           |
| `surface_turf`                                            | sourced                           | `games.csv` `surface` contains turf  | `FLAG_MISSING_SURFACE`                                                                                |
| `is_divisional_game`                                      | sourced                           | `games.csv` `div_game` or BASE map   | `FLAG_MISSING_DIV`                                                                                    |
| `home_injury_impact`                                      | **unavailable**                   | raw `injuries_2026` ≠ Kos nowcast    | `FLAG_MISSING_KOSEDGE_INJURY_NOWCAST` — never `0.0`                                                   |
| `away_injury_impact`                                      | **unavailable**                   | raw `injuries_2026` ≠ Kos nowcast    | `FLAG_MISSING_KOSEDGE_INJURY_NOWCAST` — never `0.0`                                                   |
| `diff_injury_impact`                                      | **unavailable**                   | derived from nowcast                 | `FLAG_MISSING_KOSEDGE_INJURY_NOWCAST` — never `0.0`                                                   |
| `offense_index_*` / `defense_index_*` (warehouse true-PR) | **unavailable as warehouse SoT**  | not in games/PBP alone               | `FLAG_MISSING_TRUE_PR_PRIOR` — never dataclass `1.0`; optional local backbone rebuild only (see §5.3) |
| Injury multipliers / info velocity                        | **unavailable**                   | Kos nowcast                          | `FLAG_MISSING_INJURY_OVERLAY` — never `1.0`/`0.0`                                                     |
| Live weather                                              | **unavailable**                   | Open-Meteo; post-game temp/wind only | W8 `FLAG_MISSING_WEATHER`; W4–W6 `WEATHER_POSTGAME` if used                                           |
| Travel miles / TZ                                         | **unavailable**                   | not in schedules                     | `FLAG_MISSING_TRAVEL` — never `0`                                                                     |
| Personnel / coach / ST-KAV                                | **unavailable**                   | not v3 keys                          | `FLAG_ABSENT_V3` — omit, do not zero                                                                  |
| Live / owned closes                                       | **unavailable** for W8 MODEL-ONLY | Odds / warehouse                     | omit columns; W4–W6 may attach `market_close_nflverse` for grading only                               |
| HFA `+1.05`                                               | model-applied, must declare       | BASE `HOME_FIELD_POINTS`             | `hfa_declared=true` or `HFA_UNDECLARED`; intl `FLAG_HFA_ON_NEUTRAL` → BLOCKED                         |
| Hand-entered news                                         | **forbidden**                     | —                                    | `hand_entered_news=false`                                                                             |

Counts: **38 sourced** (31 rolling/KAV + week + 3 rest + 3 venue/div) · **3 v3 keys unavailable** (injury trio) · sim extras flagged as above.

---

## 1. Why v1 could not print numbers

`simulate_nfl_game` + supervised blend on `b1d857d3` read warehouse tables (`nfl_dp_matchup_features_weekly`, rolling features, true-PR priors, injury nowcast, weather). The sealed run forbids `DATABASE_URL`. v1 therefore set `model_execution=NOT_RUN_NO_DB` and wrote nulls. e0bdcc1a correctly BLOCKED.

A compliant route is a **non-prod local feature store** built only from **pre-staged, sha-pinned nflverse files**, then fed into the **unpatched BASE worktree** of `b1d857d3`.

```text
[pre-stage, network ON]  nflverse releases → files + sha + cutoff + tag
        ↓
[feature-build, network OFF]  BASE code + local sqlite/jsonl  (not sealed)
        ↓
[sealed v2, network DENY]  read store → call BASE model → seal (BLOCKED if any null)
```

The feature-build is **not** the sealed run. The sealed run never fetches.

---

## 2. Layout

| Stage         | Path                                                                             | Network | Writes git? |
| ------------- | -------------------------------------------------------------------------------- | ------- | ----------- |
| Pre-stage     | `/var/tmp/nfl-imv-prestage-nflverse/<UTC>/`                                      | yes     | no          |
| Feature store | `/var/tmp/nfl-imv-features/<UTC>/imv-local.sqlite` + `features.jsonl`            | no      | no          |
| BASE          | **parameter**, dedicated worktree of `b1d857d3`, **not** `~/kosedge`, no patches | no      | no          |
| W4–W6 seal    | `/var/tmp/nfl-imv-sealed-v2-retrospective-w4w6/<UTC>/`                           | deny    | no          |
| W8 seal       | `/var/tmp/nfl-imv-sealed-v2-w8-pregame/<UTC>/`                                   | deny    | no          |

`LATEST` must be a **symlink to the stamp directory** (P-b). A text-file pointer is accepted only as fallback:

```text
# correct
IMV_MANIFEST=/var/tmp/nfl-imv-prestage-nflverse/LATEST/imv-manifest.tsv
# equivalent if LATEST is still a v1 text file
IMV_MANIFEST="$(tr -d '\n' < /var/tmp/nfl-imv-prestage-nflverse/LATEST)/imv-manifest.tsv"
```

v1 published `…/LATEST/imv-w7-manifest.tsv` while writing `LATEST` as a **file**. That path does not exist. v2 resolves both.

---

## 3. Exact nflverse files to pre-stage (sha-pin)

Ryan approved nflverse read-only. Fetch is a **separate** script, same metadata contract as t4139u (tag, URL, retrieval_utc, data_cutoff, sha256).

### 3.1 Schedules / scores / rest / venue (release tag `schedules`)

| File             | URL                                                                                    |
| ---------------- | -------------------------------------------------------------------------------------- |
| `games.csv`      | `https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv`      |
| `games.parquet`  | `https://github.com/nflverse/nflverse-data/releases/download/schedules/games.parquet`  |
| `timestamp.json` | `https://github.com/nflverse/nflverse-data/releases/download/schedules/timestamp.json` |
| `timestamp.txt`  | `https://github.com/nflverse/nflverse-data/releases/download/schedules/timestamp.txt`  |

There is **no** `sched_2026.csv` asset on this release.

**W4–W6 finals:** `season=2026`, `week∈{4,5,6}`, `game_type=REG`, numeric `home_score`+`away_score`. Any not final ⇒ feature-build and sealed run **BLOCKED**.

**W8 schedule:** same file, week 7 must be final before W8 features that lag W7 PBP; week 8 scores must be empty at seal.

### 3.2 Play-by-play (release tag `pbp`) — required for EPA / KAV / rolling 5g

Rolling windows in `ingest.py` are `PARTITION BY team ORDER BY season, week ROWS BETWEEN 4 PRECEDING AND CURRENT ROW`. 2026 W4 5g therefore needs **2025 tail + 2026 W1–W3**. W8 needs **2025 tail + 2026 W1–W7**.

| File                        | URL                                                                                         |
| --------------------------- | ------------------------------------------------------------------------------------------- |
| `play_by_play_2025.parquet` | `https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2025.parquet` |
| `play_by_play_2026.parquet` | `https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2026.parquet` |

CSV twins are optional sha-pins (`play_by_play_YYYY.csv`). Do not use a partial 2026 PBP without flagging `PBP_INCOMPLETE_WEEK`.

PBP columns the BASE situational/KAV path actually reads: `season,week,game_id,play_type,posteam,defteam,home_team,away_team,epa,success,yards_gained,pass,rush,down,yardline_100,touchdown,sack,qb_hit,complete_pass,cp,score_differential`.

### 3.3 Injuries (release tag `injuries`) — raw reports only

| File                    | URL                                                                                          |
| ----------------------- | -------------------------------------------------------------------------------------------- |
| `injuries_2026.parquet` | `https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2026.parquet` |

This is **not** Kos `impact_score`. It cannot feed `home_injury_impact` without a separate, named nowcast. If fetched, store as `raw_injury_report` and still flag `MISSING_KOSEDGE_INJURY_NOWCAST`. If not fetched, flag `MISSING_INJURY_INPUT`. Never write `0.0`.

### 3.4 Not fetched

Odds API, Railway, prod dump, Open-Meteo, hand-entered news, `depth_charts` (not a v3 key), `stats_team` (PBP is the EPA SoT on this pin).

---

## 4. Local store (feeds BASE, not prod)

**Preferred:** SQLite `imv-local.sqlite` with the **same column names** BASE SQL expects, populated by BASE functions pointed at this file (env `IMV_LOCAL_SQLITE=…`, never `DATABASE_URL`).

Minimum tables:

| Table                                 | Source file                                                           | Used for                                                |
| ------------------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------- |
| `nfl_dp_schedules`                    | `games.csv`                                                           | week, rest, roof, surface, div, scores, nflverse closes |
| `nfl_dp_play_by_play`                 | PBP 2025+2026                                                         | situational + KAV                                       |
| `nfl_dp_team_situational_weekly`      | built from PBP via BASE ingest semantics                              | rolling inputs                                          |
| `nfl_dp_team_rolling_features_weekly` | same 3g/5g windows as `ingest.py:1273+`                               | EPA pack                                                |
| `nfl_dp_matchup_features_weekly`      | join rolling ↔ schedule, **strict lag** (as-of week−1 for game week) | sim + supervised                                        |
| `kav_weekly`                          | `kav.build_weekly_lagged_features` (as-of week−1 only)                | KAV keys                                                |

**File-backed twin (required even if sqlite exists):** `features.jsonl` one row per game, plus `feature-flags.jsonl` one flag per missing/default-risk field. Both sha-pinned in the feature-store manifest.

Lag rule (from `kav.py:172-194`): week-1 only. Week 1 ⇒ KAV fields **null + flagged**, not zero. Same-week PBP must not enter a week’s features.

W4 production code **skips supervised** for `week<=4` (`tasks.py:4993-4995`). v2 must **flag** `SUPERVISED_SKIPPED_WEEK_LE_4` on W4. It may still emit MC-sim means if priors+EPA exist. It must not silently run the 85% blend.

---

## 5. Feature ledger — 41 v3 keys + sim inputs

`FEATURE_KEYS` from `nfl_supervised_retrain.py:30-72` / `nfl-kav-supervised-retrain-v3.json`.

### 5.1 Can source from pre-staged nflverse (via BASE builders)

| Key                                                                                                                                           | File                                                   | How                                                     | If missing                                                                        |
| --------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `week`                                                                                                                                        | `games.csv`                                            | schedule week                                           | `FLAG_MISSING_WEEK` → BLOCKED                                                     |
| `home_off_epa_5g` `away_off_epa_5g`                                                                                                           | PBP → situational → rolling 5g                         | `off_epa_per_play_5g`                                   | `FLAG_MISSING_EPA` → do not invent; BLOCKED if either side null                   |
| `home_def_epa_allowed_5g` `away_def_epa_allowed_5g`                                                                                           | same                                                   | `def_epa_allowed_per_play_5g`                           | `FLAG_MISSING_EPA`                                                                |
| `home_pressure_allowed_5g` `away_pressure_allowed_5g`                                                                                         | PBP `sack`/`qb_hit`                                    | rolling                                                 | `FLAG_MISSING_PRESSURE`                                                           |
| `home_pressure_generated_5g` `away_pressure_generated_5g`                                                                                     | same                                                   | rolling                                                 | `FLAG_MISSING_PRESSURE`                                                           |
| `home_pass_rate_5g` `away_pass_rate_5g`                                                                                                       | PBP pass/run                                           | rolling                                                 | `FLAG_MISSING_PASS_RATE`                                                          |
| `home_early_down_pass_rate_5g` `away_early_down_pass_rate_5g`                                                                                 | PBP `down`∈{1,2}                                       | rolling                                                 | `FLAG_MISSING_EARLY_DOWN`                                                         |
| `home_red_zone_td_rate_5g` `away_red_zone_td_rate_5g`                                                                                         | PBP `yardline_100`+TD                                  | rolling                                                 | `FLAG_MISSING_RZ`                                                                 |
| `home_success_offense_5g` `away_success_offense_5g`                                                                                           | PBP `success`                                          | rolling                                                 | `FLAG_MISSING_SUCCESS`                                                            |
| `home_success_defense_allowed_5g` `away_success_defense_allowed_5g`                                                                           | same                                                   | rolling                                                 | `FLAG_MISSING_SUCCESS`                                                            |
| `diff_off_epa_5g` `diff_def_epa_allowed_5g` `diff_pressure_generated_5g` `diff_pressure_allowed_5g` `diff_red_zone_td_rate_5g`                | derived                                                | only if **both** sides present                          | `FLAG_MISSING_DIFF` (never 0)                                                     |
| `diff_success_rate_5g`                                                                                                                        | derived in `matchup_pack_to_sim_input_kwargs`          | both success sides                                      | `FLAG_MISSING_DIFF`                                                               |
| `home_kav_offense_5g` `away_kav_offense_5g` `home_kav_defense_5g` `away_kav_defense_5g` `home_kav_net_5g` `away_kav_net_5g` `diff_kav_net_5g` | PBP via `kav.py`, **week−1**                           | null on week 1 / missing history                        | `FLAG_KAV_LAGGED_NULL` (never 0)                                                  |
| `home_rest_days` `away_rest_days` `diff_rest_days`                                                                                            | `games.csv` `home_rest`/`away_rest`                    | numeric only                                            | `FLAG_MISSING_REST` — **never** `7.0` (`tasks.py:4882` default is forbidden here) |
| `roof_dome`                                                                                                                                   | `games.csv` `roof`                                     | `1` iff `roof∈{dome,closed}` else `0` if roof present   | `FLAG_MISSING_ROOF` (do not assume outdoor)                                       |
| `surface_turf`                                                                                                                                | `games.csv` `surface`                                  | `1` iff `"turf" in surface` else `0` if surface present | `FLAG_MISSING_SURFACE`                                                            |
| `is_divisional_game`                                                                                                                          | `games.csv` `div_game` **or** BASE `NFL_TEAM_DIVISION` | only if one of those is present                         | `FLAG_MISSING_DIV`                                                                |

### 5.2 Cannot source from nflverse — flag, do not fill

| Key / input                                                    | Why not                                                                                                                  | Flag                                                                                                                                                                                     | Forbidden silent value                 |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| `home_injury_impact` `away_injury_impact` `diff_injury_impact` | Kos nowcast `impact_score` is not an nflverse column. Raw IR/Out reports ≠ the nowcast.                                  | `FLAG_MISSING_KOSEDGE_INJURY_NOWCAST`                                                                                                                                                    | `0.0` (`tasks.py:5028`)                |
| Injury multipliers / info velocity                             | same nowcast                                                                                                             | `FLAG_MISSING_INJURY_OVERLAY`                                                                                                                                                            | `1.0` / `0.0`                          |
| `offense_index_*` `defense_index_*` as **warehouse true-PR**   | `_load_team_strength_priors` also wants packaged 2025 backbone, SOS, QB premium, continuity — not in games.csv/PBP alone | `FLAG_MISSING_TRUE_PR_PRIOR`                                                                                                                                                             | dataclass `1.0`                        |
| Weather (wind/precip/temp live)                                | Open-Meteo; `games.csv` temp/wind only after the game                                                                    | W8: `FLAG_MISSING_WEATHER`. W4–W6: may use post-game nflverse temp/wind **only if present**, labelled `nflverse_postgame_weather` (RETROSPECTIVE leakage risk — flag `WEATHER_POSTGAME`) | `weather_available=false` without flag |
| Travel miles / TZ                                              | not in nflverse schedules                                                                                                | `FLAG_MISSING_TRAVEL`                                                                                                                                                                    | `0`                                    |
| Personnel / coach / ST-KAV                                     | not in v3 keys; warehouse second-order                                                                                   | `FLAG_ABSENT_V3` (omit; do not zero)                                                                                                                                                     | `0.0`                                  |
| Live / owned closes                                            | Odds / warehouse                                                                                                         | W8: omit (MODEL-ONLY). W4–W6: nflverse `spread_line`/`total_line` allowed as **`market_close_nflverse`** for grading only, never PLAY                                                    | invented lines                         |
| Hand-entered news                                              | forbidden                                                                                                                | `hand_entered_news=false`                                                                                                                                                                | any news text                          |

### 5.3 True-PR / offense_index — the only compliant construction

Do **not** pass `offense_index=1.0`.

Compliant path, all local:

1. Materialize 2025 + 2026 rolling tables from pre-staged PBP (BASE `materialize_matchup_features_from_usage` semantics).
2. Call BASE `efficiency_backbone.build_package_from_season_row` + `blend_packages` + `prior_current_blend_weight` (`w_current = clamp(team_completed_reg/8,0,1)`) on those rows, week-capped.
3. Stamp `prior_source=pbp_rolling_backbone`, `as_of_week`, input shas.
4. If backbone import or prior-season rows fail → **do not call** `simulate_nfl_game`. Flag `FLAG_MISSING_TRUE_PR_PRIOR`. Null outputs. BLOCKED.

That is still the `b1d857d3` model: same functions, file-backed rows, no prod DB.

### 5.4 HFA — declare, do not hide

BASE `HOME_FIELD_POINTS = 1.05` (`nfl_season_engine/calibration.py:42`) is applied inside the pin’s decomposition. A real call **will** add it.

| Action                             | Required                                                                                                          |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Call the model                     | set `hfa_declared=true`, `hfa_points_applied=1.05`, `hfa_source=b1d857d3_HOME_FIELD_POINTS`                       |
| International / `location=Neutral` | `FLAG_HFA_ON_NEUTRAL` — do not silently keep 1.05; do not silently zero. BLOCKED unless Ryan names a neutral rule |
| Not calling the model              | `hfa_points_applied=null`, `HFA_UNDECLARED`                                                                       |

### 5.5 Market blend

Documented blend weight `0.30`. W8 is MODEL-ONLY: **do not** pass `market_spread_home` / `market_total` into `simulate_nfl_game` (that would shrink toward a line). W4–W6 RETROSPECTIVE: nflverse close may be attached **after** the raw sim for grading; passing it into the sim is a blend — flag `BLEND_USED_NFLVERSE_CLOSE` if you do, or keep raw and flag `BLEND_NOT_APPLIED`. Never invent a close.

---

## 6. What “real numbers” means for each target

### W4–W6 RETROSPECTIVE

- Scores: nflverse `games.csv` finals (required).
- Features: PBP through **week−1** of that game (no same-week leak).
- W4: MC sim only if priors exist; supervised **skipped + flagged**.
- W5–W6: supervised only if all 41 keys are present **or** injury keys are explicitly NaN (HGB-native) **and** flagged `SUPERVISED_INJURY_NAN` — never `0.0`.
- Output: `model_spread_home`, `model_total`, `model_home_win_prob` from BASE. Any null ⇒ BLOCKED.
- Grading columns: nflverse closes + scores. `record_class=RETROSPECTIVE`. No PLAY.

### W8 PROSPECTIVE-RESEARCH

- Seal before `2026-10-30T00:15:00Z`. Exclude `kickoff_utc <= capture_ts`.
- W6+W7 finals required (nflverse). W7 PBP required for W8 5g.
- MODEL-ONLY: no edge/play/line columns.
- Same null⇒BLOCKED rule.
- `record_class=PROSPECTIVE-RESEARCH`. Re-run = new snapshot.

---

## 7. Builder contract (not the seal; do not run tonight)

`nfl-imv-feature-build-v2.sh --base $BASE --prestage $PRESTAGE_DIR --out /var/tmp/nfl-imv-features/<UTC>`

1. Refuse if BASE is `~/kosedge` or dirty or HEAD ≠ pin.
2. Read only sha-pinned files from the pre-stage manifest.
3. Build sqlite + `features.jsonl` + `feature-flags.jsonl`.
4. Every cell that would have used a BASE default (`7.0`, `0.0`, `1.0`, silent HFA) is **omitted** and flagged instead.
5. Write `SHA256SUMS` last. Point ` /var/tmp/nfl-imv-features/LATEST` → this dir (**symlink**).

v2 sealed runner **reads** that store. It does not build it. It does not fetch.

---

## 8. Call rule (v2)

Invoke `simulate_nfl_game` from `BASE/services/model-service` only when:

- rest both sides numeric (nflverse),
- EPA 5g both sides numeric,
- offense/defense indices from the backbone path above (not `1.0`),
- HFA declared,
- injury overlays **omitted** (None), not zeroed,
- W8: no market lines passed in.

Otherwise skip the call, write nulls, flag, **BLOCKED**, **still seal**.

---

## t4141u

No seal deadline. NFL is the enterprise model standard; correctness over speed. This design remains the approved local input architecture. Cron/Beat/deploy stay with Platform Reliability.
