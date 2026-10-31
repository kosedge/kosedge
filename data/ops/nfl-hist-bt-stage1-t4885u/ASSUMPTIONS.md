# ASSUMPTIONS — Hist BT Stage-1 t4885u

EVAL_ONLY reconstruction audit. No scoring. No IF invoke. No fit/tune.

Every derivation rule used (or refused) is listed here. Silent defaults are forbidden.

## Sample

- Source: walkforward `games.csv` pin **4fe1cdd7**
  (`data/ops/nfl-t4422u-walkforward-pergame-unblended-2013-2023/games.csv`
  @ `origin/cursor/t4422u-walkforward-pergame-export-f36b` tip `82ffb211`).
- Re-hashed this run: **MATCH** `4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8`.
- Rule: all REG rows with `season=2017` and `week∈{1,2}` and a present `kickoff_utc`.
- N = **31** (W1=15, W2=16). 2017 W1 is 15 in the pin because MIA@TB was postponed; that game is **not** added.
- `selection_hash` sealed in `SELECTION_HASH_SEAL.json` **before** `RECON_MATRIX.csv` was written.
- Recipe: `sha256(utf-8 of sorted canonical game_id list joined by "\n" with trailing "\n")`.
- Hash: `b088b83286d46be53d05206ad2d2ccc19f460cb0eb77ed14050ab7285552df39`.

## Contract (b41f4b43)

- Text: `ALEX_E1_EFFICIENCY_CONTRACT_t4770u_v2.md`
  @ `origin/cursor/hift1-efficiency-recovery-f693`
  sha256 **b41f4b43e1367bd5658c743475b9b84535c65395630a0b06c804f8b3552b81f4**.
- PASS_CONTRACT: `IMV_GRADE_t4770u_E1_EFFICIENCY_CONTRACT_v2.txt` sha256 **1a53bbd3…** ≠ DATA ACCEPT ≠ emit.
- Required efficiency fields: the 20 listed in §3.
- Required context: `game_id`, `home_team`, `away_team`, `matchup_season`, `matchup_week`, `rest_days_home`, `rest_days_away`.
- Catch-all: any other `NflGameInputs` field is OUT_OF_CONTRACT and must stay unset. Those fields are **not** rows in `RECON_MATRIX.csv` (they were never populated).

## As-of (cf514078)

- Identity: PASS_ASOF_BOUNDARY **cf514078** tip `1010b86f`.
- Module: `services/model-service/src/services/nfl_pregame_asof.py` sha256 **7dc6afea…**.
- Rule used: a candidate game may enter a field’s infoset only if its `kickoff_utc` is strictly `<` the target `kickoff_utc`.
- Contiguous pipeline: `rating_week = target_week - 1`. Week 1 has **no** same-season rating week (`contiguous_pregame_rating_week` raises). Documented; not filled from week 2 or from a latest-week substitute.
- Week 2: `rating_week = 1`. Game-specific cutoff = that game’s `kickoff_utc` (listed on every matrix row and in `SAMPLE_MANIFEST.json`).
- Earliest W2 kickoff `2017_02_HOU_CIN` `2017-09-15T00:25:00Z` is after latest W1 kickoff `2017_01_LAC_DEN` `2017-09-12T02:20:00Z`. All W1 games are therefore as-of-legal for every W2 target.

## Field rules

### Identity (5 fields)

**Status:** `DERIVED_PREGAME` for all 31 games.

- Taken from the sealed `games.csv` row: `game_id`, `home`, `away`, `season=2017`, `week`.
- `LA→LAR`, `WAS→WSH` only as already labeled in the pin (export home/away already use LAR/WSH).
- Not invented. Not substituted from a different week.

### rest_days_home / rest_days_away

**Status:** `DERIVED_PREGAME` for all 31 games.

- Contract §3: schedule-derived via `rest_days_from_schedule`.
- IF consume lineage used here is the **v3 ET heuristic** (`155d3ca0`): America/New_York kick **local** weekday.
  - Thursday → 4.0
  - Monday → 6.0
  - else → 7.0
- Same value on home and away (target-kickoff DOW, not days-since-that-team’s-last-game).
- `games.csv` columns `rest_days_*` are hardcoded `7.0` and were **not** used.
- The silent `7.0` fallback on missing/unparseable kickoff was **not** used (every sample row has a `Z` timestamp).
- UTC-DOW contrast (`nfl_data.rest_days_from_schedule` @ sha256 `2989a556…`) is recorded on the manifest. Mismatch games: `2017_01_KC_NE`, `2017_01_NYG_DAL`, `2017_01_LAC_DEN`, `2017_02_HOU_CIN`, `2017_02_GB_ATL`, `2017_02_DET_NYG`. Primary value is ET.

### T5 — offense_index_* / defense_index_*

Contract T5: `team_strength_from_record` on **same-season** W-L through completed games; ties ignored;
`off = clamp(0.90 + 0.22·wp, 0.82, 1.18)`, `def = clamp(0.92 + 0.20·wp, 0.82, 1.20)`.
Malformed record → code returns `1.0` = silent default → **not applied**.

**Week 1 (all 15 games, both sides): `MISSING_RECORD`.**

- Zero completed 2017 games as-of each W1 kickoff.
- `0-0` in `games.csv` `record_entering_*` maps inside the helper to `0.90 / 0.92` via `games = max(1, 0+0)`. That is an empty-record mapping, **not** a prior-season/preseason baseline. Not applied.
- Owner rule: Week 1 requires a valid preseason and/or prior-season (2016) baseline **per contract**. Contract T5 is same-season W-L. Contract §5 forbids prior-season efficiency substitution. Therefore 2016 W-L was **not** substituted into T5.
- 2016 REG **schedule** is present in `games.csv` (256 games, 32 teams) — availability evidence only.
- 2017 `LAC` has 2016 rows under `SD`. Franchise rename recorded; **not** applied as a fill.
- Later-2017 information was not used.

**Week 2: `DERIVED_PREGAME` when the side has ≥1 completed 2017 REG game with kickoff < target; else `MISSING_RECORD`.**

- W-L recomputed from `historical_oos_games.csv` **1ee90fac** scores joined to `games.csv` kickoffs, seasons 2016–2017 only.
- Cross-check: entering records match `games.csv` `record_entering_*` on the derived sides.
- `MISSING_RECORD` sides: `2017_02_CHI_TB` home **TB** (no 2017 W1 game — Irma postpone); `2017_02_MIA_LAC` away **MIA** (same). Those teams are not filled from 2016.

### T1–T4 — 16 EPA / success / pass-rate / pressure / RZ / matchup-diff fields

**Status:** `MISSING_RECORD` for all 31 games × 16 fields.

- T1 = `nfl_dp_team_situational_weekly` (one row per team per played game).
- T2 = season-partitioned `ROWS BETWEEN 4 PRECEDING AND CURRENT ROW`.
- T3/T4 = home/away rollups and diffs, including `matchup_diff_success_rate_5g` as the two-term mean.
- On this box:
  - `games.csv` `epa_status=MISSING`, `epa_blocker=rolling_features_unavailable_pre_2023` for all 31 rows.
  - `historical_oos` `packaged_epa_gap=no_prior_season_situational_for_packaged_priors` and `trailing_epa_gap=rolling_features_unavailable_pre_2023`.
  - Owned dump `data/ops/nfl-owned-data-20260705T201049Z/nfl_dp_team_situational_weekly.ndjson` is **2025 W1 only** (32 rows). Forbidden as modern ratings.
  - Efficiency-backbone rolling tables are 2023–2026 only (`nfl-efficiency-backbone-v1.1-20260808.md`).
  - 2026 through-W7 panel `340a06dd` not opened for values.
- PBP 2012–2022 may exist on `cursor/s1-pbp-restage-t4696u-f4de`. Mapping onto T1 is **UNVERIFIED**. This packet does not invent that transform and did not open those parquets.
- Scores-only (OOS) cannot produce EPA / success / pressure / RZ. Not used as a silent 5g proxy.
- Week 1: even a 2016 T1 row would be a prior-season substitution outside T2’s per-season partition; that row is also absent.
- Week 2: would need 2017 W1 T1 rows at `rating_week=1`. Those rows are absent.

## Status vocabulary

| Status | Meaning in this packet |
|---|---|
| DERIVED_PREGAME | Finite value reconstructed from earlier completed / schedule-known sources under cf514078 |
| MISSING_RECORD | Required source record is not on box as-of the cutoff; not invented |
| OUT_OF_CONTRACT | Not used (catch-all fields left unset; no matrix rows) |
| EXCLUDED | Not used (no sample game lacked kickoff; none dropped) |

## Explicitly not done

- No Independent Fair call. No mus, no σ, no win probs.
- No 2024–25 holdout rows copied into the working set.
- No Odds / API / credits.
- No modern (2025/2026) ratings, injuries, or personnel.
- No silent sample substitution (N frozen at 31).
- No Stage-2 rebuild.

≠FREE_PUBLIC ≠betting ≠Odds ≠merge ≠E1 ≠CERT · NFL NO-GO · CERT=0
