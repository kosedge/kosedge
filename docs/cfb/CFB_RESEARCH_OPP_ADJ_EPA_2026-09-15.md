# CFB research opponent-adjusted O/D EPA (on top of #559)

**Date:** 2026-09-15  
**Authorized:** Ryan / CoS LOCK — research-only.  
**Product:** opponent-adjusted offensive and defensive **EPA/play**.  
**Not KE Ratings. Not KEI. Not a point spread. Not a proprietary KE expected-points model.**  
Upstream EPA keeps its SportsDataverse name.

Production **SP+**, **NFL**, and **KEI** are unchanged. No CFBD. No production promote.

Evidence: `data/ops/cfb-research-opp-adj-epa-20260915/`  
Bulk (gitignored): `data/cfb/research/pbp_hist/as_of_20260915/` and `data/cfb/research/pbp_current/as_of_20260915/`

---

## 1. Delayed-game close (#559)

| Field                         | Value                                                                                                                                                                                                                                                                                                        |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `game_id`                     | `401868140`                                                                                                                                                                                                                                                                                                  |
| Teams                         | Eastern Kentucky @ Jacksonville State                                                                                                                                                                                                                                                                        |
| Week                          | 1                                                                                                                                                                                                                                                                                                            |
| Old snapshot status           | `STATUS_DELAYED`                                                                                                                                                                                                                                                                                             |
| Old snapshot score            | 21–0                                                                                                                                                                                                                                                                                                         |
| Old #559 decision             | **included** (score present and not live)                                                                                                                                                                                                                                                                    |
| Verification                  | ESPN site summary + box + recap (no CFBD)                                                                                                                                                                                                                                                                    |
| Official status               | `STATUS_FINAL` (`state=post`, `completed=true`)                                                                                                                                                                                                                                                              |
| Official score                | **49–7** (JSU 49, EKU 7)                                                                                                                                                                                                                                                                                     |
| Sources                       | `https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event=401868140` · [ESPN box](https://www.espn.com/college-football/boxscore/_/gameId/401868140) · [ESPN recap](https://www.espn.com/college-football/recap?gameId=401868140) · JSU athletics (lightning delay; final 49–7) |
| **Decision on #559 snapshot** | **EXCLUDE**                                                                                                                                                                                                                                                                                                  |

A score alone is insufficient. **DELAYED + score is not a standing eligibility rule.**

### PBP vs official 49–7 (fail-closed)

Same #559 PBP SHA `da0ec956…` (7,904,267 bytes). Game `401868140`:

| PBP fact                     | Observed                                                                          | Official final    |
| ---------------------------- | --------------------------------------------------------------------------------- | ----------------- |
| Plays / drives               | **52 / 7**                                                                        | full game (Q1–Q4) |
| Max period                   | **2**                                                                             | 4                 |
| Last clock / type            | Q2 **10:27** Interception Return (Nix TD)                                         | End of Q4         |
| Last score in PBP            | **28–0**                                                                          | **49–7**          |
| Official markers reached     | 7–0, 14–0, 21–0, 28–0                                                             | 8 scoring plays   |
| Official markers **missing** | Hensley 72yd (28–7), Likely 45yd (35–7), Gilbert 24yd (42–7), Williams 4yd (49–7) | —                 |

PBP is a **partial Q2 cut**, not the finished game. Incomplete PBP for a completed game = **exclude**. Regenerated #559 set is **84** games. A later as_of may include this game only if PBP is complete through 49–7 (period ≥ 4, all 8 scoring markers) **and** schedule is `STATUS_FINAL`.

---

## 2. Historical raw features (2014–2025)

Same #555 / #559 definitions:

- Success rate labeled **`EPA_success = EPA>0`**
- Standard 50/70/100 SR is a **separate** column
- EPA/play, pace / competitive pace, explosiveness, down splits, scoring opportunities / PPO / finishing, field position

Restore: SportsDataverse `espn_cfb_pbp` season parquets.  
**Never overwrite** `/Volumes/KosEdgeData/raw/cfb/pbp/` (Aug 13 SoT).

| Role                             | Path                                                        |
| -------------------------------- | ----------------------------------------------------------- |
| Canonical HD lake (do not write) | `/Volumes/KosEdgeData/raw/cfb/pbp/`                         |
| HD research mirror (documented)  | `/Volumes/KosEdgeData/raw/cfb/pbp_research/as_of_20260915/` |
| VM restore                       | `data/cfb/research/pbp_hist/as_of_20260915/`                |

Reconcile gate: **2021–2024 game count = 3,552** (HD). Play-count delta vs 612,597 is reported when the public copy differs.

---

## 3. Bounded first adjustment model

Target: **offensive and defensive EPA/play only**.

```
y_{g,i} = μ + h · home_{g,i} + off_i + def_j + ε
```

- `y` = garbage-weighted EPA/play on eligible scrimmage plays
- Joint ridge on offense and opposing defense
- Identifiable league baseline: FBS `off` and `def` centered at 0; `μ` is the intercept
- Home-field `h` is **joint** weighted OLS with `μ` on `y − off − def` (sequential μ-then-h absorbs ~½ HFA into the intercept when `home` is 0/1)
- Early-season shrink: `λ` play-weight **plus** `n0` game-equivalents toward the decayed prior (`n0=0` is λ-only)

### Eligible-play rules

| Rule                 | Treatment                                                                |
| -------------------- | ------------------------------------------------------------------------ |
| Scrimmage            | #555: truthy `scrimmage_play`, else pass\|rush                           |
| EPA                  | finite `EPA` required                                                    |
| Overtime             | **exclude** `period/qtr ≥ 5`                                             |
| Garbage              | warehouse `garbage_weight` (not a hard drop; min 0.10)                   |
| FCS                  | kept and flagged; `λ_fcs = 4λ`; FCS not in the centering set             |
| Insufficient history | `n_games < 2` flagged; week-1 uses decayed prior only (`prior_weight=1`) |

Pace, explosiveness, finishing, havoc, and special teams remain **supporting raw metrics only**.

---

## 4. Pregame cutoffs and priors

For target week `W` of season `S`:

- Fit uses **same-season games with `week < W` only**
- Early-season prior = `decay ×` previous season-final ratings
- Season-final ratings walk forward from 2014–2015 seed years
- Preprocessing / `λ`, `n0`, `decay` selected on **2023–2024 validation**
- **2025 holdout is untouched** until the recommendation

---

## 5. Validation

Next-game offensive and defensive EPA prediction error vs:

1. Unadjusted season-to-date EPA
2. Simple prior-season blend (`n0=4`, raw EPA)

Metrics: MAE, RMSE, bias, n, early-season (weeks 1–4).

### Historical restore (this VM)

| Check                    | Result                                                       |
| ------------------------ | ------------------------------------------------------------ |
| Seasons                  | 2014–2025                                                    |
| Games vs Aug 13          | **10,297 = 10,297** (every season game-count matches)        |
| Plays vs Aug 13          | 1,820,754 vs 1,819,153 (**+1,601**)                          |
| 2021–2024 games          | **3,552 = 3,552**                                            |
| 2021–2024 plays          | 613,851 vs 612,597 (**+1,254**, same later SDV copy as #555) |
| `EPA_success` vs `EPA>0` | **1.000** on every season (78k–126k scrimmage plays)         |
| HD lake write            | **false** (unmounted; research path only)                    |
| HD research mirror       | `/Volumes/KosEdgeData/raw/cfb/pbp_research/as_of_20260915/`  |

Largest play deltas: 2021 +952, 2025 +203, 2024 +192. Game counts never drifted.

### Regenerated #559 eligibility (closed)

|                                   |      #559 snapshot |                                                       Closed |
| --------------------------------- | -----------------: | -----------------------------------------------------------: |
| Eligible completed∩PBP `week < 3` |                 85 |                                                       **84** |
| `401868140` included              | yes (DELAYED 21–0) | **no** (`excluded_incomplete_pbp`; Q2 28–0 vs official 49–7) |

### Selected parameters (2023–2024 val only; 2025 untouched)

Estimator `fit_joint_v2_joint_mu_hfa_n0_ridge`. Pre-fix 0.1659 / λ=160 is **not frozen**.

**Frozen knobs:** `λ=40`, `λ_fcs=4λ`, `n0=4`, `decay=0.75`, 12 iters.

Val n = 3,363 team-games (same as pre-fix). Selected val MAE **0.1669** vs unadj 0.1898 vs blend 0.1810.

Grid cells that differ only in `n0` now produce different val MAE (λ=80 / decay=0.75: n0=3 → 0.16729, n0=4 → 0.16739, n0=6 → 0.16781).

### 2025 holdout (untouched; rematerialized)

n = **1,713** FBS team-games (same games as pre-fix).

| Predictor                   | Next-game EPA MAE |   RMSE |            Bias | Early (W1–4) MAE |
| --------------------------- | ----------------: | -----: | --------------: | ---------------: |
| Opponent-adjusted           |        **0.1673** | 0.2097 |         −0.0107 |           0.1775 |
| Unadjusted STD              |            0.1911 | 0.2424 | +0.011 / −0.029 |                — |
| Prior-season blend (`n0=4`) |            0.1837 | 0.2310 | +0.004 / −0.021 |                — |

Relative MAE cut: **12.4%** vs unadjusted, **8.9%** vs blend. Early-season 0.1775 still beats full-season unadjusted 0.1911.

Train diagnostic (2016–2022, n=10,594) MAE 0.1656 vs unadj 0.1897 vs blend 0.1810 — same direction, not used for selection.

Watch item (does not flip the MAE call): identified HFA ≈ **0.24 EPA/play** on the 2026 window (μ ≈ −0.11). That is large vs a typical 2–3 point CFB home edge. Research-only; do not convert to a spread.

---

## 6. 2026 research application

Frozen `λ=40 / n0=4 / decay=0.75` on the **84** closed eligible 2026 games (168 team-game observations). `401868140` remains excluded (PBP still Q2 28–0).  
134 FBS teams (92 with 2026 games; **42 prior-only**, `prior_weight=1`).  
`μ = −0.106`, `h = 0.244`.

These are **efficiency estimates**. Not spreads. Not KEI.

Sample (teams with ≥1 2026 game; off = higher better, def = EPA allowed, lower better):

| Team | off adj | def adj | n games | prior weight |
| ---- | ------: | ------: | ------: | -----------: |
| IU   |  +0.186 |  −0.127 |       2 |         0.67 |
| MIA  |  +0.198 |  −0.141 |       2 |         0.67 |
| OSU  |  +0.124 |  −0.166 |       1 |         0.80 |
| OU   |  −0.022 |  −0.156 |       2 |         0.67 |

Full table: `data/ops/cfb-research-opp-adj-epa-20260915/cfb_2026_adj_epa.json`.

---

## Reproducible commands

```bash
# Unit tests (no network, no lake write)
cd services/model-service
python3 -m pytest tests/test_cfb_research_opp_adj.py \
  tests/test_cfb_2026_w1_team_game_metrics.py \
  tests/test_cfb_owned_pbp_metrics.py -q

# Rematerialize val/holdout/2026 on the fixed estimator (reuse restored hist)
PYTHONPATH=services/model-service python3 scripts/cfb/run_research_opp_adj.py \
  --as-of 20260915 --as-of-week 3 --skip-hist --no-fetch --write-ops
```

No CFBD key. No write to Aug 13 `raw/cfb/pbp/`.

---

## Recommendation

Decision rule was locked **before** looking at 2025:

| Result                                                              | Call                                             |
| ------------------------------------------------------------------- | ------------------------------------------------ |
| Holdout MAE beats both baselines by ≥1% relative or ≥0.005 absolute | **advance** (research; not a production promote) |
| Beats one baseline, or the gain is thin                             | **revise**                                       |
| Beats neither, or n < 200                                           | **reject**                                       |

**Call: advance.** Rematerialized holdout MAE **0.1673** beats unadjusted 0.1911 (−12.4%) and prior blend 0.1837 (−8.9%), n=1,713. Locked knobs: `λ=40`, `n0=4`, `decay=0.75`, `λ_fcs=4λ`, 12 iters. Estimator `fit_joint_v2_joint_mu_hfa_n0_ridge`. `production_promote=false`. Production SP+ / NFL / KEI unchanged.

Checksums: `data/ops/cfb-research-opp-adj-epa-20260915/artifact_checksums.json`.

Do **not** convert these efficiencies into fair spreads or totals in this PR. That work comes afterward.

**STOP.**
