# ASSUMPTIONS — Hist BT Stage-1b t4893u (2017 REG W2 first)

EVAL_ONLY reconstruction. No scoring. No IF invoke. No fit/tune.

Every derivation rule used (or refused) is listed here. Silent defaults are forbidden.

## Sample

- Source: walkforward `games.csv` pin **4fe1cdd7**
  (`data/ops/nfl-t4422u-walkforward-pergame-unblended-2013-2023/games.csv`
  @ `origin/cursor/t4422u-walkforward-pergame-export-f36b` tip `82ffb211`).
- Re-hashed this run: **MATCH** `4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8`.
- Universe: all REG rows with `season=2017` and `week=2` and a present `kickoff_utc` (16).
- **Exclusion rule (fixed, pre-build):** drop any game where either side has 0 completed same-season games as-of kickoff. Leave those games out of the sealed sample; do not invent fills.
- Pre-declared and verified: `2017_02_CHI_TB` (TB home Irma) and `2017_02_MIA_LAC` (MIA away Irma). No other exclusions.
- Eligible N = **14**.
- `selection_hash` sealed in `SELECTION_HASH_SEAL.json` **before** PBP was opened for values and before `RECON_MATRIX.csv` was written.
- Recipe: `sha256(utf-8 of sorted canonical game_id list joined by "\n" with trailing "\n")`.
- Hash: `96a1317613d695fe027caf4a9230028480f64facfe460736702bd66328708640`.

## Contract (b41f4b43)

- Text: `ALEX_E1_EFFICIENCY_CONTRACT_t4770u_v2.md`
  @ `origin/cursor/hift1-efficiency-recovery-f693`
  sha256 **b41f4b43e1367bd5658c743475b9b84535c65395630a0b06c804f8b3552b81f4** (recomputed MATCH).
- PASS_CONTRACT: `IMV_GRADE_t4770u_E1_EFFICIENCY_CONTRACT_v2.txt` sha256 **1a53bbd3…** ≠ DATA ACCEPT ≠ emit.
- Required efficiency fields: the 20 listed in §3.
- Required context: `game_id`, `home_team`, `away_team`, `matchup_season`, `matchup_week`, `rest_days_home`, `rest_days_away`.
- Catch-all: any other `NflGameInputs` field is OUT_OF_CONTRACT and stays unset. Those fields are **not** rows in `RECON_MATRIX.csv`.
- Reconstruct **as written**. No substitute feature. No contract change.

## As-of (cf514078)

- Identity: PASS_ASOF_BOUNDARY **cf514078** tip `1010b86f`.
- Module: `services/model-service/src/services/nfl_pregame_asof.py` sha256 **7dc6afea…**.
- Rule used: a candidate game may enter a field’s infoset only if its `kickoff_utc` is strictly `<` the target `kickoff_utc`.
- Contiguous pipeline: `rating_week = target_week - 1` = **1** for every W2 target.
- Consumption key (contract §4): T3 does **not** join T2 at week=2 (that CURRENT ROW would be the target game). T2 is read at week=1 only.
- Earliest eligible W2 kickoff `2017_02_HOU_CIN` `2017-09-15T00:25:00Z` is after latest W1 kickoff `2017_01_LAC_DEN` `2017-09-12T02:20:00Z`. All W1 games are as-of-legal for every eligible W2 target.
- Leakage audit: 15 W1 REG games / 1830 pass+run plays consumed; 0 W2 plays; `LEAKAGE_AUDIT.json` result PASS.
- No prior-season (2016) T1/T5 substitute.

## PBP source (84eacd96)

- Path: `/workspace/data/raw/nfl/pbp/t4696u_s1_restage/play_by_play_2017.parquet`
- t4696u restage pin: sha256 `84eacd963c1fdd45965f6222c62e9329a7f3412f029d92c1ac5e34a1bb4d3710` (19,050,401 bytes).
- This box did not have the restage files mounted. The exact nflverse URL from the t4696u report was remounted and **hashed before parse**. Rehash MATCH. Not a new source. 2023 PBP not fetched.
- Only 2017 REG week=1 rows with `play_type IN ('pass','run')` were aggregated. POST/PRE unused.

### nflverse EPA retro-fit caveat

nflverse `epa` and `success` are produced by a later-fitted expected-points model and retro-applied to 2017 PBP. That is a **metric-definition** look-ahead (the EP model used later seasons), not consumption of 2017 W2+ game outcomes. Labeled on every T1–T4 matrix row. Not treated as a capture-time as-of snapshot.

## Field rules

### Identity (5 fields)

**Status:** `DERIVED_PREGAME` for all 14 eligible games.

- Taken from the sealed `games.csv` row: `game_id`, `home`, `away`, `season=2017`, `week=2`.
- `LA→LAR`, `WAS→WSH` only as already labeled in the pin (export home/away already use LAR/WSH).
- PBP identity remaps used only to join T1 teams: `LA→LAR`, `WAS→WSH`, `LV→OAK` (2017 Raiders; later nflverse code). Not a statistical fill.

### rest_days_home / rest_days_away

**Status:** `DERIVED_PREGAME` for all 14.

- Contract §3: schedule-derived via `rest_days_from_schedule`.
- IF consume lineage used here is the **v3 ET heuristic** (`155d3ca0`): America/New_York kick **local** weekday.
  - Thursday → 4.0
  - Monday → 6.0
  - else → 7.0
- Same value on home and away (target-kickoff DOW, not days-since-that-team’s-last-game).
- `games.csv` columns `rest_days_*` are hardcoded `7.0` and were **not** used.
- UTC-DOW contrast recorded on the manifest. Eligible mismatch games: `2017_02_HOU_CIN`, `2017_02_GB_ATL`, `2017_02_DET_NYG`. Primary value is ET.

### T5 — offense_index_* / defense_index_*

Contract T5: `team_strength_from_record` on **same-season** W-L through completed games; ties ignored;
`off = clamp(0.90 + 0.22·wp, 0.82, 1.18)`, `def = clamp(0.92 + 0.20·wp, 0.82, 1.20)`.
Malformed record → code returns `1.0` = silent default → **not applied**.
Empty 0-0 → 0.90/0.92 helper artifact → **not applied** (those sides are the excluded Irma games).

**Eligible W2: `DERIVED_PREGAME` both sides** (each side has ≥1 completed 2017 REG game with kickoff < target).

- W-L recomputed from `historical_oos_games.csv` **1ee90fac** scores joined to `games.csv` kickoffs, seasons 2016–2017 only (2016 scores not used as T5 input; 2024–25 rows not copied into the working set).
- Cross-check: entering records match `games.csv` `record_entering_*` on the derived sides.

### T1–T4 — 16 EPA / success / pass-rate / pressure / RZ / matchup-diff fields

**Status:** `DERIVED_PREGAME` for all 14 eligible games × 16 fields.

- T1 = port of `nfl_dp_team_situational_weekly` offense/defense CTEs in
  `services/model-service/data_platform_nfl/ingest.py` sha256 **5fc97157…** (tree @ `1b39f4e9`).
- Play filter matches T1 SQL: `play_type IN ('pass','run')` — excludes `qb_kneel`, `qb_spike`, `no_play`, kickoff/punt/FG/XP.
- T2 = season-partitioned `ROWS BETWEEN 4 PRECEDING AND CURRENT ROW`. This packet’s T1 frame is W1 only, so `games_in_window_5 = 1`. Contract T2 is “last ≤5 PLAYED games”; a 1-game window is accepted. E1 W9 “≥5 expected” is a 2026 W9 coverage rule, not applied here.
- T3 home/away = that team’s T2 row at `rating_week=1`.
- T4 diffs from contract §4 / ingest matchup SQL (not the plain-English paraphrase where they disagree):
  - `diff_off_epa_5g = h.off − a.off`
  - `diff_def_epa_allowed_5g = a.def_allowed − h.def_allowed`
  - `diff_pressure_generated_5g = h − a`
  - `diff_pressure_allowed_5g = a − h`
  - `diff_red_zone_td_rate_5g = h − a`
  - `matchup_diff_success_rate_5g` = mean of `(h_succ_off − a_succ_off)` and `(a_succ_def − h_succ_def)` — both terms required.

#### Pressure (matched — not a substitute)

Contract §4 T1 columns are `pressure_rate_allowed/generated` produced by the cited T1 SQL:

`(sack OR qb_hit)` among `play_type='pass'` / count of `play_type='pass'`.

- `qb_dropback` is **not** the T1 denominator (SQL uses `play_type='pass'`).
- Hurries are not in the T1 SQL and were not invented.
- Therefore pressure fields are DERIVED, not MISSING.

#### Red-zone TD rate (matched to T1 SQL — trips paraphrase refused)

Contract-cited T1 SQL:

`(yardline_100 ≤ 20 AND touchdown) / (yardline_100 ≤ 20)` on pass/run plays.

`T1T4_PLAIN_ENGLISH_DEFS.md` says “RZ trips ending in TD”. Using drive-trips would be a **substitute feature**. Refused. Play-based SQL used. Note recorded in `T1_TRANSFORM.md` for Alex; not a contract change.

#### T1 verification gate

- 2023 PBP is not on box (t4696u left 2023 untouched). 2025 situational dump is 2025 W1 only; 2025 PBP is not owned. No 2024–25 values opened.
- Gate used: SQL-to-pandas code-review port + synthetic fixture (abs_tol 1e-12) in `build_recon_t4893u.py`. Numeric 2023+ compare = **not possible** on this box. Fail-closed would have been MISSING if the SQL could not be matched; it was matched.

## Status vocabulary

| Status | Meaning in this packet |
|---|---|
| DERIVED_PREGAME | Finite value reconstructed from earlier completed / schedule-known sources under cf514078 |
| MISSING_RECORD | Required source record not as-of-legal; not invented (none on eligible 14) |
| OUT_OF_CONTRACT | Not used (catch-all fields left unset; no matrix rows) |
| EXCLUDED | Sample-level only (2 Irma games). No matrix rows for those games |

## Explicitly not done

- No Independent Fair call. No mus, no σ, no win probs.
- No 2024–25 holdout rows copied into the working set.
- No Odds / API / credits (0).
- No modern (2025/2026) ratings, injuries, or personnel as fills.
- No W1 games in the sealed sample (W2 first only).
- No W3–W6 extend.
- No Stage-2 rebuild.
- No merge / admit / CERT.

≠FREE_PUBLIC ≠betting ≠Odds ≠merge ≠E1 ≠CERT · NFL NO-GO · CERT=0
