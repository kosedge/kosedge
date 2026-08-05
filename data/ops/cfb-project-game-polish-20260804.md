# CFB Project Game — Polished Market Outputs

**Date:** 2026-08-04  
**Engine (unchanged):** `cfb-season-engine-v0.6.1-calibration`  
**Branch:** `feat/cfb-project-game-polish` → `deploy-vercel`  
**Scope:** UI presentation polish on calibrated project-game. No new modeling layers. Edge Board CFB stays markets-only.

## URLs

| Surface | Path |
| --- | --- |
| Project Game | `/pro/cfb/project-game` |
| Season Model hub | `/pro/cfb/model` |
| BFF project-game | `POST /api/cfb/season-engine/project-game` |

## What improved

1. **Hero market card** — Away @ Home, projected score (Away – Home), favorite-worded spread (`OSU -5.1`), total, home WP, and American ML on both sides (derived from WP, no vig).
2. **Driver chips** — Compact roster / QB name+class / OL / Skill / F7 / Sec / HFA / coaching rows instead of dense definition lists.
3. **Uncertainty banner** — W1–W4 active flag + effective margin SD called out as wider / directional; mid-season quieter.
4. **Fidelity honesty** — Approximate badge retained; explicit “not calibrated attribution” + Edge Board markets-only footnote.
5. **Formatting helpers** — `formatFavoriteSpread`, `americanOddsFromWinProb`, `formatAmericanOdds`, `formatProjectedScoreLine` with unit tests.

## Example clean projection (packaged universe)

**MICH @ OSU · Week 1** (`cfb-season-engine-v0.6.1-calibration`)

| Field | Value |
| --- | --- |
| Projected score | 31.9 – 36.9 (Away – Home) |
| Spread | **OSU -5.1** (home line −5.1) |
| Total | 68.8 |
| Home WP / ML | 59.6% / **−148** |
| Away WP / ML | 40.4% / **+148** |
| Margin SD | ~20.9 (early-season active) |
| Coherence | spread = away − home; total = home + away; WP sums to 1 |

Drivers (illustrative): roster / QB name+class / unit grades / HFA bucket+pts on home / coaching continuity adj — scannable chips, not a wall of text.

## Gaps remaining

- Full official 2026 FBS slate still densified/approximate on some paths
- Returning snap% / portal-out still proxies; coaching & HFA curated
- ML is fair WP→American only (no book vig / no Edge Board KEI invent)
- Unit grades not SP+/PFF-class calibrated
- Season simulate stays API-capped; no CFP bracket UI
- Railway must already serve v0.6.1 for live numbers; this PR is web presentation

## Tests

- `apps/web/__tests__/lib/cfb-season-engine-format.test.ts` — spread wording + American odds
- Existing BFF project-game proxy tests unchanged

## Deploy notes

1. Merge to `deploy-vercel` → Vercel web
2. Verify `https://www.kosedge.com/pro/cfb/project-game` shows market card + driver chips
3. Confirm early-week banner when week ≤ 4
4. Confirm `/edge-board/cfb` still markets-only
5. Engine version string remains `cfb-season-engine-v0.6.1-calibration` (UI-only bump)
