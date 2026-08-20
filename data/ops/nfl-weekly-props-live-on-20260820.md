# NFL weekly props LIVE on — 2026-08-20

**Flag:** `NFL_WEEKLY_PROPS_LIVE = true`  
**Spine:** `player-production-v3-phase3c`  
**Rollback:** set `NFL_WEEKLY_PROPS_LIVE = false` in `apps/web/lib/nfl-weekly-props-live.ts` and ship.

Smoke-2 pointer: `data/ops/nfl-spine-live-smoke-2-20260820.md` (A1–A4 green).  
Gap honesty: `data/ops/nfl-spine-2026-gap-20260820.md`.

## What LIVE means

- Weekly `/pro/nfl/props` loads model **means + floor/ceiling bands**.
- Edge vs market when a book is joined; blank “no mkt” otherwise.
- Same weekly means as fantasy. Season desk = SUM cap 17.
- Research→fire for numbers. Entitlement / `OPEN_ACCESS_PREVIEW` unchanged.

## What LIVE does **not** mean

- Not a CLV-proven props book.
- **No PLAY / LEAN / stake tags** on the props board (`PLAY_STAKE_ELIGIBLE` stays false).
- Not a claim that 2026 receiving is 3C-tight.
- Not profitability / lock language.

## 2026 honesty line

2026 preseason receiving totals are **elevated vs pass** (roster-width hydrate/rookie intercepts; cap-17 gap **0.417**). 2025 control remains 3C: max **4590** / n≥4000 **4** / gap **0.097**. Methods copy on the props page states this.

## Product rules shipped with the flag

1. Means + bands in the table.
2. No PLAY/WATCH tag tabs or tag column.
3. Visible methods footnote (spine, cap 17, 2026 grain, no stake tags).
4. Empty week = honest empty banner, not fake rows.
5. Disclaimer unchanged.

## Smoke LIVE (post-Vercel)

Guest/preview path uses existing Pro / `OPEN_ACCESS_PREVIEW` rules — no new checkout.

| Check | Expect |
|-------|--------|
| `/pro/nfl/props` | 200, **no** “not live — season desk only” gate |
| Board | rows or honest empty; floor/ceiling columns; **no** PLAY chrome |
| Methods | 2026 elevated-gap sentence present |
| `/pro/nfl/fantasy` | SUM rankings (McCaffrey-class, 17g); not bundle-only |
| Degraded banners | none (false) |
| Worker | `default` empty of week-22 poison after web deploy (Railway image already hygiene) |
