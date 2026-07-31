# NFL Props Systematic UNDER Bias — Diagnosis

**Date:** 2026-07-31  
**Branch:** `cursor/nfl-props-under-bias-6a2a`  
**Live board default:** `/pro/nfl/props` → season **2025** week **17** (PLAY tab)  
**Model service:** `https://model-service-production-e253.up.railway.app`

---

## 1. Symptom (measured)

Default PLAY board was **5/5 Under** (100%). Late densify weeks tip the same way; mid-season was balanced.

### 1.1 PLAY Under vs Over by week (2025, live API)

| Week | PLAY n | Under | Over | Under % |
| ---: | ---: | ---: | ---: | ---: |
| 10 | 20 | 9 | 11 | 45% |
| 11 | 31 | 15 | 16 | 48% |
| 12 | 36 | 11 | 25 | 31% |
| 13 | 40 | 20 | 20 | 50% |
| 14 | 1 | 1 | 0 | **100%** |
| 15 | 0 | — | — | — |
| 16 | 2 | 2 | 0 | **100%** |
| 17 | 5 | 5 | 0 | **100%** |
| **10–17** | **135** | **63** | **72** | **47%** |

PLAY market is **rec_yds only** (`PLAY_MARKETS = {rec_yds}`).

### 1.2 2025 W17 board mix (joined markets)

| Slice | n | Note |
| --- | ---: | --- |
| All rows | 1929 | box_score sourced |
| Market joined | 415 | |
| PLAY | 5 | **5 Under / 0 Over** |
| WATCH | 124 | Under 70 / Over 54 |

### 1.3 Signed error: model_mean − market line (joined, W17)

| Market | n | Mean gap | Median gap | % model &lt; line |
| --- | ---: | ---: | ---: | ---: |
| pass_yds | 31 | +6.99 | +11.54 | 32.3% |
| rush_yds | 86 | +1.39 | +1.94 | 43.0% |
| rec_yds | 177 | +2.01 | +3.58 | 35.6% |
| receptions | 121 | −0.16 | −0.20 | 59.5% |

Overall rec_yds is **slightly above** the market on average. The Under PLAY bias is **not** a global mean under-shoot — it is concentrated in **featured** receivers and the tagger.

### 1.4 Featured receivers (rec_yds line ≥ 40, W17)

| Metric | Value |
| --- | ---: |
| n | 44 |
| Mean raw_model_mean − line | **−13.99 yd** |
| Mean calibrated mean − line | **−6.72 yd** |

Examples (raw → line → calibrated):

| Player | Team | Raw | Line | Cal mean | Tag |
| --- | --- | ---: | ---: | ---: | --- |
| D.London | ATL | 14.4 | 68.5 | 41.0 | PASS (disagreement) |
| L.McConkey | LAC | 10.4 | 42.5 | 22.8 | PASS (disagreement) |
| T.McMillan | CAR | 22.8 | 52.5 | 34.5 | **PLAY Under** |
| J.Addison | MIN | 12.7 | 41.5 | 24.1 | **PLAY Under** |
| M.Harrison | ARI | 11.9 | 36.5 | 22.1 | **PLAY Under** |
| J.Chase | CIN | 65.0 | 90.5 | 75.5 | PASS |

### 1.5 W17 PLAY detail (all Unders)

| Player | Pos | Raw | Line | Mean | z | role (features) | shrink | reason |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| J.Addison | WR | 12.7 | 41.5 | 24.2 | −0.89 | 0.161 | 0.30 | rec_yds_research_unconfirmed |
| M.Harrison | WR | 11.9 | 36.5 | 22.1 | −0.73 | 0.150 | 0.30 | rec_yds_research_unconfirmed |
| S.Barkley | RB | 2.6 | 12.5 | 8.3 | −0.65 | 0.193 | 0.30 | rec_yds_research_unconfirmed |
| J.Warren | RB | 2.2 | 11.5 | 7.8 | −0.64 | 0.194 | 0.30 | rec_yds_research_unconfirmed |
| T.McMillan | WR | 22.8 | 52.5 | 34.5 | −0.64 | 0.150 | 0.30 | rec_yds_research_unconfirmed |

---

## 2. Code path

```
features weekly (role/target proxies)
  → baseline_projection_from_features (+ depth floors if chart hits)
  → box-score MC (Dirichlet share of team pass volume)
  → materialize_nfl_player_props_edges
       60/40 MC+baseline blend
       → apply_prop_calibration (intercept + market shrink)
       → evaluate_prop_edge / classify_prop_tag (PLAY/WATCH/PASS)
  → nfl_player_prop_model_edges → /nfl/props/board → web
```

Supervised overlays affect **sides/totals**, not player props. Props are independent of the DAL@NYG supervised/market-blend path.

---

## 3. Hypotheses tested

| Hypothesis | Verdict | Evidence |
| --- | --- | --- |
| Playing-time / snap share too low | **Partial** | Collapsed WR math without depth floor → ~14 yd matches Addison/Harrison raw |
| Pace / pass rate understated | Unlikely primary | Team pass attempts estimate ~35; healthy WR1 with floors → ~79 yd |
| Target share biased low | **Yes when depth miss** | Depth prior floor (0.24 WR1) never applied if chart join fails |
| NB/Poisson scale wrong | No | Yard means from efficiency×volume, not mis-scaled Poisson rates |
| Market structurally high | No for alphas | Books 40–90 yd vs model 12–35 raw is model failure |
| Publish policy only surfaces Unders | **Contributing** | PLAY Unders sit in gap band just inside `MAX_ABS_MEAN_GAP`; extreme collapses → disagreement PASS; Overs for featured WRs rare |
| Correlation / script dampening | Secondary | Box MC dilutes if many scrub receivers share pool; not the primary 14-yd crush |
| Missing matchup features | Not root | Opponent factors exist; crush happens even before matchup |

---

## 4. Root cause (named)

**Depth-floor miss + involvement-scale role misuse → collapsed featured receiving projections → PLAY tags the residual as Under.**

Three linked defects:

1. **Projection collapse when official depth-chart joins miss**  
   Without `depth_role_confidence_floor` + WR1 target prior, a WR with involvement-scale role ~0.16 and low `target_proxy` projects **~14 receiving yards**. Healthy WR1 with floors projects **~79 yd**. Live featured (line≥40) mean raw gap ≈ **−14 yd**.

2. **Props path used raw features `role_confidence` (p50≈0.21, max≈0.42 on W17 joins)**  
   Calibration `LOW_ROLE_CONFIDENCE=0.55` and enterprise v2 “solid role” rules assume the **floored starter scale**. Result: **100% of joined props** took `MARKET_SHRINK_LOW_ROLE=0.30`.

3. **Tag asymmetry on model failure**  
   Extreme collapses trip disagreement (`gap > 18`) → PASS. Collapses that land in gap ≈ 4–18 with `|z|≥0.60` become **PLAY Under**. That is publishing model failure as research edge — exactly the default W17 board.

Framework vs supervised: **N/A for props** (no supervised overlay on prop means). Prior DAL@NYG work was sides/ML/totals only.

---

## 5. Fix shipped (structural)

| Change | Where | Why causal |
| --- | --- | --- |
| Usage-rank depth fallback (per team×position) | `nfl_player_projection_engine` + baseline/box materializers | Restores WR1/TE1/RB1 floors when chart IDs/weeks miss |
| Effective floored role on props path | `materialize_nfl_player_props_edges` | Shrink + PLAY gates see starter-scale role, matching baselines |
| `model_role_collapse` Under gate | `nfl_prop_edge_policy` | Refuse Under tags when `raw_mean < 0.55 × line` on meaningful lines |
| `MIN_ROLE_CONFIDENCE_PLAY` → 0.50 | edge policy | Align with enterprise v2 solid-role intent after flooring |
| Canary `worker_build_id` | `props-under-bias-20260731a-usage-depth-role` | Prove deploy |

**Not done (and not a hack):** “nudge overs up 10%”.

### Offline impact of role-collapse gate alone (W10–17 PLAY)

| | Under | Over | Removed |
| --- | ---: | ---: | ---: |
| Before | 63 | 72 | — |
| After gate | 34 | 72 | 29 fake Unders |

Default W17 PLAY Unders (Addison / Harrison / McMillan class) are in the removed set.

---

## 6. Rematerialize / verify checklist

1. Deploy Railway model-service (+ worker) with canary.  
2. Run baselines → box sims → props edges for **2025 W14–W17** (and 2026 W1 when yard markets join).  
3. Re-measure PLAY Under % on W17; featured raw gap for line≥40.  
4. Sanity: fair-lines spreads/totals unchanged by props-only path; spot-check season receiving leaders not crushed.

---

## 7. Data gaps / paid feeds

| Need | Status |
| --- | --- |
| Official depth charts | In DB (`nfl_dp_depth_chart_weekly`) but joins miss — usage-rank fallback mitigates |
| Snap counts | Freshness: not fully backfilled; PBP involvement proxy in use |
| Pass/rush defensive EPA split | Shared overall EPA today; nice-to-have, not root |
| Paid prop CLOSING lines densify | Odds historical credits; continue densify batches for holdouts |

No purchase is **blocking** this Under-bias fix. Optional: SportsDataIO / Action Network closing props for denser holdout grading.


---

## 8. Deploy blocker found & fixed (same PR)

Rematerialize jobs on brave-art were failing with:

`_box_dist_moments() got an unexpected keyword argument 'season'`

**Cause:** `@celery_app.task(name="src.tasks.materialize_nfl_player_props_edges")` was accidentally decorating the helper `_box_dist_moments` instead of `materialize_nfl_player_props_edges`. In-process callers still worked; Celery `send_task` did not — board `updated_at` stuck at 2026-07-21.

**Fix:** move decorator onto the materializer; canary `props-under-bias-20260731b-celery-props-task`; regression test `test_nfl_props_celery_task_binding.py`.
