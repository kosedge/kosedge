# Edge Board Tag Policy (PLAY / LEAN / PASS + Play-To) — 2026-08-11

**Branch:** `feat/edge-board-tag-policy` → `deploy-vercel` (+ Railway for model-service)  
**Baseline tip:** `deploy-vercel` after #179 (`8ca3594d`)  
**Updates:** #177 tag policy (`26454da0`) — Week 1–2 side/total point bands only

## Doctrine

> We bet prices, not teams.  
> Tags are mechanical. Edge magnitude and confidence stay separate — never one mysterious score.

## Contract (unchanged from #177)

| Layer | Meaning |
|-------|---------|
| **Model** | Research fair — no PLAY from Model alone |
| **KEI** | Published handicap — **Fair for tags** |
| **Edge / Tag** | **KEI vs best available market only** |
| **Play-To** | Derived from KEI + week threshold policy |

Does **not** rewrite KEI factor stack, sim depth, kicker layer, Week 1 membership/density, or books.

## Labels

`PASS` · `LEAN` · `PLAY` · `BEST VALUE` · `ALERT` · `STAY AWAY`

Do **not** use “Best Bet” = biggest discrepancy only. `BEST VALUE` requires strict gates (large edge + HIGH confidence + price + clear inputs + matchup + liquidity).

## Config (single module)

| Runtime | Path |
|---------|------|
| Python | `services/model-service/src/services/nfl_tag_policy.py` |
| TypeScript | `apps/web/lib/nfl-tag-policy.ts` |

Consumed by `nfl_decision_engine` / `nfl-decision-engine.ts`. Do not duplicate bands in UI.

### Sides — Week 1–2 (2026-08-11)

| \|KEI − market\| (pts) | Grade |
|------------------------|-------|
| < 1.25 | PASS |
| 1.25 – 1.75 | LEAN |
| 2.25 – 2.75 | PLAY |
| 3.25+ | Strong candidate + confidence |

Gaps (1.75–2.25, 2.75–3.25) keep the lower grade (LEAN / PLAY). Config: `EARLY_SIDE` = `pass_max=1.25`, `lean_max=1.75`, `play_min=2.25`, `strong_min=3.25`.

### Sides — midseason baseline (Week 3+)

| \|KEI − market\| (pts) | Grade |
|------------------------|-------|
| < 1.0 | PASS |
| 1.0 – 1.5 | LEAN |
| 2.0 – 2.5 | PLAY |
| 3.0+ | PLAY candidate → confidence check; may be BEST VALUE or ALERT |

Unchanged from #177 (`STANDARD_SIDE` / `INSEASON_SIDE`).

### Totals — Week 1–2 (2026-08-11)

| \|KEI − market\| (pts) | Grade |
|------------------------|-------|
| < 1.75 | PASS |
| 1.75 – 2.25 | LEAN |
| 2.75 – 3.25 | PLAY |
| 3.75+ | Strong candidate + confidence |

`WEEK1_TOTAL_BOOST = +0.25` on each baseline band → `EARLY_TOTAL` 1.75 / 2.25 / 2.75 / 3.75.

### Totals — midseason baseline (Week 3+)

| \|KEI − market\| (pts) | Grade |
|------------------------|-------|
| < 1.5 | PASS |
| 1.5 – 2.0 | LEAN |
| 2.5 – 3.0 | PLAY |
| 3.5+ | strong + confidence |

Unchanged from #177 (`BASELINE_TOTAL`).

### Cover probability (−110) — unchanged

| Cover % | Grade |
|---------|-------|
| < 53% | PASS |
| 53–54% | LEAN |
| 54–56% | PLAY |
| 56–58% | strong / BEST VALUE only with high confidence |
| 58%+ | exceptional — force confidence + sanity |
| 60%+ vs mature markets | ops/log flag (`model_warning`) |

When both point edge and cover prob exist: **cover prob wins for the tag**; both are shown. Market past play-to still caps cover-inflated PLAY tags on refresh.

## Confidence ALERT rules (unchanged)

Large edge + messy injuries/weather/new OC → `ALERT`, not auto `PLAY`.

`PLAY` requires all three:

1. Numerical edge (point and/or cover grade)
2. Confidence not Low / not ALERT-level unresolved
3. Price still available at play-to

## Play-to ladder (unchanged formula)

**Sides:** Let KEI = fair home spread, T = week side thresholds.

Remaining edge at home price H is `|KEI − H|`.

- `play_to` (home) = price where remaining edge = `T.play_min` → `KEI + sign·play_min`
- `lean_to` = remaining edge = `T.lean_max`
- `pass_from` = remaining edge = `T.pass_max`

Away display numbers are `−home`.

Example (week 8): KEI home +6 / market +3 (BUF −3) → Play BUF to −4 · lean −4.5 · pass −5.

**Totals:** same remaining-edge idea with total thresholds (`WEEK1_TOTAL_BOOST` in early regime).

Market past play-to → tag downgrades on refresh (re-grade + explicit past-play-to cap).

Same game, four prices → four decisions — UI shows tag from **current**.

## Model-never-alone-PLAY (unchanged)

Model fair alone never produces `PLAY`. Tags use KEI vs market only.

## What changed vs #177 / 2026-08-10 ops

| Band | #177 (2026-08-10) | This brief (2026-08-11) |
|------|-------------------|-------------------------|
| W1–2 sides PASS / LEAN / PLAY / strong | 1.5 / 2.0 / 2.5 / 3.5 | **1.25 / 1.75 / 2.25 / 3.25** |
| W1–2 totals PASS / LEAN / PLAY / strong | 2.0 / 2.5 / 3.0 / 4.0 (`+0.5` boost) | **1.75 / 2.25 / 2.75 / 3.75** (`+0.25` boost) |
| Midseason sides & totals | unchanged | unchanged |
| Cover / confidence / play-to / Model contract | unchanged | unchanged |

## UI

Action cell shows:

- Tag (current)
- Edge pts (+ cover % when available)
- Confidence (separate)
- Fair KEI · Market current
- Play to / Lean to when not PASS

Methods one-liner: Tag = KEI vs market · Play-to on current. Thresholds come only from `nfl-tag-policy` — no magic numbers in UI.

## Wire points

1. Config: `nfl_tag_policy.py` / `nfl-tag-policy.ts`
2. Engine: `nfl_decision_engine.py` / `nfl-decision-engine.ts`
3. Fair-lines API: `GET /nfl/fair-lines` — tags use KEI fair (`spread_home` / `total_mean`)
4. Board assemble: `nfl-edge-board-from-fair-lines.ts`
5. UI: `EdgeBoard.tsx` ActionDecisionCell
6. Tests: `test_nfl_decision_engine.py`, `nfl-decision-engine.test.ts`

## Smoke notes

1. Three rows on `/edge-board/nfl` show Tag + Play-to / Lean-to (not PASS) with Fair KEI · Mkt.
2. Week 1 tab: 2.0-pt side edge = LEAN (not PLAY); 2.25-pt side = PLAY; 1.24-pt side = PASS.
3. Move market past play-to → refresh downgrades PLAY → LEAN/PASS.
4. Low confidence + big edge → ALERT, not PLAY.

## Non-goals

Rewriting KEI factors, sim depth, kicker layer, Week 1 membership/density polish, new books.
