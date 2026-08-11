# Edge Board Week 1 Complete Slate (No Silent Drops) — 2026-08-10

**Branch:** `feat/edge-board-week1-complete` → `deploy-vercel`  
**Baseline tip:** #177 `26454da0` (tag policy)  
**Priority:** P0

## Owns / does not own

| Owns | Does not own |
|------|----------------|
| Week 1 membership = schedule pack (16 REG) | Tag policy / density / sim depth |
| No silent drop when KEI or odds missing | New features |
| Guardrail: `week1_reg_count == schedule_pack` | |

## Ground truth — 2026 REG Week 1 (16)

Source: `services/model-service/.../nfl_regular_schedule_2026.json`  
(= packaged wall chart `apps/web/lib/nfl-wall-chart-2026.schedule.json`)

| # | game_id | away | home | week | season_type |
|---|---------|------|------|------|-------------|
| 1 | 2026-W01-ARI@LAC | ARI | LAC | 1 | REG |
| 2 | 2026-W01-ATL@PIT | ATL | PIT | 1 | REG |
| 3 | 2026-W01-BAL@IND | BAL | IND | 1 | REG |
| 4 | 2026-W01-BUF@HOU | BUF | HOU | 1 | REG |
| 5 | 2026-W01-CHI@CAR | CHI | CAR | 1 | REG |
| 6 | 2026-W01-CLE@JAX | CLE | JAX | 1 | REG |
| 7 | 2026-W01-DAL@NYG | DAL | NYG | 1 | REG |
| 8 | 2026-W01-DEN@KC | DEN | KC | 1 | REG |
| 9 | 2026-W01-GB@MIN | GB | MIN | 1 | REG |
| 10 | 2026-W01-MIA@LV | MIA | LV | 1 | REG |
| 11 | 2026-W01-NE@SEA | NE | SEA | 1 | REG |
| 12 | 2026-W01-NO@DET | NO | DET | 1 | REG |
| 13 | 2026-W01-NYJ@TEN | NYJ | TEN | 1 | REG |
| 14 | 2026-W01-SF@LA | SF | LA/LAR | 1 | REG |
| 15 | 2026-W01-TB@CIN | TB | CIN | 1 | REG |
| 16 | 2026-W01-WAS@PHI | WAS | PHI | 1 | REG |

Live `/edge-board/nfl?slate=week1` (2026-08-10) showed **13** games.

## Three missing games + root cause

| Missing | Root cause (checklist) | Fix |
|---------|------------------------|-----|
| **DAL @ NYG** (`2026-W01-DAL@NYG`) | **(4)/(5)/(7)** Absent from assembled board entirely — fair-lines / projection-backed path is the membership driver; games without a surviving fair-line/KEI row never appear. Local DB also has timezone-skew / Jan-4 twin `games` rows for this matchup (DISTINCT ON risk on prod). Odds not required for membership, but missing KEI previously meant silent drop via `filterNflProjectionBackedRows`. | Schedule-driven `ensureNflScheduleWeekOnBoard` seeds honest empty Spread+Total rows; fair-lines `LEFT JOIN` projections so missing KEI still returns the schedule game. |
| **DEN @ KC** (`2026-W01-DEN@KC`) | Same as DAL@NYG — not on live Week 1 board (0 “Broncos/Chiefs” hits). Dual kickoff rows locally; prod fair-lines join / active-model projection gap drops membership. Not PRE; not week-stamp failure (game never reached the tab). | Same schedule seed + LEFT JOIN. |
| **GB @ MIN** (`2026-W01-GB@MIN`) | Same class — absent from live board; Jan-4 twin game row locally; projection-backed filter / fair-lines INNER JOIN prevented board membership. | Same schedule seed + LEFT JOIN. |

### Checklist results (all three)

1. Not in schedule pack / wrong week — **No** (all three are REG W1 in pack + wall chart)
2. Filtered as PRE — **No**
3. Dropped by team ID map (LA/LAR) — **No** for these three (Melbourne SF@LAR was present). LA↔LAR join hardened anyway for Rams.
4. Missing KEI / fair-lines / projection → excluded — **Yes (primary)**
5. Missing odds → excluded — **Contributing** under projection-backed filter when KEI also absent; **odds must not gate Week 1 membership**
6. Date/timezone window — **Possible contributor** on Railway when DISTINCT ON prefers a past twin outside `include_past_days`
7. Dedup / slate=week1 query bug — **Secondary** (page derives Week 1 from full assemble; membership still fair-lines-driven before this fix)

## Assembly contract (after fix)

- **Schedule pack is the driver**; projections / odds are attributes.
- Week 1 tab count = unique game rows = **16**.
- REG Week 1 with no odds or no KEI still **appears** with `—`.
- PRE still excluded.

## Code

| Area | Change |
|------|--------|
| `apps/web/lib/nfl-edge-board-week.ts` | `listNflRegWeekScheduleGames`, `ensureNflScheduleWeekOnBoard`, `diffNflBoardVsScheduleWeek` |
| `apps/web/lib/build-edge-board-rows.ts` | Ensure Week 1 after stamp (both slates) |
| `apps/web/app/edge-board/[sport]/page.tsx` | Ensure before Week 1 filter (belt-and-suspenders) |
| `services/model-service/.../nfl.py` fair-lines | `LEFT JOIN LATERAL` projections; LA↔LAR team join |
| `scripts/nfl/check_edge_board_week1.py` | Ops/CI guardrail |
| `scripts/nfl/check_nfl_invariants.py` | Wires Week 1 pack count into Truth Layer |

## Guardrail

```bash
python scripts/nfl/check_edge_board_week1.py
# optional live/board snapshot:
python scripts/nfl/check_edge_board_week1.py --board /tmp/week1-rows.json
```

Fails when `week1_reg_count != 16` (pack/wall) or when `--board` is missing any schedule `game_id` (logs each missing id).

## Smoke

1. Week 1 tab shows **16** (incl. DAL@NYG, DEN@KC, GB@MIN — empties OK)
2. Full slate still sane (multi-week + complete W1)
3. PRE never on Week 1
4. Melbourne SF–LAR still Week 1 REG
5. Week stamp from #175 still works when fair-lines omit `week`

## Tests

- `apps/web/__tests__/lib/nfl-edge-board-week.test.ts` — 16-pack, seed 13→16, no KEI required, PRE out
- `python scripts/nfl/check_edge_board_week1.py` (+ invariants suite)
