# Edge Board Tag Policy (PLAY / LEAN / PASS + Play-To) — 2026-08-10

**Branch:** `feat/edge-board-tag-policy` → `deploy-vercel`  
**Baseline tip:** #176 polish align `0eab57b4`  
**Extends:** #159 decision engine (`nfl_decision_engine`)

## Doctrine

> We bet prices, not teams.  
> Tags are mechanical. Edge magnitude and confidence stay separate — never one mysterious score.

## Contract (unchanged)

| Layer | Meaning |
|-------|---------|
| **Model** | Research fair — no PLAY from Model alone |
| **KEI** | Published handicap — **Fair for tags** |
| **Edge / Tag** | **KEI vs best available market only** |
| **Play-To** | Derived from KEI + week threshold policy |

Does **not** rewrite KEI factor stack, sim depth, kicker layer, or books.

## Labels

`PASS` · `LEAN` · `PLAY` · `BEST VALUE` · `ALERT` · `STAY AWAY`

Do **not** use “Best Bet” = biggest discrepancy only. `BEST VALUE` requires strict gates (large edge + HIGH confidence + price + clear inputs + matchup + liquidity).

## Config (single module)

| Runtime | Path |
|---------|------|
| Python | `services/model-service/src/services/nfl_tag_policy.py` |
| TypeScript | `apps/web/lib/nfl-tag-policy.ts` |

Consumed by `nfl_decision_engine` / `nfl-decision-engine.ts`. Do not duplicate bands.

### Sides — midseason baseline (after Week 2)

| \|KEI − market\| (pts) | Grade |
|------------------------|-------|
| < 1.0 | PASS |
| 1.0 – 1.5 | LEAN |
| 2.0 – 2.5 | PLAY |
| 3.0+ | PLAY candidate → confidence check; may be BEST VALUE or ALERT |

### Sides — Week 1–2 (tighter)

| \|KEI − market\| | Grade |
|------------------|-------|
| < 1.5 | PASS |
| 1.5 – 2.0 | LEAN |
| 2.5 – 3.0 | PLAY |
| 3.5+ | strong candidate |

Week from schedule pack. After Week 2 → baseline.

### Totals — baseline

| \|KEI − market\| | Grade |
|------------------|-------|
| < 1.5 | PASS |
| 1.5 – 2.0 | LEAN |
| 2.5 – 3.0 | PLAY |
| 3.5+ | strong + confidence |

Week 1–2: `WEEK1_TOTAL_BOOST = +0.5` on each band.

### Cover probability (−110)

| Cover % | Grade |
|---------|-------|
| < 53% | PASS |
| 53–54% | LEAN |
| 54–56% | PLAY |
| 56–58% | strong / BEST VALUE only with high confidence |
| 58%+ | exceptional — force confidence + sanity |
| 60%+ vs mature markets | ops/log flag (`model_warning`) |

When both point edge and cover prob exist: **cover prob wins for the tag**; both are shown. Market past play-to still caps cover-inflated PLAY tags on refresh.

## Confidence (separate field)

Large edge + messy injuries/weather/new OC → `ALERT`, not auto `PLAY`.

`PLAY` requires all three:

1. Numerical edge (point and/or cover grade)
2. Confidence not Low / not ALERT-level unresolved
3. Price still available at play-to

## Play-to formula

**Sides:** Let KEI = fair home spread, T = week side thresholds.

Remaining edge at home price H is `|KEI − H|`.

- `play_to` (home) = price where remaining edge = `T.play_min` → `KEI + sign·play_min` (sign from KEI toward market)
- `lean_to` = remaining edge = `T.lean_max`
- `pass_from` = remaining edge = `T.pass_max`

Away display numbers are `−home`.

Example (week 8): KEI home +6 / market +3 (BUF −3) → Play BUF to −4 · lean −4.5 · pass −5.

**Totals:** same remaining-edge idea with total thresholds (week1 boost applied in early regime).

Market past play-to → tag downgrades on refresh (re-grade + explicit past-play-to cap).

Same game, four prices → four decisions — UI shows tag from **current**.

## UI

Action cell shows:

- Tag (current)
- Edge pts (+ cover % when available)
- Confidence (separate)
- Fair KEI · Market current
- Play to / Lean to when not PASS

Methods one-liner: Tag = KEI vs market · Play-to on current.

## Wire points

1. Config: `nfl_tag_policy.py` / `nfl-tag-policy.ts`
2. Engine: `nfl_decision_engine.py` / `nfl-decision-engine.ts`
3. Fair-lines API: `GET /nfl/fair-lines` — tags use KEI fair (`spread_home` / `total_mean`)
4. Board assemble: `nfl-edge-board-from-fair-lines.ts`
5. UI: `EdgeBoard.tsx` ActionDecisionCell
6. Tests: `test_nfl_decision_engine.py`, `nfl-decision-engine.test.ts`

## Smoke notes

1. Three rows on `/edge-board/nfl` show Tag + Play-to / Lean-to (not PASS) with Fair KEI · Mkt.
2. Week 1 tab uses tighter bands (e.g. 2.0-pt side edge = LEAN, not PLAY).
3. Move market past play-to → refresh downgrades PLAY → LEAN/PASS.
4. Low confidence + big edge → ALERT, not PLAY.

## Non-goals

Rewriting KEI factors, sim depth, kicker layer, new books.
