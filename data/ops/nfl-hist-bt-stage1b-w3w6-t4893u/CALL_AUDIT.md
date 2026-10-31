# CALL_AUDIT — Hist BT Stage-1b t4893u W3–W6

**Odds / API / credits: 0.**

No Odds client, no Railway data-plane fetch, no C10, no paid capture. One HTTP GET only: remount of the **already-pinned** t4696u nflverse 2017 PBP URL so this box could rehash `84eacd96` **after** the selection-hash seal commit. 2023 not fetched.

## Sources touched (read)

| Path / object | sha8 | How used |
|---|---|---|
| `games.csv` @ `origin/cursor/t4422u-walkforward-pergame-export-f36b` | **4fe1cdd7** | W3–W6 universe, kickoffs, identity. Re-hashed MATCH |
| `historical_oos_games.csv` | **1ee90fac** | 2016–2017 REG **scores only** for T5 W-L. File contains 2024–25 rows; those seasons were counted at header level only and **not** copied into the working set |
| `play_by_play_2017.parquet` (t4696u restage path) | **84eacd96** | T1 pass/run plays, 2017 REG W1–W5 only. Hashed before parse; MATCH. Opened after seal commit `32f9a3ec` |
| `ALEX_E1_EFFICIENCY_CONTRACT_t4770u_v2.md` @ `hift1-efficiency-recovery-f693` | **b41f4b43** | Required fields + T1–T5 + forbids. Rehashed MATCH |
| `IMV_GRADE_t4770u_E1_EFFICIENCY_CONTRACT_v2.txt` | **1a53bbd3** | PASS_CONTRACT pin (≠ DATA ACCEPT) |
| W2 builder `build_recon_t4893u.py` | packet | T1–T4 functions reused; no new transforms |
| `nfl_pregame_asof.py` identity **cf514078** / module **7dc6afea** | cited | Leakage boundary / rating_week = week−1 |
| `data_platform_nfl/ingest.py` T1/T2/T3 SQL @ `1b39f4e9` | **5fc97157** | Approved transform ported (via W2); not executed against prod DB |
| `nfl_simulator.py` @ `1b39f4e9` | **52d9e909** | Hash verify only. **Not invoked** |
| OWNER / CoS / Alex attach set (t4893u) | — | Bounds + W2 PASS_RECON gate; not data |

## Sources not touched

- Odds API, DK, books.py, line snapshots, true-close parquet
- 2024–25 holdout values (no row materialization)
- 2026 through-W7 panel values
- 2023 PBP (explicitly not fetched)
- Injury / depth / roster capture
- Production DB / Railway / `DATABASE_URL`
- `simulate_nfl_game_independent_fair`

## Network

- 1 GET: `https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2017.parquet` (t4696u remount, after seal). Bytes=19050401. sha256 MATCH pin.
- Odds = 0 credits.

## Forbidden fills (none applied)

Future-season aggregates · 2026 ratings · hindsight injuries · invented 5g · silent 7.0 rest · silent 1.0 index · silent sample add/drop · drive-trip RZ substitute · qb_dropback-as-denominator substitute · 2016 T1/T5 prior-season substitute · last-played-week T2 for W5 byes.

≠FREE_PUBLIC ≠betting ≠Odds ≠merge ≠E1 ≠CERT · NFL NO-GO · CERT=0
