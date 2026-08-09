# NFL Season Coherence — Live smoke (published board)

Date: 2026-08-09  
Engine: `nfl-season-engine-v1.16-season-coherence`  
Web pointer: `data/ops/nfl-web-launch-bundle.json` → `nfl-preseason-sim-2026-20260809T035645Z`  
Research source: `nfl-season-engine-launch-…-Nteam50000-Nplayer1000-20260809T034834Z`

## Before / after (QB1 season pass yards)

| Metric | Before (v1.12 board) | After (v1.16 live pointer) |
|--------|---------------------:|---------------------------:|
| QB1s ≥ 4000 | **32** | **7** |
| QB1s ≥ 4500 | 2 | **4** |
| Under 3500 | 0 | **14** |
| Median | 4258.7 | **3656.2** |
| p10 / p90 | 4091 / 4487 | **3019 / 4558** |
| Min / max | 4011 / 4575 | **2718 / 4858** |
| League pass yards | 145714.7 | **125998.1** |
| mean_wins_sum | 272.0 | **272.0** |
| Engine / bundle | v1.12 survivor-planner | **v1.16-season-coherence** |

Top after: CIN 4858, ARI 4700, LA 4583, DAL 4558, KC 4417  
Bottom after: BAL 2718, WAS 2979, SEA 2997, NYJ 3019, PHI 3071

## Pass criteria

| Check | Result |
|-------|--------|
| QB1s ≥4000 not 32; target ~6–12 | **PASS** (7) |
| Median ~3600–3800 | **PASS** (3656) |
| Left tail several under 3500 | **PASS** (14) |
| Top tail a few ~4500–4800 | **PASS** (4 ≥4500; max 4858) |
| League pass pool ~115–130k | **PASS** (126.0k) |
| Fantasy board not on v1.12 | **PASS** |
| Engine shows coherence / v1.16 | **PASS** |
| Sum of team wins ≈ 272 | **PASS** |

## Note on first republish attempt

The first packaged publish (…034658Z) over-damped (median ~3.1k) because path budget
enforce was scale-down-only. Retune: two-way allocate into team budgets + pass pool
126k + packaged QB1 YPA ladder. This smoke is on the retuned publish (…035645Z).
