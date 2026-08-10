# NFL Phase 3 Path A — Player yards fix + re-run (2026-08-09)

**Depends on:** #164 (`3a44b7aa…` on `deploy-vercel`)  
**Diagnosis:** [`nfl-phase3-diagnose-player-yards-20260809.md`](./nfl-phase3-diagnose-player-yards-20260809.md)  
**Protocol:** identical to #164 — seasons 2019–2025, `n_sims=25`, seed base `20260809`, `nfl-historical-replay-v1-20260809`  
**Before stamp:** `nfl-season-engine-v1.25-phase2-features`  
**Attempted stamp:** `nfl-season-engine-v1.26-phase2-features-pathA-player-volume` (**reverted**)

## Primary failure mode (one sentence)

Named player season yards are rebuilt from hierarchical depth/script noise and only conserved at the team pool, with no shrinkage to prior-year (or prior+position-mean) volume — so receiving/rushing totals systematically mis-allocate versus a simple prior+regression baseline (while the published pass ~785 vs ~228 gap is amplified by QB-only vs all-skill scorecard dilution).

## One fix attempted (then reverted)

**Lever:** path-end blend of named player season yards toward `0.5 * Y−1 + 0.5 * position_mean` with weight `0.60`, then re-enforce existing team pass/rush/rec budgets. Wins/PF/PA are finalized from game outcomes before this step.

**Why it matched diagnosis:** spot sims showed WR/TE best blend weight toward prior ≈ 0.0–0.2 and strong positive rec bias; team-budget-only conservation left player allocation free to invent volume.

**Forbidden levers not touched:** team-named overrides, 2026 retune, Decision Engine, baseline expansion / scorecard change.

## Before → after (pooled, same scorecard)

| Metric | Before (#164) MAE / bias | After (Path A) MAE / bias | Δ MAE |
|--------|-------------------------:|--------------------------:|------:|
| team wins | 2.524 / −0.000 | 2.486 / −0.000 | −0.038 |
| prior-year+reg wins | 2.463 / −0.054 | 2.463 / −0.054 | 0 |
| team PF | 55.439 / −3.014 | 55.948 / −3.094 | +0.509 |
| team PA | 45.693 / −3.015 | 45.084 / −3.094 | −0.609 |
| team pass yards | 373.251 / −91.806 | 373.507 / −90.630 | +0.256 |
| team rush yards | 273.111 / −102.146 | 273.154 / −102.254 | +0.042 |
| **player pass yards** | **785.133 / +32.071** | **847.873 / −58.148** | **+62.740** |
| player rush yards | 202.214 / +58.094 | 204.648 / +47.749 | +2.434 |
| player rec yards | 252.240 / +155.105 | 230.946 / +155.415 | −21.293 |

Prior-year+regression player baselines (unchanged): pass MAE **228.0**, rush **96.1**, rec **124.1** (n=1735 each; prior pass pool still includes all-skill zeros).

## Decision-rule outcome: **REVERT**

| Gate | Result |
|------|--------|
| Clear improvement on player yards MAE | **NO** — headline pass MAE worsened (+63); rush flat/worse; only rec improved (−21) |
| Wins / PF / PA not worse | Mixed / not decisive (wins −0.04, PF +0.5, PA −0.6); still **lose** to prior on wins (2.486 vs 2.463) |
| Action | **Revert fix.** Failure mode still open. Do not layer more complexity this pass. |

## Wins-claim status

**Still blocked.** Team-wins MAE remains above prior-year+regression. Phase 4 model-value claim stays closed.

## Why the lever failed (brief)

Shrinking **all** yard types (including QB pass) toward the same 0.5/0.5 prior anchor hurt the QB-only pass scorecard: on matched QBs the hierarchical model already beat prior (~800 vs ~1200 MAE), so pulling pass volume toward prior then re-scaling into a still-low team pool raised pass MAE and flipped bias from mild high to low. Rec improved modestly but not enough to claim a clear player-yards win.

## Artifacts

- Before: `data/ops/nfl-phase3-historical-replay-20260809/`
- After (attempt): `data/ops/nfl-phase3-pathA-rerun-20260809/`
- Raw runner markdown: `data/ops/nfl-phase3-pathA-rerun-benchmark-raw-20260809.md`
- Diagnosis: `data/ops/nfl-phase3-diagnose-player-yards-20260809.md`

## Explicit non-goals (unchanged)

- No Phase 4/5 unlock from this pass
- No second lever stacked after revert
- No scorecard rewrite mid-flight (population mismatch noted in diagnosis only)

Merged as docs+revert only; blend lever dead; failure mode still open; Path A2 next
