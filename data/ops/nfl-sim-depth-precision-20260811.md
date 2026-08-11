# NFL Sim Depth + Honest Precision (2026-08-11)

## Doctrine

Do not publish one-decimal certainty the engine did not earn.

## Chosen defaults

| Surface | Default `n` | Rationale |
|---------|-------------|-----------|
| Game Boxes | **2,000** | Meets ≥2k research floor. Cold demo latency ~65s@2k / ~186s@5k → **5k not OK** for interactive cold; ship 2k + cache. |
| Survivor paths | **2,000** | Same floor. Planner + suggest-paths share path pool when safe. |
| Heavy research publish | 50k–100k | Unchanged (CLI / launch bundles). |

Env knobs (model-service):

- `NFL_SEASON_ENGINE_N_GAME_BOX` (default 2000)
- `NFL_SEASON_ENGINE_N_SURVIVOR_PATHS` (default 2000)
- `NFL_SEASON_ENGINE_THIN_DEPTH=1` → thin/dev fallback (50 / 120) labeled **low-depth estimate**
- Cache TTL/size: `NFL_SEASON_ENGINE_GAME_BOX_CACHE_*`, `NFL_SEASON_ENGINE_SURVIVOR_CACHE_*`

## Cache strategy

### Game Boxes

- Process-local TTL LRU keyed by:
  `game_id + universe fingerprint (run_id/snapshot/roster_as_of) + scenario hash (injury paths) + n + seed`
- Never cross-serves games.
- Diagnostics requests bypass cache.
- Edge Board list load does **not** call game-boxes; cold compute stays lazy per matchup on the Game Boxes desk.
- Warm hit should be ms; cold p95 ≈ single-game MC wall time (~60–90s @2k on a laptop demo universe).

### Survivor

- Path pool cache keyed by universe fingerprint + `n_sims` + `seed` + scenario hash.
- Stores win matrix **and** per-path `(week, team)` win pairs so `path_ok` / joint survival can be recomputed for any locked slate without re-simming.
- Planner + suggest-paths share the pool when those keys match (same active run / roster / scenario).

## Display honesty

| Output | Rule |
|--------|------|
| Win % | Whole % when `n < 2000`; 1 decimal only at research depth. Surface `n` / “research depth”. |
| p10–p90 yards | Shown at ≥2k; thin `n` → wider `~mean±` band. |
| TD | **P(TD)** + expected rate (+ fair American when available). Avoid headline median 0 / p90 0.4. |
| Survivor WP | Same depth discipline. |
| Thin/dev | Badge **low-depth estimate**. |

## Latency notes (2026-08-11)

### Real packaged universe (CHI@CAR W1 / survivor plan KC W1)

| Call | n | Cold |
|------|---|------|
| Game Boxes | 50 | ~0.8s |
| Game Boxes | 2,000 | ~30s |
| Game Boxes | 5,000 | ~144s |
| Survivor plan | 120 | ~38s |
| Survivor plan | 2,000 | ~16 min |
| Survivor plan | 5,000 | ~11 min* |

\*5000 finished faster than 2000 in this run (machine load / variance); both are multi-minute cold. Path-pool cache makes warm planner/suggest ms.

### Demo universe (earlier probe)

| Call | n | Cold |
|------|---|------|
| Game Boxes | 2,000 | ~65s |
| Game Boxes | 5,000 | ~186s |
| Survivor plan | 120 | ~52s |

Cold 2k Game Boxes is a desk-wait, not a board-block. BFF `UPSTREAM_TIMEOUT_MS.seasonEngine` = 180s; Next routes `maxDuration = 180`. Survivor interactive UX depends on path-pool reuse after the first cold build.

## Smoke checklist

- [ ] Game Boxes UI shows depth badge (≥2,000 · research depth), not “50 replicates”
- [ ] Survivor planner / week desk not silently on 120; shows research-depth path count
- [ ] Skill player TD cell shows `P(TD) …` + `exp …` (not median/p90 tails as the headline)
- [ ] Repeat same game-boxes request twice → second response `notes.cache=hit`; means identical for fixed seed
- [x] Truth-layer invariants I1–I8 + Week-1 schedule guards green (2026-08-11). `KICKOFF_SMOKE` needs numpy in the local env (unrelated to sim depth).

## Deploy

- Vercel: `deploy-vercel` (web honesty + desk defaults)
- Railway: model-service (defaults, caches, TD enrichment) — required for engine defaults to take effect
