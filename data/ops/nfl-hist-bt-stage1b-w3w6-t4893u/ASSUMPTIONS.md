# ASSUMPTIONS — Hist BT Stage-1b t4893u (2017 REG W3–W6)

EVAL_ONLY reconstruction. No scoring. No IF invoke. No fit/tune.

Every derivation rule used (or refused) is listed here. Silent defaults are forbidden.
Method is the sealed W2 packet (`data/ops/nfl-hist-bt-stage1b-w2-t4893u/`) extended through W6.

## Sample

- Source: walkforward `games.csv` pin **4fe1cdd7**
  (`data/ops/nfl-t4422u-walkforward-pergame-unblended-2013-2023/games.csv`
  @ `origin/cursor/t4422u-walkforward-pergame-export-f36b` tip `82ffb211`).
- Re-hashed this run: **MATCH** `4fe1cdd7f2eb616103ee6107e6a5cb0d5280f8006be420b606af0995351abef8`.
- Universe: all REG rows with `season=2017` and `week ∈ {3,4,5,6}` and a present `kickoff_utc` (60).
- **Exclusion rule (fixed, pre-build, same as W2):** drop any game where either side has 0 completed same-season games as-of kickoff. Leave those games out of the sealed sample; do not invent fills.
- Result: **0 exclusions.** Irma TB/MIA completed W2 before W3.
- Eligible N = **60**.
- Per-week + combined `selection_hash` sealed in `SELECTION_HASH_SEAL.json` **before** PBP was opened (commit `32f9a3ec`; PBP path absent).
- Recipe: `sha256(utf-8 of sorted canonical game_id list joined by "\n" with trailing "\n")`.
- Combined hash: `e03c962ee6a95ca62a25bf050e4775f44893c384c63a31baaead5f9c9f6c5ebf`.

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
- Module pin: `nfl_pregame_asof.py` sha256 **7dc6afea…** (cited; file not on this detached tip).
- Rule used: a candidate game may enter a field’s infoset only if its `kickoff_utc` is strictly `<` the target `kickoff_utc`.
- Contiguous pipeline: `rating_week = target_week - 1` (2 for W3, 3 for W4, 4 for W5, 5 for W6).
- Consumption key (contract §4 / W2 method): T3 does **not** join T2 at the target week (that CURRENT ROW would be the target game). T2 is read at `rating_week` only, via W2 `lookup_t2` (exact week).
- Week gaps hold: max kickoff of week *k* < min kickoff of week *k+1* for *k* = 1..5.
- Leakage audit: 77 W1–W5 REG games / 9619 pass+run plays in the T1 frame; 0 W6 plays; per-target window = that team’s T1 rows with week ≤ rating_week, all those kickoffs < target. `LEAKAGE_AUDIT.json` result PASS.
- No prior-season (2016) T1/T5 substitute.

## PBP source (84eacd96)

- Path: `/workspace/data/raw/nfl/pbp/t4696u_s1_restage/play_by_play_2017.parquet`
- t4696u restage pin: sha256 `84eacd963c1fdd45965f6222c62e9329a7f3412f029d92c1ac5e34a1bb4d3710` (19,050,401 bytes).
- Remounted after seal commit. **Hashed before parse.** Rehash MATCH. Not a new source. 2023 PBP not fetched.
- 2017 REG weeks 1–5 rows with `play_type IN ('pass','run')` were aggregated. POST/PRE unused. W6 unused.

### nflverse EPA retro-fit caveat

nflverse `epa` and `success` are produced by a later-fitted expected-points model and retro-applied to 2017 PBP. That is a **metric-definition** look-ahead (the EP model used later seasons), not consumption of 2017 target-week game outcomes. Labeled on every T1–T4 matrix row. Soft carry from Alex W2 RO. Not treated as a capture-time as-of snapshot.

## Field rules

### Identity (5 fields)

**Status:** `DERIVED_PREGAME` for all 60 eligible games.

- Taken from the sealed `games.csv` row: `game_id`, `home`, `away`, `season=2017`, `week ∈ {3,4,5,6}`.
- `LA→LAR`, `WAS→WSH` only as already labeled in the pin (export home/away already use LAR/WSH).
- PBP identity remaps used only to join T1 teams: `LA→LAR`, `WAS→WSH`, `LV→OAK` (2017 Raiders; later nflverse code). Not a statistical fill.

### rest_days_home / rest_days_away

**Status:** `DERIVED_PREGAME` for all 60.

- Contract §3: schedule-derived via `rest_days_from_schedule`.
- **Same heuristic as W2** (Alex soft carry): v3 ET DOW (`155d3ca0`); America/New_York kick **local** weekday.
  - Thursday → 4.0
  - Monday → 6.0
  - else → 7.0
- Same value on home and away (target-kickoff DOW, not days-since-that-team’s-last-game).
- `games.csv` columns `rest_days_*` are hardcoded `7.0` and were **not** used.
- UTC-DOW contrast recorded on the manifest. TNF/MNF produce the same ET vs UTC mismatch pattern as W2.

### T5 — offense_index_* / defense_index_*

Contract T5: `team_strength_from_record` on **same-season** W-L through completed games; ties ignored;
`off = clamp(0.90 + 0.22·wp, 0.82, 1.18)`, `def = clamp(0.92 + 0.20·wp, 0.82, 1.20)`.
Malformed record → code returns `1.0` = silent default → **not applied**.
Empty 0-0 → 0.90/0.92 helper artifact → **not applied**.

**Eligible W3–W6: `DERIVED_PREGAME` both sides** (each side has ≥1 completed 2017 REG game with kickoff < target).

- W-L recomputed from `historical_oos_games.csv` **1ee90fac** scores joined to `games.csv` kickoffs, seasons 2016–2017 only (2016 scores not used as T5 input; 2024–25 rows not copied into the working set).
- Cross-check: entering records match `games.csv` `record_entering_*` on all 60 derived sides (0 mismatches).

### T1–T4 — 16 EPA / success / pass-rate / pressure / RZ / matchup-diff fields

**Status:** `DERIVED_PREGAME` when both sides have a T2 row at exact `rating_week`. `MISSING_RECORD` when W2 `lookup_t2` returns None (exact week miss). No last-played-week fill.

- T1 = W2 port of `nfl_dp_team_situational_weekly` offense/defense CTEs (`t1_from_plays`).
- Play filter matches T1 SQL: `play_type IN ('pass','run')`.
- T2 = W2 `rolling_5g`: season-partitioned `ROWS BETWEEN 4 PRECEDING AND CURRENT ROW` (last ≤5 **played** games).
- T3 home/away = that team’s T2 row at `rating_week = target_week - 1` via W2 `lookup_t2` (exact week).
- T4 diffs from contract §4 / ingest matchup SQL (same signs as W2):
  - `diff_off_epa_5g = h.off − a.off`
  - `diff_def_epa_allowed_5g = a.def_allowed − h.def_allowed`
  - `diff_pressure_generated_5g = h − a`
  - `diff_pressure_allowed_5g = a − h`
  - `diff_red_zone_td_rate_5g = h − a`
  - `matchup_diff_success_rate_5g` = mean of `(h_succ_off − a_succ_off)` and `(a_succ_def − h_succ_def)` — both terms required.

#### Pressure (matched — not a substitute)

`(sack OR qb_hit)` among `play_type='pass'` / count of `play_type='pass'`.
`qb_dropback` is **not** the T1 denominator. Hurries not invented.

#### Red-zone TD rate (matched to T1 SQL — trips paraphrase refused)

`(yardline_100 ≤ 20 AND touchdown) / (yardline_100 ≤ 20)` on pass/run plays.

#### Exact-week T2 miss (W6 / W5 byes)

W5 byes: ATL, DEN, NO, WSH. Those teams have no T1/T2 row at week=5.
W6 games with those teams as home: `2017_06_MIA_ATL`, `2017_06_NYG_DEN`, `2017_06_DET_NO`, `2017_06_SF_WAS`.
W2 `lookup_t2` is exact week → None → fail-closed MISSING on that side’s 5 T1 fields + 6 T4 diffs (11 cells). Other side’s 5 T1 fields + identity/rest/T5 remain DERIVED (16/27). **No last-played-week substitute.**

#### T1 verification gate

- W1 T1 vs W2 packet file: max abs diff **0** (same function, same pin).
- 2023+ backbone compare: **not possible** on this box (same as W2).
- Synthetic fixture via W2 builder: PASS.

## Status vocabulary

| Status | Meaning in this packet |
|---|---|
| DERIVED_PREGAME | Finite value reconstructed from earlier completed / schedule-known sources under cf514078 |
| MISSING_RECORD | Required T2 row at exact rating_week not present; not invented (44 cells / 4 games) |
| OUT_OF_CONTRACT | Not used (catch-all fields left unset; no matrix rows) |
| EXCLUDED | Sample-level only. None on W3–W6 |

## Explicitly not done

- No Independent Fair call. No mus, no σ, no win probs.
- No 2024–25 holdout rows copied into the working set.
- No Odds / API / credits (0).
- No modern (2025/2026) ratings, injuries, or personnel as fills.
- No last-played-week T2 fill for W5 byes.
- No W7+ extend.
- No Stage-2 rebuild.
- No merge / admit / CERT.

≠FREE_PUBLIC ≠betting ≠Odds ≠merge ≠E1 ≠CERT · NFL NO-GO · CERT=0
