# Edge Board Current market restore — 2026-08-23

**Branch:** `cursor/edge-current-market-restore-e929` → `deploy-vercel`  
**Baseline:** post-#286 (`0ce06b6`)  
**Scope:** restore numeric **Current** on `/edge-board/nfl` Week 1. No KEI/spine/fantasy. No new Odds plan.

## Root cause

Live Odds is dead on every key the stack already has. Railway `ODDS_API_KEY` returns **401 DEACTIVATED_KEY**; the embedded backup (same key the web overlay always tries) returns **401 OUT_OF_USAGE_CREDITS** (500/500). Fair-lines therefore ships `odds_feed_status=degraded`, `market_joined_count=0`, and null `market_*` / `best_*`. The Vercel overlay (`pullOddsRows` → `overlayOddsOntoFairLineRows`) hits the same 401s and overlays nothing. #284 already made Action follow Current when Current exists; it cannot paint a number the overlay never receives. Opens were never the break — `odds_snapshots` still hold first-capture Open for all 16 Week 1 games. Current simply had no live feed **and** did not read the latest owned snapshot.

## Fix (minimal)

When the live Odds pull is empty/401, fair-lines fills **Current** from the **latest-per-book** `odds_snapshots` consensus (`ORDER BY captured_at DESC`). Open stays first capture (`ASC`). The merge helper never copies `open_*` into Current; missing Current stays `—` even if Open exists. Diagnostics: `snapshot_current_count`, `current_source=odds_snapshots|live|mixed`. Odds API keys are redacted from `odds_feed_error`.

Web mapping is unchanged: `row.best` = Current from fair-lines `best_*` / `market_*`; Action = KEI vs that Current (#284). Overlay still wins when a live key works again.

## Before → after (Week 1 REG, live Railway 2026-08-23)

Live `/nfl/fair-lines?season=2026&days_ahead=200` before this deploy:

| | Current (mkt/best) | Open | Action vs market |
|--|--|--|--|
| **Before** | **0 / 16** (all `—`) | **16 / 16** | Edge **0.0** · Mkt **—** |
| **After (sim, latest snapshot)** | **16 / 16** numeric | **16 / 16** unchanged | KEI vs Current (not 0.0) |

Open values did not move. Copy-Open test: `copied_open_any = false`.

| Game | Open spr | Current spr (latest snap) | Open tot | Current tot | Action edge | Mkt | Action |
|------|----------|---------------------------|----------|-------------|-------------|-----|--------|
| ARI@LAC | -10.5 | -10.5 | 46.5 | 46.5 | 1.54 | -10.5 | LEAN |
| ATL@PIT | -3.0 | -3.0 | 41.5 | 41.5 | 0.21 | -3.0 | PASS |
| BAL@IND | 3.5 | 3.5 | 48.5 | 48.5 | 1.09 | 3.5 | PASS |
| BUF@HOU | 1.5 | 1.5 | 44.5 | 44.5 | 0.82 | 1.5 | PASS |
| CHI@CAR | 2.5 | 2.5 | 45.5 | 45.5 | 0.8 | 2.5 | PASS |
| CLE@JAX | -7.5 | -7.5 | 40.5 | 40.5 | 0.64 | -7.5 | PASS |
| DAL@NYG | 2.5 | 2.5 | 48.5 | 48.5 | 0.62 | 2.5 | PASS |
| DEN@KC | -3.0 | -3.0 | 42.5 | 42.5 | 0.41 | -3.0 | PASS |
| GB@MIN | -1.5 | -1.5 | 45.5 | 45.5 | 1.86 | -1.5 | LEAN |
| MIA@LV | -3.5 | -3.5 | 40.5 | 40.5 | 0.32 | -3.5 | PASS |
| **NE@SEA** | **-3.5** | **-3.5** | **44.5** | **44.5** | **0.72** | **-3.5** | **PASS** |
| NO@DET | -7.0 | -7.0 | 49.5 | 49.5 | 0.51 | -7.0 | PASS |
| NYJ@TEN | -2.5 | -2.5 | 38.5 | 38.5 | 0.47 | -2.5 | PASS |
| SF@LAR | -3.5 | -3.5 | 48.5 | 48.5 | 0.35 | -3.5 | PASS |
| TB@CIN | -3.5 | -3.5 | 52.5 | 52.5 | 0.83 | -3.5 | PASS |
| WAS@PHI | -4.5 | -4.5 | 47.5 | 47.5 | 1.6 | -4.5 | LEAN |

NE@SEA: KEI −4.22 vs Current −3.5 → Action **Edge 0.72 · Mkt −3.5** (was Edge 0.0 · Mkt —). PASS is correct (Week 1 band). Total Action Edge 1.17 vs o44.5.

Current equals Open on this slate because the last owned persist is the same 2026-08-21 capture that set Open (`odds_captured_at=2026-08-21T13:42:55Z`). That is latest-quote Current, not an Open→Current backfill. When a newer snapshot (or a working live key) lands, Current will move and Open will not.

## Remaining gaps

- Live The Odds API is still 401 on the configured + embedded keys. Current will not tick until a working key is provisioned (out of scope: no new paid plan). Snapshot Current is as-of last persist (21 Aug).
- If a game has **no** `odds_snapshots` row, Current stays **—** (honest empty). All 16 Week 1 games currently have snapshots.
- Mkt shop books (DK/FD juice / best-of-books) stay thin on the snapshot path until live Odds returns; consensus Current is enough for Action.
- Re-smoke production `/edge-board/nfl` after Railway picks up this model-service change.

## Smell tests

1. Majority of Week 1 games show numeric Current if snapshots/feed have them → **16/16** on owned snaps.
2. NE@SEA no longer Current — → **−3.5 / 44.5**.
3. Action moves with Current (0.72 vs −3.5), no Edge 0.0 vs null market.
4. No market → — ; Open is never copied into Current.
