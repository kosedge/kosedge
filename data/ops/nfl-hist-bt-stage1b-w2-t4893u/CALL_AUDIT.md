# CALL_AUDIT — Hist BT Stage-1b t4893u

**Odds / API / credits: 0.**

No Odds client, no Railway data-plane fetch, no C10, no paid capture. One HTTP GET only: remount of the **already-pinned** t4696u nflverse 2017 PBP URL so this box could rehash `84eacd96`. 2023 not fetched.

## Sources touched (read)

| Path / object | sha8 | How used |
|---|---|---|
| `games.csv` @ `origin/cursor/t4422u-walkforward-pergame-export-f36b` | **4fe1cdd7** | W2 universe, kickoffs, identity. Re-hashed MATCH |
| `historical_oos_games.csv` | **1ee90fac** | 2016–2017 REG **scores only** for T5 W-L. File contains 2024–25 rows; those seasons were counted at header level only and **not** copied into the working set |
| `play_by_play_2017.parquet` (t4696u restage path) | **84eacd96** | T1 pass/run plays, 2017 REG W1 only. Hashed before parse; MATCH |
| `ALEX_E1_EFFICIENCY_CONTRACT_t4770u_v2.md` @ `hift1-efficiency-recovery-f693` | **b41f4b43** | Required fields + T1–T5 + forbids. Rehashed MATCH |
| `IMV_GRADE_t4770u_E1_EFFICIENCY_CONTRACT_v2.txt` | **1a53bbd3** | PASS_CONTRACT pin (≠ DATA ACCEPT) |
| `nfl_pregame_asof.py` @ `1010b86f` / t4822u | **7dc6afea** / identity **cf514078** | Leakage boundary / rating_week = week−1 |
| `data_platform_nfl/ingest.py` T1/T2/T3 SQL @ `1b39f4e9` | **5fc97157** | Approved transform ported; not executed against prod DB |
| `nfl_matchup_features.py` T4 success-mean | **107151d6** (contract cite) | Two-term mean; both terms required |
| `nfl_data.py` `team_strength_from_record` / UTC rest | **2989a556** | T5 formula; UTC contrast only |
| `nfl_simulator.py` @ `1b39f4e9` | **52d9e909** | Hash verify only. **Not invoked** |
| OWNER / Alex attach set (t4893u / t4890u) | — | Bounds + plain-English defs; not data |

## Sources not touched

- Odds API, DK, books.py, line snapshots, true-close parquet
- 2024–25 holdout values (no row materialization)
- 2026 through-W7 panel values
- 2023 PBP (explicitly not fetched)
- 2025 situational dump **values** (schema awareness only from prior inventory; not used as a fill)
- Injury / depth / roster capture
- Production DB / Railway / `DATABASE_URL`
- `simulate_nfl_game_independent_fair`

## Network

- 1 GET: `https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2017.parquet` (t4696u remount). Bytes=19050401. sha256 MATCH pin.
- Odds = 0 credits.

## Forbidden fills (none applied)

Future-season aggregates · 2026 ratings · hindsight injuries · invented 5g · silent 7.0 rest · silent 1.0 index · silent sample add/drop · drive-trip RZ substitute · qb_dropback-as-denominator substitute · 2016 T1/T5 prior-season substitute.

≠FREE_PUBLIC ≠betting ≠Odds ≠merge ≠E1 ≠CERT · NFL NO-GO · CERT=0
