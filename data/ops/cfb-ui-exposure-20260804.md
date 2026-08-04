# CFB Season Engine — First UI Exposure + Projection Tightening

**Date:** 2026-08-04  
**Engine:** `cfb-season-engine-v0.5.1-ui`  
**Branch:** `feat/cfb-projection-ui` → `deploy-vercel`  
**Status:** First Pro UI surface + measured project-game coherence tweaks. Additive vs NFL engine and CFB Edge Board markets-only.

## URLs

| Surface | Path |
| --- | --- |
| Season Model hub | `/pro/cfb/model` |
| Project Game | `/pro/cfb/project-game` |
| BFF status | `GET /api/cfb/season-engine/status` |
| BFF project-game | `POST /api/cfb/season-engine/project-game` |
| BFF simulate (capped) | `POST /api/cfb/season-engine/simulate` |
| Upstream (Railway) | `GET/POST /cfb/season-engine/{status,project-game,simulate}` |

Browser never holds `INTERNAL_API_SECRET` — Next.js BFF proxies like NFL season-engine desks.

## What the model can do

- Compose roster strength + QB situation + position groups → O/D indices
- Project a game: expected scores → coherent spread / total / win probs
- Expose drivers: roster, QB class/index, OL/skill/F7/secondary, variable HFA, coaching flags
- Surface early-season uncertainty (W1–W4 wider margin SD + identity flags)
- Thin power-style ladder from packaged indices (status)
- Path-coherent season sim (API/CLI; web proxy capped ≤50 sims)

## What it cannot do (yet)

- Official full 2026 FBS schedule (densified approximate paths)
- Live portal / recruiting / returning-production DB feeds
- Live home ATS / coaching-change feeds
- Market-grade KEI fair lines on Edge Board (CFB stays **markets-only**)
- Player box production path / CFP bracket
- Calibrated SP+/PFF-class unit grades

## Projection tightening (v0.5 → v0.5.1)

Measured knobs only — not a modeling rewrite.

| Knob | v0.5 | v0.5.1 | Why |
| --- | --- | --- | --- |
| `WIN_PROB_MARGIN_SD` | 16.5 | 14.5 | Mid-season WP tracks spread more naturally (~−8.5 ≈ 71%) |
| `MATCHUP_RESPONSE` | 1.05 | 1.08 | Slightly clearer peer separation after early soften |
| `MATCHUP_RATIO_CLAMP` + retain | none | (0.60, 1.32) + 40% excess | Soft-cap placeholder blowouts; keep ordering |
| Early separation soften W1–W4 | 0.68→0.93 | 0.74→0.95 | Slightly less collapsed early favorites |

**Before/after samples (packaged, same seed universe):**

| Matchup | Metric | v0.5 | v0.5.1 |
| --- | --- | --- | --- |
| CLEM@UGA W1 | spread / home WP / margin_sd | −4.49 / 57.5% / 23.7 | −4.56 / 58.7% / 20.8 |
| CLEM@UGA W5 | spread / home WP / margin_sd | −4.78 / 61.0% / 17.2 | −4.80 / 62.5% / 15.1 |
| MICH@OSU W5 | spread / home WP / margin_sd | −8.37 / 68.1% / 17.8 | −8.49 / 70.7% / 15.6 |
| UGA vs BALL W5 | spread | −29.9 | −30.9 (soft-clamped; raw would be wider at new response) |

Score/spread/total coherence unchanged: `spread=away−home`, `total=home+away`, `wp_home+wp_away=1`.

## Honesty labels in UI

- Fidelity badges: **approximate**
- Early-season banner when `uncertainty.active`
- Explicit “Edge Board markets-only unchanged”
- Can / approximate / cannot lists from status `solid_vs_approximate`

## Tests

- `services/model-service/tests/test_cfb_season_engine.py` (version, clamp, coherence, status ladder)
- `apps/web/__tests__/lib/cfb-season-engine-format.test.ts`
- `apps/web/__tests__/api/cfb/season-engine-project-game.test.ts`
- Nav: CFB primary includes Season Model + Project Game; other sports unchanged

## Deploy notes

1. Merge to `deploy-vercel` → Vercel web + Railway model-service (engine bump)
2. Verify `https://www.kosedge.com/pro/cfb/model` and `/pro/cfb/project-game`
3. Verify Railway `GET /cfb/season-engine/status` → `cfb-season-engine-v0.5.1-ui`
4. Confirm `/edge-board/cfb` still markets-only (no KEI invent)
