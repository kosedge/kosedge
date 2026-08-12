# NFL Player Futures columns — 2026-08-11

Doctrine: every player-future row shows **Projected · Current (YTD) · Current odds** in that order. No orphan markets. No prior-season stats dressed as Current.

## Current conventions

| Row kind | Current cell | Rationale |
|----------|--------------|-----------|
| Counting (yards / rec / TDs / team wins) | **0** before Week 1 REG | 2026 YTD only; preseason smoke must not be empty or 2025 |
| Award-only (MVP / OPOY) | **—** | No fake “award progress”; documented as `AWARD_CURRENT_CONVENTION = "emdash"` |
| Missing odds | **—** | Never invent |

Quiet UI hint on surfaces: `Current = 2026 YTD (0 before Week 1)`.

## Surfaces updated

| Surface | Route | Columns |
|---------|-------|---------|
| Awards | `/pro/nfl/awards` | # · Player · Team · **Award Score** (0–100 index, not %) · Current (—) · Current odds · Note |
| Futures · Player | `/pro/nfl/projections?tab=player` | # · Player · Tm · Pos · Projected · Current (0) · Current odds — race via yards/TDs/receptions |
| Futures · Team | `/pro/nfl/projections?tab=team` | Wins use Projected · Current (0) · odds (—); SB odds joined when available |
| Player Previews awards | `/pro/nfl/player-previews` | Same Projected · Current · Current odds on MVP/OPOY tables |

Shared UI: `components/pro/nfl/PlayerFutureTripleColumns.tsx`  
Shared formatters: `lib/nfl-player-futures.ts`  
Odds join: `lib/nfl-futures-odds.ts`

## Odds coverage status (2026-08-11)

| Market | Join | Status |
|--------|------|--------|
| Super Bowl winner (team) | Odds API `americanfootball_nfl_super_bowl_winner` outrights → best American | Best-effort; as-of when present |
| MVP / OPOY player futures | — | **Not in Odds API** → Current odds **—** |
| Yardage / TD / reception leaders | — | **Not in Odds API** → Current odds **—** |
| Team win totals | — | No win-total outright key → Wins odds **—** |

Honest footnote on Futures/Awards when odds load: player award/leader futures omitted from API, not stubbed with fake prices.

Railway: **not required** for this PR — web best-effort Odds API + existing award/projection loaders.

## Smoke checklist

```bash
# Unit: Current = 0 counting / — award / odds never invented
pnpm --filter @kosedge/web exec vitest run __tests__/lib/nfl-player-futures.test.ts

# Pages (auth/paywall follows existing Pro patterns)
curl -sS -o /dev/null -w "%{http_code} awards\n" http://127.0.0.1:3000/pro/nfl/awards
curl -sS -o /dev/null -w "%{http_code} futures-player\n" "http://127.0.0.1:3000/pro/nfl/projections?tab=player"
curl -sS -o /dev/null -w "%{http_code} futures-team\n" "http://127.0.0.1:3000/pro/nfl/projections?tab=team"
curl -sS -o /dev/null -w "%{http_code} player-previews\n" http://127.0.0.1:3000/pro/nfl/player-previews
```

Manual UI checks:

- [ ] Awards desktop: Projected / Current / Current odds headers; Current = **—**; odds = **—** (or price if API ever adds markets)
- [ ] Awards mobile cards: same three fields
- [ ] Futures player races (yards / TDs / rec): Current cells are **0** preseason, not empty / not 2025
- [ ] Futures team Wins Current = **0**; SB odds column populated when Odds API key works
- [ ] Lineage / source line visible when projections shown
- [ ] Tooltip / hint: `Current = 2026 YTD (0 before Week 1)`

## Non-goals (unchanged)

Full in-season stats warehouse, new award models, prop engine, Edge Board tag policy, fake odds/YTD.
