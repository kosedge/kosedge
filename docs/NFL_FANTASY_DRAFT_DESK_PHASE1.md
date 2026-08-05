# NFL Fantasy Draft Desk — Phase 1

Premium season-long draft experience powered by the KosEdge NFL season /
player projection stack. **Not** a disconnected consensus board.

## Product surfaces

| Route | Purpose |
| --- | --- |
| `/pro/nfl/fantasy` | Rankings desk — format toggle, position filters, value board, player card |
| `/pro/nfl/fantasy/builder` | Manual team builder (add/remove, needs, grade, suggestions) |
| `/pro/nfl/fantasy/mock` | Phase 2 snake mock draft room (10/12, CPU, post-draft grade) |
| `/pro/nfl/fantasy/player/[playerId]` | Player detail — drivers, expert blurb, schedule/risk |

## Data flow

1. **Primary:** `GET /nfl/fantasy/draft-rankings` on model-service  
   Materialized from `nfl_player_projection_baselines` season totals →  
   `fantasy_points_from_projection` × Standard/Half-PPR/PPR → VOR ranking.
2. **Floor / median / ceiling:** Materializer stores bands in  
   `projection_payload` from baseline `floor_outcome` / `ceiling_outcome`  
   (yards/receptions) + scaled TD means (same 0.60 / 1.35 convention as weekly fantasy).
3. **Fallback:** If the API is empty/unreachable, the web desk builds a board  
   from the latest `nfl-preseason-sim-2026-*` player totals (skill positions only).
4. **Market ADP:** FantasyPros consensus ADP (format-aware STD/HALF/PPR) via  
   partners feed + snapshot fallback. See `docs/NFL_FANTASY_DRAFT_DESK_ADP.md`.
5. **Schedule context:** Opponent expected wins for weeks 1–6 vs 14–17 from  
   packaged 2026 schedule + preseason team outcomes.
6. **Risk flags:** Depth chart (W1 packaged) + backfield share pressure from  
   projected rush yards. No live injury feed on Phase 1.

## Fantasy Expert voice

Template-driven, sharp blurbs in `apps/web/lib/fantasy/expert.ts` for:

- model-vs-ADP gaps  
- tier / value cliffs  
- concise player drivers  

Ready to swap to an LLM-backed voice later without changing the desk contract.

## Scoring

Canonical conversion (mirrors `fantasy_points_from_projection`):

- Pass: 1 / 25 yd, 4 / TD  
- Rush / rec: 1 / 10 yd, 6 / TD  
- Receptions: 0 / 0.5 / 1.0 by Standard / Half-PPR / PPR  

Overall board order uses **Value Over Replacement** (not raw points) so  
single-QB drafts do not stack the top with mediocre QBs. K/DST append to  
board end (real ADP convention).

## Known limitations (honest)

- ADP is FantasyPros consensus (platform mix), not a single draft room — unmatched players show ADP as —.  
- Floor/ceiling on fallback boards use position-aware bands when quantiles  
  are absent.  
- Schedule softness is a simple opponent-wins signal, not full matchup sim.  
- Risk flags are concise; availability is not a medical grade.  
- Team builder is **manual** — no 12-team CPU mock room yet (Phase 2).  
- Preseason fallback omits K/DST.

## Phase 2

Mock draft room: see `docs/NFL_FANTASY_DRAFT_DESK_PHASE2_MOCK.md`.

Further hooks:

- Richer schedule SOS from season-engine opponent defense indices  
- Live injury / availability overlay  
- Optional second ADP source merge (Sleeper/Yahoo) if needed  
- Live league sync / auction / Superflex (explicitly later)

## Key files

- `apps/web/lib/fantasy/*` — scoring, VOR, ADP, schedule, risk, expert, loader, team builder  
- `apps/web/components/pro/nfl/fantasy/FantasyDraftDeskClient.tsx`  
- `services/model-service/src/services/nfl_fantasy_draft_rankings.py`  
- `services/model-service/src/tasks.py` (`materialize_nfl_fantasy_season_draft_rankings`)  
- `services/model-service/src/routes/nfl.py` (`/nfl/fantasy/draft-rankings`)  
