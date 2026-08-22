# NFL 100k + K/DST launch — 2026-08-21 / 2026-08-22 UTC

**Branch:** `feat/nfl-100k-kdst-launch` → `deploy-vercel`  
**Brief:** Week-1 research republish. No model rewrite. Odds 401 / missing opens out of scope.

## Identity

| | |
|--|--|
| Engine | `nfl-season-engine-v1.27-kicker-layer` |
| Lock | `nfl-season-engine-2026-preseason-lock` |
| Identity | `nfl-season-engine-2026-preseason-lock · N_team=100000 · 2026-08-22` |
| N_team | **100,000** |
| N_player | **1,000** (383 named skill rows) |
| Seed | `20260821` |
| Snapshot | `nfl-depth-2026-w1-20260813T120000Z` |
| Web bundle | `nfl-preseason-sim-2026-20260822T013711Z` |
| Research | `data/ops/nfl-season-engine-launch-nfl-season-engine-v1.27-kicker-layer-Nteam100000-Nplayer1000-20260822T004326Z` |
| HD | `/Volumes/KosEdgeData/clean/nfl/research/` (same names) |

## Runtime

| Phase | Seconds | Notes |
|-------|--------:|-------|
| Team W/L | 2253.1 | 7 workers, packaged 272-game slate |
| Player full | 971.7 | single process, path-coherent |
| Survivor derive | 0.0 | from team week matrix, week 1 |
| Wall | ~53.7 min | |

Σ mean wins = **271.9999** (target 272). Truth Layer I1–I8 + Week-1 pack 16 + kickoff smoke **PASS**. Preseason release gate **PASS** (Walker KC 1172 rush; 8 QBs ≥4000; min pass yards on the QB pool 86 — backups; QB1 min **2826.5**).

## K/DST

Artifact: `data/ops/artifacts/nfl-kdst-season-2026.json`  
Source: `player-production-v3-phase3c-100k`

| | Count |
|--|------:|
| Named kickers | **32** (roster primary K; no invented names) |
| DST teams | **32** |
| Artifact gaps | **none** |

FG/XP volume from `kicker_layer.kicking_points_for_season_production` using player-path offensive TDs (pass+rush). FG attempts sit on the layer’s league prior (~31.45); XP scales with team TDs. DST counting rates from `nfl_dp_team_defense_weekly` (same history remat uses). Yahoo-ish `fantasy_points` on the file so the Fantasy desk can merge if Railway ranks are still skill-only.

Local remat `materialize_nfl_fantasy_season_draft_rankings(season=2026)`:

```
players=908 kickers=32 dst_teams=32 rows_upserted=2916
kdst_publish.status=ready
```

**Railway remat** is required after this PR deploys model-service (artifact is in git so the worker can load it):

```
POST /nfl/ops/materialize-fantasy-draft-rankings?season=2026
```

Web also merges K/DST from the artifact when the API board has no K/DST rows (no silent empty if the file shipped). Value tab / ADP behavior unchanged.

## Smell tests

| Check | Result |
|-------|--------|
| Σ wins | **271.9999** (272) |
| Kickoffs | Canonical pack unchanged: NE@SEA **8:20 PM ET**, SF@LAR **8:35 PM ET** (Melbourne). Gate `KICKOFF_SMOKE` 5/5. |
| Fantasy | ADP + Value Δ unchanged. **32 K + 32 DST** on artifact; local draft ranks rematted. Railway remat is the remaining live-desk step. |
| Power / Survivor | Pointer `nfl-preseason-sim-2026-20260822T013711Z`; identity includes N_team=100000 + 2026-08-22. Short strip only (existing launch-research notice). Survivor week-1 eval derived from the 100k matrix. |
| QB1 shape | **Not 32×4000.** 8 QB1s ≥4000 yards; QB1 min 2826.5. Gate `qb_pass_shape` PASS (8/96 ≥4000). |
| Top wins vs 20260813 launch | LAR 11.071 (−0.014), SEA 10.808 (+0.015), DET 10.686 (−0.027), DEN 10.506 (−0.002), PHI 10.348 (+0.024). Largest |Δ| is 0.027 — seed/path noise, not a rewrite. |
| Edge | Untouched. Week-1 pack **16** games. Honest `open=missing` stays `—` (DAL@NYG, DEN@KC, NE@SEA, SF@LAR). |

## Residual gaps

- **Railway** draft-rankings remat after deploy (local already has 32/32).
- Odds API 401 / Current — (feed/secrets) — not this pass.
- Four Week-1 opens still missing; do not invent `open=current`.
- Interactive / Railway HTTP sim caps remain ≤500 (labeled).
- 2026 receiving grain vs pass (~0.42) unchanged; 2025 3C control still the tight board.
- Kicker FG volume is kicker_layer approximate (league attempt prior + TD-driven XP), not a new ST model.

## Non-goals (held)

Odds secrets, inventing opens, new model layers, nav trim, DFS, KEI policy, Production Gate vitest wiring.

Leave the spine alone until real games or the next intel pass.
