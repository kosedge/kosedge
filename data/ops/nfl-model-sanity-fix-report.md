# NFL Model Sanity Fix Report

**Date:** 2026-07-30  
**Branch:** `nfl-second-order-edge`  
**Symptom (example, not a special-case):** DAL @ NYG — market NYG +2.6 / DAL −152, model `spread_home` −3.07, `home_win_prob` 0.59, spread+ML **PLAY**.

## Root cause

Not HFA alone and not a single-game bug.

1. **Framework EPA alone favors Dallas.** Reconstructing offense/defense indices from the Week-1 matchup pack yields ~`spread_home` **+1.06** after 0.30 market blend (Cowboys slight favorite). Published line was Giants −3.07 — a ~4-point swing past the framework.

2. **Validated supervised blend unlocked on a not-yet-played season.** `detect_real_rolling_features()` only checked `COUNT(DISTINCT off_epa_per_play_5g) > 1`. Preseason hydration / carry-forward can put **week-varying** EPA into the 2026 week grid before any REG game is scored. That returned `True` for both clubs and unlocked `VALIDATED_BLENDING_WEIGHTS` (**85% supervised spread**, ±14 pt trust region). Conservative path is 30% / ±7.

3. **Slate pattern matched the failure mode.** Across 167 fair-lines: 24 side flips vs market; home dogs pulled ~1.8 pts toward home; big favorites compressed. Classic “high-trust supervised on OOD early-season features.”

4. **Secondary issues addressed**
   - Team strength priors looked up by full name while rolling table keys are abbreviations → silent fallback to weaker context indices.
   - Early-season market blend stayed at 0.30 even in Week 1.
   - PLAY tags could fire on market-side disagreements (Giants PLAY as favorite while market has them as dogs).

## Fixes shipped (on `nfl-second-order-edge`)

| Change | File | Effect |
| --- | --- | --- |
| Real-features gate requires ≥3 **scored REG** games **and** EPA variance | `nfl_supervised_retrain.py` | Blocks validated weights until in-sample season |
| Ignore `fit_payload["blending"]` on conservative path | `nfl_supervised_retrain.py` | Stops saved 0.85 weights from leaking back in |
| Matchup pack lookup uses **team abbr** (not full name) | `tasks.py` | Week/features actually load; early-season gates can fire |
| Skip supervised overlay entirely for weeks 1–4 (and missing pack on 2026+) | `tasks.py` | No OOD supervised margin on early board |
| Prior lookup prefers `home_abbr` / `away_abbr` | `tasks.py` | EPA priors apply |
| Early-season market blend boost (W1 +0.25 → ~0.55) | `nfl_simulator.py` | Anchors thin weeks to consensus |
| PLAY blocked on market side disagreement | `nfl_side_total_publish_policy.py` + fair-lines | **Already live on API** — DAL@NYG spread/ML are PASS |
| Drop ST-KAV kwargs from `NflGameInputs` | `nfl_matchup_features.py` | Unblocked Celery re-sims (were FAILING) |
| `worker_build_id` canary in sim task result | `tasks.py` | Confirm worker image after deploy |

## Live status (as of 2026-07-30 evening deploy)

- **Railway deploy:** SUCCESS (api + worker + beat). Worker deployment `0ca23fbd` SUCCESS.
- **Canary:** `POST /api/jobs/run-nfl-simulations?game_date=2026-09-13&simulations=2000` → SUCCESS with
  `worker_build_id=sanity-fix-20260730c-abbr-skip-supervised-w1-4` (canary **LIVE**).
- **Full re-sim:** all **37** unique fair-lines dates (`days_ahead=120`), 4000 sims each, **37/37 SUCCESS**, same `worker_build_id`.
- **API publish gate:** LIVE — DAL@NYG spread/ML/total tags **PASS** (`market_side_disagreement` / `spread_not_play` / `totals_sides_only_launch`).
- **deploy-vercel:** cherry-picked odds+previews (`c25310f9` content) → pushed tip **`6fb2da80`**.

## AFTER (post canary + full re-sim)

| Metric | Value |
| --- | --- |
| `worker_build_id` | `sanity-fix-20260730c-abbr-skip-supervised-w1-4` |
| DAL@NYG model `spread_home` | **−3.07** (NYG −3.07) |
| DAL@NYG market `spread_home` | **+2.6** (NYG +2.6) |
| DAL@NYG `home_win_prob` | 0.5887 |
| DAL@NYG `total_mean` / market | 43.86 / 48.2 |
| DAL@NYG `spread_edge` | −5.57 |
| Publish tags (S/ML/T) | **PASS / PASS / PASS** |
| Side flips vs pre-resim snapshot | **1** (`DEN@PIT` AWAY→HOME on 2026-11-27) |
| Giants heavily favored vs market? | **YES** (still ≤ −3) — **FAIL** vs target “not Giants −3” |
| deploy-vercel SHA | `6fb2da809491cf47a64c031163c6b8500bc2862a` |

**Verdict:** Worker canary is live and publish PASS gate holds, but Celery board numbers for DAL@NYG remain Giants ≈−3 after full re-sim — residual model path still diverges from framework-only recon (~+1.1) and from “not Giants −3” acceptance. Further investigation needed beyond deploy/canary.

## Validation example (DAL @ NYG)

| | Market | Published AFTER re-sim | Framework-only recon | Target |
| --- | --- | --- | --- | --- |
| Home spread | +2.6 | **−3.07** | ~+1.1 | Cowboys side of market / no PLAY on flip |
| Home win prob | ~0.42 (no-vig) | **0.59** | ~0.47 | Near market after conservative blend |
| Spread PLAY | — | **PASS** | — | **PASS** (`market_side_disagreement`) |

## Residual risks

- Supervised model can still pull within the conservative trust region; Week 1–4 market boost mitigates.
- Totals remain sides-only; props research-only.
- Re-enable validated weights only after ≥3 scored REG games per team (automatic).

## Deploy / ops

1. ~~Deploy model-service~~ — done (`bash scripts/deploy-railway-model-service.sh --wait`).
2. ~~Canary worker_build_id~~ — live (`sanity-fix-20260730c-abbr-skip-supervised-w1-4`).
3. ~~Re-sim all fair-lines dates~~ — 37/37 SUCCESS.
4. ~~Ship odds to `deploy-vercel`~~ — tip `6fb2da80`.
5. **Open:** drive DAL@NYG model spread off Giants −3 while canary remains present.
