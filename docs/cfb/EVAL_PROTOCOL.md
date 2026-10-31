# EVAL PROTOCOL — CFB efficiency → scoring (research)

**Locked:** 2026-09-15, commit on this file **before** any scoring-knob search or model selection.  
**Authorized:** Ryan / CoS GO — research-only.  
**`production_promote=false`.** Boards stay Coming soon. Live SP+ / KEI unchanged. No board reopen.

This protocol governs the **scoring conversion** (team points → margin / total).  
It does **not** reopen #560 EPA knobs.

---

## 0. Why 2025 is not a fresh scoring test

2025 is a **known result** of the EPA experiment (#560). λ / n0 / decay were selected on 2023–2024; 2025 was the sealed EPA holdout (MAE 0.1673 vs unadj / blend).  

**Do not present 2025 as an untouched confirmation set for scoring.**  
If 2025 scoring numbers are published, they are labeled **development evidence** only.

---

## 1. Frozen EPA stack (do not retune)

| Item | Value |
| --- | --- |
| Estimator | `fit_joint_v2_joint_mu_hfa_n0_ridge` |
| Knobs | `λ=40`, `n0=4`, `decay=0.75`, `λ_fcs=4λ`, 12 iters |
| Pregame cutoff | same-season `week < W`; decayed prior-season finals |
| Seed | 2014–2015 |
| EPA train diagnostic | 2016–2022 (not used for EPA selection) |
| EPA selection | 2023–2024 (`holdout_used_for_selection=false`) |
| EPA holdout | 2025 (sealed) |
| Thin-window `h≈0.244` | EPA/play on the **home offense** row, 2026 W1–2 (168 obs). **Not a spread.** Do **not** multiply by play count. |

Carry-in A (this PR, before scoring): unadj / blend fallbacks must be **independent of the candidate** (see §6). Re-report #560-style holdout on the **same** 1,713 obs keys. File the delta. Do not claim the old pair-MAE improvement if the clean benchmark changes the story.

---

## 2. Scoring task

Predict **each team’s points** from pregame features only, then:

```
margin = home_points − away_points     # home perspective; documented sign
total  = home_points + away_points
```

Inputs (pregame only; no synthetic fills; no CFBD):

1. Pregame opponent-adjusted O/D EPA from the frozen #560 method (research artifacts, not production KEI).
2. Expected pace / possessions from owned PBP (formula locked in §5).
3. Verified supporting features only (#555 / #559 definitions).

---

## 3. Chronological sets for **this scoring task**

| Set | Seasons / window | Role | May look at for selection? |
| --- | --- | --- | --- |
| **Train** | 2016–2022, all weeks with official scores | Fit scoring intercept / slope / long-run HFA prior / pace constants | **Fit only.** No candidate ranking. |
| **Validation** | **2023 full season** | Select scoring knobs (HFA shrink `k`, pace source) | **Yes — only set used to pick among candidates.** |
| **Confirmation (seal)** | **2024 weeks ≥ 10** | Genuinely unseen for **scoring knobs**. Recommendation is based on this set. | **No. Forbidden until knobs are frozen.** |
| **Development evidence** | 2025 full season | EPA-known year. Transfer check only. | **No.** Report after confirmation, labeled development evidence. |
| 2026 W1–2 | 84 closed #559 games | Application sketch only; too thin to seal | **No.** |

### Why confirmation is 2024 weeks ≥ 10 (not 2025, not 2026)

- **2025** was the EPA holdout. Using it as the scoring seal would recycle a known EPA result. Forbidden as confirmation.
- **2026** is an incomplete early window (84 games). Too thin; application only.
- **2024 weeks ≥ 10** was never used to choose scoring knobs (val is 2023 only). It is a late-season window with a real slate (regular + CFP/bowl as present in owned PBP).

**Caveat (required):** EPA λ was selected on **full** 2023–2024 next-game EPA MAE. Confirmation therefore seals the **scoring conversion given frozen EPA**, not a fully independent EPA+scoring stack. If we must reuse history, this window is still the cleanest unused-for-scoring cut. It is **confirmation for scoring knobs**, not a claim that 2024 was unseen by EPA.

A later season that EPA selection never touched does not exist in the owned lake yet (2026 is incomplete).

### When selection may look at which sets

| Activity | Train 2016–22 | Val 2023 | Confirm 2024 W≥10 | Dev-ev 2025 | 2026 |
| --- | --- | --- | --- | --- | --- |
| Fit `a`, `b`, HFA prior, pace constants | yes | no | no | no | no |
| Rank / pick scoring candidates | no | **yes** | no | no | no |
| Freeze knobs | after val pick | after val pick | no | no | no |
| Recommendation (advance / revise / reject) | supporting | supporting | **seal** | labeled only | no |
| Retune after seeing confirmation | **forbidden** | **forbidden** | **forbidden** | **forbidden** | **forbidden** |

Software seal: `select_scoring_params` must receive `val_seasons=(2023,)` only. Contract test: 2024 / 2025 / 2026 not in selection seasons; confirmation scored only after knobs are written.

---

## 4. Metrics (always separate)

Report **all** of the following on each set. Do not collapse margin and total into one number.

| Target | Error | Bias |
| --- | --- | --- |
| **Margin** (`home − away`) | MAE, RMSE | mean(pred − actual) |
| **Total** (`home + away`) | MAE, RMSE | mean(pred − actual) |
| **Per-team points** | MAE, RMSE | mean(pred − actual) |

Slices (same metrics):

- Early: weeks 1–4
- Mid: weeks 5–9
- Late: weeks ≥ 10
- FBS vs FBS only (primary); FBS vs FCS as a footnote if n is reported separately

n = number of **games** for margin/total; n = team-games for per-team points.

---

## 5. Model form (structure locked; knobs selected on 2023 only)

### 5.1 Expected pace / possessions (owned PBP)

From #555 / #559:

- `pace_plays` = scrimmage plays as `pos_team` in that game  
- `competitive_pace_plays` = same with `|pos_score_diff| < 16`  
- `n_drives` = unique `(game_id, drive.id)` for that offense  

**Plays per possession** (train constant):

```
ppp = mean( pace_plays / n_drives )
```

over train (2016–2022) FBS-offense team-games with `n_drives ≥ 1`. Document the number. No synthetic fill.

**Pregame expected plays for team i at week W:**

1. Same-season mean of the chosen pace source for games with `week < W`, if ≥ 1 game.  
2. Else prior-season mean of that source.  
3. Else train-period league mean of that source (IBF-style; never a candidate-model μ).

**Game-level expected plays** (both offenses share a pace):

```
exp_plays = 0.5 * (pace_pregame_home + pace_pregame_away)
exp_poss  = exp_plays / ppp
```

Pace **source** is a scoring knob: `{competitive_pace_plays, pace_plays}`, selected on **2023 val total MAE** only.

### 5.2 Points

EPA prediction for team i vs j uses frozen #560 `predict_game` **without converting the EPA `h` term into points**.

```
epa_i = μ_fit + off_i + def_j     # drop h·home from the EPA predictor for scoring
points_i = a + b * (epa_i * exp_plays) + h_pts * home_i
```

- `home_i = 1` if i is the home team, else `0` (neutral / unknown → 0).  
- `a`, `b` fit by weighted OLS on **train** only (weight = 1 per team-game).  
- `μ_fit` is the EPA intercept from the pregame fit (league EPA/play). It is **not** HFA.

### 5.3 HFA shrinkage (points, not EPA/play × plays)

Long-run prior, **train only**, non-neutral games with official scores:

```
h_prior = mean(home_points − away_points)     # expected home margin if teams otherwise cancel
```

Window estimate `h_window` = OLS `h` on the train points equation (large-N).  

For any apply window with `N` non-neutral games in the **HFA estimation sample** (train N for the locked model; never the 2026 84-game window alone):

```
h_pts = (N / (N + k)) * h_window + (k / (N + k)) * h_prior
```

`k` selected on **2023 val margin MAE** from grid `{10, 20, 40, 80, 160}`.

**Forbidden:** `spread ≈ 0.244 × n_plays` (or any thin-window EPA `h` × play count).

Document the locked `h_pts` in points (and `k`, `N`, `h_window`, `h_prior`).

### 5.4 Candidate grid (2023 val only)

| Knob | Grid |
| --- | --- |
| Pace source | `competitive_pace_plays`, `pace_plays` |
| HFA shrink `k` | 10, 20, 40, 80, 160 |

`a`, `b`, `h_window`, `h_prior`, `ppp`, league pace mean: **estimated on train**, not searched.

Selection objective (2023 only): minimize `0.5 * (margin_MAE + total_MAE)`. Tie-break: smaller `|margin_bias|`.

---

## 6. Independent baseline fallbacks (EPA carry-in A)

#560 rematerialize: 5 defender rows used adj-model `μ` when STD and prior-season raw were missing. That couples the baseline to the candidate.

**IBF-v1 (exact rule):**

When a team has no same-season STD (`week < W`) and no prior-season raw mean:

```
fallback = mean(y) over FBS-offense team-games in seasons 2014–2022
           (PRIOR_SEED ∪ TRAIN)
```

- One constant, computed once from seed+train `y` only.  
- Same constant for offense and defense fallbacks.  
- **Never** `fit.mu`. **Never** val (2023–2024) or holdout (2025) or apply (2026) games.  
- If seed+train rows are absent in a unit test, use `0.0` (league-centered raw).

Re-report opp-adj vs unadj vs prior blend on the **same** 2025 obs keys (`009ce549…`). File delta vs `frozen_method.json` / `validation_report.json` holdout pair-MAE. Do not claim the old 12.4% / 8.9% figures if they move.

Scoring baselines (Vegas-free; same pregame cutoff):

1. Season-to-date mean points (week < W); IBF-v1-style train league mean points if missing.  
2. Prior-season mean points blend (`n0=4` game-equivalents).  
3. League mean total / zero-mean margin (train constants).

---

## 7. Decision rule (locked before confirmation is scored)

On the **confirmation** set only (2024 weeks ≥ 10):

| Result | Call |
| --- | --- |
| Beats **both** points baselines on **margin MAE and total MAE** by ≥1% relative **or** ≥0.25 points absolute, and \|margin bias\| and \|total bias\| are not worse than the better baseline by more than 1.5 points | **advance** (research; not a production promote) |
| Beats one of {margin, total}, or the gain is thinner than the row above | **revise** |
| Beats neither, or confirmation n (games) < 150 | **reject** |

`production_promote` is **always false** in this PR regardless of call.

2025 numbers, if shown, must not change the call. They are development evidence.

---

## 8. Out of scope

- UI / Edge Board / Coming soon chrome  
- Production SP+ / KEI / NFL  
- Stake tags, PLAY / LEAN  
- CFBD  
- Synthetic score or pace fills  
- Promoting research EPA or scoring into live boards  

**STOP** when the research PR + recommendation are ready. Promotion is a separate Ryan decision.

---

## 9. Reproducible entrypoints (filled after lock; do not use to retune)

```bash
# Unit tests (no lake)
cd services/model-service
python3 -m pytest tests/test_cfb_research_opp_adj.py \
  tests/test_cfb_research_scoring.py -q

# A) Clean EPA baselines, same obs keys (frozen knobs; no grid)
PYTHONPATH=services/model-service python3 scripts/cfb/run_research_opp_adj_clean_baselines.py \
  --as-of 20260915 --write-ops

# B) Scoring: fit train / select val / seal confirmation (in that order)
PYTHONPATH=services/model-service python3 scripts/cfb/run_research_scoring.py \
  --as-of 20260915 --write-ops
```

No CFBD key. No write to Aug 13 `raw/cfb/pbp/`.
