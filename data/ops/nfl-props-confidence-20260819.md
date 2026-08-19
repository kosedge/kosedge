# NFL props confidence — 2026-08-19

**Part 1:** shipped in [PR #263](https://github.com/kosedge/kosedge/pull/263) (DK/FD PLAY tags; weekly props still gated).  
**Part 2:** diagnosis only. `NFL_WEEKLY_PROPS_LIVE = false`. No residual-only promote.

Machine JSON: `data/ops/nfl-props-confidence-diagnosis.json`  
Cursor rule: `.cursor/rules/nfl-production-spine.mdc` (single spine mandatory).

---

## Go / no-go

| Gate | Result |
|------|--------|
| Beat close **and** actual on holdout (shared frozen dict) | **NO-GO** — rush frozen worsens actual MAE |
| Pass bias toward 0 vs frozen (−12.4) | Candidate helps (−6.6) but residual-only |
| Season pool insane (32×4k QB) | **Not that shape** on 2025 baseline sums (max ~3.8k; 0 QBs ≥4k) |
| Spine coherent fantasy↔props | **NO** — five drift points below |
| **NFL_WEEKLY_PROPS_LIVE** | **false** |

**Recommendation:** structural fix first (team pass/rush budgets + usage shares), then one shared cal re-fit. Do **not** swap frozen intercepts alone.

---

## Spine drift (fantasy ≠ props today)

| ID | Surface | Production path | Frozen prop-cal-v1? |
|----|---------|-----------------|---------------------|
| D1 | Weekly props board | baseline ⊕ box MC blend → `apply_prop_calibration` → edges | **Yes** |
| D2 | Fantasy weekly | raw `nfl_player_projection_baselines` → fantasy points | **No** |
| D3 | Fantasy season / draft | `SUM(weekly baselines)` | **No** |
| D4 | Season box-score sims | aggregate game box sims | **No** |
| D5 | Season engine / futures budgets | `nfl_season_engine` + offensive stack | **No** (separate conservation) |

Hard product rule: fix means once; fantasy / props / futures inherit. Promoting “props live” without D2–D3 reading the same means would fake confidence.

---

## Holdout table (2025) — raw / frozen / candidate

MAE; residual = pred − target (negative = undershoot).

| Market | n | Raw vs close | Frozen vs close | Cand vs close | Raw vs actual | Frozen vs actual | Cand vs actual | Frozen intercept | Cand intercept |
|--------|---|--------------|-----------------|---------------|---------------|------------------|----------------|------------------|----------------|
| pass_yds | 431 | 51.0 / −34.1 | **22.5** / −15.4 | 20.6 / −9.6 | 65.5 / −31.1 | **53.5** / **−12.4** | 52.9 / −6.6 | −8.5 | +6.1 |
| rush_yds | 1291 | 11.5 / −1.5 | **9.9** / +1.8 | 9.7 / −1.0 | **16.27** / −4.6 | **16.48** / −1.3 | 16.18 / −4.0 | +3.6 | +0.2 |
| rec_yds | 2663 | 13.3 / −7.4 | **10.3** / −4.4 | 10.6 / −5.8 | 17.2 / −11.1 | **16.5** / −8.1 | 16.6 / −9.6 | +1.6 | −0.3 |
| receptions | 2595 | 1.29 / −0.52 | **1.10** / −0.36 | 1.14 / −0.48 | 1.14 / −0.58 | **1.09** / −0.41 | 1.12 / −0.54 | +0.12 | −0.02 |

**Locked failure mode:** rush frozen beats close but **regresses vs actual** (16.48 > 16.27). Shared cal dict cannot ship a pass-only intercept swap.

---

## Bucket bias (root layer)

### Pass yards by close

| Close bucket | n | Frozen MAE vs actual | Frozen residual vs actual |
|--------------|---|----------------------|---------------------------|
| 0–224 | 249 | 51.9 | −6.2 |
| **225–274** | **180** | **55.8** | **−20.6** |
| 275+ | 2 | n too small | — |

Starter-ish pass lines (225–275) are where volume is most wrong. That points at **team pass budget / QB script**, not a flat intercept.

### Rush by role (team rush-attempt rank)

| Role | n | Frozen MAE vs actual | Frozen residual |
|------|---|----------------------|-----------------|
| RB1 | 424 | **25.1** | −6.8 |
| Committee / RB2+ | 770 | 13.1 | +0.9 |

RB1 undershoot is the structural rush problem; committee is closer to flat.

### Rec yards by target tier (same-game targets)

| Tier | n | Frozen MAE vs actual | Frozen residual |
|------|---|----------------------|-----------------|
| 8+ targets | 434 | **33.5** | **−26.5** |
| 5–7 targets | 661 | 18.6 | −12.2 |
| &lt;5 targets | 1568 | 10.9 | −1.2 |

High-target receivers are crushed — **usage share / team pass volume**, not residual cal.

---

## Season pool coherence (2025 baseline sums)

Source: `SUM(pass_yards_mean)` from `nfl_player_projection_baselines` (same path fantasy draft uses).

| Check | Value |
|-------|-------|
| QB n | 78 |
| Median season pass yards | 1172 |
| P90 | 3398 |
| Max | 3760 (Stafford, 20 game-rows) |
| QBs ≥ 4000 | **0** |
| Team \|QB pass − skill rec\| / QB pass (mean) | **0.28** |

Not a “32 QBs at 4k” blow-up on this table. Still broken conservation: ~28% pass↔rec gap, and season rows can exceed 17 games. Season engine (D5) is a **second** pool — futures must not invent a third.

---

## Structural vs residual-only

| Option | Verdict |
|--------|---------|
| Residual-only (swap frozen intercepts / pass-only +6.1) | **Reject** — shared dict; rush fails actual gate; high-target WR / RB1 / 225–275 pass still structural |
| Structural (budgets → usage → shared means → one cal) | **Pursue** — then re-grade close+actual+pool |

Next fix order (when you greenlight):

1. Unify weekly props board means with fantasy (same post-budget player-game vector; cal is a thin shared layer).
2. Lift team pass volume / QB script so 225–275 and 8+ target WR residuals move toward 0 **before** intercept retune.
3. RB1 rush share / committee split.
4. Re-fit **one** cal; require every core market: close not worse, actual not worse, rush not regress.
5. Only then consider `NFL_WEEKLY_PROPS_LIVE = true` with research→fire framing.

---

## Explicit non-goals (still)

- Loosen PLAY 2.5–7
- Flip props live on close-MAE alone
- Path-v5 / 1H / SB models as props substitutes
