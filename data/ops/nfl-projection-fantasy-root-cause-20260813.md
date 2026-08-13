# NFL projection / fantasy root cause — 2026-08-13

**Branch:** `feat/nfl-projection-fantasy-enterprise-fix`  
**Depends on:** published bundle `nfl-preseason-sim-2026-20260813T132801Z` + SoT (#220)  
**Do not revert:** KEI Week 1 factor stack, True PR, continuity, SOS

## Live symptoms (pre-fix, Half-PPR on `20260813T132801Z`)

| Player | ADP | Model overall | Pos rank | Med pts | Rush / rec / pass | Rush TD |
|--------|----:|-------------:|---------:|--------:|-------------------|--------:|
| Gibbs | 1 | 53 | RB15 | 248.4 | 956 / 478 / — | 6.8 |
| Cook | 9 | 25 | RB3 | 294.4 | 1505 / 316 / — | 11.4 |
| Henry | 21 | 33 | RB8 | 285.2 | 1500 / 262 / — | 11.4 |
| Charbonnet | 124 | 31 | RB6 | 288.6 | **1425** / 339 / — | 10.6 |
| Bijan | 2 | 30 | RB5 | 289.1 | 1417 / 359 / — | 10.3 |
| JT | 7 | 66 | RB18 | 234.6 | 1023 / 378 / — | 7.2 |
| Allen | 22 | 23* | QB20 | 295.3 | 289 rush / 3407 pass | **2.35** |
| Lamar | 37 | 39* | QB27 | 271.4 | 286 rush / 2830 pass | **2.35** |
| Chase | 3 | 13 | WR1 | 313.9 | 1716 rec | — |
| Puka | 4 | 56 | WR9 | 246.4 | 1326 rec | — |
| JSN | 6 | 63 | WR14 | 239.2 | 1276 rec | — |
| Baker | 131 | 10 | QB9 | 317.3 | 306 rush / 3684 pass | 2.5 |
| Daniel Jones | 178 | 11 | QB10 | 316.8 | 183 rush / 3966 pass | 1.5 |

\*Allen ~94 and Lamar ~QB12 overall were the **VOR-sorted** live desk. On a raw-points sort of the same CSV, Allen is already overall 23 — rank policy was burying dual-threat QBs. Production shape was still wrong (2.35 rush TDs).

## End-to-end trace (allocator → finalize → desk)

1. **100k MC** (`player_season_totals.json` in the 13:17Z launch dir) already had role signal: Charbonnet ~1205 rush, Gibbs ~975, Allen ~376 rush / **2.0 rush TD**, Puka ~1011 rec.
2. **Finalize post-process** (`scripts/nfl/finalize_100k_expert_candidate.py`) then applied:
   - rush variance lift → 64k
   - sticky alpha usage
   - HV pass-TD floors
   - **`apply_soft_rb_priors_on_board`** — the smoking gun
3. Web fantasy fallback scores `player_regular_season_totals.csv` via `loadLatestNflPreseasonBundle2026()`. Railway `/nfl/fantasy/draft-rankings` sums Postgres weekly baselines (often empty → this CSV).

## Classified bugs

### 1. Role / depth allocation (equalized + magnet)

`apply_soft_rb_priors_on_board` in `offensive_production_stack.py`:

- Soft prior **1380**, hard floor **1350**, ceiling **1520**, blend **0.90**
- Treats **whoever currently has the most rush yards** as RB1
- **Skips** teams where `team_rush * 0.58 < 1350` → **Gibbs (DET) and JT (IND) never get the lift**
- High-rush teams pin **every** listed RB1 (including Charbonnet) to ~1350–1520

SoT pack `nfl_depth_chart_2026_w1.json`: Gibbs = DET RB1 (correct). Charbonnet = **SEA RB1** (Walker is KC in this 2026 pack). The Charbonnet gate “not top-8 if SoT is RB2” does **not** fire — pack says RB1. The bug was pinning that non-alpha RB1 to the 1380 magnet.

Fallback usage `_fallback_usage_from_rows` ranked by current yards, not `player_key` depth (`DET-RB1-JahmyrGibbs`). Patched to sort by key depth.

Sticky structural 1380 prior inside `apply_sticky_alpha_shares` was applied to **any** RB1 on a high-rush team. Patched to proven rush alphas only.

### 2. Production compression (efficiency + TDs)

- Soft prior + 90% blend flattened Cook / Henry / Charbonnet / Swift / Bijan into a ~10-pt blob (~294–298).
- Dual-threat: `qb_rushing_profile.py` labels Allen `dual_threat` / Lamar `designed_run_heavy`, but board rush-TD allocation gave QB weight ×1.15 then the RB 1400-yard pile ate the team rush-TD pool → Allen/Lamar ~2 rush TDs.
- WR alpha pin existed for Chase-class; Puka 1326 was helped vs MC 1011 but not enough to leave WR8–15.

### 3. Pure-model rank sort

Overall rank used **VOR**, which is correct for 1QB draft *value* and catastrophic for “does this look like a draft board”: every starting QB clustered ~310–319, VOR buried Allen at ~94, HIGH DEVIATION badges read as bet slips. Phase C switches Model rank to **projected Half-PPR points**. VOR stays a column. Value-aware ADP blend stays on Mock/Builder only.

## What is *not* the bug

- Team W/L / PF checksum universe (Tua ATL, Willis MIA, Kyler MIN, ARI ≠ Kyler) — PASS, untouched.
- KEI Week 1 factor stack — untouched.
- Fantasy scorer reading team totals ÷ N — **not** found. Scorer reads player CSV fields.
- League-wide YPC constants in the MC itself — secondary; the 1380 magnet dominated published yards.

## Fix at source

Replace step 5 of finalize with `apply_role_aware_player_shape` (`role_aware_production.py`). Republish player CSV from the existing 132801Z board (no 100k re-run). See `nfl-projection-fantasy-enterprise-fix-20260813.md`.
