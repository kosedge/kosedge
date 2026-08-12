# NFL Fantasy + Survivor product fixes

Date: 2026-08-12  
Branch: `feat/nfl-fantasy-survivor-product-fixes` → `deploy-vercel`  
Doctrine: Working controls > new features. Honest empty > fake K/DST. No reach CTAs beyond ±12 vs ADP.

## Root causes

### Fantasy player dropdown / Add

Builder had **no player picker**. Search lived on Rankings/Value only; on the Builder tab the search box was a no-op (filtered rows were not rendered). Position filters were `<Link>`s to `/pro/nfl/fantasy`, so Builder users got dumped off the page. “Add to builder” required hunting the rankings table.

**Fix:** searchable `PlayerCombobox` on Builder (and Rankings). Position filters are client-side buttons. Rankings loads the full board and filters in the client. Select → Add to builder → Remove works on desktop and mobile.

### Survivor pick control

Three stacked issues:

1. Plan request used `topN: 6`, so matchup rows (and, if `available_teams` was missing, the picker itself) only covered the top lean — not any remaining team.
2. Native `<select>` showed team codes only; matchup (opponent + %) was on chips, not in the dropdown.
3. Mobile sticky grade bar (`z-30` under the pro header) sat on top of week pickers — same class of tap-eater as prior sticky-header bugs.

**Fix:** `topN = 32` (`NFL_SURVIVOR_PLAN_TOP_N`). Custom week picker lists every remaining team with matchup before lock. Used + available lists at the top. Sticky overlay removed. Duplicate teams dropped client-side (`normalizeSurvivorPlanPicks` / `lockWeek` moves the team) and rejected by the Next API (`duplicateSurvivorPlanTeams` → 400) plus model-service `normalize_plan_picks`.

## K/DST

**Still blocked. No invented rows.**

| Path | Status |
|------|--------|
| Preseason bundle `playerTotalsRegular` | QB / RB / WR / TE only (`load-desk` fallback filters to those four) |
| `GET /nfl/fantasy/draft-rankings` | Empty in preseason → fallback board; no named K/DST |
| Engine kicker layer (`v1.27-kicker-layer`) | Game Boxes FG/XP only — not fantasy K rankings |
| `nfl_kicker_dst_projections` | Exists in model-service; **not materialized into the fantasy desk / preseason bundle** |

Unblock: materialize named K/DST into `/nfl/fantasy/draft-rankings` (and the preseason player-totals pack). Until then the amber banner is the product: mocks skip those slots; grades do not ding missing K/DST.

## ±12 recommendation policy

`MAX_RECOMMEND_RANK_DELTA = 12` in `apps/web/lib/fantasy/value-aware-recs.ts`.

Wired in:

- Mock + Builder suggestion rails (`computeTiming` / `bestAvailableByValueAware` / `bestAvailableByNeedAware`)
- Expert blurbs + value notes (`shouldSoftFrameAdpGap`)
- Positional cliff copy (`tierCliffNote`) — no “take X before the drop” when \|model−ADP\| > 12

Value Δ and **High deviation** flags still display large gaps. CTAs do not say take-now / must-wait / take a round early past the cap.

## Smoke checklist

- [ ] Fantasy player dropdown / Add works (search, select, add, remove, position filter)
- [ ] K/DST present **or** honest unavailable banner only (current: banner)
- [ ] No recommend reach >12 spots vs ADP
- [ ] Survivor pick any available team for the week
- [ ] Used + available lists at top
- [ ] Cannot double-pick a team (client + API 400 + engine)
- [ ] Mobile survivor pick works (no sticky overlay on the picker)
