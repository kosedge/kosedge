# Read-only trace notes — INC-2026-09-08

Captured before code changes. Sources: production model-service `/nfl/fair-lines`, www `/api/nfl/edges-desk`, www `/api/edge-board/{sport}/assemble`.

## ARI @ LAC root cause

| Field | Value | Role |
| --- | ---: | --- |
| `spread_home` / fair | −8.31 | KEI fair (unchanged) |
| `market_spread_home` | −9.5 | Consensus average — **desk Book column** |
| `stake_spread_home` / DK | −10.0 | **Edge SoT** (`spread_edge = fair − stake`) |
| `fd_spread_home` | −9.5 | Stake fallback only |
| `best_spread_home` | −10.0 | Shop / Current column |
| `spread_edge` | +1.69 | vs stake −10, not vs −9.5 |
| Desk display | Fair −8.31 · Book −9.50 · Edge +1.7 | **Arithmetic lie** |

Correct pairing if showing stake edge: Fair −8.31 · Mkt **−10.0** · Edge **+1.7**.  
Correct pairing if showing consensus Book: Fair −8.31 · Mkt −9.5 · Edge **+1.2** (and Action thresholds must use that same market — out of scope to retune thresholds; we paint the calc market).

Known fail-closed until reconcile: do not paint an edge when Fair/Book/Edge disagree.

## BAL @ IND / NYJ @ TEN sign bug

Home-perspective signed edge is negative when model likes Home more than the book (`fair_home − market_home < 0`). Desk mapped that to Side=Home but left `edgeDisplay` signed negative and painted it green.

Canonical Edge Board already uses `Math.abs` + separate favor; desks did not.

## Code pointers (pre-fix)

- `apps/web/lib/nfl-edges.ts` — `deskEdgesFromFairLine` Book=`marketSpreadHome`, signed `edgeDisplay`
- `apps/web/components/pro/nfl/NflEdgesDeskClient.tsx` — always `text-edge-green`
- `services/model-service/.../nfl.py` — `spread_edge` vs `compare_spread_home` / stake close
- `apps/web/lib/flat-rows-to-legacy.ts` — Edge Board abs magnitude (already correct direction)
- `apps/web/lib/mlb-desk-helpers.ts` — same signed total / ML desk pattern
