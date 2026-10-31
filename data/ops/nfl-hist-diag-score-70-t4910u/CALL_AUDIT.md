# CALL_AUDIT — t4910u bounded diagnostic score 70

**Odds / API / credits: 0.**

No Odds client. No Railway data-plane fetch. No C10. No paid capture. No 2024–25 holdout open. No 2023 PBP fetch. PBP 84eacd96 cited only, not remounted.

## Rest bind (PASS)

| check | result |
|---|---|
| IF tip | **6ca03716** — not switched to 90bf65ab |
| W8 `rest_days_from_schedule` / `verify_rest_days` | **not called** |
| `nfl_data.rest_days_from_schedule` | **not called** |
| IF `rest_days_home` / `rest_days_away` | sealed packet reconstructed values |
| `games.csv` hardcoded 7.0 rest | **not used** |
| UTC-DOW contrast | recorded only (Thu packet rest=4.0 vs UTC 7.0 on HOU_CIN, LA_SF, CHI_GB, NE_TB, PHI_CAR) |
| contract/code change required to bind? | **no** — `NflGameInputs` already accepts `rest_days_*` |
| HOLD | not raised |

Hypothesis accepted: rest was already correct in packets; only consumption binding was required.

## Sources touched (read)

| Path / object | sha8 | How used |
|---|---|---|
| IF tip `6ca03716fe52930332d5ffba302c312a651980cc` | **6ca03716** | framework tree / `simulate_nfl_game_independent_fair` |
| `nfl_simulator.py` @ 6ca03716 | **52d9e909** | IF invoke. Rehash MATCH. Not the deploy-vercel HEAD object |
| `nfl_handicapping_framework.py` @ 6ca03716 | **a0051cc4** | IF decompose. Rehash MATCH |
| contract `ALEX_E1_EFFICIENCY_CONTRACT_t4770u_v2.md` | **b41f4b43** | required fields. Rehash MATCH |
| as-of module `nfl_pregame_asof.py` | **7dc6afea** / identity **cf514078** | cited. Not re-derived |
| W2 packet tip `440314e4` `RECON_MATRIX.csv` | **708513db** | 14 complete IF inputs + sealed rest |
| W2 Alex PASS_RECON | **91e2d7db** | cited (document sha8; not a git object on this box) |
| W3–W6 packet tip `f92aaea3` #671 `RECON_MATRIX.csv` | **cdff0115** | 56 complete IF inputs + sealed rest |
| W3–W6 Alex PASS_RECON | **af30adba** | cited (document sha8; not a git object on this box) |
| `historical_oos_games.csv` | **1ee90fac** | 2017 REG scores only. Rehash MATCH. Market columns not read into metrics |
| PBP 2017 | **84eacd96** | cited only. Not opened |
| OWNER_ACCEPT box original | **1102720e** | remount CLOSED — exact bytes from Agent Store uploads |
| EXEC_FREEZE box original | **5ecdef1c** | remount CLOSED — exact bytes from Agent Store uploads |
| Alex RO | **fbd7abe9** | CONDITIONAL; CoS CLOSE addendum only |

## Box remount — CLOSED

| file | expected sha8 | observed | match |
|---|---|---|---|
| `EXEC_FREEZE_t4910u_BOUNDED_DIAG_SCORE_70.md` | **5ecdef1c** | **5ecdef1c** | YES |
| `OWNER_ACCEPT_t4910u_BOUNDED_DIAG_SCORE_70.md` | **1102720e** | **1102720e** | YES |

19c6a460 recreations (8ef7a834 / d3acd43d) **SUPERSEDED** by box originals. See `REMOUNT_NOTE.md`. CoS ACCEPT: box originals are SoT.

## Addendum close (no IF re-invoke)

`METRICS_ADDENDUM_t4910u` computed from sealed `SCORE_RESULTS.json` only. `simulate_nfl_game` / `simulate_nfl_game_independent_fair` **not called** on this close. SCORE_RESULTS bytes unchanged.

## Sources not touched

- Odds API, DK, books.py, line snapshots, true-close parquet
- 2017 market columns on `historical_oos_games.csv` (present on file; not used)
- 2024–25 holdout values
- 2026 through-W7 / W8 panel
- 2023 PBP
- Injury / depth / roster capture
- Production DB / Railway / `DATABASE_URL`
- W8 `nfl_offline_if_eval_w8.py` rest helper
- Tip `90bf65ab` / `155d3ca0` (not fetched; not used)

## Network

- 0 Odds credits.
- git fetch of already-cited research refs only (packet tips, contract branch, IF tip). No nflverse remount.

## Invoke

- Original score tip `19c6a460`: `simulate_nfl_game_independent_fair` × 70 (sealed).
- This close: **zero** IF / `simulate_nfl_game` calls.
- simulations=4000 · market_spread_home=None · market_total=None · market_blend=0 on all 70
- seed formula frozen in ASSUMPTIONS / PINS before first SCORE_RESULTS write
- 70/70 SCORED · 0 FAILED

## Forbidden fills (none applied)

Future-season aggregates · 2026 ratings · hindsight injuries · invented rest · silent 7.0 rest · silent sample add/drop · W8 UTC rest re-derive · tip switch · CLV · 2017 odds-as-metric.

≠FREE_PUBLIC ≠betting ≠Odds ≠merge ≠E1 ≠CERT · NFL NO-GO · CERT=0
