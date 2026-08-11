# NFL Fix — LAR Power Ratings blank columns — 2026-08-11

Branch: `feat/fix-lar-power-ratings` → `deploy-vercel`  
Also touches model-service intel serialization (Railway).

## Symptom

Los Angeles Rams on `/pro/power-ratings/nfl` showed projected wins (~9.69) but
**—** for Off / Def / Record while every other franchise was populated.

## Root cause (exact key mismatch)

| Layer | Rams key |
|-------|----------|
| Preseason sim / launch bundles (nflverse) | **`LA`** |
| Bundle loader (`nfl-preseason-artifacts`) after Truth Layer #171 | **`LAR`** (canonicalized) |
| Power Ratings `teamNorm` | **`LAR`** |
| Intel `/nfl/intel/standings` + `/stats` DB rows | **`LA`** |
| Power Ratings join (pre-fix) | `Map.get(teamNorm)` with **raw** intel `team` |

Join failed: board looked up **`LAR`**, intel map was keyed **`LA`**.

Blank fields (vs PHI/KC peers):

- `offense` (Off EPA/play)
- `defense` (Def EPA allowed/play)
- `record` (from intel standings wins/losses)

Expected wins / rank stayed filled because they come from the sim bundle, not intel.

Standings page already joined via `canonicalizeNflTeam`; Power Ratings did not.

## Fix

1. **Web** — `enrichNflPowerRatingsWithIntel` indexes standings/stats by
   `canonicalizeNflTeam` before join (same pattern as standings).
2. **Model-service** — `_serialize_intel_rows` emits product **`LAR`**;
   `_intel_storage_team` maps filter `LAR` → DB `LA` so team-scoped intel still hits.
3. Unit tests: `power-ratings-lar-join.test.ts`, intel LA→LAR route helpers.

## Acceptance smoke

- [x] LAR Off/Def/Record join when intel keys `LA`
- [x] Exactly one Rams entry (no LA+LAR duplicate on board)
- [x] I1–I7 / Week 1 schedule pack still green (Σ wins / 32 teams; SF@LAR W1 present)
- [ ] Deploy: confirm live Power Ratings after Vercel + Railway

## Non-goals

No re-ranking; no new model features.
