# NFL Model Sanity Fix Report

**Date:** 2026-07-30 / 2026-07-31  
**Branch:** `nfl-second-order-edge`  
**Symptom (example, not a special-case):** DAL @ NYG — market NYG +2.6 / DAL −152, model `spread_home` −3.07, `home_win_prob` 0.59, spread+ML **PLAY**.

## Root cause

Not HFA alone and not a single-game bug. Layered failure:

1. **Validated supervised blend unlocked on a not-yet-played season** (fixed earlier canaries). Preseason hydration made EPA look week-varying → 85% supervised spread.

2. **Matchup pack lookup used full team names** while packs are keyed by abbr → week null → early-season supervised skips never fired (fixed in `5625391d`).

3. **Residual after supervised skip (this pass):** Celery market blend silently no-oped because `odds_snapshots` were keyed to a *parallel* Odds-API `games` UUID, not the schedule `game_id`. Probe proved:
   - pack hit, week=1, supervised skipped, OOD dampened, pack-aligned indices correct
   - `market_spread_home=null` → `market_blend.spread_applied=false`
   - framework margin stayed ~+1.5 from HFA over EPA → published Giants −1.65 / −3.07 historically

4. **Secondary:** season-max-week hydrated priors / KAV / injury nowcasts could fight week-1 pack EPA when market blend was absent.

## Fixes shipped (on `nfl-second-order-edge`)

| Change | File | Effect |
| --- | --- | --- |
| Real-features gate requires ≥3 **past-dated** scored REG games **and** EPA variance | `nfl_supervised_retrain.py` | Blocks validated weights until in-sample season |
| Ignore `fit_payload["blending"]` on conservative path | `nfl_supervised_retrain.py` | Stops saved 0.85 weights from leaking back in |
| Matchup pack lookup uses **team abbr** | `tasks.py` / `routes/nfl.py` | Week/features actually load |
| Skip supervised for unplayed seasons + weeks 1–4 | `tasks.py` | No OOD supervised margin on early board |
| Pack-aligned strength priors from matchup EPA | `tasks.py` | Base indices match game week, not week-18 hydrate |
| Prior-season priors when season unplayed | `tasks.py` | Avoids season-max-week OOD priors |
| Dampen KAV / second-order / injury / tuning before REG games | `tasks.py` | Removes OOD margin tilt |
| Early-season market side-disagreement blend boost | `nfl_simulator.py` | Extra market weight when sides disagree in W1–4 |
| **Live Odds API consensus fallback by abbr** | `tasks.py` | Market blend fires even when snapshot `game_id` mismatches |
| DB odds fallback by team+date (typed params) | `tasks.py` | Secondary path for parallel game rows |
| `worker_build_id` + `sanity_probe` in sim task result | `tasks.py` | Prove build + inspect blend/gates |
| PLAY blocked on market side disagreement | `nfl_side_total_publish_policy.py` | Already live on API |

## Live status

- **Railway deploy:** SUCCESS (api + worker + beat).
- **Canary:** `worker_build_id=sanity-fix-20260730i-live-odds-blend` (**LIVE**).
- **Full re-sim:** **37/37 SUCCESS**, same `worker_build_id`.
- **API publish gate:** LIVE.

## AFTER (post `…i-live-odds-blend` + full re-sim)

| Metric | Value |
| --- | --- |
| `worker_build_id` | `sanity-fix-20260730i-live-odds-blend` |
| DAL@NYG model `spread_home` | **+1.88** (NYG +1.88 dog) |
| DAL@NYG market `spread_home` | **+2.5** |
| DAL@NYG `home_win_prob` | 0.441 |
| DAL@NYG `total_mean` / market | 47.24 / 48.25 |
| DAL@NYG `|model−market|` | **0.62** (≤1.5 ✓) |
| Publish tags (S/ML/T) | **PASS** (`edge_below_band` / related) |
| Sanity probe (Sept 13 re-sim) | pack hit, supervised skipped, live market 2.5, blend weight 0.85 (disagreement boost) |
| Market side disagreements (≥1.5) | **7** (was 26 on pre-fix board) |
| Model side flips vs pre-full-resim snapshot | 20 (mostly HOME→AWAY corrections toward market dogs) |
| Within 1.5 pts of market | **126 / 168** |
| Giants heavily favored vs market? | **NO** — **PASS** |

## Validation example (DAL @ NYG)

| | Market | BEFORE (canary c) | AFTER (canary i) | Target |
| --- | --- | --- | --- | --- |
| Home spread | +2.5 / +2.6 | **−3.07** | **+1.88** | Near market / dog-side |
| Home win prob | ~0.42 | **0.59** | **0.441** | Near market |
| Spread PLAY | — | PASS (`market_side_disagreement`) | **PASS** (`edge_below_band`) | PASS |

## Residual risks

- Odds API pull at sim-start costs credits; DB snapshot join by schedule `game_id` should still be healed long-term (dedupe parallel games).
- Totals remain sides-only; props research-only.
- Re-enable validated supervised weights only after ≥3 past-dated REG games per team (automatic).

## Deploy / ops

1. ~~Deploy model-service~~ — done (`bash scripts/deploy-railway-model-service.sh --wait`).
2. ~~Canary worker_build_id~~ — live (`sanity-fix-20260730i-live-odds-blend`).
3. ~~Re-sim all fair-lines dates~~ — 37/37 SUCCESS.
4. Helper: `scripts/nfl/resim-fair-lines-dates.sh`.
