# B2-PACE-v1 — Frozen Challenger Specification

**Status:** FROZEN for implementation / Train-A diagnostics / pocket readiness  
**Not promoted. Not production default. Not scored on Test-A or pocket_2025 in this phase.**

## Immutable identifiers

| Field | Value |
|---|---|
| Candidate ID | `B2-PACE-v1` |
| Method ID | `kenpom_adjem_pit_tempo_plus_game_hca_v1` |
| Research alias (docs only) | `C3` |
| Incumbent preserved | `B2-C0-v1` / `kenpom_adjem_plus_hca_v1` |

## Exact formula

```
adjem_diff = clip(home_adjem - away_adjem, -30, +30)
expected_possessions = (home_adjt + away_adjt) / 2
raw_home_margin = adjem_diff * (expected_possessions / 100) + 2.8696
fair_home_margin = clip(raw_home_margin, -28, +28)
```

### Units

- AdjEM: points per 100 possessions (KenPom)
- AdjT: possessions per 40 minutes (KenPom)
- HCA `2.8696`: game points (frozen; identical to incumbent)
- fair_home_margin: predicted home margin in game points

### Sign convention

`fair_spread_home` / `fair_spread_home_b2_pace_v1` = predicted **home margin**.  
Positive ⇒ home predicted to win by that many points. Matches incumbent B2.

### Operation order (immutable)

1. Clip AdjEM differential at ±30  
2. Scale by `(expected_possessions / 100)`  
3. Add HCA `2.8696` **after** scaling  
4. Clip final margin at ±28  

## Inputs required (fail-closed)

- home AdjEM, away AdjEM (PIT)
- home AdjT, away AdjT (PIT)
- valid as-of timestamps ≤ tip for both sides

If any AdjT missing/invalid, or PIT as-of missing/post-tip: **no B2-PACE-v1 fair**.

### Forbidden substitutions

- current / post-tip / SETTLED ratings  
- market-implied tempo  
- fitted β  
- national-average pace fallback  

## Continuity honesty

PRIOR / UNKNOWN only. SETTLED forbidden (same portal DATA GAP rule as incumbent).

## What this candidate is / is not

**Is:** atomic unit correction (pts/100 → game points via PIT tempo).  
**Is not:** open-shrink, market feature, injury feature, HCA retune, neutral-site fix, fitted slope, gate change.

## Neutral-site known limitation

Incumbent C0 and B2-PACE-v1 both apply HCA `2.8696` to every game.  
Schedule SoT packs carry `neutral_site`, but it is **not** a Lab fair-engine input.  
Train-A descriptive split shows large negative bias on neutral games under C0.  
Registered future challenger stub: `B2-NEUTRAL-HCA-v1` (not implemented here).

## Code entrypoints

- Challenger: `apps/web/src/ncaam_lab/fair_b2_pace_v1.py`  
- Incumbent (unchanged): `apps/web/src/ncaam_lab/fair_b2.py`  
- Materialize still calls **only** incumbent `compute_fair_b2`  
- Explicit selection helper: `select_fair_candidate(...)` (no silent default)

## Train-A diagnostics (this freeze)

See:

- `data/ops/lab/ncaam/ncaam-b2-pace-v1-train-a-diagnostics.json`
- `data/ops/lab/ncaam/ncaam-b2-pace-v1-train-a-diagnostics.md`

Summary (eligible n=3583):

| Model | MAE | RMSE | bias | cal slope |
|---|---:|---:|---:|---:|
| C0 | 9.509 | 11.961 | -0.295 | 0.703 |
| B2-PACE-v1 | 9.060 | 11.449 | +0.370 | 1.013 |
| B1 | 8.746 | 11.092 | +0.375 | 1.009 |

Paired bootstrap (game grain, B=2000, seed=20260905):

- MAE(B2-PACE-v1)−MAE(C0) = **-0.449**, 95% CI **[-0.562, -0.336]** (all draws < 0)
- MAE(B2-PACE-v1)−MAE(B1) = **+0.314**, 95% CI **[+0.232, +0.394]** (all draws > 0)

AdjT coverage on Train-A Lab frame: **3676/3676 eligible (100%)**; missing AdjT either side: **0**.

## Test-A classification

Test-A is **development-exposed** for:

1. H1 / open-shrink family  
2. B2 unit / possession-correction family (this candidate)

Reason: Test-A residual structure and large-disagreement failures contributed to forming both hypotheses.  
Test-A may be reported historically but **cannot** serve as untouched confirmation for B2-PACE-v1.

## Preregistered pocket evaluation (NOT run this phase)

Pocket: `2025-11-01` → `2025-12-31` (sealed).

### Primary endpoint

`paired_delta_mae_b1 = MAE(B2-PACE-v1) - MAE(B1 close consensus)`

“Beat B1” requires frozen Predictive gate on the same pocket:

- eligible n ≥ 100  
- B2-PACE-v1 MAE ≤ pocket B1 MAE  
- |signed bias| ≤ 2  
- leakage = 0  
- no SETTLED inputs  

Report paired bootstrap CI for the MAE difference (gate itself unchanged).

### Secondary endpoints

- MAE vs frozen C0  
- RMSE vs B1 and C0  
- signed bias  
- calibration slope/intercept  
- by |raw AdjEM gap|  
- favorites with |raw AdjEM gap| ≥ 12  
- PIT coverage / missingness  
- neutral-site descriptive split if flag reliable  

No result-dependent filtering or threshold selection.

## Hard locks

- No Test-A challenger scoring in this phase  
- No 2025 pocket performance access in this phase  
- No open-shrink / market / injury / HCA retune / neutral fix / fitted β  
- No gate changes / odds pull / scorecard rewrite  
- No production default change / board / PLAY  
- No merge or deploy without separate authorization  

## Hashes / commit

Filled at freeze commit time in twin JSON:
`data/ops/lab/ncaam/ncaam-b2-pace-v1-frozen-spec.json`
