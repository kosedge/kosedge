# NFL Week 1 desk agreement — one production spine (2026-09-02)

**PR target:** `deploy-vercel` (do not merge from agent — CoS merges)  
**Branch:** `cursor/nfl-week1-spine-agreement-3bf4`

## Problem

Week 1 surfaces disagreed: Props spine mean vs Game Boxes MC median (Maye 216.2 vs 160), KEI Lines still wrote SF→LA same-coast / LA weather while Edge Board already had Melbourne, Edges Lean hardcoded Over on abs-tie, QB Anytime TD included pass TDs, blank-line fair juice, stuck Aug 21 as-of, Kyler Murray on GB@MIN.

## Fixes in this PR

| # | Fix |
|---|-----|
| 1 | Game Boxes overlays `nfl_player_projection_baselines` means onto `point_estimate`; UI prefers mean over p50. Same spine version as Props (`player-production-v3-phase3c`). |
| 2 | Fair-lines Gate B passes Week 1 `game_card` from canonical venue (Melbourne Cricket Ground). International chips replace same-coast / SoFi weather strings. |
| 3 | Odds overlay no longer overwrites canonical kickoff (NE@SEA stays 8:20 ET). |
| 4 | Edge Board `linesAsOf` prefers board stamp when odds snapshot is >6h stale (no more stuck 2026-08-21 display). |
| 5 | Edges Lean follows positive edge side / model−line (Holani Under). |
| 6 | QB Anytime TD = rush TDs only (not pass). |
| 7 | Props nulls fair O/U when Line blank; UI shows —. |
| 8 | Depth SoT: Kyler→ARI1, McCarthy→MIN1 (GB@MIN attribution). |

## Flagged (P3, not fixed)

**B.Robinson ADP dual on ATL** — abbreviated `B.Robinson` can collide Bijan (ADP 2) vs Brian (rank ~174). Matcher already refuses ambiguous `initial_last` when length≠1; remaining risk is identity in depth pack / sportsdata_id. Left for a follow-up identity pass.

## Rematerialize after merge

Props anytime TD + blank fair juice need a Week 1 props rematerialize on Railway (`/nfl/ops/rebuild-props-layers` weeks 1–18). Game Boxes overlay reads baselines live. Depth pack ships with the web/model deploy.
