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

| Field | Value |
| --- | --- |
| `game_id` | `401868140` |
| Teams | Eastern Kentucky @ Jacksonville State |
| Week | 1 |
| Old snapshot status | `STATUS_DELAYED` |
| Old snapshot score | 21–0 |
| Old #559 decision | **included** (score present and not live) |
| Verification | ESPN site summary + box + recap (no CFBD) |
| Official status | `STATUS_FINAL` (`state=post`, `completed=true`) |
| Official score | **49–7** (JSU 49, EKU 7) |
| Sources | `https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event=401868140` · [ESPN box](https://www.espn.com/college-football/boxscore/_/gameId/401868140) · [ESPN recap](https://www.espn.com/college-football/recap?gameId=401868140) · JSU athletics (lightning delay; final 49–7) |
| **Decision on #559 snapshot** | **EXCLUDE** |

A score alone is insufficient. The 21–0 capture is a mid-game lightning delay, not the official final. Regenerated #559 eligibility treats **all parked DELAYED/POSTPONED games as unfinished** unless the schedule row is `STATUS_FINAL`. A later as_of may include `401868140` only when status is `STATUS_FINAL` and scores are 49–7.

---

## 2. Historical raw features (2014–2025)

Same #555 / #559 definitions:

- Success rate labeled **`EPA_success = EPA>0`**
- Standard 50/70/100 SR is a **separate** column
- EPA/play, pace / competitive pace, explosiveness, down splits, scoring opportunities / PPO / finishing, field position

Restore: SportsDataverse `espn_cfb_pbp` season parquets.  
**Never overwrite** `/Volumes/KosEdgeData/raw/cfb/pbp/` (Aug 13 SoT).

| Role | Path |
| --- | --- |
| Canonical HD lake (do not write) | `/Volumes/KosEdgeData/raw/cfb/pbp/` |
| HD research mirror (documented) | `/Volumes/KosEdgeData/raw/cfb/pbp_research/as_of_20260915/` |
| VM restore | `data/cfb/research/pbp_hist/as_of_20260915/` |

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
- Home-field `h` estimated on the fitting window only (neutral / unknown → 0)

### Eligible-play rules

| Rule | Treatment |
| --- | --- |
| Scrimmage | #555: truthy `scrimmage_play`, else pass\|rush |
| EPA | finite `EPA` required |
| Overtime | **exclude** `period/qtr ≥ 5` |
| Garbage | warehouse `garbage_weight` (not a hard drop; min 0.10) |
| FCS | kept and flagged; `λ_fcs = 4λ`; FCS not in the centering set |
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

Filled after `run_research_opp_adj.py` (see ops JSON).

---

## 6. 2026 research application

Frozen selected parameters applied to 2026 completed∩PBP games after the delayed-game close. Outputs are efficiency estimates with sample size, prior weight, and uncertainty. **Not spreads.**

---

## Reproducible commands

```bash
# Unit tests (no network, no lake write)
cd services/model-service
python3 -m pytest tests/test_cfb_research_opp_adj.py \
  tests/test_cfb_2026_w1_team_game_metrics.py \
  tests/test_cfb_owned_pbp_metrics.py -q

# Full research run (SDV restore + validation + 2026 apply)
PYTHONPATH=services/model-service python3 scripts/cfb/run_research_opp_adj.py \
  --as-of 20260915 --as-of-week 3 --write-ops
```

No CFBD key. No write to Aug 13 `raw/cfb/pbp/`.

---

## Recommendation

**Pending holdout numbers** from the research run. Decision rule (locked before looking at 2025):

| Result | Call |
| --- | --- |
| Holdout MAE beats both baselines by ≥1% relative or ≥0.005 absolute | **advance** (research; not a production promote) |
| Beats one baseline, or the gain is thin | **revise** |
| Beats neither, or n < 200 | **reject** |

Converting efficiencies into fair spreads/totals is **out of scope**.

**STOP.**
