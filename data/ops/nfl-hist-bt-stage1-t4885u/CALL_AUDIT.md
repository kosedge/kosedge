# CALL_AUDIT — Hist BT Stage-1 t4885u

**Odds / API / credits: 0.**

No `socket.connect`, no Odds client, no Railway data-plane fetch, no C10, no paid capture.

## Sources touched (read)

| Path / object | sha8 | How used |
|---|---|---|
| `games.csv` @ `origin/cursor/t4422u-walkforward-pergame-export-f36b` | **4fe1cdd7** | Sample universe, kickoffs, identity, 2016 REG availability. Re-hashed MATCH |
| `historical_oos_games.csv` | **1ee90fac** | 2016–2017 REG **scores only** for Week-2 T5 W-L. File contains 2024–25 rows; those seasons were counted at header level only and **not** copied into the working set |
| `ALEX_E1_EFFICIENCY_CONTRACT_t4770u_v2.md` @ `hift1-efficiency-recovery-f693` | **b41f4b43** | Required fields + T1–T5 + forbids |
| `IMV_GRADE_t4770u_E1_EFFICIENCY_CONTRACT_v2.txt` | **1a53bbd3** | PASS_CONTRACT pin (≠ DATA ACCEPT) |
| `nfl_pregame_asof.py` @ `1010b86f` / t4822u | **7dc6afea** / identity **cf514078** | Leakage boundary |
| `nfl_offline_if_caller.py` REQUIRED_20 @ t4838u | — | Confirms field list matches b41f4b43 |
| `nfl_offline_if_eval_w8.py` rest ET heuristic @ `155d3ca0` | — | rest_days rule |
| `nfl_data.py` `team_strength_from_record` / UTC rest | **2989a556** | T5 formula; UTC contrast only |
| `nfl_simulator.py` @ `1b39f4e9` | **52d9e909** | Hash verify only. **Not invoked** |
| `nfl-owned-data-20260705T201049Z/*.ndjson` | — | Season inventory: **2025 W1 only**. Values not consumed |
| `nfl-efficiency-backbone-v1.1-20260808.md` | — | Documents rolling seasons 2023–2026 |
| OWNER / CoS / Alex papers in the upload set | 48a76836 / 6fc8ec8c / card 1a7ae9a4 | Bounds; not data |

## Sources not touched

- Odds API, DK, books.py, line snapshots, true-close parquet
- 2024–25 holdout values (no row materialization)
- 2026 through-W7 panel `340a06dd` values
- 2026 W8 eval packets (style reference from git tree listing only)
- S1 PBP parquets (`cursor/s1-pbp-restage-t4696u-f4de`) — mapping UNVERIFIED; not opened
- Injury / depth / roster capture
- Production DB / Railway / `DATABASE_URL`
- `simulate_nfl_game_independent_fair`

## Network

Builder is local CSV/JSON only. No HTTP.

## Forbidden fills (none applied)

Future-season aggregates · 2026 ratings · hindsight injuries · invented 5g · silent 7.0 rest · silent 1.0 index · silent sample add/drop · SD→LAC as T5 input.

≠FREE_PUBLIC ≠betting ≠Odds ≠merge ≠E1 ≠CERT · NFL NO-GO · CERT=0
