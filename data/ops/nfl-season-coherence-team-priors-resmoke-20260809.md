# NFL Season Coherence — Team pass priors re-smoke (v1.17)

Date: 2026-08-09  
Engine: `nfl-season-engine-v1.17-season-coherence-team-priors`  
Web pointer: `data/ops/nfl-web-launch-bundle.json` → `nfl-preseason-sim-2026-20260809T092006Z`  
Method: budget-ratio rescale of v1.16 research paths after ARI/BAL/SEA pre-pool identity weights

## Identity weights (pre-pool)

| Team | Adjustment | Soft bound | Pre-pool | Post-pool |
|------|------------|------------|---------:|----------:|
| ARI | residual 0.78× + LaFleur 0.92× | ceiling 4250 | 3829 | 4350 |
| BAL | dual-threat 0.88× + Doyle 1.12× | floor 3150 | 3150 | 3579 |
| SEA | 70/30 Darnold + Fleury/Shanahan 1.05× | floor 3400 | 3748 | 4259 |

## Before / after (QB1 season pass yards)

| Metric | Before (v1.16 live) | After (v1.17 priors) |
|--------|--------------------:|---------------------:|
| QB1s ≥ 4000 | 7 | **7** |
| QB1s ≥ 4500 | 4 | **3** |
| Under 3500 | 14 | **13** |
| Median | 3656.2 | **3681.8** |
| Min / max | 2718 / 4858 | **2951 / 4813** |
| League pass yards | 126.0k | **126.0k** |
| ARI | 4700 | **4083** |
| BAL | 2718 | **3345** |
| SEA | 2997 | **3975** |

Top after: CIN 4813, LA 4540, DAL 4516, KC 4376, DEN 4220  
Bottom after: MIN 3262, CLE 3232, PHI 3042, NYJ 2991, WAS 2951

## Pass criteria

| Check | Result |
|-------|--------|
| QB1s ≥4000 not 32; target ~6–12 | **PASS** (7) |
| Median ~3600–3800 | **PASS** (3682) |
| Left tail several under 3500 | **PASS** (13) |
| Top tail a few ~4500–4800 | **PASS** (3 ≥4500; max 4813) |
| League pass pool ~115–130k | **PASS** (126.0k) |
| ARI zone 3850–4200 | **PASS** (4083) |
| BAL zone 3250–3550 | **PASS** (3345) |
| SEA zone 3650–4050 | **PASS** (3975) |
| Sum of team wins ≈ 272 | **PASS** (unchanged) |

Other 29 teams only move by the tiny pool-renorm ripple (~±1%).
