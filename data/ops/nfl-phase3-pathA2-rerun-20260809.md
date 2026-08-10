# NFL Phase 3 Path A2 — Player yards usage-prior fix + re-run (2026-08-09)

**Depends on:** #166 (`bd63dc53…` / tip `526bc2b3…` on `deploy-vercel`)  
**Diagnosis:** [`nfl-phase3-diagnose-player-yards-A2-20260809.md`](./nfl-phase3-diagnose-player-yards-A2-20260809.md)  
**Protocol:** identical to #164 — seasons 2019–2025, `n_sims=25`, seed base `20260809`, `nfl-historical-replay-v1-20260809`  
**Before stamp:** `nfl-season-engine-v1.25-phase2-features` (post-#166 reverted baseline)  
**After stamp:** `nfl-season-engine-v1.26-phase3-pathA2-usage-prior` (**kept**)

## Primary failure mode (one sentence)

At usage construction, returning players’ season target/carry shares are stamped from depth-order archetype / structure tables and then script–Dirichlet noise, with prior-year player volume never applied as a usage input — so production and season aggregates rebuild roles without Y−1 volume shrinkage (while team budgets only conserve the pool, and the published pass 785 vs 228 gap was further inflated by QB-only vs all-skill scorecard dilution).

## One fix (matches diagnosis)

**Lever:** for returning players with material Y−1 volume, blend depth archetype `target_share` / `rush_share` toward prior-season share of **team** targets / rush attempts at usage construction (`PRIOR_USAGE_ANCHOR_WEIGHT=0.80`), after depth structure tables and before process priors / weekly sim. Rookies / unmatched keep depth defaults. QB pass volume untouched (rush share only). **No path-end season-yards blend.**

**Why it matches:** Path A proved path-end yard blending hurts QBs; the destroy point is usage construction. Anchoring shares before production is the in-path fix the diagnosis names.

**Scorecard hygiene (not the engine lever):** prior+reg player pass/rush/rec now use the **same position filters** as the model pool (QB / QB+RB / WR+TE+RB). Published #164 prior pass MAE ~228 was diluted by non-QB zeros; aligned prior pass MAE ≈ **1078** (n=365).

## Before → after (pooled, same protocol)

| Metric | Before (#164 / post-#166) MAE / bias | After (Path A2) MAE / bias | Δ MAE |
|--------|-------------------------------------:|---------------------------:|------:|
| team wins | 2.524 / −0.000 | 2.515 / −0.000 | −0.009 |
| prior-year+reg wins | 2.463 / −0.054 | 2.463 / −0.054 | 0 |
| team PF | 55.439 / −3.014 | 54.720 / −3.232 | −0.719 |
| team PA | 45.693 / −3.015 | 45.637 / −3.232 | −0.056 |
| team pass yards | 373.251 / −91.806 | 373.704 / −92.277 | +0.453 |
| team rush yards | 273.111 / −102.146 | 272.166 / −102.236 | −0.945 |
| player pass yards | 785.133 / +32.071 | 781.812 / +31.858 | −3.321 |
| player rush yards | 202.214 / +58.094 | 199.842 / +57.597 | −2.372 |
| player rec yards | 252.240 / +155.105 | 238.870 / +154.830 | −13.370 |

Aligned prior+reg player baselines (same universe as model): pass MAE **1077.7** (n=365), rush **190.5** (n=836), rec **156.5** (n=1370). Model still beats prior on pass; still loses on rush/rec.

## Decision-rule outcome: **KEEP**

| Gate | Result |
|------|--------|
| Clear improvement on player yards MAE | **YES (modest)** — pass/rush/rec all improved; largest gain on rec (−13.4). Rec bias still ~+155 (pool/level failure remains open for a later pass). |
| Wins / PF / PA not worse | **YES** — wins −0.009, PF −0.72, PA −0.06 |
| Action | **Keep** the usage-prior anchor. Do not stack further levers this pass. |

## Wins-claim status

**Still blocked.** Team-wins MAE 2.515 remains above prior-year+regression 2.463. Phase 4 model-value claim stays closed.

## Why this is not Path A theater

Path A blended **final yards** after the hierarchical rebuild (and hurt QB pass). Path A2 changes **usage inputs** for returning players only, leaves QB pass path alone, and keeps team budget enforcement unchanged.

## Artifacts

- Before: `data/ops/nfl-phase3-historical-replay-20260809/`
- After: `data/ops/nfl-phase3-pathA2-rerun-20260809/`
- Raw runner markdown: `data/ops/nfl-phase3-pathA2-rerun-benchmark-raw-20260809.md`
- Diagnosis: `data/ops/nfl-phase3-diagnose-player-yards-A2-20260809.md`

## Explicit non-goals (unchanged)

- No Phase 4/5 unlock from this pass
- No second lever stacked
- No path-end yard blend
- No props / Decision Engine / baseline freeze
