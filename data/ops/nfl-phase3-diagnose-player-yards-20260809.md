# NFL Phase 3 Path A — Diagnose player season yards (2026-08-09)

**Depends on:** #164 merged (`3a44b7aa…` on `deploy-vercel`)  
**Engine under test:** `nfl-season-engine-v1.25-phase2-features`  
**Scorecard:** identical 2019–2025 no-look-ahead protocol (`nfl-historical-replay-v1-20260809`)  
**Artifacts:** `data/ops/nfl-phase3-historical-replay-20260809/` + spot sims (2019/2023, n=15)

## Headline gap

| Pool | Model MAE / bias | Prior-year+reg MAE (scorecard) |
|------|------------------:|-------------------------------:|
| player pass yards | **785** / +32 | **~228** (n≈228–270) |
| player rush yards | 202 / +58 | ~90–110 |
| player rec yards | 252 / **+155** | ~110–140 |
| team pass yards | 373 / −92 | — |
| team rush yards | 273 / −102 | — |

## 1. Bias vs noise

- **Pass (QB pool):** MAE ~785 with bias only ~+32 → **noise both ways**, not a one-sided level shift. Same shape every year (MAE 708–844).
- **Rush (QB/RB):** mild **high** bias (~+58); MAE ~2× prior.
- **Rec (WR/TE/RB):** **systematic high** (pooled bias +155; spot sims +236 / +289). This is the clearest directional failure.

Spot sims (matched QBs / RBs / WR-TE):

| Season | Group | Model MAE / bias | Prior MAE (same players) |
|--------|-------|------------------:|-------------------------:|
| 2019 | QB pass | 810 / +28 | 1206 |
| 2019 | RB rush | 261 / +107 | 238 |
| 2019 | WR/TE rec | 342 / +236 | 210 |
| 2023 | QB pass | 795 / +29 | 1192 |
| 2023 | WR/TE rec | 352 / +289 | 169 |

## 2. Anchor strength

Hierarchical path rebuilds season yards from depth × script × Dirichlet draws, then scales into **team** budgets. There is **no player-level prior-year volume shrink** on path totals (team budgets get a light `VOLUME_PRIOR_BLEND`; players do not).

Evidence the prior carry is too weak:

- WR/TE: `corr(pred, Y−1)` ≈ 0.45–0.50; median `|pred − Y−1|` ≫ median `|act − Y−1|` (model moves roles farther than reality).
- Best blend weight toward raw Y−1 volume for WR/TE: **0.0–0.2 model** (i.e. almost pure prior).
- RB: best blend often 0.25–0.75 toward prior depending on year.
- QB: already tracks Y−1 better (`corr` 0.58–0.79); best blend stays mostly on the model — QBs are not the primary lever.

## 3. Depth volatility

Path-0 logs ~74 share drifts + ~6 role shuffles. QB1 season CV across sims is tiny (~0.02), and QB1 takes ~94% of named QB pass — **mid-season role noise is not what destroys QB season means**. Volatility matters more as part of the broader “roles get rebuilt” story for WR/RB committees, not as the single QB failure mode.

## 4. Team pool vs player split

- Team pass/rush pools are **low** (bias −92 / −102) → pools are wrong.
- Player pass bias is near zero while MAE is huge → not explained by pool level alone.
- Player rec is **high** while team pass is **low** → named skill **allocation** invents receiving volume relative to actuals (and relative to a prior+regression baseline).

So: pools imperfect, but the player-yards loss vs prior is driven by **allocation without prior volume shrink**, especially receiving.

## 5. Year pattern

Failure is **regime-stable 2019–2025** (including COVID 2020). Not a single-year artifact.

## Scorecard caveat (explains ~785 vs ~228)

Published prior pass MAE (~228) scores **all matched skill players** on `pass_yards` (many near-zero non-QBs), while model pass MAE (~785) scores **QBs only** (n≈65–72). On **QB-matched** players, prior MAE is ~1200 — **worse** than the hierarchical model (~800).

Honest read: the headline gap is inflated by population mismatch; the engine’s real, fixable loss vs prior on player season yards is **rush/rec volume rebuilt without prior-year shrinkage** (rec bias the smoking gun).

## Single primary failure mode

**Named player season yards are rebuilt from hierarchical depth/script noise and only conserved at the team pool, with no shrinkage to prior-year (or prior+position-mean) volume — so receiving/rushing totals systematically mis-allocate and inflate MAE versus a simple prior+regression baseline (while the published pass 785 vs 228 gap is amplified by QB-only vs all-skill scorecard dilution).**

## Chosen fix (one lever)

Stronger **prior-year volume anchor / shrinkage on player season totals** after path accumulation, then re-enforce existing team budgets (wins/PF/PA path unchanged). Matches diagnosis; does not retune 2026 looks or stack unrelated levers.

**Outcome:** implemented, re-ran identical scorecard, **reverted** — see [`nfl-phase3-pathA-rerun-20260809.md`](./nfl-phase3-pathA-rerun-20260809.md). Player pass MAE worsened; failure mode remains open.
